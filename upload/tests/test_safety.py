"""The upload job must refuse unsafe or oversized files and strip active content."""
import io
import os
import sys

import pikepdf
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "job"), os.path.join(HERE, "..", "..", "pipeline")]
import uploadprof as P  # noqa: E402


def make_pdf(pages=1, js=False, embed=False, encrypt=False):
    pdf = pikepdf.new()
    for _ in range(pages):
        pdf.add_blank_page()
    if js:
        action = pdf.make_indirect(pikepdf.Dictionary(S=pikepdf.Name.JavaScript, JS=pikepdf.String("app.alert(1)")))
        pdf.Root.OpenAction = action
        pdf.Root.Names = pikepdf.Dictionary(JavaScript=pikepdf.Dictionary(Names=pikepdf.Array([pikepdf.String("x"), action])))
        pdf.pages[0].obj.AA = pikepdf.Dictionary(O=action)
    if embed:
        pdf.attachments["payload.exe"] = pikepdf.AttachedFileSpec(pdf, b"MZ fake")
    out = io.BytesIO()
    pdf.save(out, encryption=pikepdf.Encryption(owner="o", user="u") if encrypt else None)
    return out.getvalue()


def test_clean_pdf_passes():
    assert P.check_and_clean(make_pdf()).startswith(b"%PDF-")


def test_not_a_pdf():
    with pytest.raises(P.Rejected, match="isn't a PDF"):
        P.check_and_clean(b"MZ\x90\x00 definitely an exe")


def test_too_big():
    with pytest.raises(P.Rejected, match="25 MB"):
        P.check_and_clean(b"%PDF-1.7\n" + b"0" * (25 * 1024 * 1024 + 1))


def test_too_many_pages():
    with pytest.raises(P.Rejected, match="limit is 400"):
        P.check_and_clean(make_pdf(pages=401))


def test_encrypted():
    with pytest.raises(P.Rejected, match="password|encrypted"):
        P.check_and_clean(make_pdf(encrypt=True))


def test_active_content_stripped():
    cleaned = pikepdf.open(io.BytesIO(P.check_and_clean(make_pdf(js=True, embed=True))))
    assert "/OpenAction" not in cleaned.Root
    assert "/AA" not in cleaned.pages[0].obj
    names = cleaned.Root.get("/Names", {})
    assert "/JavaScript" not in names and "/EmbeddedFiles" not in names


def test_damaged():
    with pytest.raises(P.Rejected):
        P.check_and_clean(b"%PDF-1.7\n garbage with no xref")
