"""Quick triage of every PDF: pages, text characters per page, images. Usage: scan_pdfs.py <pdf dir>"""
import pymupdf as fitz,glob,os,sys,json
from paths import WORKSPACE
rows=[]
for p in sorted(glob.glob(sys.argv[1]+'/*.pdf')+glob.glob(sys.argv[1]+'/*.PDF')):
    try:
        d=fitz.open(p); n=d.page_count
        chars=sum(len(pg.get_text()) for pg in d)
        imgs=sum(len(pg.get_images()) for pg in d)
        rows.append((os.path.basename(p),n,chars//max(n,1),imgs, d.is_encrypted, bool(d.embfile_count()), any(pg.get_links() and any(l.get('kind')==fitz.LINK_LAUNCH for l in pg.get_links()) for pg in d)))
    except Exception as e: rows.append((os.path.basename(p),'ERR',str(e)))
json.dump(rows,open(WORKSPACE/'pdfscan.json','w'))
for r in rows: print(r)
