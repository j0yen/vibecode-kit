"""Retained reviewer probe (re-review 11 of 74551e2c, probes/pos11.py), source path made relative to this repo. Not collected by unittest discovery."""
import sys,random
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import envelope_validate as ev
r=random.Random(9)
hx=lambda n:"".join(r.choice("0123456789abcdef") for _ in range(n))
U="-".join([hx(8),hx(4),hx(4),hx(4),hx(12)])
pos=[
("worker.unit","claude-code-session-1234.scope","ident"),("worker.unit","seat-tick@rb.service","ident"),("worker.unit","wm-decide-regrade.service","ident"),
("worker.unit","agorabus-reap.timer","ident"),("worker.unit","memlog-witness.service","ident"),("worker.unit","user@1000.service","ident"),
("worker.unit","tmux-spawn-%s.scope"%U,"ident"),("worker.unit","session-c3.scope","ident"),("worker.unit","app-gnome-Terminal-12345.scope","ident"),
("worker.unit","run-p3947245-i3947546.scope","ident"),("worker.unit","fleet-merge.timer","ident"),("worker.unit","fleet-token-rotate.service","ident"),
("worker.unit","wm-build-r7-wfr11-20261113.service","ident"),("worker.unit","wm-build@%s.service"%hx(8),"ident"),("worker.unit","run-r%s.scope"%hx(32),"ident"),
("consumer","claude-3947245-r7-a1303rv8-20261113-worker","ident"),("consumer","claude-2927248-r7-wfr11-20261113","ident"),("consumer","hermes-aae-worker","ident"),
("owner","claude-3947245-r7-a1303rv8-20261113","ident"),("owner","ctl","ident"),("owner","aide","ident"),("owner","controller","ident"),("owner","orch","ident"),("owner","hermes","ident"),("owner","r7-seatret-20261113-worker","ident"),
("worker.host","ryzen7.tail4a6b2.ts.net","host"),("worker.host","ip-172-31-4-5.us-west-2.compute.internal","host"),("worker.host","hub","host"),("worker.host","orch","host"),("worker.host","mcphost-1","host"),("worker.host","RedBaron","host"),("worker.host","carbon","host"),("worker.host","hetzner-hub","host"),
("target.branch","r7/wfr11-20261113","ident"),("target.branch","worker-fit-skill","ident"),("target.branch","feat/A1663-repair-11","ident"),("target.branch","main","ident"),("target.branch","r7/worker-fit-skill","ident"),
("task_id","A1663","ident"),("task_id","a1303rv8","ident"),("task_id","d-20261113-0310-r7-ab12","ident"),("task_id","WF-1663","ident"),("task_id","SYN-100","ident"),
("worker.session","sess-3947245","ident"),("worker.session","syn-session-100","ident"),("worker.session",U,"ident"),("worker.session","session-"+U,"ident"),
("worker.account","jyen.tech","ident"),("worker.account","jyen.pm","ident"),("worker.account","mcphost.dev","ident"),("worker.account","josephsyen","ident"),("worker.account","acctA","ident"),
("worker.model","claude-opus-5-5","ident"),("worker.model","claude-sonnet-5-5","ident"),("worker.model","claude-fable-5-1","ident"),("worker.model","claude-haiku-5-5","ident"),("worker.model","claude-opus-5-5[1m]","ident"),
("worker.effort","medium","ident"),("worker.effort","xhigh","ident"),("worker.effort","max","ident"),
("target.repo","j0yen/vibecode-kit","ident"),("target.repo","j0yen/mcphost","ident"),("target.repo","j0yen/swarm-decide","ident"),
("result.artifact","/mnt/ssd/cargo-target/r7-wfr11-20261113/out/review.md","path"),("result.artifact","/home/jsy/Notes/hermes-director-bootstrap-proof-20261108.json","path"),("result.artifact","/tmp/wf3-abc/b.json","path"),
("result.event","evt-20261113-0042","path"),("result.artifact","/mnt/ssd/cargo-target/r7-wfit-20261112/fix11/out/report.md","path"),
("target.head","a9d096aa9f8d8cc45f9398375d1593579f8565ec","sha"),("target.head","74551e2","sha"),
]
bad=0
for f,v,k in pos:
    o=ev.show(f,v,k)
    if v not in o: bad+=1; print("OPAQUE %-16s %s"%(f,v))
print("positives opaque: %d/%d"%(bad,len(pos)))
