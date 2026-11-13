import os, tempfile
_HERE = os.path.dirname(os.path.abspath(__file__))
SKR = os.environ.get("IRS") or os.path.normpath(os.path.join(_HERE, "..", ".."))
R = os.environ.get("IRV_PROBE_WORK") or tempfile.mkdtemp(prefix="irv7-probes-")
for _d in ("out", "probes", "probes/w7"):
    os.makedirs(os.path.join(R, _d), exist_ok=True)
import time, subprocess, json, os, random
from mods6 import *
random.seed(3)
def shapes(n):
    S={}
    S["same-path-distinct-repo"]=[row(i,repo=f"o{i}/r",ident=cm("%x"%(i%15+1)),path="a.py",ev="side=producer") for i in range(n)]
    S["same-path-same-repo-distinct-commit"]=[row(i,repo="o/r",ident="commit "+("%040x"%i),path="a.py",ev="side=producer") for i in range(n)]
    S["same-path-one-repo-many-sources(no commit)"]=[row(i,repo="o/r",ident=sha("%x"%(i%16)),path="a.py",ev="side=producer") for i in range(n)]
    S["pathless-distinct-repo"]=[row(i,repo=f"o{i}/r",ident=cm("1"),ev="side=producer") for i in range(n)]
    S["unstated-repo-rows"]=[row(i,repo=None,ident=None,path="a.py",ev="side=producer") for i in range(n)]
    S["half-repo-half-unknown"]=[row(i,repo=(f"o{i}/r" if i%2 else None),ident=cm("%x"%(i%15+1)) if i%3 else None,path="a.py",ev="side=producer") for i in range(n)]
    S["distinct-paths-shared-sha"]=[row(i,repo=f"o{i}/r",ident="path+sha256:/p/x%d.py "%i+"c"*64,path=f"p{i}.py",ev="side=producer") for i in range(n)]
    S["many-keys-small"]=[row(i,repo=f"o{i%7}/r",ident=cm("%x"%(i%3+1)),path=f"p{i%50}.py",comp=f"c{i%40}",ev="side=producer") for i in range(n)]
    S["mixed-random"]=[row(i,repo=random.choice(["o1/r","o2/r",None,"o3/r"]),ident=random.choice([cm("1"),cm("2"),sha("a"),None]),path=random.choice(["a.py","b.py",None,"c.py"]),ev="side=producer") for i in range(n)]
    return S
print("n shape convert_s")
worst={}
for n in (100,400,1000):
    for k,rows in shapes(n).items():
        for h in (False,True):
            t=time.time(); NEW.convert(rows,"partial",heuristic_fusion=h); d=time.time()-t
            worst[n]=max(worst.get(n,0),d)
            if d>0.5: print(n,k,"heur" if h else "",round(d,2))
print("worst convert():",{k:round(v,2) for k,v in worst.items()})
# CLI
W=R+"/probes/w7/perf"; os.makedirs(W,exist_ok=True); cw={}
for n in (100,400,1000):
    for k,rows in shapes(n).items():
        f=W+"/in.jsonl"; open(f,"w").write("\n".join(json.dumps(r) for r in rows)+"\n")
        t=time.time(); subprocess.run(["python3","-I",SKR+"/scripts/extract_register.py",f,W+"/o"],capture_output=True); d=time.time()-t
        # validator
        t2=time.time(); subprocess.run(["python3","-I",SKR+"/scripts/register_validate.py",W+"/o/register-partial.json","--now","2026-11-12T12:00:00Z"],capture_output=True); d2=time.time()-t2
        cw[(n,"x")]=max(cw.get((n,"x"),0),d); cw[(n,"v")]=max(cw.get((n,"v"),0),d2)
        if max(d,d2)>1: print("CLI",n,k,round(d,2),round(d2,2))
print("worst CLI extract/validate:",{f"{k[0]}-{k[1]}":round(v,2) for k,v in cw.items()})
