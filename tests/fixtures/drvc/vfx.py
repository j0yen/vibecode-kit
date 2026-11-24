#!/usr/bin/env python3
"""drvc fixture: the datr control-mutant mission `cm-freezes-in-launch-order-none-unread` (three freezes m0, m1, m2 reviewed in launch
order by S_R1, S_R2 and CM_S_R3; clean), built by tests/fixtures/datr/dfx.py, plus a fresh correction session for m0's chain review:
a launch row copied from S_R1's (role review, m0's scope and scope_id, resume false) with its own session and a ts after m2's review
launch, the shape a verdict correction of an earlier freeze's review always has (it is launched after the later rounds).

usage: vfx.py <variant> <out>
  fresh-row      the fresh session's launch row only, no correction file
  corrected      the row and a valid identity correction of notes/reviews/cm0.txt (each line keeps its slug and verdict word)
  refused        the row and a correction of cm0.txt that changes a verdict word (review-correction-verdict-changed)
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DFX = os.path.join(os.path.dirname(HERE), "datr", "dfx.py")
BASE_CASE = "cm-freezes-in-launch-order-none-unread"
S_FRESH = "cccccccc-0000-4000-8000-00000000c0c3"
FRESH_TS = "2026-11-15T03:00:00-08:00"          # after m2's review launch (01:50) and before the entry (2026-11-21)
VERDICT = "notes/reviews/cm0.txt"


def main(argv):
    if len(argv) != 2 or argv[0] not in ("fresh-row", "corrected", "refused"):
        sys.exit(__doc__)
    variant, out = argv
    subprocess.run([sys.executable, "-I", DFX, BASE_CASE, out], check=True)
    dec = os.path.join(out, "decisions.jsonl")
    rows = [json.loads(ln) for ln in open(dec, encoding="utf-8").read().splitlines() if ln.strip()]
    m0 = [r for r in rows if r.get("decision") == "launch" and r.get("role") == "review"
          and str(r.get("scope", "")).endswith("snapshots/m0/m.sha256")]
    if len(m0) != 1:
        sys.exit(f"vfx: want one review launch row on m0, found {len(m0)}")
    orig = m0[0]
    with open(dec, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(orig, session=S_FRESH, ts=FRESH_TS, resume=False)) + "\n")
    if variant == "fresh-row":
        return 0
    vf = os.path.join(out, "home", VERDICT)
    raw = open(vf, "rb").read()
    lines = []
    for ln in raw.decode("utf-8").split("\n"):
        p = ln.split()
        if len(p) >= 3 and p[1] in ("APPROVE", "FIX", "REJECT") and not p[0].startswith("mission="):
            lines.append({"line": " ".join(p), "slug": p[0], "verdict": p[1]})
    if len(lines) != 2:
        sys.exit(f"vfx: want two verdict lines in {VERDICT}, found {len(lines)}")
    if variant == "refused":
        lines[1] = dict(lines[1], verdict="FIX" if lines[1]["verdict"] != "FIX" else "APPROVE")
    head = {"corrects": VERDICT, "sha256": hashlib.sha256(raw).hexdigest(), "session": orig["session"], "corrected_by": S_FRESH}
    with open(vf + ".verdicts.corrected-1.jsonl", "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(x) + "\n" for x in [head] + lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
