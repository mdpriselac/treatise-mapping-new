# Uploads

Lets anyone signed in with a Google account upload a paper and get its citation profile,
scored exactly like the corpus. The PDF is never kept. Design notes:
[Upload Feature: Design](https://claude.ai/artifact/ByLwuGvR14jix2kvs7Uhpk).

| Part | What it is | Where |
| --- | --- | --- |
| `job/` | Cloud Run Job `upload-parse`: checks and cleans the PDF (pikepdf), triages it, parses with docling, finds and checks citations (the `pipeline/` code), builds the profile, deletes the PDF | Service account `upload-job@`, 4 CPU / 8 GiB, egress through VPC `upload-egress` with no internet (Private Google Access only) |
| `api/` | Cloud Run service `upload-api` (FastAPI): Google sign-in check, rate limits, signed upload URLs, starting the job, progress, profiles, uploader edits, contributions and admin review | Service account `upload-api@` |
| Bucket | `gs://treatise-mapping-new-uploads`, PDFs in flight under `incoming/` | One-day delete rule; CORS for the site's origin |
| Firestore | Collection `uploads`, one document per upload | TTL policy on `expires` (30 days; removed when a contribution is approved) |
| Site | `/upload/` and `/upload/view/` pages | `PUBLIC_UPLOAD_API`, `PUBLIC_GOOGLE_CLIENT_ID` in `site/.env.production` |

Limits: 25 MB, 400 pages, 1 upload a minute and 5 per half hour per Google account, 50 a day
site-wide, 150 model checks per upload.

## Reference data

The job and API score against `job/reference/reference.json` (core passages, per-paragraph
citation rates, the theme model, corpus papers' chapter profiles). Rebuild it whenever the
corpus is re-scored, then rebuild both images:

```bash
pipeline/.venv/bin/python pipeline/themes.py 4
pipeline/.venv/bin/python pipeline/build_reference.py
```

## Tests

```bash
pipeline/.venv/bin/python -m pytest -q upload/tests      # safety checks
TM_WORKSPACE=... pipeline/.venv/bin/python upload/job/try_local.py <pdf> [--no-model]   # compare with the corpus
```

## Deploy

```bash
P=treatise-mapping-new; R=us-central1; REG=$R-docker.pkg.dev/$P/cloud-run-source-deploy
gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin https://$R-docker.pkg.dev
# job
docker buildx build --platform linux/amd64 -f upload/job/Dockerfile -t $REG/upload-job:$(git rev-parse --short HEAD) --load . \
  && docker push $REG/upload-job:$(git rev-parse --short HEAD)
gcloud run jobs update upload-parse --image $REG/upload-job:$(git rev-parse --short HEAD) --region $R --project $P
# api
docker buildx build --platform linux/amd64 -f upload/api/Dockerfile -t $REG/upload-api:$(git rev-parse --short HEAD) --load . \
  && docker push $REG/upload-api:$(git rev-parse --short HEAD)
gcloud run deploy upload-api --image $REG/upload-api:$(git rev-parse --short HEAD) --region $R --project $P
```

The job image bakes in docling's models at build time (`warmup.py`), because it runs without
internet access.
