"""Novelty measures on the re-scored corpus: each paper's focus (share of cites on the 15
most-cited paragraphs) and breadth-adjusted surprise, plus rare passages cited by focused
papers. Writes phase2_papers.csv and phase2_passages.csv. Themes: see themes.py."""
import json,re,numpy as np,pandas as pd
from scipy.optimize import brentq
from sklearn.decomposition import NMF
import os
from paths import REFERENCE, TREATISE, WORKSPACE
os.chdir(WORKSPACE)
titles=json.load(open(REFERENCE/'file_to_title_dict.json'))
bib=pd.read_csv(REFERENCE/'List-of-Works.csv')
bib['name']=bib.Filename.str.replace(r'\.pdf$','',regex=True,flags=re.I)
author=dict(zip(bib.name,bib.Author)); year=dict(zip(bib.name,bib.Year))
S=pd.read_csv('rescored/summary.csv',index_col=0)
names=list(S.index[S.cites>=10]); N=len(names)
W=pd.DataFrame({n:json.load(open(f'rescored/{n}.json'))['paragraph_weights'] for n in names}).T.fillna(0)
P=W.div(W.sum(axis=1),axis=0); lit=W.sum()/W.sum().sum()
core=list(lit.sort_values(ascending=False).index[:15])
pin=(W>=0.3).astype(int); nv=S.loc[names,'cites'].values.astype(float)
def rate(p,excl):
    m=np.ones(N,bool); m[excl]=False
    tgt=(pin[p].values[m].sum()+0.5)/(m.sum()+1)
    return brentq(lambda r:np.mean(1-(1-r)**nv[m])-tgt,1e-9,0.999)
surp={}
for i,n in enumerate(names):
    surp[n]=pd.Series({p:-np.log(1-(1-rate(p,i))**nv[i]) for p in pin.columns[pin.loc[n]==1]},dtype=float).sort_values(ascending=False)
focus=pd.Series({n:float(P.loc[n][core].sum()) for n in names})
papers=pd.DataFrame({'author':[author.get(n,'') for n in names],'year':[year.get(n,'') for n in names],
  'title':[titles.get(n,'') for n in names],'cites':nv.astype(int),'focus':focus.round(2).values,
  'surprise':[round(surp[n].iloc[0],2) if len(surp[n]) else 0 for n in names],
  'rare_passages':[int((surp[n]>np.log(20)).sum()) for n in names],
  'top_rare':[', '.join(surp[n].index[:3]) for n in names]},index=names)
papers.to_csv('phase2_papers.csv')
# passage-level: rare passages (<=3 papers) cited precisely by focused papers
df_=pin.sum()
rows=[]
for p in df_[df_<=3].index:
    citers=[n for n in names if pin.loc[n,p]==1]
    fc=[n for n in citers if focus[n]>=0.4]
    if not fc: continue
    rows.append(dict(passage=p,n_papers=int(df_[p]),focused_citers=', '.join(fc),
        score=round(max(focus[n]*surp[n][p] for n in fc),2)))
passages=pd.DataFrame(rows).sort_values('score',ascending=False)
# Treatise text snippets
T=open(TREATISE,errors='ignore').read()
marks=list(re.finditer(r'T\s+((?:\d+\.){1,3}\d+(?:n\d+)?|App\.?\s*\d+|Abs\.?\s*\d+),\s*SBN[^\n]*\n',T))
text={}
for a,b in zip(marks,marks[1:]+[None]):
    k=a.group(1).replace(' ',''); seg=' '.join(T[a.end():b.start() if b else None].split())
    text[k]=seg
passages['opening']=passages.passage.map(lambda p:' '.join(text.get(p,'').split()[:18]))
passages.to_csv('phase2_passages.csv',index=False)
print('papers',N,'core',core)
