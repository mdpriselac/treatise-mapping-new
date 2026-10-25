"""Ask an LLM (Claude or Gemini on Vertex AI) whether each uncertain candidate is a Treatise citation.
Usage: adjudicate.py <claude|gemini> <model> <in.csv> <out.csv>
Importable: judge(rows, backend, model, convention_for) for the upload job."""
import sys,csv,json,re,os,time,concurrent.futures as cf
PROJECT=os.environ.get('TM_GCP_PROJECT','treatise-mapping-new')
CONV=re.compile(r'[^.\n]{0,200}(Selby-Bigge|Treatise of Human Nature, ed|page references|references to the Treatise|cited as|abbreviat|parenthetical)[^.\n]{0,200}',re.I)
def convention_from_text(t):
    """The paper's own statements about how it cites the Treatise (up to three, 800 chars)."""
    return ' … '.join(m.group(0).strip() for m in list(CONV.finditer(t))[:3])[:800]
PROMPT="""You are checking citations in a scholarly paper about David Hume.
A detector flagged a number in parentheses that might cite Hume's *A Treatise of Human Nature*.
Selby-Bigge/Nidditch (SBN) page numbers for the Treatise run from about 1 to 676 (Appendix 623-639, Abstract 641-662); Norton cites look like 1.4.6.4.

Paper's statements about its citation conventions (may be empty):
{conv}

Candidate: {text}
Text around it (the candidate is near the end): {ctx}

Is this candidate a citation to the Treatise? Answer only with JSON:
{{"is_treatise_cite": true|false, "kind": "sbn_page"|"norton"|"appendix_paragraph"|"other_work"|"not_a_citation", "location": "<page or Norton location, or empty>", "confidence": 0-1, "reason": "<short>"}}"""
def client(backend,model):
    if backend=='claude':
        from anthropic import AnthropicVertex
        # Claude 5.5 models on Vertex are served from the 'us' multi-region endpoint, not us-east5
        cl=AnthropicVertex(project_id=PROJECT,region='us')
        return lambda p: cl.messages.create(model=model,max_tokens=200,messages=[{"role":"user","content":p}]).content[0].text
    from google import genai
    cl=genai.Client(vertexai=True,project=PROJECT,location='global')
    return lambda p: cl.models.generate_content(model=model,contents=p,config={"response_mime_type":"application/json"}).text
def judge(rows,backend,model,convention_for,workers=8):
    """rows: dicts with paper, text, context. convention_for(paper) -> str. Returns rows with llm_* keys added."""
    ask=client(backend,model)
    def run(r):
        p=PROMPT.format(conv=convention_for(r['paper']) or '(none found)',text=r['text'],ctx=r['context'])
        for a in range(5):
            try:
                out=ask(p); j=json.loads(re.search(r'\{.*\}',out,re.S).group()); break
            except Exception as e:
                j={'error':str(e)[:200]}; time.sleep(2**a)
        return {**r,**{f'llm_{k}':v for k,v in j.items()}}
    with cf.ThreadPoolExecutor(workers) as ex: return list(ex.map(run,rows))
if __name__=='__main__':
    from paths import CORPUS
    backend,model,src,dst=sys.argv[1:5]
    cache={}
    def convention(paper):
        if paper not in cache: cache[paper]=convention_from_text(open(CORPUS/f'{paper}.md',errors='ignore').read())
        return cache[paper]
    rows=list(csv.DictReader(open(src)))
    t=time.time()
    res=judge(rows,backend,model,convention)
    keys=list(dict.fromkeys(k for r in res for k in r))
    w=csv.DictWriter(open(dst,'w'),fieldnames=keys); w.writeheader(); w.writerows(res)
    print(len(res),'done in',round(time.time()-t),'s; errors',sum('llm_error' in r for r in res),'; yes',sum(r.get('llm_is_treatise_cite') is True for r in res))
