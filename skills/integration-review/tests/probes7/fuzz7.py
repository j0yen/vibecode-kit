import os, tempfile
_HERE = os.path.dirname(os.path.abspath(__file__))
SKR = os.environ.get("IRS") or os.path.normpath(os.path.join(_HERE, "..", ".."))
R = os.environ.get("IRV_PROBE_WORK") or tempfile.mkdtemp(prefix="irv7-probes-")
for _d in ("out", "probes", "probes/w7"):
    os.makedirs(os.path.join(R, _d), exist_ok=True)
import random, itertools, json, importlib.util, sys
from mods6 import *
RV=importlib.util.spec_from_file_location("rv",SKR+"/scripts/register_validate.py"); rv=importlib.util.module_from_spec(RV); RV.loader.exec_module(rv)
N=NEW._N
random.seed(7)
repos=["o1/r","o2/r","https://github.com/o1/r.git","git@github.com:o1/r",None,"UNKNOWN"]
cms=[cm("1"),cm("2"),None]
paths=["a.py","./a.py","b.py",None]
bad=0;dup=0;n=0;idc=0
for it in range(6000):
    k=random.randint(2,7); rows=[]
    for i in range(k):
        shaid=random.random()<.25
        ident=sha(random.choice("ab")) if shaid else random.choice(cms)
        rows.append(row(i,repo=random.choice(repos),ident=ident,path=random.choice(paths),ev="side=producer"))
    out=NEW.convert(rows,"partial"); recs=out["register"]["records"]
    n+=1
    ids=[r["record_id"] for r in recs]
    if len(set(ids))!=len(ids): idc+=1; print("ID COLLISION",rows); 
    res=rv.validate(out["register"],rv.load_schema(),None)
    if any(f["code"]=="duplicate-record" for f in res["findings"]): dup+=1; 
    # invariant: a record with path never holds rows with provably different repo / commit
    by={r["record_id"]:r for r in recs}
    for r in recs:
        srcs=r.get("sources",[r.get("source_identity")])
        if r.get("path_or_command") and not r.get("fusion_basis"):
            rp={N.repo_id(s["repo"]) for s in srcs if s["repo"]!="UNKNOWN"}; cs={s["commit"] for s in srcs if "commit" in s}
            if len(rp)>1 or len(cs)>1: bad+=1; print("BAD merge",r["source_rows"],rp,cs)
print("iters",n,"idcollisions",idc,"validator-duplicate",dup,"bad-merge",bad)
