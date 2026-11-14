"""Retained reviewer probe (re-review 14 of bffbfc29, probes/own/unk14.py), source path made relative to this repo. Not collected by unittest
discovery."""
import os
import sys, random
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
sys.path.insert(0, S)
import envelope_validate as ev
r = random.Random(77)
D = "0123456789"
rs = lambda n, a: "".join(r.choice(a) for _ in range(n))
card = "4" + rs(15, D)
SYM = [chr(c) for c in range(0x2190, 0x2400)] + [chr(c) for c in range(0x2500, 0x2800)]
cases = {
  "unknown <16-digit card>": "unknown " + card,
  "unknown:<40 digits>": "unknown:" + rs(40, D),
  "N/A <6-digit otp>": "N/A " + rs(6, D),
  "tbd-<card grouped>": "tbd-" + "-".join(card[i:i+4] for i in range(0, 16, 4)),
  "pending <digits> (not yet known)": "pending " + rs(20, D) + " (not yet known)",
  "unknown #<digits>": "unknown #" + rs(30, D),
  "symbols only (unicode arrows/box)": "".join(r.choice(SYM) for _ in range(40)),
  "punctuation only": "".join(r.choice("!#$%^&*()[]{}<>?|~-_=+") for _ in range(24)),
}
FIELDS = [("current_owner", "ident"), ("worker.account", "ident"), ("worker.unit", "ident"), ("consumer", "ident"), ("task_id", "ident"),
          ("target.repo", "ident"), ("worker.host", "host"), ("result", "path"), ("evidence-ref", "path"), ("target.head", "sha")]
for name, v in cases.items():
    f = [n for n, k in FIELDS if ev.unmark(ev.show(n, v, k)) == v]
    rw = [n for n in ("row", "owner", "claim", "waits-on") if ev.show_row(n, v) == v]
    print("%-36s unknown=%s prints in %2d/%d fields %s | rows %s | redact keeps=%s" % (name, ev.is_unknown(v), len(f), len(FIELDS), f, rw, v in ev.redact(v)))
