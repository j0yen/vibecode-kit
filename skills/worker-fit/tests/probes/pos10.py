"""Retained reviewer probe (re-review 10 of 8f250d8e, probes/pos10.py), source path made relative to this repo. Run: python3 pos10.py. Not collected by unittest discovery; test_review_fixes11.RetainedReviewerProbes runs it."""
import sys,random
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import envelope_validate as ev
r=random.Random(77)
hx=lambda n:"".join(r.choice("0123456789abcdef") for _ in range(n))
pos=[("worker.unit","wm-build-wf1663-impl.service"),("worker.unit","wm-build-r7-wfit-20261112.service"),("worker.unit","run-r1a2b3c4d5e6f.scope"),("worker.unit","wm-build-tail9z8y7.service"),
("worker.unit","wm-build-WF1663Impl.service"),("worker.unit","wmbuild1663impl2.service"),("worker.unit","app-claude@"+hx(8)+".service"),
("worker.invocation",hx(32)),("worker.session","-".join([hx(8),hx(4),hx(4),hx(4),hx(12)])),("worker.session","01HZXK3M7Q2V8N5R4T6Y9B0C1D"),
("result.artifact","/mnt/ssd/cargo-target/r7-wfit-20261112/out/report.md"),("result.artifact","/mnt/ssd/cargo-target/r7-wfr10-20261113/out/review.md"),
("target.head",hx(40)),("consumer.named","hermes"),("consumer.named","claude-1275054-hermes-aae"),("consumer.named","r7-seatret-20261113-worker"),
("worker.host","ryzen7"),("worker.host","redbaron"),("worker.host","ryzen7.tail1234.ts.net"),("worker.host","ip-10-0-1-23.ec2.internal"),("worker.host","10.0.1.23"),("worker.host","100.64.1.2"),
("worker.host","fe80::1%eth0"),("worker.host","2001:db8:0:0:0:0:0:1"),("worker.host","carbon"),("worker.host","i-0a1b2c3d4e5f60718"),
("task_id","A1663"),("task_id","d-20261101-173305-aide-f24a"),("task_id","a1663-r10"),("owner","r7"),("owner","alice-"+hx(12)),("owner","jsy-"+hx(8)),("owner","rb"),
("target.repo","j0yen/vibecode-kit"),("target.branch","r7/worker-fit-skill"),("target.branch","feature/A1663-fix-gate"),("worker.account","jyen.tech"),("worker.account","mcphost.dev"),("worker.account","josephsyen"),
("worker.model","claude-opus-5-5"),("worker.model","claude-sonnet-5-5"),("worker.model","claude-fable-5-1"),
]
for f,v in pos:
    k="path" if f.startswith("result") or f=="evidence" else ("host" if f.endswith("host") else "ident")
    if f=="target.head": k="sha"
    o=ev.show(f,v,k)
    print("%-17s %-6s %s"%(f,"PRINT" if v in o else "OPQ",v[:60]))
print("---rows")
import queue_adapter as qa
rows=[("row_id","d-20261101-173305-aide-f24a"),("row_id","A1663"),("owner","r7"),("owner","hermes"),("claim","r7-wfr10-20261113-worker"),("claim","tmux:rb:%12"),("status","running"),("waits_on","hermes"),("waits_on","A1662"),("claim","claimed by r7 at 2026-11-13T10:00:00Z"),("row_id","wm-1663-r10")]
for f,v in rows:
    o=qa._gate(f,v); print("%-10s %-6s %s"%(f,"PRINT" if v in o else "OPQ",v))
