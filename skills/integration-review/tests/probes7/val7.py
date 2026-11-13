import json
from t6 import *
def S(repo=None,commit=None,**kw):
    d={"version":commit or "v1","available":True,"captured_at":"2026-11-12T09:00:00Z"}
    if repo: d["repo"]=repo
    if commit: d["commit"]=commit; d["raw"]="commit "+commit
    d.update(kw); return d
H="a"*40; H2="b"*40
def R(rid,path="a.py",**kw):
    r=rec(rid,path=path,state="source-only"); r.pop("source_identity",None); r.update(kw); return r
def run(label,recs,expect_rc):
    rc,o=V(reg(recs+[rec("cons",role="consumer",comp="c2")]),label=label)
    keys=[l for l in o.splitlines() if "duplicate" in l.lower() or "REFUSED" in l or l.startswith("OK")]
    T(label,"validator-dup",f"rc {expect_rc}",rc==expect_rc,f"rc {rc} {keys[:3]}")
run("dup-identical-sources",[R("r1",source_identity=S("o/r",H)),R("r2",source_identity=S("o/r",H))],1)
run("dup-one-has-commit-other-not",[R("r1",source_identity=S("o/r",H)),R("r2",source_identity=S("o/r"))],1)
run("dup-one-has-repo-other-unknown",[R("r1",source_identity=S("o/r",H)),R("r2",source_identity=S(None,H))],1)
run("dup-repo-spelling",[R("r1",source_identity=S("o/r",H)),R("r2",source_identity=S("https://github.com/O/R.git",H))],1)
run("dup-distinct-commit",[R("r1",source_identity=S("o/r",H)),R("r2",source_identity=S("o/r",H2))],0)
run("dup-distinct-repo",[R("r1",source_identity=S("o/r",H)),R("r2",source_identity=S("p/r",H))],0)
run("dup-sources-list-union",[R("r1",sources=[S("o/r",H),S("p/r",H)]),R("r2",source_identity=S("o/r",H))],1)
run("dup-no-path-diff-repo",[R("r1",path=None,source_identity=S("o/r",H)),R("r2",path=None,source_identity=S("p/r",H2))],1)
