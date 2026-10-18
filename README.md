# Treatise Mapping

Which passages of Hume's *Treatise of Human Nature* does the secondary literature on personal identity cite, and
which papers find their way to passages the rest of the literature passes by?

This is the modern version of the project, served at
<https://treatise-mapping-project-new.outsidethevillage.com>. The original 2020 site is archived, unchanged, at
<https://treatise-mapping-project-ur.outsidethevillage.com> from its own repository. The two deploy independently.

## What is in this repo

| Path | What |
| --- | --- |
| `pipeline/build_data.py` | Exports the site's data from the private corpus workspace |
| `site/src/data/` | The exported, derived data the site is built from |
| `site/` | Astro static site, Observable Plot charts, Pagefind search |
| `Dockerfile`, `deploy/nginx.conf` | Static container for Cloud Run |

Only derived data is committed: citation locations, paragraph weights, scores, the short snippet of text around
each citation, and bibliographic records. Paper PDFs and full texts stay in the private corpus workspace and are
never added here.

## Rebuilding the data

The pipeline that converts PDFs (docling), detects and checks citations, and scores papers lives in the private
corpus workspace. Once it has run, export its results here:

```bash
python3 pipeline/build_data.py \
  --lab ~/Single-File-Processing-for-Hume-Project/modernization_lab \
  --treatise "~/Single-File-Processing-for-Hume-Project/data/Full Treatise in HTML.txt" \
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

```bash
gcloud run deploy treatise-new --source . --project treatise-mapping-new --region us-central1 \
  --service-account treatise-new-run@treatise-mapping-new.iam.gserviceaccount.com --allow-unauthenticated
```

## Sources

Treatise text and Norton/SBN numbering from [Hume Texts Online](https://davidhume.org/texts/t/), edited by
Peter Millican and Amyas Merivale.
