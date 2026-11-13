from t6 import *
import copy
import io,contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import val7
ROWS.clear()
from mods6 import NEW
S,H,H2=val7.S,val7.H,val7.H2
E="side=producer"
def er(**kw):
    d=erow(evidence=E); d.update(kw); return {k:v for k,v in d.items() if v is not None}
def nrec(rows): return len(NEW.convert(rows,"partial")["register"]["records"])
def N(i,cls,exp,ok,act): T(i,cls,exp,ok,act)
c1,c2="1"*40,"2"*40
# identity (extractor)
N("n01","fusion","2 records (same path, 2 repos, distinct commits)",nrec([er(source_repo="o1/r",source_identity="commit "+c1),er(source_repo="o2/r",source_identity="commit "+c2)])==2,"")
N("n02","fusion","2 records (github vs gitlab same owner/name, same commit)",nrec([er(source_repo="github.com/o/r",source_identity="commit "+c1),er(source_repo="gitlab.com/o/r",source_identity="commit "+c1)])==2,"")
N("n03","fusion","3 records (same repo, 3 commits, same path)",nrec([er(source_identity="commit "+h*40) for h in "123"])==3,"")
n=NEW.convert([er(source_identity="commit "+h*40) for h in "123"])["register"]["records"]; N("n04","fusion","3 distinct record_ids",len({r["record_id"] for r in n})==3,"")
N("n05","fusion","1 record (https/.git vs scp spelling same commit)",nrec([er(source_repo="https://github.com/o/r.git",source_identity="commit "+c1),er(source_repo="git@github.com:o/r",source_identity="commit "+c1)])==1,"")
N("n06","fusion","1 record (case + trailing slash spelling)",nrec([er(source_repo="https://GitHub.com/O/R/",source_identity="commit "+c1),er(source_repo="github.com/o/r",source_identity="commit "+c1)])==1,"")
N("n07","fusion","2 records: pathless rows, same repo, DISTINCT commits (SKILL: distinct commits never fuse)",nrec([er(path_or_command=None,source_identity="commit "+c1),er(path_or_command=None,source_identity="commit "+c2)])==2,f"got {nrec([er(path_or_command=None,source_identity='commit '+c1),er(path_or_command=None,source_identity='commit '+c2)])}")
N("n08","fusion","2 records: pathless rows from 2 repos (SKILL: different repos stay separate)",nrec([er(path_or_command=None,source_repo="o1/r",source_identity="commit "+c1),er(path_or_command=None,source_repo="o2/r",source_identity="commit "+c2)])==2,"got "+str(nrec([er(path_or_command=None,source_repo="o1/r",source_identity="commit "+c1),er(path_or_command=None,source_repo="o2/r",source_identity="commit "+c2)])))
sh1="path+sha256:/p/x.py "+"a"*64
o=NEW.convert([er(source_repo="o1/r",source_identity=sh1,path_or_command="a.py"),er(source_repo="o2/r",source_identity=sh1,path_or_command="b.py")])
N("n09","fusion","1 labelled record same-content-sha256 (diff repos, diff paths)",len(o["register"]["records"])==1 and o["register"]["records"][0].get("fusion_basis")=="same-content-sha256",o["stats"])
N("n10","fusion","stat fused_multi_source_components==1 for n09",o["stats"].get("fused_multi_source_components")==1,o["stats"])
N("n11","fusion","2 records: same sha, distinct stated commits",nrec([er(source_repo="o/r",source_identity="commit "+c1,path_or_command="a.py"),er(source_repo="o/r",source_identity="commit "+c2,path_or_command="b.py")])==2,"")
N("n12","fusion","2 records: same path normalised 'src/../a.py' vs 'a.py' repo o1 vs o2",nrec([er(source_repo="o1/r",source_identity="commit "+c1,path_or_command="src/../a.py"),er(source_repo="o2/r",source_identity="commit "+c1,path_or_command="a.py")])==2,"")
N("n13","fusion","2 records (UNKNOWN placeholder repo 'N/A' row vs o/r, same path, distinct commits)",nrec([er(source_repo="N/A",source_identity="commit "+c1),er(source_repo="o/r",source_identity="commit "+c2)])==2,"")
# validator duplicate key
def vr(a,b): return V(reg([a,b,rec("cons",role="consumer",comp="c2")]))[0]
r1=val7.R("r1",source_identity=S("o/r",H)); r1["installed_state"]="source-only"
b=val7.R("r2",source_identity=S("o/r")); b["installed_state"]="installed"
N("n14","validator-dup","rc1: same endpoint twice, conflicting states, commit stated on one side only (identical at cff40cb: rc1)",vr(r1,b)==1,"rc %s"%vr(r1,b))
b=val7.R("r2",source_identity=S("o/r",H)); b["installed_state"]="installed"
N("n15","validator-dup","rc1: same endpoint twice, same repo+commit, conflicting states",vr(r1,b)==1,"")
b=val7.R("r2",source_identity=S("p/r",H)); N("n16","validator-dup","rc0: same path, different repos",vr(r1,b)==0,"")
b=val7.R("r2",source_identity=S("o/r",H2)); N("n17","validator-dup","rc0: same path, distinct commits",vr(r1,b)==0,"")
b=val7.R("r2",source_identity=S("git@github.com:o/r.git",H)); a=val7.R("r1",source_identity=S("https://github.com/o/r",H)); N("n18","validator-dup","rc1: spelling variants of one repo, same commit",vr(a,b)==1,"")
b=val7.R("r1",source_identity=S("p/r",H)); N("n19","validator-dup","rc1: same record_id across repos",vr(r1,b)==1,"")
b=val7.R("r2",source_identity=S("o/r")); a=val7.R("r1",source_identity=S("o/r")); N("n20","validator-dup","rc1: neither states a commit, same repo",vr(a,b)==1,"")
b=val7.R("r2",source_identity=S("o/r",H)); a=val7.R("r1",sources=[S("o/r",H),S("p/r",H)]); N("n21","validator-dup","rc1: multi-source record repeats a single-source one's endpoint",vr(a,b)==1,"rc %s"%vr(a,b))
# extractor output validates
o=NEW.convert([er(source_repo="o1/r",source_identity="commit "+c1),er(source_repo="o2/r",source_identity="commit "+c1)])
rc,_=V(o["register"]); N("n22","roundtrip","extractor split records pass partial validate (no duplicate-record)",rc in (0,1) and "duplicate-record" not in _,_[-120:])
# redaction through CLIs
can={"ghp":"".join(["gh","p_","Zq9Xw3Lm5Nb7Vc1Kd4Jf6Hg8Sa2Pe0Ro3Ti5U"]),"sk":"".join(["sk","_li","ve_","51Hq3w9Zx7Vb2Nm4Kd8"]),"aws":"".join(["AKI","AIOSF","ODNN7EXAMPLE"]),"jwt":"".join(["ey","JhbGciOi","JIUzI1NiJ9"]),"bearer":"Bearer_"+"abcDEF123xyz789"}
def leak(o,cn): return cn[:14] in o
for k in ("ghp","sk","jwt"):
    cn=can[k]; good=wf({"type":"object"})
    rc,o=sh("n23","schema_compat.py",good,W+"/"+cn+".json"); N("n23-"+k,"redaction","schema missing file name masked",not leak(o,cn),"rc%s"%rc)
    f=W+"/"+cn+"_l.json"; open(f,"w").write("[1]"); rc,o=sh("n24","schema_compat.py",good,f); N("n24-"+k,"redaction","non-object schema file name masked",not leak(o,cn),"rc%s"%rc)
    src=W+"/s.sh"; open(src,"w").write("X='^a$'\n"); rc,o=sh("n25","discriminator_check.py",src,"--line","1","--names","a","--sha256",cn); N("n25-"+k,"redaction","discriminator --sha256 mismatch masked",not leak(o,cn),"rc%s"%rc)
    rc,o=sh("n26","discriminator_check.py",src,"--line",cn,"--names","a"); N("n26-"+k,"redaction","discriminator argparse int error masked",not leak(o,cn),"rc%s"%rc)
    rc,o=sh("n27","extract_register.py",good,W+"/"+cn+"_f/"+cn); N("n27-"+k,"redaction","extract unwritable out masked",not leak(o,cn),"rc%s"%rc)
cn=can["aws"]
for nm in (cn,"backup_"+cn,"prod-"+cn,"x"+cn+"y"):
    rc,o=sh("n28","schema_compat.py",wf({"type":"object"}),nm+".json"); N("n28-"+nm[:8],"redaction","AWS key id inside file name masked",not leak(o,cn),"rc%s"%rc)
pw="hun"+"ter2x9"
for nm,label in (("https:∕∕alice:%s@h.example"%pw,"division-slash"),("https:\\\\alice:%s@h.example"%pw,"backslash"),("https:__alice:%s@h.example"%pw,"underscores (the repaired form)")):
    rc,o=sh("n29","schema_compat.py",wf({"type":"object"}),W+"/"+nm+".json"); N("n29-"+label,"redaction","URL credential in file name (%s) masked"%label,pw not in o,"rc%s"%rc)
em="alice.smith@example.com"
rc,o=sh("n30","schema_compat.py",wf({"type":"object","properties":{em:{"type":"string"}},"required":[em]}),wf({"type":"object","properties":{em:{"type":"integer"}},"required":[em]}),"--direction","both"); N("n30","redaction","e-mail in a property name not printed (task step 5; SKILL promises credential-shaped only)",em not in o,"rc%s"%rc)
dump("neg7"); print(sum(r["pass"] for r in ROWS),"/",len(ROWS))
