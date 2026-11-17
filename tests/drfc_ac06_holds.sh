#!/usr/bin/env bash
# AC6 (R7, R2) — before the second chain review (rows written, the after manifest listed and
# unreviewed) a or b eligible is mission-approval-blocked naming F1 and d naming "no chain
# review of the last manifest", with pending_after true (r7 F40); in the three-review variant,
# before the third review a, b and d are refused, after its APPROVE all pass eligible with
# exit 0 and provenance.mission verified (r4 F25), and a third FIX keeps a and b refused
# naming row 1's finding; a declined row whose decline nothing accepts keeps a and b held under
# the final APPROVE (r3 F20); the drfc fixture's final APPROVE releases every row (exit 0).
set -uo pipefail
# shellcheck source=tests/drfc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drfc_lib.sh"
setup_fc
PRE="a=linted a=reviewed:FIX b=linted b=reviewed:FIX c=linted c=reviewed:FIX d=linted d=reviewed:APPROVE"
use pre; run_fc; [ "$RC" = 0 ] || fail "in progress, nothing eligible: rc=$RC $ERR"; rep 'm["pending_after"] is True' "pending_after true"
for s in a b; do use pre; st2 "$PRE $s=eligible"; run_fc; findings_eq '["mission-approval-blocked"]'; has_fail mission-approval-blocked "slug $s" "F1"; done
use pre; st2 "$PRE d=eligible"; run_fc; has_fail mission-approval-blocked "slug d" "no chain review of the last manifest"
T3="a=linted a=reviewed:FIX a=reviewed:APPROVE b=linted b=reviewed:FIX b=reviewed:APPROVE c=linted c=reviewed:FIX c=reviewed:APPROVE d=linted d=reviewed:APPROVE d=reviewed:FIX"
for s in a b d; do use three-pre; st2 "$T3 $s=eligible"; run_fc; has_fail mission-approval-blocked "slug $s" "no chain review of the last manifest"; done
use three; run_fc; [ "$RC" = 0 ] || fail "three-review, all eligible after the APPROVE: rc=$RC $ERR"; findings_eq '[]'
jtrue 'd["provenance"]["mission"] == "verified" and all("eligible" in v for v in d["states"].values())' "three: verified, all eligible"
for s in a b; do use three-fix; st2 "$T3 a=reviewed:APPROVE b=reviewed:APPROVE c=reviewed:APPROVE d=reviewed:FIX $s=eligible"; run_fc
  has_fail mission-approval-blocked "slug $s" "F1"; done
use declined; rm -f -- "${H:?}/$R2D/verdict.txt.findings.jsonl"; capture "$R2D/result.json" "L[:] = [('findings=none' if l.startswith('findings=') else l) for l in L]"
run_fc; for s in a b; do has_fail mission-approval-blocked "slug $s" "F1"; done
use base; run_fc; [ "$RC" = 0 ] || fail "drfc fixture, all eligible: rc=$RC $ERR"
pass "in progress a, b, d; three-review before/after/FIX; unaccepted decline held; released"
