"""Convert every corpus PDF with docling. Text-layer PDFs skip OCR; PDFs with
under 300 text characters per page get full OCR. Writes <name>.md and <name>.json into
the private corpus folder. Usage: convert_corpus.py <pdf dir>  (run scan_pdfs.py first)"""
import sys,time,os,json,glob
from paths import CORPUS, WORKSPACE
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
src=sys.argv[1]; out=str(CORPUS); os.makedirs(out,exist_ok=True)
scan={r[0]:r for r in json.load(open(WORKSPACE/'pdfscan.json'))}
def conv(ocr):
    o=PdfPipelineOptions(); o.do_ocr=ocr; o.do_table_structure=False
    return DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=o)})
fast,slow=conv(False),conv(True)
log_path=os.path.join(out,'_log.json'); log=json.load(open(log_path)) if os.path.exists(log_path) else {}
for p in sorted(glob.glob(src+'/*.pdf')+glob.glob(src+'/*.PDF')):
    name=os.path.basename(p)[:-4]
    if name in log and 'err' not in log[name]: continue
    cpp=scan.get(os.path.basename(p),(0,0,9999))[2]
    ocr=isinstance(cpp,int) and cpp<300
    t=time.time()
    try:
        r=(slow if ocr else fast).convert(p)
        md=r.document.export_to_markdown()
        open(f"{out}/{name}.md","w").write(md)
        json.dump(r.document.export_to_dict(),open(f"{out}/{name}.json","w"))
        log[name]=dict(ocr=ocr,secs=round(time.time()-t,1),chars=len(md),pages=len(r.document.pages))
    except Exception as e:
        log[name]=dict(ocr=ocr,err=repr(e)[:300])
    json.dump(log,open(log_path,'w'),indent=1); print(name,log[name],flush=True)
