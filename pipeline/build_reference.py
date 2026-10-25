"""Bundle the corpus reference the upload job scores against: core passages, per-paragraph
citation rates (for surprise), the theme model, each corpus paper's chapter profile (for
nearest papers), plus the Treatise text and Norton/SBN tables. Derived data only.
Writes upload/job/reference/."""
import json,os,re,shutil
import numpy as np,pandas as pd
from scipy.optimize import brentq
from paths import WORKSPACE, REFERENCE, TREATISE
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','upload','job','reference')
os.makedirs(OUT,exist_ok=True)
os.chdir(WORKSPACE)
S=pd.read_csv('rescored/summary.csv',index_col=0)
names=list(S.index[S.cites>=10]); N=len(names)
W=pd.DataFrame({n:json.load(open(f'rescored/{n}.json'))['paragraph_weights'] for n in names}).T.fillna(0)
P=W.div(W.sum(axis=1),axis=0); lit=W.sum()/W.sum().sum()
core=list(lit.sort_values(ascending=False).index[:15])
pin=(W>=0.3).astype(int); nv=S.loc[names,'cites'].values.astype(float)
def rate(col):
    tgt=(col.sum()+0.5)/(N+1)
    return brentq(lambda r:np.mean(1-(1-r)**nv)-tgt,1e-9,0.999)
rates={p:round(rate(pin[p].values),8) for p in pin.columns if pin[p].sum()>0}
default_rate=brentq(lambda r:np.mean(1-(1-r)**nv)-0.5/(N+1),1e-9,0.999)
chap=lambda p:re.match(r'(App\.|Abs|\d+\.\d+\.\d+|0)',p).group(1).rstrip('.')
C=W.T.groupby(lambda p:chap(p)).sum().T; C=C.div(C.sum(axis=1),axis=0)
titles=json.load(open(REFERENCE/'file_to_title_dict.json'))
bib=pd.read_csv(REFERENCE/'List-of-Works.csv'); bib['id']=bib.Filename.str.replace(r'\.pdf$','',regex=True,flags=re.I)
au=dict(zip(bib.id,bib.Author)); yr=dict(zip(bib.id,bib.Year))
ref=dict(core=core,rates=rates,default_rate=default_rate,n_papers=N,
    focus_min=0.40,surprise_min=4.4,
    themes=json.load(open('themes_model_k4.json')),
    papers={n:dict(title=re.sub(r'\\textquoteright',"'",titles.get(n,'')),author=str(au.get(n,'')).strip(),year=str(yr.get(n,'')),
                   chapters={c:round(v,5) for c,v in C.loc[n].items() if v>0}) for n in names})
json.dump(ref,open(os.path.join(OUT,'reference.json'),'w'))
for f in ('Norton to SBN Dictionary.txt','SBN to Norton Dictionary.txt'): shutil.copy(REFERENCE/f,os.path.join(OUT,f))
shutil.copy(TREATISE,os.path.join(OUT,'treatise.txt'))
print('reference for',N,'papers,',len(rates),'paragraph rates ->',os.path.abspath(OUT))
