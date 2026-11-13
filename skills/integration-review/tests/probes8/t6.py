import os, tempfile
_HERE = os.path.dirname(os.path.abspath(__file__))
SKR = os.environ.get("IRS") or os.path.normpath(os.path.join(_HERE, "..", ".."))
R = os.environ.get("IRV_PROBE_WORK") or tempfile.mkdtemp(prefix="irv8-probes-")
for _d in ("out", "probes", "probes/w8"):
    os.makedirs(os.path.join(R, _d), exist_ok=True)
import json, os, re, subprocess, sys, tempfile, atexit
SK=SKR; SC=SK+"/scripts/"
W=R+"/probes/w8"; os.makedirs(W,exist_ok=True)
LOG=open(R+"/out/probes.log","a")
CRED=re.compile(r"(token|secret|passw|bearer|api[_-]?key|sk-ant|ghp_|sk_live|glpat|AKIA|@[A-Za-z0-9.-]+\.[a-z]{2,}|://[^/\s]*:[^/\s]*@)",re.I)
def red(t): return "\n".join("[credential-shaped line filtered]" if CRED.search(l) else l for l in t.splitlines())
_n=[0]
def wf(obj,ext="json"):
    _n[0]+=1; p=f"{W}/f{_n[0]}.{ext}"
    open(p,"w").write(obj if isinstance(obj,str) else (json.dumps(obj) if ext=="json" else "\n".join(json.dumps(x) for x in obj)+"\n")); return p
def sh(label,script,*a):
    p=subprocess.run(["python3","-I",SC+script,*map(str,a)],capture_output=True,text=True,cwd=W); o=p.stdout+p.stderr
    LOG.write(f"### {label}\n$ python3 -I scripts/{script} {' '.join(os.path.basename(str(x)) for x in a)}\nexit={p.returncode}\n"+"\n".join(red(o).splitlines()[:20])+"\n\n"); LOG.flush()
    return p.returncode,o
NOW=("--now","2026-11-12T12:00:00Z")
def V(reg,*a,label="validate"): return sh(label,"register_validate.py",wf(reg),*NOW,*a)
def X(rows,*a,label="extract"):
    out=W+"/xo%d"%_n[0]; _n[0]+=1; os.makedirs(out,exist_ok=True)
    rc,o=sh(label,"extract_register.py",*a,wf(rows,"jsonl"),out)
    d={}
    for f in ("register-partial.json","register-declared-complete.json","extraction.json","rejected.json"):
        try: d[f]=json.load(open(out+"/"+f))
        except Exception: d[f]=None
    return rc,o,d,out
def src(repo="o/r1",ver="v1",cap="2026-11-12T09:00:00Z",**kw):
    d={"repo":repo,"version":ver,"available":True}
    if cap: d["captured_at"]=cap
    d.update(kw); return d
def rec(rid,role="producer",comp="c1",fam="IF001",path=None,state="installed",**kw):
    r={"record_id":rid,"family":fam,"role":role,"host":"h","component":comp,"interface_kind":"http","installed_state":state,"label":"positive-control","evidence":[{"ref":"e","observed_at":"2026-11-12T10:00:00Z"}]}
    if path: r["path_or_command"]=path
    if "sources" not in kw: r["source_identity"]=src()
    r.update(kw); return r
def reg(recs,declared="all-interfaces-complete",fams=("IF001",)):
    return {"schema_version":1,"coverage":{"declared":declared},"families":[{"id":f} for f in fams],"records":recs}
def good(): return [rec("p"),rec("c",role="consumer",comp="c2")]
ROWS=[]
def T(i,cls,exp,ok,act): 
    ROWS.append({"id":i,"class":cls,"expected":exp,"actual":red(str(act))[:200],"pass":bool(ok)}); print(i,"PASS" if ok else "FAIL",cls,"|",red(str(act))[:150])
def dump(n): json.dump(ROWS,open(f"{R}/out/{n}.json","w"),indent=1)
H64="e"*64; H40="1"*40
def erow(**kw):
    r={"family":"IF001","role":"producer","host":"h","component":"c","interface_kind":"http","installed_state":"source-only","evidence":"side=producer","source_repo":"o/r","source_identity":"commit "+H40,"path_or_command":"a.py"}
    r.update(kw); return {k:v for k,v in r.items() if v is not None}
