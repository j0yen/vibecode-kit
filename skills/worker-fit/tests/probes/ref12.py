"""Retained reviewer probe (re-review 12 of d970f49c, probes/ref12.py), source path made relative to this repo; literal canary words are
assembled from fragments. Not collected by unittest discovery."""
import os
import sys,subprocess,os,re
S=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
code="import sys;sys.path.insert(0,%r);import envelope_validate as ev;print(ev.opaque('worker.account','secretvalue1'),ev.opaque('current_owner','secretvalue1'),ev.opaque('worker.account','secretvalue1'))"%S
def run(env):
    e={k:v for k,v in os.environ.items() if k not in("PYTHONHASHSEED",)}; e.update(env)
    return subprocess.run([sys.executable,"-c",code],capture_output=True,text=True,env=e).stdout.strip()
for env in [{},{"PYTHONHASHSEED":"0"},{"PYTHONHASHSEED":"0"},{"PYTHONHASHSEED":"1"},{"PYTHONHASHSEED":"random"}]:
    print(env,run(env))
