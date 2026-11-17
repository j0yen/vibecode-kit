#!/usr/bin/env bash
# AC2 (R3, R5, R2) — row 1 (missing-producer-runner on a, consumer b) without an edge incident
# to a in its sweep is sweep-missing naming F1 and the edge; class authority-bypass is
# repair-class-mismatch; row 2 (provenance, empty sweep and changed) fires nothing; edges only
# in after's frozen copy are reported as edges_added; row 1's after not a later listed manifest,
# or its following review bound to an earlier manifest, is repair-scope-mismatch naming the row;
# the amended-row variant's interrupted sub-variant (the middle manifest's only review row on no
# Review: line; the third manifest's chain review follows the base rows; r7 F44, r8 F47) exits
# 0 with pending_after false and the unlisted row reported.
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
use amended-interrupted; run_fc
[ "$RC" = 0 ] || fail "interrupted sub-variant: rc=$RC $ERR"; findings_eq '[]'
rep 'm["pending_after"] is False and m["rows"] == 3' "interrupted: pending_after false"
jtrue '[x["session"] for x in d["mission"]["unlisted_review_sessions"]] == ["'"$S_F2"'"]' "the middle review reported unlisted"
pass "sweep-missing; class; provenance row; edges_added; after earlier x2; interrupted sub-variant"
