"""Retained reviewer probe (re-review 10 of 8f250d8e, probes/pairs10.py), source path made relative to this repo. Run: python3 pairs10.py. Not collected by unittest discovery; test_review_fixes11.RetainedReviewerProbes runs it."""
import sys,random,json
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import envelope_validate as ev, queue_adapter as qa
r=random.Random(1010)
A="abcdefghijklmnopqrstuvwxyz";B=A.upper()+A+"0123456789"
hx=lambda n:"".join(r.choice("0123456789abcdef") for _ in range(n))
lc=lambda n:"".join(r.choice(A) for _ in range(n))
b62=lambda n:"".join(r.choice(B) for _ in range(n))
dg=lambda n:"".join(r.choice("0123456789") for _ in range(n))
uu=lambda:"-".join([hx(8),hx(4),hx(4),hx(4),hx(12)])
def idshow(f,v,k="ident"): return ev.show(f,v,k)
def rowshow(f,v): return qa._gate(f,v)
def redshow(t): return ev.redact(t)
# (label, kind, field, pos, neg) ; kind: id|path|host|row|free
P=[
("unit","id","worker.unit","wm-build-wf1663-impl.service","wm-build-"+b62(9)+".service"),
("unit-hex","id","worker.unit","run-r"+hx(12)+".scope","run-r"+hx(32)+".scope"),
("unit-tmpl","id","worker.unit","app-claude@"+hx(8)+".service","app-claude@"+hx(8)+hx(8)+hx(8)+".service"),
("invocation","id","worker.invocation",hx(32),"build-"+hx(32)),
("session-uuid","id","worker.session",uu(),"hunter-"+lc(16)),
("session-ulid","id","worker.session","01HZXK3M7Q2V8N5R4T6Y9B0C1D","01HZXK3M7Q2V8N5R4T6Y9B0C1D01HZXK3M7Q"),
("child","id","worker.child","wm-1663-r10",lc(8)+"-"+lc(8)),
("consumer","id","consumer.named","claude-1275054-hermes-aae","claude-1275054-"+b62(10)),
("artifact","path","result.artifact","/mnt/ssd/cargo-target/r7-wfit-20261112/out/report.md","/mnt/ssd/cargo-target/r7/out/"+b62(12)+".md"),
("event","path","result.event","evt-20261113-0042","evt-"+dg(10)+"-"+dg(10)),
("head","sha","target.head",hx(40),None),
("host-dns","host","worker.host","ryzen7.tail1234.ts.net",lc(12)+"."+lc(12)+".net"),
("host-ec2","host","worker.host","ip-10-0-1-23.ec2.internal","ip-"+lc(10)+".ec2.internal"),
("host-ipv4","host","worker.host","10.0.1.23","10.0.1.23@"+lc(9)),
("host-ipv6","host","worker.host","fe80::1%eth0","ac60:992a:c792:dba9:b936:fbc9:69cc:bbd6"),
("task","id","task_id","A1663","A1663-"+b62(8)+"-"+b62(8)),
("owner","id","owner","r7","r7:"+lc(9)),
("repo","id","target.repo","j0yen/vibecode-kit","j0yen/"+b62(14)),
("branch","id","target.branch","r7/worker-fit-skill","r7/"+lc(7)+"-"+lc(7)+"-"+lc(7)),
("account","id","worker.account","jyen.tech",hx(64)),
("model","id","worker.model","claude-opus-5-5","claude-"+lc(7)+"-"+lc(7)+"-"+lc(7)),
("row_id","row","row_id","d-20261101-173305-aide-f24a","d-"+b62(6)+"-"+b62(6)+"-"+b62(6)+"-"+b62(6)),
("row_owner","row","owner","hermes","hermes-"+lc(9)),
("row_claim","row","claim","r7-wfr10-20261113-worker","r7-"+lc(5)+"-"+lc(5)+"-"+lc(5)+"-"+lc(5)),
("row_status","row","status","running","running-"+lc(6)+"-"+lc(6)),
("row_wait","row","waits_on","A1662","A1662-"+lc(5)+"-"+lc(5)+"-"+lc(5)),
("kv","free","","token=%s",None),
]
res=[]
def chk(lbl,kind,f,pos,neg):
    if kind=="free": return
    sh={"id":lambda v:idshow(f,v),"path":lambda v:idshow(f,v,"path"),"host":lambda v:idshow(f,v,"host"),"sha":lambda v:idshow(f,v,"sha"),"row":lambda v:rowshow(f,v)}[kind]
    pp=pos in sh(pos); nh=(neg is None) or (neg not in sh(neg))
    res.append((lbl,pp,nh,neg))
for p in P: chk(*p)
# free pair-form pairs: name,pos value,neg value
F=[("mfa-4dig","count=1234","mfa=1234"),("mypass","pid=4242","mypass=abc-def"),("seed","exit=0","seedphrase=nested-golden-shadow"),("recov","retry=3","recoverycode=1234"),
   ("flag","--timeout 30","--unlockpw 1234"),("json",'{"line": 12}','{"totp": "4821"}'),("quote",'name="build ok"','blob="abc def"'),("cred-prose","password rotated","password is hunter2"),
   ("esc",'{\\"line\\": 12}','{\\"mfa\\": \\"1234\\"}'),("userinfo","https://host.example/x","https://bob:dr4gon@host.example/x"),("hex-name","head=a1b2c3d4e5f6","blob=a1b2c3d4e5f6")]
for lbl,pos,neg in F:
    o1=ev.redact(pos); o2=ev.redact(neg)
    pv=pos.split("=")[-1].strip(' "\\}')
    nv={"mfa-4dig":"1234","mypass":"abc-def","seed":"nested-golden-shadow","recov":"1234","flag":"1234","json":"4821","quote":"abc def","cred-prose":"hunter2","esc":"1234","userinfo":"dr4gon","hex-name":"a1b2c3d4e5f6"}[lbl]
    res.append(("free:"+lbl,pv in o1 or o1==pos,nv not in o2,nv))
ok=0
for lbl,pp,nh,neg in res:
    good=pp and nh; ok+=good
    print("%-16s pos_prints=%-5s neg_hidden=%-5s %s"%(lbl,pp,nh,"" if nh else "NEG-LEAK %s"%str(neg)[:50]))
print("pairs ok %d/%d"%(ok,len(res)))
