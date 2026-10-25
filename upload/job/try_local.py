"""Run the upload pipeline on local PDFs and compare with the corpus scores (dev aid).
Usage: TM_WORKSPACE=... python try_local.py <pdf> [<pdf> ...] [--no-model]"""
import json,os,sys,time
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','pipeline'))
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import uploadprof as P
use_model='--no-model' not in sys.argv
for path in [a for a in sys.argv[1:] if not a.startswith('--')]:
    t=time.time(); data=open(path,'rb').read()
    clean=P.check_and_clean(data); tri=P.triage(clean)
    tmp=f'/tmp/tm_upload_{os.getpid()}.pdf'; open(tmp,'wb').write(clean)
    try: md=P.to_markdown(tmp,tri['ocr'])
    finally: os.remove(tmp)
    cites=P.find_citations(md,use_model=use_model,progress=print)
    prof=P.build_profile(cites)
    name=os.path.basename(path).rsplit('.',1)[0]
    ws=os.environ.get('TM_WORKSPACE',os.path.expanduser('~/Single-File-Processing-for-Hume-Project/modernization_lab'))
    try:
        old=json.load(open(os.path.join(ws,'rescored',name+'.json'))); oc=len(old['cites'])
    except Exception: oc=None
    nov={}
    try:
        import csv
        for r in csv.DictReader(open(os.path.join(ws,'phase2_papers.csv'))):
            if r['']==name: nov=r
    except Exception: pass
    print(f"{name}: {tri} | {time.time()-t:.0f}s | cites {prof['cites']} (corpus {oc}) | focus {prof['focus']} (corpus {nov.get('focus')}) | surprise {prof['surprise']} (corpus {nov.get('surprise')}) | themes {prof['themes']} | nearest {[n['id'] for n in prof['nearest'][:3]]}")
