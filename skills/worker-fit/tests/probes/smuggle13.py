"""Retained reviewer probe (re-review 13 of e9632349, probes/own/smuggle13.py), source path made relative to this repo; literal canary words are
assembled from fragments. Not collected by unittest discovery."""
import os
import sys, random
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
sys.path.insert(0, S)
import envelope_validate as ev
r = random.Random(4242)
L = "abcdefghijklmnopqrstuvwxyz"; D = "0123456789"
rs = lambda n, a: "".join(r.choice(a) for _ in range(n))
card = "4" + "1" * 15  # a test-card shaped number
num40 = rs(40, D)
alt = "-".join(rs(1, D) + "-" + r.choice(L + L.upper()) for _ in range(13)) + "-" + rs(1, D)
cases = {
  "ts-frac-card": "2026-11-13T09:41:27.%sZ" % card,
  "ts-frac-40digits": "2026-11-13T09:41:27.%s" % num40,
  "ts-frac-in-name": "r7-2026-11-13T09:41:27.%s" % card,
  "alt-13-letters-14-digits": alt,
  "alt-dots": alt.replace("-", "."),
}
fields = [("current_owner", "ident"), ("worker.account", "ident"), ("worker.model", "ident"), ("worker.host", "host"), ("worker.unit", "ident"),
          ("consumer", "ident"), ("reviewed_by", "ident"), ("target.branch", "ident"), ("target.repo", "ident"), ("task_id", "ident"),
          ("worker.invocation", "ident"), ("sess-id", "ident"), ("result", "path"), ("worker.child", "ident")]
for name, v in cases.items():
    pr = [f for f, k in fields if v in ev.show(f, v, k)]
    rows = [f for f in ("row", "owner", "claim", "waits-on") if v in ev.show_row(f, v)]
    print("%-26s len=%3d prints in %2d/%d fields %s | rows %s" % (name, len(v), len(pr), len(fields), pr, rows))
