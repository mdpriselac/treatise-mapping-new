# Treatise Mapping

Which passages of Hume's *Treatise of Human Nature* does the secondary literature on personal identity cite, and
which papers find their way to passages the rest of the literature passes by?

This is the modern version of the project, served at
<https://treatise-mapping-project-new.outsidethevillage.com>. The original 2020 site is archived, unchanged, at
<https://treatise-mapping-project-ur.outsidethevillage.com> from its own repository. The two deploy independently.

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
pipeline/.venv/bin/python pipeline/build_data.py \
  --lab ~/Single-File-Processing-for-Hume-Project/modernization_lab \
  --treatise "$HOME/Single-File-Processing-for-Hume-Project/data/Full Treatise in HTML.txt" \
  --runtime ~/Hume-on-Personal-Identity/data/runtime
```

## Running the site

```bash
cd site
npm ci
npm run build    # astro build, then the Pagefind search index
npm run preview
```

## Deploying

Cloud Run service `treatise-new` in GCP project `treatise-mapping-new` (us-central1), running as
`treatise-new-run@`, a service account with no roles. Build the image locally for amd64, push it, deploy it:

```bash
TAG=$(git rev-parse --short HEAD)
IMG=us-central1-docker.pkg.dev/treatise-mapping-new/cloud-run-source-deploy/treatise-new:$TAG
gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin https://us-central1-docker.pkg.dev
docker buildx build --platform linux/amd64 -t $IMG --load . && docker push $IMG
gcloud run deploy treatise-new --image $IMG --project treatise-mapping-new --region us-central1 \
  --service-account treatise-new-run@treatise-mapping-new.iam.gserviceaccount.com \
  --allow-unauthenticated --memory 256Mi --max-instances 3 --port 8080
```

The domain is a Cloud Run domain mapping; DNS is a CNAME for `treatise-mapping-project-new` at Squarespace
pointing to `ghs.googlehosted.com`.

## Sources

Treatise text and Norton/SBN numbering from [Hume Texts Online](https://davidhume.org/texts/t/), edited by
Peter Millican and Amyas Merivale.
Hume's text is in the public domain, but the edition's corrections and paragraph numbering are the editors' work.
That edited text (`site/src/data/passages.json`, and `upload/job/reference/treatise.txt` where present) is not
covered by this repo's MIT license, so please credit Hume Texts Online if you reuse it.

## License

The code is under the [MIT License](LICENSE). The Treatise text is excepted, as described under Sources.
