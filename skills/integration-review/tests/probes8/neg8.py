import json, io, contextlib
from t6 import *
import importlib.util
sp=importlib.util.spec_from_file_location("n",SKR+"/scripts/ir_norm.py"); NN=importlib.util.module_from_spec(sp); sp.loader.exec_module(NN)
ROWS.clear()
c1,c2="1"*40,"2"*40
def er(**kw):
    d=erow(evidence="side=producer"); d.update(kw); return {k:v for k,v in d.items() if v is not None}
def nrecs(rows,*a):
    rc,o,d,out=X(rows,*a); reg=d["register-partial.json"]; return rc,(reg["records"] if reg else None),d
# ---- extractor identity
rc,r,d=nrecs([er(path_or_command=None,source_identity="commit "+c1),er(path_or_command=None,source_identity=None)]); T("e01","identity","1 record: pathless, same repo, one states commit other none",len(r)==1,f"{len(r)}")
rc,r,d=nrecs([er(path_or_command=None,source_repo="o1/r",source_identity=None),er(path_or_command=None,source_repo="o2/r",source_identity=None)]); T("e02","identity","2 records: pathless distinct repos, no commits",len(r)==2,len(r))
rc,r,d=nrecs([er(source_repo="o1/r",source_identity="commit "+c1),er(source_repo="o2/r",source_identity="commit "+c1)]); T("e03","identity","2 records, 2 ids: two repos share one commit sha, same path",len(r)==2 and len({x["record_id"] for x in r})==2,len(r))
rc,r,d=nrecs([er(path_or_command=None,source_repo="https://github.com/o/r.git",source_identity="commit "+c1),er(path_or_command=None,source_repo="git@github.com:o/r",source_identity="commit "+c1)]); T("e04","identity","1 record: pathless spelling variants same commit",len(r)==1,len(r))
rc,r,d=nrecs([er(path_or_command=None,source_repo="o1/r",source_identity=None),er(path_or_command=None,source_repo="o2/r",source_identity=None)],"--heuristic-fusion"); T("e05","identity","2 records under --heuristic-fusion: pathless rows never fuse across repos",len(r)==2,len(r))
sh1="path+sha256:/p/x.py "+"a"*64
rc,r,d=nrecs([er(source_repo="o1/r",source_identity=sh1,path_or_command="a.py"),er(source_repo="o2/r",source_identity=sh1,path_or_command="b.py"),er(path_or_command=None,source_repo="o3/r",source_identity="commit "+c1)])
T("e06","identity","fused sha pair + pathless member stay 2 records with distinct ids; validator passes",len(r)==2 and len({x["record_id"] for x in r})==2,[ (x["record_id"],x.get("fusion_basis")) for x in r])
rc,r,d=nrecs([er(source_repo="o1/r",source_identity="commit "+c1),er(source_repo="n/a",source_identity="commit "+c1),er(source_repo="?",source_identity="commit "+c1)]); T("e07","identity","1 record: placeholder repos are unstated",len(r)==1,len(r))
rc,r,d=nrecs([er(source_repo="git@github.com:o/r.git",source_identity="commit "+c1)]); T("e08","redaction-trace","scp repo spelling survives in register output (data, not message)",r and any("git@github.com" in json.dumps(s) for s in r[0].get("sources",[r[0].get("source_identity")])),json.dumps(r[0].get("source_identity"))[:100] if r else None)
# ---- validator duplicates
def S(repo=None,commit=None):
    d={"version":commit or "v1","available":True,"captured_at":"2026-11-12T09:00:00Z"}
    if repo: d["repo"]=repo
    if commit: d["commit"]=commit; d["raw"]="commit "+commit
    return d
def R_(rid,path="a.py",**kw):
    r=rec(rid,path=path,state="source-only"); r.pop("source_identity",None); r.update(kw); return r
def VD(i,exp_rc,recs,exp):
    rc,o=V(reg(recs+[rec("cons",role="consumer",comp="c2")]),label=i)
    T(i,"validator-dup",exp,rc==exp_rc,f"rc {rc} "+" ".join(l for l in o.splitlines() if l.startswith(("OK","REFUSED")))[:100])
VD("v01",1,[R_("r1",source_identity=S("o/r","a"*40)),R_("r2",source_identity=S("o/r","A"*40))],"dup: commit differs only by case")
VD("v02",1,[R_("r1",source_identity=S("o/r","a"*40)),R_("r2",source_identity=S("o/r","a"*7))],"dup: 7-char prefix of the same commit")
VD("v03",1,[R_("r1",sources=[S("o1/r"),S("o2/r")]),R_("r2",source_identity=S("o2/r"))],"dup: multi-source record shares o2/r")
VD("v04",0,[R_("r1",source_identity=S("o/r","c"*40)),R_("r2",source_identity=S("o/r","b"*40))],"distinct: different stated commits")
VD("v05",0,[R_("r1",source_identity=S("o1/r","a"*40)),R_("r2",source_identity=S("o2/r","a"*40))],"distinct: same sha, different repos")
VD("v06",1,[R_("r1",source_identity=S("o/r","a"*40)),R_("r2",source_identity=S("o/r","b"*40)),R_("r3",source_identity=S("o/r"))],"dup: commit-less record beside two commit records")
VD("v07",1,[R_("r1",path=None,source_identity=S("o/r","a"*40)),R_("r2",path=None,source_identity=S("o/r"))],"dup: pathless, one omits commit")
VD("v08",0,[R_("r1",path=None,source_identity=S("o1/r")),R_("r2",path=None,source_identity=S("o2/r"))],"distinct: pathless distinct repos")
VD("v09",1,[R_("r1",source_identity=S("https://github.com/o/r.git")),R_("r2",source_identity=S("git@github.com:o/r"))],"dup: spellings of one repo, no commits")
VD("v10",1,[R_("r1",source_identity=S("o/r")),R_("r2",source_identity=S("o/r"),installed_state="installed")],"dup: same repo, differing installed state")
# ---- negated evidence
def role(ev,claimed="producer"):
    rc,r,d=nrecs([er(role=claimed,evidence=ev)]); return r[0]["role"]
for i,(ev,exp) in enumerate([("no evidence that side=producer","UNKNOWN"),("not verified that side=producer","UNKNOWN"),("has not been confirmed as side=producer","UNKNOWN"),("side=producer is false","UNKNOWN"),("it was never really established that side=producer","UNKNOWN"),("side=producer; no regressions seen","producer"),("side=consumer, not side=producer","UNKNOWN")],1):
    a=role(ev); T(f"ne0{i}","negated-evidence",f"role {exp} for {ev!r}",a==exp,a)
def missing(ref,declared="all-interfaces-complete"):
    g=good(); g[0]["evidence"]=[{"ref":ref,"observed_at":"2026-11-12T10:00:00Z"}]
    rc,o=V(reg(g),label="ev"); return rc,("missing-evidence" in o)
for i,ref in enumerate(["verification unchecked","skipped","pending review","tests: 0 failed, 12 passed","TBD fill in later","check was waived","claim disproved","evidence is invalid"],1):
    rc,m=missing(ref); T(f"ne1{i}","negated-evidence",f"complete refused (missing-evidence) for non-evidence {ref!r}" if "0 failed" not in ref else "legit '0 failed, 12 passed' accepted",(m if "0 failed" not in ref else not m),f"rc {rc} missing={m}")
# ---- redaction
def U(s): return NN.redact(s)
T("r01","redaction","file-name AKIA after digit masked",U("backup1"+"AKI"+"A"+"IOSFODNN7EXAMPLE.json")==NN.REDACTED,"")
T("r02","redaction-trace","record id 'pkg@1.2.3' (version pin, not an e-mail) kept traceable",U("pkg@1.2.3")=="pkg@1.2.3",U("pkg@1.2.3"))
T("r03","redaction-trace","two distinct version-pinned ids stay distinguishable",U("pkg@1.2.3")!=U("pkg@2.0.0"),U("pkg@1.2.3")+" / "+U("pkg@2.0.0"))
T("r04","redaction","e-mail with IDN domain masked",U("alice@bücher.example")==NN.REDACTED,U("alice@bücher.example"))
T("r05","redaction","e-mail @localhost masked",U("alice@localhost")==NN.REDACTED,U("alice@localhost"))
T("r06","redaction","quoted local part e-mail masked",U('"alice smith"@example.com')==NN.REDACTED,U('"alice smith"@example.com'))
T("r07","redaction","full-width @ e-mail masked",U("alice＠example.com")==NN.REDACTED,U("alice＠example.com"))
T("r08","redaction","percent-encoded @ e-mail masked",U("alice%40example.com")==NN.REDACTED,U("alice%40example.com"))
T("r09","redaction","ZWSP-split e-mail masked",U("alice​@example.com")==NN.REDACTED,U("alice​@example.com"))
pw="".join(["hun","ter","2x9"])
T("r10","redaction","URL cred with slash in password, host without dot",U("https://alice:%s/x@localhost/a"%pw)==NN.REDACTED,U("https://alice:%s/x@localhost/a"%pw))
T("r11","redaction","8-underscore separator URL cred in a file name",U("https:________alice:%s@h"%pw)==NN.REDACTED,"")
T("r12","redaction","ASIA session key id in free text",U("ctx "+"AS"+"IA"+"ABCDEFGH12345678 end")==NN.REDACTED,"")
# CLI-level: record id traceability in validator
g=[rec("p"),rec("svc@1.2.3",role="consumer",comp="c2",state="source-only",path="a.py"),rec("other",role="consumer",comp="c3",state="source-only",path="b.py")]
for r_ in g[1:]: r_["evidence"]=[]
rc,o=V(reg(g),label="traceid")
T("r13","redaction-trace","REFUSED line still names the other gap record 'other' when one id contains '@'",("other" in [l for l in o.splitlines() if l.startswith("REFUSED")][0]) if any(l.startswith("REFUSED") for l in o.splitlines()) else False,[l for l in o.splitlines() if l.startswith("REFUSED")][:1])
g=[rec("p"),rec("tok-svc",role="consumer",comp="c2",state="source-only",path="a.py"),rec("other",role="consumer",comp="c3",state="source-only",path="b.py")]
for r_ in g[1:]: r_["evidence"]=[]
rc,o=V(reg(g),label="traceid2")
T("r14","redaction-trace","REFUSED line names 'other' when another id is 'tok-svc' (pre-existing class)",("other" in [l for l in o.splitlines() if l.startswith("REFUSED")][0]) if any(l.startswith("REFUSED") for l in o.splitlines()) else False,[l for l in o.splitlines() if l.startswith("REFUSED")][:1])
json.dump(ROWS,open(R+"/out/neg8.json","w"),indent=1)
print(sum(r["pass"] for r in ROWS),"/",len(ROWS))
