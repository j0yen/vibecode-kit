"""Retained reviewer probe (re-review 11 of 74551e2c, probes/flake11.py), source path made relative to this repo. Not collected by unittest discovery."""
import sys, random, importlib.util, os
import os; which = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts')
sys.path.insert(0, which)
import envelope_validate as ev
ALPH = "abcdefghijklmnopqrstuvwxyz0123456789_"   # tempfile._RandomNameSequence characters
r = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
N = 3000; bad = []
for _ in range(N):
    suf = "".join(r.choice(ALPH) for _ in range(8))
    p = "/tmp/wf3-%s/b.json" % suf
    o = ev.redact_tool("UNREADABLE usage: recommend.py takes exactly one FILE; extra argument(s) not evaluated: %s" % p)
    if p not in o: bad.append((suf, o[-60:]))
print("scripts", "rate %d/%d = %.2f%%" % (len(bad), N, 100*len(bad)/N), bad[:6])
