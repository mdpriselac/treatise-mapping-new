"""List uncertain candidates that have not been checked yet (not in all_checked.csv), so a
detector change only sends new candidates to the quote check and the LLM.
Usage: new_uncertain.py -> new_uncertain.csv in the workspace; then
    adjudicate.py gemini gemini-3.8-flash new_uncertain.csv new_gemini.csv
    quote_check.py new_gemini.csv new_checked.csv
and append new_checked.csv to all_checked.csv (merge_checked.py)."""
import csv,glob,json,os
from paths import WORKSPACE
os.chdir(WORKSPACE)
seen={(r['paper'],r['context']) for r in csv.DictReader(open('all_checked.csv'))} if os.path.exists('all_checked.csv') else set()
rows=[]
for f in sorted(glob.glob('docling_corpus/*.cands.json')):
    n=os.path.basename(f).split('.cands')[0]
    for i,c in enumerate(json.load(open(f))):
        if c['tier'] in ('probable','possible') and (n,c['ctx']) not in seen:
            rows.append(dict(paper=n,idx=i,tier=c['tier'],text=c['text'],context=c['ctx']))
with open('new_uncertain.csv','w') as fh:
    w=csv.DictWriter(fh,fieldnames=['paper','idx','tier','text','context']); w.writeheader(); w.writerows(rows)
print(len(rows),'new uncertain candidates')
