import random, importlib.util, json, collections
from mods6 import *
sp=importlib.util.spec_from_file_location("rv",SKR+"/scripts/register_validate.py"); rv=importlib.util.module_from_spec(sp); sp.loader.exec_module(rv)
random.seed(77)
repos=["o1/r","o2/r","https://github.com/o1/r.git","git@github.com:o2/r.git",None,"UNKNOWN","tbd","GitLab.com/o1/r"]
ids=[cm("1"),cm("2"),sha("a"),sha("b"),"path+sha256:/q/y.py "+"a"*64,None,None,"v1.2"]
paths=["a.py","b.py","./a.py","src/../a.py",None,None]
comps=["c","c","d"]
stats=collections.Counter()
for it in range(5000):
    rows=[row(i,repo=random.choice(repos),ident=random.choice(ids),path=random.choice(paths),comp=random.choice(comps),role=random.choice(["producer","consumer"]),ev="side=producer side=consumer"[:13] if random.random()<.5 else "side=consumer") for i in range(random.randint(2,12))]
    for h in (False,True):
        o=NEW.convert(rows,"partial",heuristic_fusion=h)["register"]
        recs=o["records"]
        rid=[r["record_id"] for r in recs]
        if len(set(rid))!=len(rid): stats["idcollision"]+=1
        g=rv._duplicate_groups(recs)
        if g: stats["validator-dup-heur" if h else "validator-dup"]+=1; 
        if g and stats["shown"]<2: stats["shown"]+=1; print(json.dumps(rows)[:700]); print([[r["record_id"] for r in x] for x in g])
        # rows lost?
        allrows=sorted(x for r in recs for x in r["source_rows"])
        if allrows!=list(range(1,len(rows)+1)): stats["rowloss"]+=1
print(dict(stats))
