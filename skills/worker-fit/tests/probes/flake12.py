"""Retained reviewer probe (re-review 12 of d970f49c, probes/flake12.py), source path made relative to this repo; literal canary words are
assembled from fragments. Not collected by unittest discovery."""
import os
import sys, random
sys.path.insert(0, sys.argv[1])  # usage: flake12.py <scripts dir> <seed> <N>
import envelope_validate as ev
ALPH = "abcdefghijklmnopqrstuvwxyz0123456789_"
r = random.Random(int(sys.argv[2])); N=int(sys.argv[3]); bad=[]
import tempfile
for _ in range(N):
    suf = "".join(r.choice(ALPH) for _ in range(8))
    p = "/tmp/wf3-%s/b.json" % suf
    o = ev.redact_tool("UNREADABLE usage: recommend.py takes exactly one FILE; extra argument(s) not evaluated: %s" % p)
    if p not in o: bad.append(suf)
print(sys.argv[1].split("/")[-3], "rate %d/%d = %.2f%%"%(len(bad),N,100*len(bad)/N), bad[:4])
