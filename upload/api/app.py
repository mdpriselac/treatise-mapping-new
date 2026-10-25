"""Upload API: Google sign-in, rate limits, signed upload URLs, job start, progress and profiles.

Env: GOOGLE_CLIENT_ID (OAuth web client), UPLOAD_BUCKET, JOB_NAME (projects/…/locations/…/jobs/…),
SITE_ORIGIN (CORS), ADMIN_EMAILS (comma-separated; can review contributions),
API_SERVICE_ACCOUNT (signs upload URLs).
"""
import datetime as dt
import os
import re
import secrets
import time

import google.auth
from google.auth.transport import requests as grequests
from google.cloud import firestore, run_v2, storage
from google.oauth2 import id_token
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from profile_measures import build_profile

CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
BUCKET = os.environ["UPLOAD_BUCKET"]
JOB_NAME = os.environ["JOB_NAME"]
SITE_ORIGIN = os.environ.get("SITE_ORIGIN", "https://treatise-mapping-project-new.outsidethevillage.com")
ADMINS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}
SA_EMAIL = os.environ.get("API_SERVICE_ACCOUNT", "")

MAX_BYTES = 25 * 1024 * 1024
PER_MINUTE, PER_HALF_HOUR, PER_DAY_SITE = 1, 5, 50
PROFILE_DAYS = 30

app = FastAPI(title="Treatise Mapping uploads", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=[SITE_ORIGIN], allow_methods=["GET", "POST", "PATCH"],
                   allow_headers=["Authorization", "Content-Type"], max_age=600)
db = firestore.Client()
uploads = db.collection("uploads")
gcs = storage.Client()
jobs = run_v2.JobsClient()
_req = grequests.Request()


# ---------------------------------------------------------------- auth
def user(authorization: str = Header(default="")) -> str:
    """Any verified Google account. Returns the lower-cased email."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in with Google first.")
    try:
        info = id_token.verify_oauth2_token(authorization[7:], _req, CLIENT_ID)
    except Exception:
        raise HTTPException(401, "Your sign-in has expired; please sign in again.")
    if not info.get("email_verified"):
        raise HTTPException(403, "That Google account's email isn't verified.")
    return info["email"].lower()


def owned(upload_id: str, email: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,64}", upload_id):
        raise HTTPException(404, "No such upload.")
    snap = uploads.document(upload_id).get()
    if not snap.exists or (snap.get("owner") != email and email not in ADMINS):
        raise HTTPException(404, "No such upload.")
    return snap


# ---------------------------------------------------------------- create
class NewUpload(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    author: str = Field(min_length=2, max_length=200)
    date: str = Field(pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$")   # 2009, 2009-05 or 2009-05-14
    size: int = Field(gt=0, le=MAX_BYTES)


def _count_since(field, value, seconds):
    since = time.time() - seconds
    q = uploads.where(filter=firestore.FieldFilter("created", ">=", since))
    if field:
        q = q.where(filter=firestore.FieldFilter(field, "==", value))
    return q.count().get()[0][0].value


@app.post("/api/uploads")
def create(body: NewUpload, email: str = Depends(user)):
    if _count_since("owner", email, 60) >= PER_MINUTE:
        raise HTTPException(429, "One upload a minute, please. Try again shortly.")
    if _count_since("owner", email, 1800) >= PER_HALF_HOUR:
        raise HTTPException(429, "You've reached 5 uploads in half an hour. Please try again later.")
    if _count_since(None, None, 86400) >= PER_DAY_SITE:
        raise HTTPException(429, "The site has reached today's upload limit. Please try again tomorrow.")
    upload_id = secrets.token_urlsafe(18)
    now = time.time()
    uploads.document(upload_id).set({
        "owner": email, "title": body.title.strip(), "author": body.author.strip(), "date": body.date,
        "status": "awaiting_file", "steps": [], "created": now,
        "expires": dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=PROFILE_DAYS),  # Firestore TTL field
        "contribution": None,
    })
    creds, _ = google.auth.default()
    creds.refresh(_req)
    url = gcs.bucket(BUCKET).blob(f"incoming/{upload_id}.pdf").generate_signed_url(
        version="v4", expiration=dt.timedelta(minutes=15), method="PUT", content_type="application/pdf",
        headers={"x-goog-content-length-range": f"0,{MAX_BYTES}"},
        service_account_email=SA_EMAIL or getattr(creds, "service_account_email", None),
        access_token=creds.token)
    return {"id": upload_id, "uploadUrl": url,
            "uploadHeaders": {"Content-Type": "application/pdf", "x-goog-content-length-range": f"0,{MAX_BYTES}"}}


@app.post("/api/uploads/{upload_id}/start")
def start(upload_id: str, email: str = Depends(user)):
    snap = owned(upload_id, email)
    if snap.get("status") != "awaiting_file":
        raise HTTPException(409, "This upload has already started.")
    blob = gcs.bucket(BUCKET).get_blob(f"incoming/{upload_id}.pdf")
    if blob is None:
        raise HTTPException(400, "The file hasn't arrived yet.")
    if blob.size > MAX_BYTES:
        blob.delete()
        raise HTTPException(400, "The file is over 25 MB.")
    jobs.run_job(request=run_v2.RunJobRequest(name=JOB_NAME, overrides=run_v2.RunJobRequest.Overrides(
        container_overrides=[run_v2.RunJobRequest.Overrides.ContainerOverride(
            env=[run_v2.EnvVar(name="UPLOAD_ID", value=upload_id)])])))
    uploads.document(upload_id).update({"status": "queued"})
    return {"status": "queued"}


# ---------------------------------------------------------------- read
PUBLIC_FIELDS = ("title", "author", "date", "status", "steps", "triage", "profile", "citations",
                 "error", "excluded", "contribution", "created", "finished")


@app.get("/api/uploads/{upload_id}")
def get(upload_id: str, email: str = Depends(user)):
    d = owned(upload_id, email).to_dict()
    out = {k: d.get(k) for k in PUBLIC_FIELDS}
    out["id"] = upload_id
    out["expires"] = d["expires"].isoformat() if d.get("expires") else None
    return out


@app.get("/api/my-uploads")
def mine(email: str = Depends(user)):
    q = uploads.where(filter=firestore.FieldFilter("owner", "==", email)).order_by(
        "created", direction=firestore.Query.DESCENDING).limit(50)
    return [{"id": s.id, **{k: s.get(k) for k in ("title", "author", "date", "status", "created")}} for s in q.stream()]


# ---------------------------------------------------------------- uploader edits
class Exclusions(BaseModel):
    excluded: list[int] = Field(default_factory=list, max_length=5000)


@app.patch("/api/uploads/{upload_id}/citations")
def exclude(upload_id: str, body: Exclusions, email: str = Depends(user)):
    """Untick citations that look wrong; the profile is re-scored without them."""
    snap = owned(upload_id, email)
    if snap.get("status") != "done":
        raise HTTPException(409, "The profile isn't ready yet.")
    cites = snap.get("citations") or []
    ex = sorted({i for i in body.excluded if 0 <= i < len(cites)})
    prof = build_profile([c for i, c in enumerate(cites) if i not in set(ex)])
    uploads.document(upload_id).update({"excluded": ex, "profile": prof})
    return {"excluded": ex, "profile": prof}


@app.post("/api/uploads/{upload_id}/contribute")
def contribute(upload_id: str, email: str = Depends(user)):
    """Offer this profile to the public corpus. It joins only after an admin approves it."""
    snap = owned(upload_id, email)
    if snap.get("status") != "done":
        raise HTTPException(409, "The profile isn't ready yet.")
    uploads.document(upload_id).update({"contribution": "pending", "offered": time.time()})
    return {"contribution": "pending"}


# ---------------------------------------------------------------- admin
def admin(email: str = Depends(user)) -> str:
    if email not in ADMINS:
        raise HTTPException(403, "Admins only.")
    return email


@app.get("/api/admin/contributions")
def pending(_: str = Depends(admin)):
    q = uploads.where(filter=firestore.FieldFilter("contribution", "==", "pending"))
    return [{"id": s.id, **{k: s.get(k) for k in ("title", "author", "date", "owner", "profile")}} for s in q.stream()]


class Decision(BaseModel):
    approve: bool


@app.post("/api/admin/contributions/{upload_id}")
def decide(upload_id: str, body: Decision, email: str = Depends(admin)):
    owned(upload_id, email)
    update = {"contribution": "approved" if body.approve else "declined", "decided_by": email, "decided": time.time()}
    if body.approve:
        update["expires"] = firestore.DELETE_FIELD   # approved profiles don't expire
    uploads.document(upload_id).update(update)
    return {"contribution": update["contribution"]}


@app.get("/api/health")
def health():
    return {"ok": True}
