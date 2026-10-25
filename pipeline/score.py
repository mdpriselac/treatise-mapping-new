"""Turn accepted citations into paragraph-level scores.
A citation carries weight 1, split across the paragraphs it covers (SBN pages split evenly, then
across each page's paragraphs, as in 2020). A paragraph counts as 'precise' for a paper when it gets >= 0.3."""
import re,json,glob,os,csv,collections
import roman
from paths import REFERENCE
R=str(REFERENCE)+'/'
n2s={};s2n={}
for line in open(R+'Norton to SBN Dictionary.txt'):
    if ' : ' in line: k,v=line.split(' : '); n2s[k.strip()]=[x.strip() for x in v.split(',')]
for line in open(R+'SBN to Norton Dictionary.txt'):
    if ' : ' in line: k,v=line.split(' : '); s2n[k.strip()]=[x.strip() for x in v.split(',')]
PARAS=list(n2s)
DASH='[-–—]'
def _num(x):
    x=x.strip().rstrip('.')
    if re.fullmatch(r'[ivxlc]+',x,re.I): return roman.fromRoman(x.upper()),True
    return int(x),False
def expand(spec):
    """'253-63, 657-8, xiv' -> ['253',...,'263','657','658','xiv']"""
    out=[]
    for part in re.split(r'[,;]',spec):
        part=part.strip()
        if not part: continue
        ends=re.split(DASH,part)
        try:
            a,ra=_num(ends[0])
            if len(ends)>1 and ends[1].strip():
                bs=ends[1].strip(); b,rb=_num(bs)
                if not ra and len(bs)<len(ends[0].strip()): b=int(ends[0].strip()[:len(ends[0].strip())-len(bs)]+bs)
                rng=range(a,b+1) if b>=a and b-a<60 else [a]
            else: rng=[a]
            out+= [roman.toRoman(n).lower() if ra else str(n) for n in rng]
        except Exception: pass
    return out
def sbn_weights(spec):
    pages=[p for p in expand(spec) if p in s2n]
    w=collections.Counter()
    for p in pages:
        for para in s2n[p]: w[para]+=1/len(pages)/len(s2n[p])
    return w
def norton_weights(spec):
    spec=re.sub(r'\s+','',spec)
    m=re.match(r'(App|Abs)\.?(.*)',spec)
    if m:
        pre='App.' if m.group(1)=='App' else 'Abs'
        ps=[pre+x for x in expand(m.group(2))]
    else:
        parts=spec.split('.')
        try:
            b=str(_num(parts[0])[0]); pt=str(_num(parts[1])[0]); sec=re.match(r'\d+',parts[2]).group()
        except Exception: return collections.Counter()
        chap=f'{b}.{pt}.{sec}'
        rest='.'.join(parts[3:]) if len(parts)>3 else ''
        tail=parts[2][len(sec):]  # chapter ranges like 1.4.5-6
        if rest: ps=[f'{chap}.{x}' for x in expand(rest)]
        elif tail and re.match(DASH,tail): ps=[p for s in expand(sec+tail) for p in PARAS if p.startswith(f'{b}.{pt}.{s}.')]
        else: ps=[p for p in PARAS if p.startswith(chap+'.')]
    ps=[p for p in ps if p in n2s]
    return collections.Counter({p:1/len(ps) for p in ps}) if ps else collections.Counter()
def cite_weights(kind,text,value):
    if kind=='norton': return norton_weights(value)
    if kind in('sbn','sbn_page'):
        spec=re.sub(r'^\(?\s*(Treatise|Selby-Bigge|Hume[^,:\d]*(?:\(?\d{4}[a-z]?\)?)?|SBN|THN|L-?B|SB|T)\s*[,:]?\s*(p{1,2}\.\s*)?','',text.strip('() '),flags=re.I)
        return sbn_weights(spec.rstrip(')'))
    if kind=='section_plus_sbn': return sbn_weights(value.split('p.')[-1])
    return collections.Counter()
