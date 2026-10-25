"""Run the detector over docling markdown for every paper and compare with the 2020 counts."""
import json,glob,os,collections,sys
from paths import CORPUS, REFERENCE, WORKSPACE
from detect import detect
R=str(REFERENCE/'publications')+'/'
os.chdir(WORKSPACE)
log=json.load(open('docling_corpus/_log.json'))
rows=[]
for name in sorted(log):
    if 'err' in log[name]: rows.append(dict(name=name,err=log[name]['err'])); continue
    c=detect(open(f'docling_corpus/{name}.md').read())
    json.dump(c,open(f'docling_corpus/{name}.cands.json','w'),indent=1)
    t=collections.Counter(x['tier'] for x in c)
    old=json.load(open(R+name+'.json')) if os.path.exists(R+name+'.json') else {}
    rows.append(dict(name=name,ocr=log[name]['ocr'],old_strict=old.get('totalStrictCites'),old_aggr=old.get('totalAggressiveCites'),
        new_strict=t['strict'],new_probable=t['probable'],new_possible=t['possible']))
import pandas as pd
df=pd.DataFrame(rows).set_index('name'); df.to_csv('corpus_comparison.csv')
ok=df.dropna(subset=['old_strict'])
print('papers',len(df),'errors',df.get('err',pd.Series()).notna().sum())
print('old strict==0:',(ok.old_strict==0).sum(),' new strict==0:',(ok.new_strict==0).sum(),' new strict+probable==0:',((ok.new_strict+ok.new_probable)==0).sum())
print('old strict>=10:',(ok.old_strict>=10).sum(),' new strict>=10:',(ok.new_strict>=10).sum(),' new strict+probable>=10:',((ok.new_strict+ok.new_probable)>=10).sum())
print('totals old strict/aggr',ok.old_strict.sum(),ok.old_aggr.sum(),' new strict/prob/poss',ok.new_strict.sum(),ok.new_probable.sum(),ok.new_possible.sum())
d=ok.new_strict-ok.old_strict
print('\nbiggest drops (new strict < old strict):'); print(ok[d<0].assign(diff=d[d<0]).sort_values('diff').head(12).to_string())
print('\nzero-strict-in-2020 papers now:'); print(ok[ok.old_strict==0].sort_values('new_probable',ascending=False).to_string())
