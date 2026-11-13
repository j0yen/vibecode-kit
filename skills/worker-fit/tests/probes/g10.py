"""Retained reviewer probe (re-review 10 of 8f250d8e, probes/g10.py), source path made relative to this repo. Run: python3 g10.py. Not collected by unittest discovery; test_review_fixes11.RetainedReviewerProbes runs it."""
import sys,random
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import envelope_validate as ev
r=random.Random(10)
hx=lambda n:"".join(r.choice("0123456789abcdef") for _ in range(n))
dg=lambda n:"".join(r.choice("0123456789") for _ in range(n))
lc=lambda n:"".join(r.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(n))
b62=lambda n:"".join(r.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789") for _ in range(n))
c={
"vocab-pass-4":"claude-fable-opus-canary",
"vocab-pass-6":"claude-fable-opus-canary-gate-prod-wake",
"vocab+hex32":"build-"+hx(32),
"hex32 bare":hx(32),
"hex64 bare":hx(64),
"hex40 bare":hx(40),
"vocab+hex64":"task-"+hx(64),
"hex12+vocab":"run-"+hx(12),
"dig7x2":"run-"+dg(7)+"-"+dg(7),
"dig14 piece mix":"wm-"+dg(7)+"-"+dg(7),
"unlisted8":"run-"+lc(5)+"-"+lc(3),
"short5+3":"run-"+b62(5)+"."+b62(3),
"uuid+vocab":"task-%s-%s-%s-%s-%s"%(hx(8),hx(4),hx(4),hx(4),hx(12)),
"uuid bare":"%s-%s-%s-%s-%s"%(hx(8),hx(4),hx(4),hx(4),hx(12)),
"ulid":"01H"+b62(23).upper(),
"ipv4":"10.%d.%d.%d"%(r.randrange(256),r.randrange(256),r.randrange(256)),
"ipv6 4grp":"2001:db8:%s:%s::1"%(hx(4),hx(4)),
"ts-stuffing":"run-20261113T123456Z-20261114T010203Z-20261115T020304Z",
"date-pieces":"run-20261113-20261114-20261115-20261116",
"wordcompound4":"wmbuildtaskrun",
"vocabcompound40":"wmbuildtaskrunreviewverifier",
"vocab+digit7":"run-"+dg(7),
"wf+num":"wf"+dg(7)+"impl"+dg(7),
"pairs-chain":"pid=12345&port=22&seq=99",
"name=val":"pid=77",
"num+id grammar":"run-"+hx(8)+"-12345678",
"hex40 build":"build-"+hx(40),
"tld host":"tail9z8y7.tailnet.net",
"host random lbls":lc(12)+"."+lc(12)+".net",
"host 3 random short":"abcde.fghij.klmno.com",
"b62 8 piece":b62(8),
"b62 5x2":b62(5)+"-"+b62(3),
"digitsplit":"run-"+dg(4)+"-"+dg(4)+"-"+dg(4)+"-"+dg(4),
"digitsplit 14":"run-"+dg(4)+"-"+dg(4)+"-"+dg(4)+"-"+dg(2),
"hex7-mix":"a1b2c3d",
"hexword sha":"sess-"+hx(7),
}
print("%-18s %-8s %-8s %s"%("case","ident","row","value"))
for k,V in c.items():
    a=ev.show("worker.account",V); b=ev.show_row("owner",V); p=ev.show("task_id",V,"path")
    print("%-18s %-7s %-7s %-7s %s"%(k,"PRINT" if V in a else "opq","PRINT" if V in b else "opq","PRINT" if V in p else "opq",V[:70]))
