"""Where the pipeline reads and writes. The corpus workspace is private (PDFs, docling
text, full-text candidates) and never lives in this repo; set the env vars to point at it.

    TM_WORKSPACE  private working folder: docling_corpus/, rescored/, CSVs
                  (default: workspace/ in this repo, which is gitignored)
    TM_REFERENCE  2020 reference data: Norton/SBN dictionaries, titles, List-of-Works.csv
                  (default: data/runtime in a sibling clone of Hume-on-Personal-Identity)
    TM_TREATISE   Treatise text with "T 1.4.6.4, SBN 252" paragraph markers
                  (default: in the workspace)
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKSPACE = Path(os.environ.get("TM_WORKSPACE", REPO / "workspace"))
REFERENCE = Path(os.environ.get("TM_REFERENCE", REPO.parent / "Hume-on-Personal-Identity/data/runtime"))
TREATISE = Path(os.environ.get("TM_TREATISE", WORKSPACE / "Full Treatise in HTML.txt"))
CORPUS = WORKSPACE / "docling_corpus"
RESCORED = WORKSPACE / "rescored"
MANUAL = WORKSPACE / "manual_review"
