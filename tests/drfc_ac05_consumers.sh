#!/usr/bin/env bash
# AC5 (R6) — with PRD b (consumer of the changed producer a over E1) removed from the second
# Review: row's manifest, and no later review listing b at its after digest (a listing at the
# before digest does not count), affected-consumer-unreviewed names a, b and E1; a bounded
# re-review later in line order listing b at its after digest satisfies it. PRD d (unchanged,
# not a consumer of a or b) absent from every later manifest: no finding of this PRD fires
# and d's earlier APPROVE stands (r1's pin, no review-snapshot-stale naming d); the previous
# PRD's R1 and R5 still refuse a manifest that drops a member of its frozen header and an
# APPROVE that leaves a prds member unpinned (mission-scope-incomplete, mission-snapshot-stale),
# the ambiguity resolved fail-closed and reported.
set -uo pipefail
# shellcheck source=tests/drfc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drfc_lib.sh"
setup_fc
use base; mansign "$AFT" "L[:] = [l for l in L if not l.endswith('  PRD-b.md')]"; run_fc
has_fail affected-consumer-unreviewed "PRD-a.md" "PRD-b.md" "E1"
# bounded <digest of b>: a bounded re-review after r2 (an unlisted manifest over a and b; b at the
# given digest) whose file APPROVEs b, its launch row and Review: line, b's State token
bounded() {
  mkdir -p "$H/notes/snapshots/bounded" "$H/notes/reviews/bounded"
  printf '%s  PRD-a.md\n%s  PRD-b.md\n' "$(digest built-prds/PRD-a.md)" "$1" > "$H/notes/snapshots/bounded/bounded.sha256"
  local bid; bid=$("$LINT" --scope-id "$H/notes/snapshots/bounded/bounded.sha256")
  printf 'b APPROVE %s\n' "$S_FB" > "$H/notes/reviews/bounded/verdict.txt"
  python3 - "$DEC" "$S_FB" "$bid" "$LOG" <<'PY2'
import sys, json
p, s, sid, log = sys.argv[1:]
R = [json.loads(l) for l in open(p).read().splitlines()]
R.append(dict(R[-1], ts="2026-11-18T12:30:00-08:00", session=s, scope="notes/snapshots/bounded/bounded.sha256", scope_id=sid))
open(p, "w").write("".join(json.dumps(r) + "\n" for r in R))
L = open(log).read().split("\n"); i = max(i for i, l in enumerate(L) if l.startswith("Review:"))
L.insert(i + 1, f"Review: notes/reviews/bounded/verdict.txt reviewer-session={s}")
L = [l.replace("b=reviewed:APPROVE b=eligible", "b=reviewed:APPROVE b=reviewed:APPROVE b=eligible") if l.startswith("State:") and k > i else l
     for k, l in enumerate(L)]
open(log, "w").write("\n".join(L))
PY2
}
old=$(sha256sum < "$FCFIX/home/notes/snapshots/before/PRD-b.md" | cut -d' ' -f1)
use base; mansign "$AFT" "L[:] = [l for l in L if not l.endswith('  PRD-b.md')]"; bounded "$old"; run_fc
has_fail affected-consumer-unreviewed "PRD-a.md" "PRD-b.md" "E1"
use base; mansign "$AFT" "L[:] = [l for l in L if not l.endswith('  PRD-b.md')]"; bounded "$(digest built-prds/PRD-b.md)"; run_fc
no_id affected-consumer-unreviewed
# d absent from every later manifest: r2's manifest, verdict file, capture and State token
use base; mansign "$AFT" "L[:] = [l for l in L if not l.endswith('  PRD-d.md')]"
vedit "$R2D/verdict.txt" "L[:] = [l for l in L if not l.startswith('d APPROVE')]"
capture "$R2D/result.json" "L[:] = [l for l in L if not l.startswith('d APPROVE')]"
st2 "${ST2_ALL/d=reviewed:APPROVE d=reviewed:APPROVE/d=reviewed:APPROVE}"
run_fc
jtrue 'not [f for f in d["findings"] if f.startswith(("repair-", "sweep-", "affected-"))]' "no finding of this PRD for d"
jtrue 'set(d["findings"]) <= {"mission-scope-incomplete", "mission-snapshot-stale"}' "only the chain-review packet refusals"
if printf '%s\n' "$ERR" | grep '^FAIL review-snapshot-stale' | grep >/dev/null 'slug d'; then fail "d's earlier APPROVE does not stand: $ERR"; fi
pass "b removed; b at its before digest; bounded re-review; d unrequired"
