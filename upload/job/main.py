"""Cloud Run Job entry point: process one upload.

Env: UPLOAD_ID (Firestore doc id in `uploads`), UPLOAD_BUCKET. The API creates the doc and
the job reads gs://$UPLOAD_BUCKET/incoming/$UPLOAD_ID.pdf. Every step updates doc.status and
doc.steps so the page can show progress. The PDF is deleted in all cases, and the extracted
text only ever lives in memory and a temp file removed straight after parsing.
"""
import os
import sys
import tempfile
import time
import traceback

from google.cloud import firestore, storage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uploadprof as P  # noqa: E402

UPLOAD_ID = os.environ["UPLOAD_ID"]
BUCKET = os.environ["UPLOAD_BUCKET"]

db = firestore.Client()
doc = db.collection("uploads").document(UPLOAD_ID)
blob = storage.Client().bucket(BUCKET).blob(f"incoming/{UPLOAD_ID}.pdf")


def step(name, detail=""):
    print(f"[{UPLOAD_ID}] {name}: {detail}", flush=True)
    doc.update({"status": name, "steps": firestore.ArrayUnion([{"name": name, "detail": detail, "at": time.time()}])})


def main():
    try:
        step("checking", "Checking the file")
        data = blob.download_as_bytes()
        clean = P.check_and_clean(data)
        del data
        tri = P.triage(clean)
        doc.update({"triage": tri})
        step("parsing", f"{tri['pages']} pages, " + ("scanned, reading with OCR" if tri["ocr"] else "text layer present")
             + f", about {tri['estimate_seconds']} seconds")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(clean)
            tmp.flush()
            md = P.to_markdown(tmp.name, tri["ocr"])
        del clean
        step("citations", "Finding citations to the Treatise")
        cites = P.find_citations(md, progress=lambda m: step("citations", m))
        del md
        step("profile", "Comparing with the corpus")
        prof = P.build_profile(cites)
        doc.update({"profile": prof, "citations": cites, "status": "done", "finished": time.time()})
        step("done", f"{prof['cites']} citations found")
    except P.Rejected as e:
        doc.update({"status": "rejected", "error": str(e), "finished": time.time()})
    except Exception:
        traceback.print_exc()
        doc.update({"status": "failed", "error": "Something went wrong while processing the file.", "finished": time.time()})
    finally:
        try:
            blob.delete()
        except Exception:
            pass  # already gone; the bucket's one-day rule is the backstop


if __name__ == "__main__":
    main()
