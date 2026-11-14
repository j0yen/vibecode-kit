"""Retained reviewer probe (re-review 12 of d970f49c, probes/pairs12.py), source path made relative to this repo; literal canary words are
assembled from fragments. Not collected by unittest discovery."""
import os
import sys, random, json
S=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
if len(sys.argv)>1: S=sys.argv[1]
sys.path.insert(0,S)
import envelope_validate as ev, queue_adapter as qa
r=random.Random(1212)
A="abcdefghijklmnopqrstuvwxyz"; B=A.upper()+A+"0123456789"
b62=lambda n:"".join(r.choice(B) for _ in range(n))
lc=lambda n:"".join(r.choice(A) for _ in range(n))
hx=lambda n:"".join(r.choice("0123456789abcdef") for _ in range(n))
dg=lambda n:"".join(r.choice("0123456789") for _ in range(n))
Z=b62(14); Z2=lc(9)
P=[]
def idp(name,f,kind,pos,neg):
    P.append((name,lambda:(pos in ev.show(f,pos,kind), neg not in ev.show(f,neg,kind))))
def rowp(name,f,pos,neg):
    P.append((name,lambda:(pos in qa._gate(f,pos), neg not in qa._gate(f,neg))))
def freep(name,pos,neg,sec=None):
    sec=sec or Z
    P.append((name,lambda:(pos in ev.redact(pos), sec not in ev.redact(neg))))
def toolp(name,pos,neg,sec=None):
    sec=sec or Z
    P.append((name,lambda:(pos in ev.redact_tool(pos), sec not in ev.redact_tool(neg))))
# identity fields
idp("unit/tmux-scope","worker.unit","ident","tmux-spawn-7f3c9a1e-5b2d-4c8a-9e1f-0a2b3c4d5e6f.scope","tmux-spawn-"+b62(20)+".scope")
idp("unit/claude-at","worker.unit","ident","claude@ab12cd34.service","claude@"+b62(20)+".service")
idp("unit/wm-build-hex","worker.unit","ident","wm-build-3fa9c21b.service","wm-build-"+Z+".service")
idp("unit/words","worker.unit","ident","fleet-token-429-watch.timer",lc(11)+"-"+lc(11)+".timer")
idp("owner/ctl","current_owner","ident","controller","sun"+"shine")
idp("owner/r7-hex","current_owner","ident","r7-a1b2c3d4","r7-"+b62(16))
idp("owner/random2words","current_owner","ident","hermes",lc(5)+"-"+lc(6))
idp("reviewer/session","reviewed_by","ident","claude-2765718-r7-wfr12-20261113-worker","drag"+"onfly")
idp("branch/feat","target.branch","ident","feat/A1663-repair-12","feat/"+"pri"+"ncess")
idp("branch/hex-prefixed","target.branch","ident","r7/worker-fit-skill","r7/"+hx(40))
idp("repo/own","target.repo","ident","j0yen/vibecode-kit","j0yen/"+"mus"+"tang")
idp("repo/swarm","target.repo","ident","j0yen/swarm-decide","j0yen/"+b62(16))
idp("task/slug","task_id","ident","A1663","a1663-"+"foot"+"ball")
idp("task/mixed","task_id","ident","WF1663Impl","WF1663-"+Z)
idp("session/uuid","worker.session","ident","3b9a1c52-7e4d-4f1a-8c6b-2d5e9f0a1b3c","sess-"+Z)
idp("session/ulid","worker.session","ident","01HZXK3M7Q2V8N5R4T6Y9B0C1D","01HZXK3M7Q2V8N5R4T6Y9B0C1D"+b62(6))
idp("invocation/h32","worker.invocation","ident",hx(32)[:31]+"a","inv-"+Z+Z)
idp("account/ok","worker.account","ident","jyen.tech","acct-"+b62(24))
idp("account/pron","worker.account","ident","mcphost.dev","kobamitoru")
idp("model/ctx","worker.model","ident","claude-fable-5-1[1m]","claude-"+hx(40))
idp("model/ctx-evil","worker.model","ident","claude-opus-5-5","claude-opus-5-5["+"99m]"+b62(12))
idp("effort/enum","worker.effort","ident","xhigh","hunter22")
idp("host/tailnet","worker.host","host","ryzen7.tailabc123.ts.net",lc(10)+"."+lc(8)+".ts.net")
idp("host/cloud","worker.host","host","ip-10-0-1-5.ec2.internal","ip-"+b62(18)+".internal")
idp("host/ipv6","worker.host","host","2001:db8::1",":".join(hx(4) for _ in range(4))+"::")
idp("host/ipv6b","worker.host","host","fe80::a1b2:c3d4:1",":".join(hx(4) for _ in range(5))+"::1")
idp("head/digits40","target.head","sha","a1b2c3d4e5f60718293a4b5c6d7e8f9012345678","4111111111111111111111111111111111111111")
idp("head/upper","target.head","sha","A1B2C3D4E5F60718293A4B5C6D7E8F9012345678","1234567890123456")
idp("artifact/path","result.artifact","path","/mnt/ssd/cargo-target/r7-wfr12-20261113/out/review.md","/mnt/ssd/out/"+b62(24)+".md")
idp("artifact/pron","result.artifact","path","/mnt/ssd/cargo-target/r7-wfit-20261112/in/task.md","/mnt/ssd/"+"corr"+"ecthorse"+"/x.md")
idp("consumer/peer","consumer","ident","claude-121547-hermes-aae-worker",b62(20))
idp("consumer/vocab6","consumer","ident","wm-decide-regrade.service","queue-support-timeout-merge-watch-reap-unit-lane")
# rows
rowp("row/id","row","d-20261101-173305-aide-f24a","d-"+b62(24))
rowp("row/owner","owner","hermes","sun"+"shine")
rowp("row/claim","claim","r7-wfr12-20261113-worker","drag"+"onfly")
rowp("row/waits","waits-on","A1662","A1662-"+b62(12))
# free text
freep("free/kv","exit=0","password=%s"%Z)
freep("free/spacekv-multiword","note=\"build ok\"","passphrase=\"%s %s\""%(Z,Z2),Z)
freep("free/json","{\"line\": 12}","{\"api_key\": \"%s\"}"%Z)
freep("free/json-esc","{\\\"line\\\": 12}","{\\\"api_key\\\": \\\"%s\\\"}"%Z)
freep("free/json-u","{\"line\": 12}","{\"to\\u006ben\": \"%s\"}"%Z)
freep("free/json-dbl","\\\\\"line\\\\\": 12","\\\\\"secret\\\\\": \\\\\"%s\\\\\""%Z)
freep("free/json-str",json.dumps({"x":json.dumps({"line":1})}),json.dumps({"x":json.dumps({"secret":Z})}))
freep("free/nested","{\"meta\": {\"line\": 12}}","{\"auth\": {\"inner\": {\"v\": \"%s\"}}}"%Z)
freep("free/nested-arr","{\"lines\": [1,2]}","{\"secrets\": [\"%s\", \"%s\"]}"%(Z,Z2),Z)
freep("free/pct","path=%2Fvar%2Flog","token%%3D%s"%Z)
freep("free/userinfo","https://host.example/p?x=1","https://bob:%s@host.example/p"%Z)
freep("free/flag-eq","--retries=3","--client-secret=%s"%Z)
freep("free/short","-n 5","-p %s"%Z)
freep("free/camel","lineCount=12","accessToken=%s"%Z)
freep("free/leet","line=12","s3cr3t=%s"%Z)
freep("free/glue-digit","line=12","token2=%s"%Z)
freep("free/glue-letter","line=12","mytoken=%s"%Z)
freep("free/unlisted-kv","count=1234","vault=%s"%Z)
freep("free/unlisted-pron","count=1234","vault=%s"%("sun"+"shine"),"sun"+"shine")
freep("free/dbpass-space","the build is ok","dbpass %s"%Z)
freep("free/userpass-space","the build is ok","the userpass is %s"%Z)
freep("free/bare","the build is ok","please use %s for login"%Z)
freep("free/numeric-glue","retry_count=4","mfa_count=482917","482917")
freep("free/wide-numeric","bytes=1234567890","otp_bytes=482917","482917")
freep("free/vocab-pp","state: queue-support","hush=queue-support-timeout","queue-support-timeout")
freep("free/schema-field-cred","invocation=%s"%hx(32),"session=%s"%Z)
freep("free/schema-account","account=jyen.tech","account=%s"%Z)
freep("free/head-field","head=a1b2c3d4e5f6","head=%s"%Z)
freep("free/task-field","task_id=A1663","task_id=%s"%Z)
toolp("tool/kv","exit=0","password=%s"%Z)
toolp("tool/bearer","state ok","Authorization: Bearer %s"%Z)
ok=0; 
for n,fn in P:
    try: pp,nh=fn()
    except Exception as e: pp,nh=False,False; n+=" EXC %r"%e
    g=pp and nh; ok+=g
    print("%-28s pos_prints=%-5s neg_hidden=%-5s %s"%(n,pp,nh,"" if g else "<<<"))
print("PAIRS12 %d/%d"%(ok,len(P)))
