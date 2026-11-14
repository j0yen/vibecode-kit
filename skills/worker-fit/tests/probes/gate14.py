"""Retained reviewer probe (re-review 14 of bffbfc29, probes/own/gate14.py), source path made relative to this repo. Not collected by unittest
discovery."""
import os
import sys, random, math
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
sys.path.insert(0, S)
import envelope_validate as ev
r = random.Random(9)
SENT = getattr(ev, "_CHARGED", "")
J = "-_./:@"
vals = ["r7" + "".join(r.choice(J) + SENT for _ in range(37)) for _ in range(30)]
print("sentinel pieces after 'r7' (37 joiners, ~%.0f bits): rows print %d/30, owner prints %d/30, is_unknown=%s" % (
    37 * math.log2(6), sum(ev.show_row("owner", v) == v for v in vals), sum(ev.unmark(ev.show("current_owner", v)) == v for v in vals), ev.is_unknown(vals[0])))
W = ["invocation", "bootstrap", "controller", "wintermute", "production", "synthorg"]
case = [" ".join("".join(c.upper() if r.random() < .5 else c for c in w) for w in W) for _ in range(30)]
print("6 vocab words, random case (~%d case bits): row prints %d/30" % (sum(map(len, W)), sum(ev.show_row("claim", v) == v for v in case)))
