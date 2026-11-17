#!/usr/bin/env bash
# AC2 (R3, R5, R2) — row 1 (missing-producer-runner on a, consumer b) without an edge incident
# to a in its sweep is sweep-missing naming F1 and the edge; class authority-bypass is
# repair-class-mismatch; row 2 (provenance, empty sweep and changed) fires nothing; edges only
# in after's frozen copy are reported as edges_added; row 1's after not a later listed manifest,
# or its following review bound to an earlier manifest, is repair-scope-mismatch naming the row;
# in the three-review variant, the round-two row (F4, issued by r2 on the second manifest) moved
# to the consecutive pair before -> after is repair-scope-mismatch naming row 3 and both ids (R5:
# before canonicalizes to the scope_id of the issuing review), beside the two repair-hash-mismatch
# lines the move itself causes; the amended-row variant's interrupted sub-variant (the middle
# manifest's only review row on no Review: line; the third manifest's chain review follows the
# base rows; r7 F44, r8 F47) exits 0 with pending_after false and the unlisted row reported.
set -uo pipefail
# shellcheck source=tests/drfc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drfc_lib.sh"
setup_fc
use base; redit "R[0]['sweep'] = ['E2']"; run_fc; findings_eq '["sweep-missing"]'; has_fail sweep-missing "F1" "E1"
use base; redit "R[0]['class'] = 'authority-bypass'"; run_fc; has_fail repair-class-mismatch "F1"
use base; run_fc; no_id sweep-missing; no_id repair-grammar
rep 'm["edges_added"] == ["E4"] and m["edges_removed"] == [] and m["swept_edges"] == 2' "edges_added E4, two swept"
use base; redit "R[0]['after'] = '$BEF'"; run_fc; has_fail repair-scope-mismatch "row 1"
use base; id=$("$LINT" --scope-id "$H/$BEF")
decedit "dict(r, scope='$BEF', scope_id='$id') if r.get('session') == '$S_F2' else r"
run_fc; has_fail repair-scope-mismatch "row 1" "$id"
# before bound to the issuing review: row 3 (F4, issued by r2, bound to the after manifest) set to
# the consecutive pair before -> after, which does not start at r2's manifest
use three; redit "R[2]['before'] = '$BEF'; R[2]['after'] = '$AFT'"
ib=$("$LINT" --scope-id "$H/$BEF"); ia=$("$LINT" --scope-id "$H/$AFT")
run_fc; [ "$RC" = 1 ] || fail "row 3 before the issuing review's manifest: rc=$RC $ERR"
findings_eq '["repair-scope-mismatch", "repair-hash-mismatch"]'
has_fail repair-scope-mismatch "row 3 (finding F4): before $BEF canonicalizes to $ib" "the issuing review $R2D/verdict.txt is bound to $ia"
use amended-interrupted; run_fc
[ "$RC" = 0 ] || fail "interrupted sub-variant: rc=$RC $ERR"; findings_eq '[]'
rep 'm["pending_after"] is False and m["rows"] == 3' "interrupted: pending_after false"
jtrue '[x["session"] for x in d["mission"]["unlisted_review_sessions"]] == ["'"$S_F2"'"]' "the middle review reported unlisted"
pass "sweep-missing; class; provenance row; edges_added; after earlier x2; before not the issuing review's; interrupted sub-variant"
