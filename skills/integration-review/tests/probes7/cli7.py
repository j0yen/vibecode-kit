import os, tempfile
_HERE = os.path.dirname(os.path.abspath(__file__))
SKR = os.environ.get("IRS") or os.path.normpath(os.path.join(_HERE, "..", ".."))
R = os.environ.get("IRV_PROBE_WORK") or tempfile.mkdtemp(prefix="irv7-probes-")
for _d in ("out", "probes", "probes/w7"):
    os.makedirs(os.path.join(R, _d), exist_ok=True)
import os, subprocess, json, sys
SC=SKR+"/scripts/"; W=R+"/probes/w7/cli"; os.makedirs(W,exist_ok=True)
def mk(*p): return "".join(p)
CAN={"ghp":mk("gh","p_","Zq9Xw3Lm5Nb7Vc1Kd4Jf6Hg8Sa2Pe0Ro3Ti5U"),"sk":mk("sk","_li","ve_","51Hq3w9Zx7Vb2Nm4Kd8"),"bearer":mk("Bear","er ","abc","DEF123xyz789"),
 "url":mk("https://ali","ce:hun","ter2x9@h.example"),"akia":mk("AKI","AIOSF","ODNN7EXAMPLE"),"jwt":mk("ey","JhbGciOi","JIUzI1NiJ9")}
rows=[]
def run(label,script,args,canary):
    p=subprocess.run(["python3","-I",SC+script,*args],capture_output=True,text=True,cwd=W); o=p.stdout+p.stderr
    key=canary.split()[-1][:10] if canary else None
    leak = any(c in o for c in {canary, canary.split()[-1][:12], canary.split("@")[0][-12:]}) 
    rows.append((label,p.returncode,leak)); print(("LEAK " if leak else "ok   ")+label,p.returncode, ("|"+o.replace("\n"," / ")[:200]) if leak else "")
good_schema=W+"/good.json"; json.dump({"type":"object"},open(good_schema,"w"))
for cn,c in CAN.items():
    fn=c.replace("/","_").replace(" ","_")
    # nonexistent path as each positional
    run(f"sc-missing-{cn}","schema_compat.py",[good_schema,fn],c)
    run(f"sc-missing-first-{cn}","schema_compat.py",[fn,good_schema],c)
    run(f"sc-dir-{cn}","schema_compat.py",[good_schema,os.path.join(W,"")+"."],c)
    d=os.path.join(W,fn+"_d"); os.makedirs(d,exist_ok=True)
    run(f"sc-isdir-{cn}","schema_compat.py",[good_schema,d],c)
    for nm,content in (("badutf",b"\xff\xfe\x00{"),("list",b"[1]"),("badjson",b"{"),("str",b'"x"'),("dupkey",b'{"a":1,"a":2}')):
        f=os.path.join(W,fn+"_"+nm+".json"); open(f,"wb").write(content)
        run(f"sc-{nm}-{cn}","schema_compat.py",[good_schema,f],c)
        run(f"rv-{nm}-{cn}","register_validate.py",[f,"--now","2026-11-12T12:00:00Z"],c)
        run(f"lm-{nm}-{cn}","lost_message_check.py",[f],c)
        run(f"ex-{nm}-{cn}","extract_register.py",[f,W+"/xo"],c)
    run(f"rv-missing-{cn}","register_validate.py",[fn],c)
    run(f"rv-now-{cn}","register_validate.py",[good_schema,"--now",c],c)
    run(f"rv-extra-{cn}","register_validate.py",[good_schema,c],c)
    run(f"lm-missing-{cn}","lost_message_check.py",[fn],c)
    run(f"lm-extra-{cn}","lost_message_check.py",[good_schema,c],c)
    run(f"ex-missing-{cn}","extract_register.py",[fn,W+"/xo"],c)
    run(f"ex-flag-{cn}","extract_register.py",[good_schema,W+"/xo",c],c)
    # unwritable outdir: parent is a file
    pf=os.path.join(W,fn+"_file"); open(pf,"w").write("x")
    run(f"ex-outdir-{cn}","extract_register.py",[good_schema,os.path.join(pf,fn)],c)
    # discriminator
    src=W+"/src.sh"; open(src,"w").write("X='^(a|b)$'\n")
    run(f"dc-missing-{cn}","discriminator_check.py",[fn,"--line","1","--names","a"],c)
    run(f"dc-line-{cn}","discriminator_check.py",[src,"--line",c,"--names","a"],c)
    run(f"dc-flag-{cn}","discriminator_check.py",[src,"--line","1","--names","a","--"+c.replace(" ","")],c)
    run(f"dc-flag2-{cn}","discriminator_check.py",[src,"--line","1","--names","a","--sha256",c],c)
    run(f"dc-names-{cn}","discriminator_check.py",[src,"--line","1","--names",c],c)
    run(f"dc-expect-{cn}","discriminator_check.py",[src,"--line","1","--names","a","--expect-refuse",c],c)
    run(f"dc-extra-{cn}","discriminator_check.py",[src,"--line","1","--names","a",c],c)
    run(f"dc-choice-{cn}","discriminator_check.py",[src,"--line","1","--names","a","--lin"+c.replace(" ","")],c)
    run(f"dc-ambig-{cn}","discriminator_check.py",[src,"--n="+c.replace(" ",""),"--line","1"],c)
    open(W+"/src2.sh","w").write("X='%s'\n"%c.replace("'",""))
    run(f"dc-pattern-{cn}","discriminator_check.py",[W+"/src2.sh","--line","1","--names","a"],c)
    run(f"dc-pattern-json-{cn}","discriminator_check.py",[W+"/src2.sh","--line","1","--names","a","--json"],c)
print("leaks:",sum(1 for r in rows if r[2]),"of",len(rows))
