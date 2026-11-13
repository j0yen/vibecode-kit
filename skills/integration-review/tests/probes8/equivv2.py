import random, importlib.util
from mods6 import SKR, R
sp=importlib.util.spec_from_file_location("rv",SKR+"/scripts/register_validate.py"); rv=importlib.util.module_from_spec(sp); sp.loader.exec_module(rv)
random.seed(int(__import__("sys").argv[1]))
repos=["o1/r","o2/r","https://github.com/o1/r.git","git@github.com:o2/r",None,"UNKNOWN","N/A"]
commits=["a"*40,"b"*40,None,None,"A"*40,"a"*7,"abcdef0","abcdef012"+"3"*10,"zz","B"*12]
def src(): 
    si={"version":"v","available":True,"captured_at":"2026-11-12T09:00:00Z"}
    r=random.choice(repos); c=random.choice(commits)
    if r: si["repo"]=r
    if c: si["commit"]=c
    return si
def rec(i):
    d={"record_id":f"r{i}","family":"IF001","role":"producer","host":"h","component":random.choice(["c","c","d"]),"interface_kind":"http","installed_state":"source-only","path_or_command":random.choice(["a.py","b.py",None])}
    d={k:v for k,v in d.items() if v is not None}
    if random.random()<0.25: d["sources"]=[src() for _ in range(random.randint(1,3))]
    else: d["source_identity"]=src()
    return d
bad=0
for it in range(8000):
    recs=[rec(i) for i in range(random.randint(2,24))]
    got={frozenset(r["record_id"] for r in g) for g in rv._duplicate_groups(recs)}
    # naive closure
    n=len(recs); par=list(range(n))
    def f(i):
        while par[i]!=i: par[i]=par[par[i]]; i=par[i]
        return i
    ids=[rv._ident(r) for r in recs]; keys=[rv._key(r) for r in recs]
    for i in range(n):
        for j in range(i):
            if keys[i]==keys[j] and rv._conflict(ids[i],ids[j]): par[f(i)]=f(j)
    comp={}
    for i in range(n): comp.setdefault(f(i),[]).append(recs[i]["record_id"])
    ref={frozenset(c) for c in comp.values() if len(c)>1}
    if got!=ref: bad+=1; print("MISMATCH",got,ref) if bad<4 else None
print("validator group mismatches",bad)
