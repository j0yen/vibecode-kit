#!/usr/bin/env bash
# AC5 (R5) — under mission=APPROVE a mission PRD named by no per-PRD verdict that changes is
# mission-snapshot-stale naming it and both digests, as is a changed edges file, matrix,
# packet member or repairs= file; the unchanged packet passes; mission=FIX pins nothing; in
# the superseded-APPROVE variant (a's bytes moved between s1 and s2, both reviews APPROVE a)
# no review-snapshot-stale fires for the s1 line, while with the s2 line removed, or the s2
# file naming b and c only, it fires naming a and the s1 file.
set -uo pipefail
# shellcheck source=tests/drmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmr_lib.sh"
setup_mr
digest() { sha256sum "$1" | cut -d' ' -f1; }
use base
vedit "$MR_CHAIN/verdict.txt" "L[:] = [l for l in L if not l.startswith('c APPROVE')]"
capture "$MR_CHAIN/result.json" "L[:] = [l for l in L if not l.startswith('c APPROVE')]"
state "a=linted a=reviewed:APPROVE b=linted b=reviewed:APPROVE c=linted"
run_mr; [ "$RC" = 0 ] || fail "c unnamed, unchanged: rc=$RC $ERR"
old=$(digest "$H/built-prds/PRD-c.md"); printf 'edited after the freeze\n' >> "$H/built-prds/PRD-c.md"; new=$(digest "$H/built-prds/PRD-c.md")
run_mr; findings_eq '["mission-snapshot-stale"]'; has_fail mission-snapshot-stale "PRD-c.md" "$old" "$new"
for f in "notes/missions/$MR_EB" "notes/reviews/$MR_MXB" visions/drmr-vision.md; do
  use base; printf '\n' >> "$H/$f"; run_mr; findings_eq '["mission-snapshot-stale"]'; has_fail mission-snapshot-stale "$(basename "$f")"
done
use twomanifest; printf '\n' >> "$H/notes/missions/$MR_RB"; run_mr; has_fail mission-snapshot-stale "$MR_RB"
use base; run_mr; findings_eq '[]'
use fix; printf '\n' >> "$H/notes/missions/$MR_EB"; run_mr; no_id mission-snapshot-stale
use superseded; run_mr
[ "$RC" = 0 ] || fail "superseded APPROVE: rc=$RC $ERR"; findings_eq '[]'; no_id review-snapshot-stale
jtrue '[x.get("superseded") for x in d["reviews"]][0] == [{"slug": "a", "by": "'"$S_M2"'"}]' "s1 review names a superseded by s2"
use superseded; python3 - "$LOG" <<'PY'
import sys
p = sys.argv[1]; L = [l for l in open(p).read().split("\n") if not (l.startswith("Review:") and "/s2/" in l)]; open(p, "w").write("\n".join(L))
PY
state "$ST_ALL"; run_mr; has_fail review-snapshot-stale "notes/reviews/s1/verdict.txt" "slug a"
use superseded-bc; run_mr; has_fail review-snapshot-stale "notes/reviews/s1/verdict.txt" "slug a"
pass "unnamed PRD, edges, matrix, packet, repairs stale; FIX pins nothing; superseded A01 and its two controls"
