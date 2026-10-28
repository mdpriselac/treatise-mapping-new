"""Point the scorer at the Norton/SBN concordance copied into tests/fixtures/reference/, so the
tests run on a fresh clone without the 2020 repository alongside."""
import os
from pathlib import Path

os.environ.setdefault("TM_REFERENCE", str(Path(__file__).resolve().parent / "fixtures" / "reference"))
