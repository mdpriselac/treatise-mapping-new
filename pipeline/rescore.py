"""Re-score every paper from docling text: strict detector hits plus uncertain candidates accepted
by the quote check or the LLM. Writes rescored/<paper>.json and rescored/summary.csv."""
import json,glob,os,csv,collections,re
from score import cite_weights,sbn_weights,norton_weights,PARAS
from paths import WORKSPACE, MANUAL
os.chdir(WORKSPACE)
os.makedirs('rescored',exist_ok=True)
acc={}
for r in csv.DictReader(open('all_checked.csv')):
    yes=r['qc']=='quote_match_page_ok' or r.get('llm_is_treatise_cite')=='True'
    if not yes: continue
    loc=(r.get('llm_location') or '').strip(); kind=r.get('llm_kind','')
    if r['qc']=='quote_match_page_ok' or kind=='sbn_page':
        w=sbn_weights(loc) or cite_weights('sbn_page',r['text'],None)
    elif kind=='norton': w=norton_weights(loc)
    elif kind=='appendix_paragraph': w=norton_weights('App.'+re.sub(r'\D','',loc))
    else: w=collections.Counter()
    acc[(r['paper'],r['context'])]=(w,'quote' if r['qc']=='quote_match_page_ok' else 'llm')
summary=[]
for f in sorted(glob.glob('docling_corpus/*.cands.json')):
    n=os.path.basename(f).split('.cands')[0]
    cands=json.load(open(f)); cites=[]
    mpath=MANUAL/f'{n}.json'  # a hand-read paper: its reading replaces the uncertain candidates
    for i,c in enumerate(cands):
        if c['tier']=='strict': w,src=cite_weights(c['kind'],c['text'],c['value']),'pattern'
        elif (n,c['ctx']) in acc and not mpath.exists(): w,src=acc[(n,c['ctx'])]
        else: continue
        if w: cites.append(dict(text=c['text'],context=c['ctx'],source=src,kind=c['kind'],weights=dict(w)))
    # Citations found by reading the paper (manual_review/<paper>.json); other editions can't be mapped yet
    if mpath.exists():
        for m in json.load(open(mpath))['citations']:
            if m.get('exclude'): continue
            ed,loc=m['edition'],m['location']
            w=sbn_weights(loc) if ed=='sbn_page' else norton_weights(loc) if ed in('norton','section') else norton_weights('App.'+re.sub(r'\D','',loc)) if ed=='appendix_paragraph' else collections.Counter()
            if w: cites.append(dict(text=loc,context=m['snippet'],source='manual',kind=ed,weights=dict(w)))
    total=collections.Counter()
    for c in cites: total.update(c['weights'])
    json.dump(dict(name=n,cites=cites,paragraph_weights=dict(total)),open(f'rescored/{n}.json','w'),indent=1)
    srcs=collections.Counter(c['source'] for c in cites)
    summary.append(dict(name=n,cites=len(cites),pattern=srcs['pattern'],quote=srcs['quote'],llm=srcs['llm'],manual=srcs['manual'],
        unscorable=sum(1 for c in cands if c['tier']=='strict')-srcs['pattern']-sum(1 for c in cands if c['tier']=='paired')*0))
w=csv.DictWriter(open('rescored/summary.csv','w'),fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
print('papers',len(summary),'total cites',sum(s['cites'] for s in summary),'by source',{k:sum(s[k] for s in summary) for k in('pattern','quote','llm','manual')})
