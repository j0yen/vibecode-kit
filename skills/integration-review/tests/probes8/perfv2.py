import time, sys, importlib.util, json
from mods6 import SKR, R
sp=importlib.util.spec_from_file_location("rv",SKR+"/scripts/register_validate.py"); rv=importlib.util.module_from_spec(sp); sp.loader.exec_module(rv)
def mk(i,repo,commit,path="a.py"):
    si={"version":"v","available":True,"captured_at":"2026-11-12T09:00:00Z"}
    if repo: si["repo"]=repo
    if commit: si["commit"]=commit
    return {"record_id":f"r{i}","family":"IF001","role":"producer","host":"h","component":"c","interface_kind":"http","installed_state":"source-only","path_or_command":path,"source_identity":si}
shapes={
 "loose-distinct-repo-nocommit": lambda n:[mk(i,f"o{i}/r",None) for i in range(n)],
 "loose-nocommit-same-repo-distinct-path-key": lambda n:[mk(i,"o/r",None,path=f"p{i}") for i in range(n)],
 "full-distinct-repo": lambda n:[mk(i,f"o{i}/r","%040x"%i) for i in range(n)],
 "full-same-repo-distinct-commit": lambda n:[mk(i,"o/r","%040x"%i) for i in range(n)],
 "norepo-distinct-commit": lambda n:[mk(i,None,"%040x"%i) for i in range(n)],
}
for k,f in shapes.items():
    out=[]
    for n in (500,1000,2000,4000):
        recs=f(n); t=time.time(); g=rv._duplicate_groups(recs); out.append(f"n={n}:{time.time()-t:.2f}s groups={len(g)}")
    print(k," ".join(out))
