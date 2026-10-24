"""Citation themes: NMF on each paper's chapter-level profile with 1.4.6 and the Appendix
set aside (nearly every paper cites them, so they hide the differences). Fits 30 random
starts, keeps the best, and reports stability (mean adjusted Rand index across 10 starts).
Usage: themes.py [k]   (default 4) -> phase2_themes_noncore_k<k>.csv in the workspace"""
import json,os,re,sys
import numpy as np,pandas as pd
from sklearn.decomposition import NMF
from sklearn.metrics import adjusted_rand_score as ari
from paths import WORKSPACE
os.chdir(WORKSPACE)
k=int(sys.argv[1]) if len(sys.argv)>1 else 4
S=pd.read_csv('rescored/summary.csv',index_col=0)
names=list(S.index[S.cites>=10])
W=pd.DataFrame({n:json.load(open(f'rescored/{n}.json'))['paragraph_weights'] for n in names}).T.fillna(0)
chap=lambda p:re.match(r'(App\.|Abs|\d+\.\d+\.\d+|0)',p).group(1).rstrip('.')
C=W.T.groupby(lambda p:chap(p)).sum().T
C=C.drop(columns=[c for c in ('1.4.6','App') if c in C]); C=C[C.sum(axis=1)>=3]
Cn=C.div(C.sum(axis=1),axis=0)
fit=lambda s:NMF(k,init='random',random_state=s,max_iter=5000).fit(Cn.values)
labs=[fit(s).transform(Cn.values).argmax(1) for s in range(10)]
print('papers',len(C),'stability',round(np.mean([ari(a,b) for i,a in enumerate(labs) for b in labs[i+1:]]),3))
best=min((fit(s) for s in range(30)),key=lambda m:m.reconstruction_err_)
Wt=best.transform(Cn.values); Wt=Wt/Wt.sum(1,keepdims=True)
for t,h in enumerate(best.components_):
    print(f'theme t{t}:',[(C.columns[j],round(h[j]/h.sum(),2)) for j in np.argsort(-h)[:5]])
# Keep theme ids stable across refits (the site names t0..t3): match each fitted theme to the
# named theme whose anchor chapter it weights most.
ANCHORS={'t0':'2.1.','t1':'1.3.14','t2':'1.4.2','t3':'1.4.5'}  # passions, causation, external world, soul
cols=[f'x{t}' for t in range(k)]
if k==4:
    score=lambda h,a:sum(h[j] for j,c in enumerate(C.columns) if c.startswith(a))/h.sum()
    order={}
    for tid,a in ANCHORS.items():
        order[tid]=max((t for t in range(k) if t not in order.values()),key=lambda t:score(best.components_[t],a))
    Wt=Wt[:,[order[t] for t in ANCHORS]]; cols=list(ANCHORS)
    print('theme ids:',{t:f'fit {order[t]}' for t in ANCHORS})
pd.DataFrame(Wt,index=C.index,columns=cols).round(3).to_csv(f'phase2_themes_noncore_k{k}.csv')
