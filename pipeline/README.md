# Corpus pipeline

Turns the paper PDFs into the citation data the site shows. The code lives here; the corpus
itself (PDFs, docling text, candidate contexts, hand-review notes) lives in a private workspace
outside the repo, because it contains the papers' full text. Point the scripts at it with
environment variables (defaults in `paths.py`):

| Variable | What it is |
| --- | --- |
| `TM_WORKSPACE` | Private working folder: `docling_corpus/`, `manual_review/`, `rescored/`, the CSVs (default `workspace/`, gitignored) |
| `TM_REFERENCE` | 2020 reference data: Norton↔SBN dictionaries, titles, `List-of-Works.csv`, 2020 scores (default: a sibling clone of Hume-on-Personal-Identity) |
| `TM_TREATISE` | Treatise text with `T 1.4.6.4, SBN 252` paragraph markers |
| `TM_GCP_PROJECT` | The GCP project the model check calls Vertex AI in |

## Setup

```bash
cd pipeline
uv venv -p 3.12 .venv
uv pip install -p .venv/bin/python -r requirements.txt
```

The model check runs Gemini on Vertex AI in your own GCP project, authorised by your
`gcloud auth application-default login`. There is no API key.

## Steps, in order

| Step | Script | Writes (in the workspace) |
| --- | --- | --- |
| 1. Triage PDFs | `scan_pdfs.py <pdf dir>` | `pdfscan.json` (pages, text per page; decides OCR) |
| 2. Convert | `convert_corpus.py <pdf dir>` | `docling_corpus/<id>.md` and `.json` |
| 3. Detect | `compare_2020.py` (runs `detect.py` on every paper) | `docling_corpus/<id>.cands.json`, `corpus_comparison.csv` |
| 4. Check uncertain candidates | `new_uncertain.py`, then `adjudicate.py gemini gemini-3.8-flash new_uncertain.csv new_gemini.csv`, `quote_check.py new_gemini.csv new_checked.csv`, `merge_checked.py` | `all_checked.csv` |
| 5. Score | `rescore.py` | `rescored/<id>.json`, `rescored/summary.csv` |
| 6. Measures | `measures.py`, `themes.py 4` | `phase2_papers.csv`, `phase2_passages.csv`, `phase2_themes_noncore_k4.csv` |
| 7. Export to the site | `build_data.py --lab … --treatise … --runtime …` | `site/src/data/*.json` (derived data only) |

Step 4 only sends candidates that haven't been checked before, so a detector change costs
seconds, not a full re-run.

## How a citation gets accepted

- **Pattern** (`detect.py`, tier `strict`): Norton (`T 1.4.6.4`, `App. 10`, `Abs 28`), SBN
  (`SBN 252`), `(T 252)`, `(Treatise 252)`, `(Hume 1978, p. 252)`, and `T 1. iv. 6. 261`. A Norton
  cite followed by its SBN page counts once.
- **Quote match** (`quote_check.py`): for a bare page number after a quotation, the quoted words
  are found in the Treatise and the page checked against that paragraph's SBN pages.
- **Model check** (`adjudicate.py`): the remaining `probable`/`possible` candidates (bare page
  numbers, footnotes like `Treatise, p. 252`) go to the model with their context and the paper's
  stated citation convention.
- **Read by hand** (`manual_review/<id>.json`): papers the detector found nothing in were read in
  full. Where a paper has a hand review, it replaces that paper's uncertain candidates. Entries
  marked `exclude` (inferred or borderline) and citations of other editions are not scored.

Scoring (`score.py`) gives each citation a weight of 1, split across the paragraphs it covers.
A paragraph counts as cited *precisely* when it gets at least 0.3.

## Tests

```bash
.venv/bin/python -m pytest -q tests
```

The tests use a copy of the Norton↔SBN concordance in `tests/fixtures/reference/`, so they run on a
fresh clone with only `pytest`, `roman`, `pandas` and `numpy` installed.
