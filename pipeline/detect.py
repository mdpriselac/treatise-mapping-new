"""Prototype v2 citation candidate detector: runs on whitespace-preserving text,
tags each candidate with a type and a confidence tier, and keeps context for review."""
import re,sys,json,collections
NORTON=re.compile(r'(?<![\d.])(?:T\s*|THN\s*|Treatise\s*)?((?:[1-3]|I{1,3})\.(?:[1-4]|i{1,3}v?|I{1,3}V?)\.\d{1,2}(?:\.\d{1,2}(?:n\d+)?)?(?:\s*[-–—]\s*\d{1,2})?(?:\s*,\s*\d{1,2}(?:\s*[-–—]\s*\d{1,2})?)*)(?![\d])')
APPABS=re.compile(r'\b(?:T\s*)?(App(?:endix)?|Abs(?:tract)?)\.?\s*§?\s*(\d{1,2}(?:\s*[-–—,]\s*\d{1,2})*)')
SBN=re.compile(r'\b(SBN|SB|L-?B|Selby-Bigge)\s*:?\s*([xvi]{1,6}|\d{1,3})(?:\s*[-–—]\s*([xvi]{1,6}|\d{1,3}))?((?:\s*,\s*(?:[xvi]{1,6}|\d{1,3})(?:\s*[-–—]\s*\d{1,3})?)*)')
TPAGE=re.compile(r'\((?:T|THN|Treatise|Hume(?:\s*\(?1739[^)]*\)?|\s*1978|\s*1888)?)[,:]?\s*(?:p{1,2}\.\s*)?(\d{1,3})(?:\s*[-–—]\s*\d{1,3})?(?:\s*[,;]\s*\d{1,3}(?:\s*[-–—]\s*\d{1,3})?)*\)')
BARE=re.compile(r'([”"\'’][\s.,;]*)?\((?:p{1,2}\.\s*)?(\d{1,3})(?:\s*[-–—]\s*\d{1,3})?(?:\s*,\s*\d{1,3}(?:\s*[-–—]\s*\d{1,3})?)*\)')
# 'T 1. iv. 6. 261' style: Book.Part.Section followed by an SBN page (2-3 digits)
HYBRID=re.compile(r'(?<![\d.])(?:T|THN|Tr|Treatise)?\.?\s*((?:[1-3]|I{1,3})\.\s*(?:[1-4]|i{1,3}v?|I{1,3}V?)\.\s*\d{1,2})\.\s*(\d{2,3}(?:\s*[-–—]\s*\d{1,3})?)(?![\d.])')
# Footnote style: 'Hume, A Treatise of Human Nature, ed. Selby-Bigge ..., p. 252' or 'Treatise, pp. 252-3'.
# Kept 'probable' because the edition is not always Selby-Bigge; the quote check or LLM decides.
FOOT=re.compile(r'Treatise(?: of Human Nature)?[^\n]{0,120}?\bpp?\.\s*(\d{1,3}(?:\s*[-–—]\s*\d{1,3})?)')
ENQ=re.compile(r'\b(EHU|EPM|Enquiry|E|DP|NHR|DNR)\s*\d')
def detect(text):
    out=[]; taken=[]
    def add(kind,tier,m,val):
        s,e=m.span()
        if any(s<b and e>a for a,b in taken): return
        taken.append((s,e))
        out.append(dict(kind=kind,tier=tier,start=s,end=e,text=m.group(0).strip(),value=val,ctx=text[max(0,s-90):e+20].replace('\n',' ')))
    for m in HYBRID.finditer(text):
        if int(re.match(r'\d+',m.group(2)).group())>40: add('section_plus_sbn','strict',m,m.group(1)+' p.'+m.group(2))
    for m in NORTON.finditer(text): add('norton','strict',m,m.group(1))
    for m in APPABS.finditer(text): add('norton','strict',m,m.group(1)[:3]+'.'+m.group(2))
    for m in SBN.finditer(text): add('sbn','strict',m,m.group(0))
    for m in TPAGE.finditer(text): add('sbn_page','strict',m,m.group(1))
    for m in BARE.finditer(text):
        n=int(m.group(2))
        pre=text[max(0,m.start()-12):m.start()]
        if ENQ.search(pre): continue
        if m.group(1) and 1<=n<=676: add('bare_page_after_quote','probable',m,m.group(2))
        elif 1<=n<=676 and n>=10: add('bare_page','possible',m,m.group(2))
    for m in FOOT.finditer(text): add('footnote_page','probable',m,m.group(1))
    # A Norton cite followed closely by its SBN page ("1.4.6.4; SBN 252") is one citation, not two
    out.sort(key=lambda x:x['start'])
    for a,b in zip(out,out[1:]):
        if a['kind']=='norton' and b['kind']=='sbn' and b['start']-a['end']<=25 and re.fullmatch(r'[\s;,/]*',text[a['end']:b['start']]):
            b['tier']='paired'
    return out
if __name__=='__main__':
    for p in sys.argv[1:]:
        t=open(p,errors='ignore').read()
        c=detect(t); cnt=collections.Counter((x['kind'],x['tier']) for x in c)
        print(p.split('/')[-1], dict(cnt))
        json.dump(c,open(p+'.cands.json','w'),indent=1)
