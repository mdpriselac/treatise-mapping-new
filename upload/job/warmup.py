"""Build-time: run docling once with and without OCR so every model is downloaded into the
image. The job runs with no internet access, so nothing may be fetched at run time."""
import os,sys,tempfile
import pymupdf
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from uploadprof import to_markdown
with tempfile.TemporaryDirectory() as d:
    doc=pymupdf.open(); page=doc.new_page()
    page.insert_text((72,72),"Warm-up page. A bundle or collection of different perceptions (T 1.4.6.4).",fontsize=12)
    text_pdf=os.path.join(d,'text.pdf'); doc.save(text_pdf)
    pix=doc[0].get_pixmap(dpi=150); img=pymupdf.open(); p=img.new_page(width=pix.width,height=pix.height)
    p.insert_image(p.rect,pixmap=pix); scan_pdf=os.path.join(d,'scan.pdf'); img.save(scan_pdf)
    print(to_markdown(text_pdf,False)[:80]); print(to_markdown(scan_pdf,True)[:80])
