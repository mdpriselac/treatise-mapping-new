# Treatise Mapping

Which passages of Hume's *Treatise of Human Nature* does the secondary literature on personal identity cite, and
which papers find their way to passages the rest of the literature passes by?

[![ci](https://github.com/mdpriselac/treatise-mapping-new/actions/workflows/ci.yml/badge.svg)](https://github.com/mdpriselac/treatise-mapping-new/actions/workflows/ci.yml)

This is the modern version of the project, served at
<https://treatise-mapping-project-new.outsidethevillage.com>. The original 2020 site is archived, unchanged, at
<https://treatise-mapping-project-ur.outsidethevillage.com> from [its own repository](https://github.com/mdpriselac/Hume-on-Personal-Identity). The two deploy
independently. [2020 vs 2026](docs/2020-vs-2026.md) compares them: what the old pipeline missed, what
changed in the measures, and who did what.

## What is in this repo

| Path | What |
| --- | --- |
| `pipeline/` | The corpus pipeline (docling, citation detection and checks, scoring, measures) and `build_data.py`, which exports the site's data |
| `site/src/data/` | The exported, derived data the site is built from |
| `site/` | Astro static site, Observable Plot charts, Pagefind search |
| `Dockerfile`, `deploy/nginx.conf` | Static container for Cloud Run |

Only derived data is committed: citation locations, paragraph weights, scores, the short snippet of text around
each citation, and bibliographic records. Paper PDFs and full texts stay in the private corpus workspace and are
never added here.

## Rebuilding the data

The pipeline that converts PDFs (docling), detects and checks citations, and scores papers is in
[`pipeline/`](pipeline/README.md). It reads and writes a private corpus workspace that never enters
this repo. Its last step exports the derived data here:

```bash
export TM_WORKSPACE=/path/to/corpus-workspace
export TM_TREATISE="$TM_WORKSPACE/Full Treatise in HTML.txt"
pipeline/.venv/bin/python pipeline/build_data.py \
  --lab "$TM_WORKSPACE" --treatise "$TM_TREATISE" \
  --runtime ../Hume-on-Personal-Identity/data/runtime
```

The detector and scorer tests need none of this: `cd pipeline && python -m pytest -q tests`.

## Running the site

```bash
cd site
npm ci
npm run build    # astro build, then the Pagefind search index
npm run preview
```

## Deploying

A static container on Cloud Run, running as a service account with no roles. Build the image for
amd64, push it to Artifact Registry, and deploy it:

```bash
PROJECT=your-gcp-project REGION=us-central1 SERVICE=treatise-new
TAG=$(git rev-parse --short HEAD)
IMG=$REGION-docker.pkg.dev/$PROJECT/cloud-run-source-deploy/$SERVICE:$TAG
gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin https://$REGION-docker.pkg.dev
docker buildx build --platform linux/amd64 -t $IMG --load . && docker push $IMG
gcloud run deploy $SERVICE --image $IMG --project $PROJECT --region $REGION \
  --service-account <run-service-account>@$PROJECT.iam.gserviceaccount.com \
  --allow-unauthenticated --memory 256Mi --max-instances 3 --port 8080
```

## How this was built

I built the original project by hand in 2020. For this version, Claude agents wrote nearly all of
the code (the pipeline, the measures and the site) and ran the pipeline, from plans I set and
reviewed; their commits carry a `Co-Authored-By: Claude` trailer. The decisions about what counts
as a citation, which measures to trust and which themes to keep were mine.
[2020 vs 2026](docs/2020-vs-2026.md) tells the story in more detail.

## Sources

Treatise text and Norton/SBN numbering from [Hume Texts Online](https://davidhume.org/texts/t/), edited by
Peter Millican and Amyas Merivale.
