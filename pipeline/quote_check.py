"""Gold-label candidates automatically: if the text just before a candidate quotes the Treatise,
find that passage and check the candidate's number against its SBN pages."""
import re,csv,sys,collections
from paths import REFERENCE, TREATISE
T=open(TREATISE,errors='ignore').read()
sbn2n={}
for line in open(REFERENCE/'SBN to Norton Dictionary.txt'):
    if ':' in line:
        k,v=line.split(':',1); [sbn2n.setdefault(x.strip(),set()).add(k.strip()) for x in v.split(',')]
# split into paragraphs on 'T x.x.x.x, SBN ...' markers
marks=list(re.finditer(r'T\s+((?:\d+\.){1,3}\d+(?:n\d+)?|App\.?\s*\d+|Abs\.?\s*\d+|0\.\d+),\s*SBN',T))
norm=lambda s:re.sub(r'[^a-z]','',s.lower().replace("'d","ed").replace("'","").replace('’d','ed'))
big=[];idx=[]
for a,b in zip(marks,marks[1:]+[None]):
    seg=norm(T[a.end():b.start() if b else len(T)]); idx.append((len(''.join(big)) if False else None)); big.append((a.group(1),seg))
joined='';starts=[]
for nid,seg in big: starts.append((len(joined),nid)); joined+=seg
import bisect
pos=[s for s,_ in starts]
def find(q):
    i=joined.find(q)
    return None if i<0 else starts[bisect.bisect_right(pos,i)-1][1]
def pages_for(nid):
    nid=nid.replace(' ','')
    return sbn2n.get(nid) or sbn2n.get(nid.replace('App.','App')) or sbn2n.get(nid.replace('App','App.').replace('..','.')) or set()
def check(text,ctx):
    i=ctx.rfind(text.strip()[-6:]) if text.strip() else -1
    before=ctx[:ctx.rfind('(')] if '(' in ctx else ctx
    q=norm(before)[-60:]
    for L in (60,45,30):
        qq=norm(before)[-L:]
        if len(qq)<25: break
        nid=find(qq)
        if nid:
            m=re.search(r'\d+',text); n=m.group() if m else ''
            pg=pages_for(nid)
            near={str(int(p)+d) for p in pg if p.isdigit() for d in (-1,0,1)}
            return ('quote_match_page_ok' if n in near else 'quote_match_page_mismatch'), nid, ','.join(sorted(pg))
    return 'no_treatise_quote','',''
if __name__=='__main__':
    rows=list(csv.DictReader(open(sys.argv[1])))
    for r in rows: r['qc'],r['qc_norton'],r['qc_pages']=check(r['text'],r['context'])
    w=csv.DictWriter(open(sys.argv[2],'w'),fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(collections.Counter(r['qc'] for r in rows))
