#!/usr/bin/env bash
# AC1 (R1, R2, R3, R8) — the drfc fixture (every non-advisory finding with a row) exits 0 with
# repairs.rows 2; the declined variant lists {finding, reason, accepted_by, superseded} and
# exits 0 when the second review's advisory row accepts row 1 (accepted_by that reviewer; a
# same-manifest third review's row when it moves there); with nothing accepting, a
# non-advisory row re-using the id (r6 F39), or an advisory row in the issuing review's own
# sidecar (R2: acceptance comes from a chain review later in line order; review L11),
# repair-declined-unaccepted names F1, a eligible is
# refused naming F1 and accepted_by is null; the unaccepted decline holds the finding's prds and
# consumers and their one-hop edge neighbours in either direction (R7, over the issuing review's
# frozen edges copy): with F1 on a and b, c (consumer of E2 b -> c) is held and d is not; with F1
# on c and d (sweep E1-E3), b (producer of E2 b -> c) is held and a is not; the reversed
# same-manifest variant (r7 F42) is repair-missing for F1, repair-declined-unaccepted with a
# declined row, exit 0 once accepted.
# Matrix controls: a row for an unknown id beside the real finding unrepaired is repair-grammar
# and repair-missing (R1); `provenance` written for a missing-producer-runner finding is
# repair-class-mismatch (R3). A malformed sidecar row (chain-review R4) still names its id for R1.
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
# held: F1's a and b and their one-hop neighbour c (E2 b -> c, producer to consumer); d is two hops
held() { # <slug...>: dependent_slugs is exactly these slugs, each held by the decline alone
  local want; want=$(printf "'%s', " "$@")
  jtrue "[(x['slug'], x['reason']) for x in d['mission']['dependent_slugs']] == [(s, 'declined F1 (row 1)') for s in [${want%, }]]" "declined hold [$*]"
}
has_fail mission-approval-blocked "slug c=eligible" "declined F1 (row 1)"
if printf '%s\n' "$ERR" | grep -q '^FAIL mission-approval-blocked: slug d='; then fail "d (two hops from F1) held: $ERR"; fi
held a b c
# the other direction: F1 on c (prds) and d (consumers), its sweep widened to E1-E3; b, the
# producer of E2 b -> c, is held by that hop alone, and a (two hops) is not
use declined; rm -f -- "${H:?}/$R2D/verdict.txt.findings.jsonl"; capture "$R2D/result.json" "L[:] = [('findings=none' if l.startswith('findings=') else l) for l in L]"
side "$R1D" "R[0]['prds'] = ['PRD-c.md']; R[0]['consumers'] = ['PRD-d.md']"; resign "$R1D"
redit "R[0]['sweep'] = ['E1', 'E2', 'E3']"
run_fc; findings_eq '["repair-declined-unaccepted", "mission-approval-blocked"]'
has_fail mission-approval-blocked "slug b=eligible" "declined F1 (row 1)"
if printf '%s\n' "$ERR" | grep -q '^FAIL mission-approval-blocked: slug a='; then fail "a (two hops from F1) held: $ERR"; fi
held b c d
use reused-id; run_fc; has_id mission-finding-incomplete; unacc "re-used id"
use declined; rm -f -- "${H:?}/$R2D/verdict.txt.findings.jsonl"; capture "$R2D/result.json" "L[:] = [('findings=none' if l.startswith('findings=') else l) for l in L]"
side "$R1D" "R.append({'id': 'F8', 'class': 'provenance', 'accepts': ['F1'], 'prds': [], 'consumers': [], 'counterexample': 'F8 accepts the decline', 'correction': 'none', 'control': 'F8 control'})"; resign "$R1D"
run_fc; findings_eq '["repair-declined-unaccepted", "mission-approval-blocked"]'; unacc "the issuing review's own row"
has_fail repair-declined-unaccepted "F1" "no later chain review's sidecar holds an advisory row accepting it"
use reversed; run_fc; findings_eq '["repair-missing"]'; has_fail repair-missing "F1" "no repairs= token"
use reversed-declined; run_fc; findings_eq '["repair-declined-unaccepted", "mission-approval-blocked"]'; unacc "reversed, declined"
use reversed-accepted; run_fc; [ "$RC" = 0 ] || fail "reversed, accepted: rc=$RC $ERR"
rep 'm["declined"][0]["accepted_by"] == "'"$S_F2"'"' "reversed accepted_by r2"
use base; redit "R[0]['finding'] = 'F99'"; run_fc; has_fail repair-grammar "F99"; has_fail repair-missing "F1"
use base; redit "R[0]['class'] = 'provenance'"; run_fc; has_fail repair-class-mismatch "F1"
# a malformed sidecar row still names its id (R1: "an id present in some chain review's findings
# sidecar"): chain-review R4 refuses the row on its own, the repairs row for it is no repair-grammar
use base; side "$R1D" "R[0]['consumers'] = []"; resign "$R1D"; run_fc; findings_eq '["mission-finding-incomplete"]'
has_fail mission-finding-incomplete "row 1" "consumers"
pass "base rows 2; declined accepted x2; unaccepted (its one-hop hold both ways), re-used id, the issuing review's own row; reversed x3; unknown id; class; malformed row's id"
