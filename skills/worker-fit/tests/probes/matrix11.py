"""Retained reviewer probe (re-review 11 of 74551e2c, probes/matrix11.py), source path made relative to this repo. Not collected by unittest discovery."""
import sys,random,itertools
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import envelope_validate as ev, queue_adapter as qa
r=random.Random(1111)
A="abcdefghijklmnopqrstuvwxyz";B=A.upper()+A+"0123456789"
hx=lambda n:"".join(r.choice("0123456789abcdef") for _ in range(n))
hxm=lambda n:(lambda s:s if any(c.isdigit() for c in s) and any(c.isalpha() for c in s) else hxm(n))(hx(n))
lc=lambda n:"".join(r.choice(A) for _ in range(n))
b62=lambda n:"".join(r.choice(B) for _ in range(n))
uu=lambda:"-".join([hxm(8),hxm(4),hxm(4),hxm(4),hxm(12)])
FIELDS=[("host","host"),("unit","ident"),("child","ident"),("session","ident"),("invocation","ident"),("account","ident"),("model","ident"),("effort","ident"),
 ("consumer","ident"),("alternate","ident"),("owner","ident"),("current_owner","ident"),("reviewed_by","ident"),("repo","ident"),("branch","ident"),("task","ident"),("task_id","ident"),
 ("result","path"),("artifact","path"),("event","path"),("evidence-ref","path"),("ref","path"),("head","sha"),("sess-id","ident"),("named","ident"),("target","path")]
SH={}
for _ in range(1):
  h32,h40,h64,u=hxm(32),hxm(40),hxm(64),uu()
  SH={"hex32":h32,"hex40":h40,"hex64":h64,"uuid":u,"pre-hex32":"build-"+h32,"pre-hex12":"acct-"+hxm(12),"pre-uuid":"acct-"+u,
      "b62-8":b62(8),"b62-12":b62(12),"b62-20":b62(20),"b62-40":b62(40),"lc-16":lc(16),"lc8-lc8":lc(8)+"-"+lc(8),
      "sk-b62-24":"sk-"+b62(24),"ghp":"ghp_"+b62(36),"pre-b62-16":"acct-"+b62(16),"r7-b62":"r7-"+b62(16),"feat-b62":"feat-"+b62(16),
      "dns-rand":lc(12)+"."+lc(12)+".net","b64":b62(43)+"=","hex-dash":"-".join(hx(4) for _ in range(8)),
      "digits16":"".join(r.choice("0123456789") for _ in range(16)),"digits-3x7":"-".join("".join(r.choice("0123456789") for _ in range(7)) for _ in range(3)),
      "words8":"-".join(r.choice(["claude","opus","build","review","worker","task","run","gate"]) for _ in range(8)),
      "unit-hex32":"wm-build-%s.service"%h32,"unit-b62":"wm-build-%s.service"%b62(16),"path-b62":"/mnt/ssd/out/"+b62(24)+".md","path-hex32":"/mnt/ssd/out/evt-%s.json"%h32,
      "path-hex64":"/mnt/ssd/out/%s"%h64}
out={}
for f,k in FIELDS:
  pr=[]
  for n,v in SH.items():
    o=ev.show(f,v,k)
    if v in o: pr.append(n)
  out[f]=pr
for f,pr in out.items(): print("%-14s prints: %s"%(f,", ".join(pr)))
# rows
print("--- rows")
for f in ("row","owner","claim","status","waits-on","seq"):
  pr=[n for n,v in SH.items() if v in qa._gate(f,v)]
  print("%-10s prints: %s"%(f,", ".join(pr)))
