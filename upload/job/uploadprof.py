"""Turn one uploaded PDF into a citation profile, scored the same way as the corpus.

Steps: check_and_clean (is it a safe, small-enough PDF?) -> triage (does it need OCR?) ->
to_markdown (docling) -> find_citations (detector, quote check, model check) ->
build_profile (paragraph weights, focus, surprise, themes, nearest corpus papers).
The pipeline modules are imported from ../../pipeline (copied next to this file in the image).
"""
import collections
import io
import json
import os
import re


HERE = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.environ.get("TM_REFERENCE", os.path.join(HERE, "reference"))
os.environ.setdefault("TM_REFERENCE", REF_DIR)
os.environ.setdefault("TM_TREATISE", os.path.join(REF_DIR, "treatise.txt"))

from detect import detect                      # noqa: E402  (pipeline)
from quote_check import check as quote_check   # noqa: E402
from score import cite_weights, sbn_weights, norton_weights  # noqa: E402
import adjudicate                              # noqa: E402


MAX_BYTES = 25 * 1024 * 1024
MAX_PAGES = 400
MAX_MODEL_CALLS = 150          # per upload
SNIPPET = 120                  # characters of context kept per citation
MODEL = os.environ.get("TM_MODEL", "gemini-3.8-flash")


class Rejected(Exception):
    """The file failed a safety or size check; the message is shown to the uploader."""


# ---------------------------------------------------------------- safety
def check_and_clean(data: bytes) -> bytes:
    """Return a cleaned copy of the PDF, or raise Rejected with a plain reason."""
    import pikepdf
    if len(data) > MAX_BYTES:
        raise Rejected(f"The file is {len(data) / 1e6:.1f} MB; the limit is 25 MB.")
    if b"%PDF-" not in data[:1024]:
        raise Rejected("That file isn't a PDF.")
    try:
        pdf = pikepdf.open(io.BytesIO(data))
    except pikepdf.PasswordError:
        raise Rejected("The PDF is password-protected.")
    except Exception:
        raise Rejected("The PDF couldn't be opened; it may be damaged.")
    if pdf.is_encrypted:
        raise Rejected("The PDF is encrypted.")
    if len(pdf.pages) > MAX_PAGES:
        raise Rejected(f"The PDF has {len(pdf.pages)} pages; the limit is {MAX_PAGES}.")
    root = pdf.Root
    for key in ("/OpenAction", "/AA", "/AcroForm"):
        if key in root:
            del root[key]
    if "/Names" in root:
        for key in ("/JavaScript", "/EmbeddedFiles"):
            if key in root.Names:
                del root.Names[key]
    for page in pdf.pages:
        if "/AA" in page.obj:
            del page.obj["/AA"]
        for annot in page.obj.get("/Annots", []):
            for key in ("/A", "/AA"):
                if key in annot:
                    del annot[key]
    out = io.BytesIO()
    pdf.save(out)
    return out.getvalue()


# ---------------------------------------------------------------- triage + parse
def triage(data: bytes) -> dict:
    import pymupdf
    doc = pymupdf.open(stream=data, filetype="pdf")
    chars = [len(p.get_text()) for p in doc]
    per_page = sum(chars) / max(len(chars), 1)
    ocr = per_page < 300
    return {"pages": len(chars), "chars_per_page": round(per_page), "ocr": ocr,
            "estimate_seconds": round(len(chars) * (6 if ocr else 0.3)) + 10}


def to_markdown(path: str, ocr: bool) -> str:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    opts = PdfPipelineOptions()
    opts.do_ocr = ocr
    opts.do_table_structure = False
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    return conv.convert(path).document.export_to_markdown()


# ---------------------------------------------------------------- citations
def _model_weights(r):
    loc, kind = (r.get("llm_location") or "").strip(), r.get("llm_kind", "")
    if kind == "sbn_page":
        return sbn_weights(loc) or cite_weights("sbn_page", r["text"], None)
    if kind == "norton":
        return norton_weights(loc)
    if kind == "appendix_paragraph":
        return norton_weights("App." + re.sub(r"\D", "", loc))
    return collections.Counter()


def find_citations(text: str, use_model: bool = True, progress=lambda msg: None) -> list:
    """Accepted citations, each {text, kind, source, context, weights}."""
    cites, uncertain = [], []
    for c in detect(text):
        ctx = c["ctx"]
        if c["tier"] == "strict":
            w = cite_weights(c["kind"], c["text"], c["value"])
            if w:
                cites.append(dict(text=c["text"], kind=c["kind"], source="pattern", context=ctx, weights=w))
        elif c["tier"] in ("probable", "possible"):
            verdict, _, _ = quote_check(c["text"], ctx)
            if verdict == "quote_match_page_ok":
                w = cite_weights("sbn_page", c["text"], None) or sbn_weights(c["value"])
                if w:
                    cites.append(dict(text=c["text"], kind=c["kind"], source="quote", context=ctx, weights=w))
            else:
                uncertain.append(dict(paper="upload", text=c["text"], context=ctx, kind=c["kind"]))
    if use_model and uncertain:
        batch = uncertain[:MAX_MODEL_CALLS]
        progress(f"Checking {len(batch)} uncertain citations with the model")
        conv = adjudicate.convention_from_text(text)
        for r in adjudicate.judge(batch, "gemini", MODEL, lambda _: conv):
            if r.get("llm_is_treatise_cite") is True:
                w = _model_weights(r)
                if w:
                    cites.append(dict(text=r["text"], kind=r["kind"], source="llm", context=r["context"], weights=w))
    for c in cites:
        c["context"] = c["context"][-SNIPPET:]
        c["weights"] = {k: round(v, 4) for k, v in c["weights"].items()}
    return cites


from profile_measures import build_profile  # noqa: E402,F401  (re-exported for main.py)
