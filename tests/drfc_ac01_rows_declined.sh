#!/usr/bin/env bash
# AC1 (R1, R2, R3, R8) — the drfc fixture (every non-advisory finding with a row) exits 0 with
# repairs.rows 2; the declined variant lists {finding, reason, accepted_by, superseded} and
# exits 0 when the second review's advisory row accepts row 1 (accepted_by that reviewer; a
# same-manifest third review's row when it moves there); with nothing accepting, or a
# non-advisory row re-using the id (r6 F39), repair-declined-unaccepted names F1, a eligible is
# refused naming F1 and accepted_by is null; the reversed same-manifest variant (r7 F42) is
# repair-missing for F1, repair-declined-unaccepted with a declined row, exit 0 once accepted.
# Matrix controls: a row for an unknown id beside the real finding unrepaired is repair-grammar
# and repair-missing (R1); `provenance` written for a missing-producer-runner finding is
# repair-class-mismatch (R3).
set -uo pipefail
# shellcheck source=tests/drfc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drfc_lib.sh"
setup_fc
use base; run_fc
[ "$RC" = 0 ] || fail "drfc fixture: rc=$RC $ERR"; findings_eq '[]'
rep 'm["rows"] == 2 and m["repaired"] == 2 and m["declined"] == [] and m["pending_after"] is False' "base repairs block"
jtrue 'd["provenance"]["mission"] == "verified"' "base verified"
use declined; run_fc
[ "$RC" = 0 ] || fail "declined, accepted: rc=$RC $ERR"; findings_eq '[]'
rep 'm["declined"] == [{"finding": "F1", "reason": m["declined"][0]["reason"], "accepted_by": "'"$S_F2"'", "superseded": False}] and m["declined"][0]["reason"]' "declined listed, accepted by r2"
use declined-later; run_fc
[ "$RC" = 0 ] || fail "declined, accepted by a later same-manifest review: rc=$RC $ERR"
rep 'm["declined"][0]["accepted_by"] == "'"$S_F3"'"' "accepted_by the same-manifest re-review"
unacc() { # <label>: the refusal, a held naming F1, accepted_by null
  has_fail repair-declined-unaccepted "F1"; has_fail mission-approval-blocked "slug a" "F1"
  rep 'm["declined"][0]["accepted_by"] is None' "$1: accepted_by null"
}
use declined; rm -f -- "${H:?}/$R2D/verdict.txt.findings.jsonl"; capture "$R2D/result.json" "L[:] = [('findings=none' if l.startswith('findings=') else l) for l in L]"
run_fc; findings_eq '["repair-declined-unaccepted", "mission-approval-blocked"]'; unacc "nothing accepts"
has_fail repair-declined-unaccepted "F1" "$R2D/verdict.txt"
use reused-id; run_fc; has_id mission-finding-incomplete; unacc "re-used id"
use reversed; run_fc; findings_eq '["repair-missing"]'; has_fail repair-missing "F1" "no repairs= token"
use reversed-declined; run_fc; findings_eq '["repair-declined-unaccepted", "mission-approval-blocked"]'; unacc "reversed, declined"
use reversed-accepted; run_fc; [ "$RC" = 0 ] || fail "reversed, accepted: rc=$RC $ERR"
rep 'm["declined"][0]["accepted_by"] == "'"$S_F2"'"' "reversed accepted_by r2"
use base; redit "R[0]['finding'] = 'F99'"; run_fc; has_fail repair-grammar "F99"; has_fail repair-missing "F1"
use base; redit "R[0]['class'] = 'provenance'"; run_fc; has_fail repair-class-mismatch "F1"
pass "base rows 2; declined accepted x2; unaccepted, re-used id; reversed x3; unknown id; class"
