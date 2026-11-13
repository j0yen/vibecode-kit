import time, subprocess, json, os
from mods6 import *
W=R+"/probes/w8/perfv3"; os.makedirs(W,exist_ok=True)
def run(label,mk):
  line=[]
  for n in (500,1000,2000,4000):
    f=W+"/in.jsonl"; open(f,"w").write("\n".join(json.dumps(r) for r in mk(n))+"\n")
    t=time.time(); subprocess.run(["python3","-I",SKR+"/scripts/extract_register.py",f,W+"/o"],capture_output=True); d=time.time()-t
    t=time.time(); p=subprocess.run(["python3","-I",SKR+"/scripts/register_validate.py",W+"/o/register-partial.json","--now","2026-11-12T12:00:00Z"],capture_output=True,text=True); v=time.time()-t
    line.append(f"n={n}: extract {d:.2f}s validate {v:.2f}s rc{p.returncode}")
  print(label," | ".join(line),flush=True)
run("same-path, distinct repo, sha identity (no commit)",lambda n:[row(i,repo=f"o{i}/r",ident="path+sha256:/p/x.py "+("%064x"%i),path="a.py",ev="side=producer") for i in range(n)])
run("same-path, same repo, distinct commits",lambda n:[row(i,repo="o/r",ident="commit %040x"%i,path="a.py",ev="side=producer") for i in range(n)])
run("same-path, no repo, distinct commits",lambda n:[row(i,repo=None,ident="commit %040x"%i,path="a.py",ev="side=producer") for i in range(n)])
