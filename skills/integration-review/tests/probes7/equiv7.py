import random
from mods6 import *
N=NEW._N
random.seed(11)
def ref_groups(rows):
    items=list(enumerate(rows,1)); eps={}
    for n,r in items:
        si=NEW.parse_identity(r); ev=NEW.evidence_text(r); role,_=NEW.norm_role(r,ev)
        path=NEW._s(r.get("path_or_command")); host=NEW._s(r.get("host")) or "UNKNOWN"; comp=NEW._s(r.get("component")) or "UNKNOWN"
        k=(r.get("family"),role,host,comp,r.get("interface_kind"),path)
        placed=False
        for g in eps.setdefault(k,[]):  # D2 (re-review 7): path-less rows follow the same repo/commit rule
            repos={N.repo_id(s["repo"]) for _,s in g if s["repo"]!="UNKNOWN"}
            cms={s["commit"] for _,s in g if "commit" in s}
            ok=True
            if si["repo"]!="UNKNOWN" and repos and N.repo_id(si["repo"]) not in repos: ok=False
            if cms and "commit" in si and si["commit"] not in cms: ok=False
            if ok: g.append((n,si)); placed=True; break
        if not placed: eps[k].append([(n,si)])
    return [frozenset(n for n,_ in g) for gs in eps.values() for g in gs]
repos=["o1/r","o2/r","https://github.com/o1/r.git",None,"UNKNOWN"]
bad=0
for it in range(4000):
    rows=[row(i,repo=random.choice(repos),ident=random.choice([cm("1"),cm("2"),sha("a"),None]),path=random.choice(["a.py","b.py",None,"a.py"]),ev="side=producer") for i in range(random.randint(2,9))]
    ref=set(ref_groups(rows)); out=NEW.convert(rows,"partial")["register"]["records"]
    outs=[frozenset(r["source_rows"]) for r in out]
    for r in out:
        s=frozenset(r["source_rows"])
        if r.get("fusion_basis"):
            if not any(g<=s for g in ref) or set().union(*[g for g in ref if g<=s])!=s: bad+=1; print("fused not union",rows)
        elif s not in ref: bad+=1; print("diff",s,ref)
print("equiv mismatches",bad)
