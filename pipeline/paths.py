"""Where the pipeline reads and writes. The corpus workspace is private (PDFs, docling
text, full-text candidates) and never lives in this repo; set the env vars to point at it.

    TM_WORKSPACE  private working folder: docling_corpus/, rescored/, CSVs  (default below)
    TM_REFERENCE  2020 reference data: Norton/SBN dictionaries, titles, List-of-Works.csv
    TM_TREATISE   Treatise text with "T 1.4.6.4, SBN 252" paragraph markers
"""
import os
from pathlib import Path

HOME = Path.home()
WORKSPACE = Path(os.environ.get("TM_WORKSPACE", HOME / "Single-File-Processing-for-Hume-Project/modernization_lab"))
REFERENCE = Path(os.environ.get("TM_REFERENCE", HOME / "Hume-on-Personal-Identity/data/runtime"))
TREATISE = Path(os.environ.get("TM_TREATISE", HOME / "Single-File-Processing-for-Hume-Project/data/Full Treatise in HTML.txt"))
CORPUS = WORKSPACE / "docling_corpus"
RESCORED = WORKSPACE / "rescored"
MANUAL = WORKSPACE / "manual_review"
