#!/usr/bin/env bash
# AC4 (R3, R4) — the FIX fixture lints clean with its finding counted (the advisory accepts
# row, empty prds, uncounted); its sidecar absent, empty, lacking a field or a known class,
# or holding an advisory accepts row of a class other than provenance (R4, review L10) (the
# capture's findings= line re-signed so the rows are read), or differing from the
# capture's findings= line (an accepts row appended, a finding deleted), also before
# SIDECAR_BINDING_SINCE when the line is present, is mission-finding-incomplete naming the
# file, row, field or result path; before SIDECAR_BINDING_SINCE without the line it is
# sidecar_bound false and no finding, and launched after it without the line (the FIX fixture,
# its findings= line removed) it is mission-finding-incomplete naming the file, the result path
# and "no findings= line" (review M3: the time only excuses a pre-install absence); a sidecar
# that exists but cannot be read (mode 000, beside the passing fixture's findings=none) is no
# absence (R3: none if and only if the file is absent): mission-finding-incomplete naming it
# unreadable, sidecar_bound false (review L14; as root the case prints a SKIP line); 0 or 2
# mission= lines, another session's, a differing
# result= line or no result= is mission-verdict-missing with provenance.mission self. R4's
# cross-sidecar uniqueness (the re-used-id variant; r9 F50 notes AC4's text omits it) is
# asserted too: a re-used id names the id and both files; a new id fires nothing of R4.
set -uo pipefail
# shellcheck source=tests/drmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmr_lib.sh"
setup_mr
SC="$MR_CHAIN/verdict.txt.findings.jsonl"
use fix; run_mr
[ "$RC" = 0 ] || fail "FIX fixture: rc=$RC $ERR"; findings_eq '[]'
jtrue 'd["mission"]["verdict"] == "FIX" and d["mission"]["findings"] == 1 and d["provenance"]["mission"] == "self" and d["mission"]["chain_reviews"][0]["sidecar_bound"] is True' "FIX fixture JSON"
use fix; rm -f -- "${H:?}/${SC:?}"; run_mr; has_fail mission-finding-incomplete "$MR_CHAIN/verdict.txt"
use fix; : > "$H/$SC"; resign "$MR_CHAIN"; run_mr; has_fail mission-finding-incomplete "$SC"
use fix; side "$MR_CHAIN" "del R[0]['control']"; resign "$MR_CHAIN"; run_mr; findings_eq '["mission-finding-incomplete"]'
has_fail mission-finding-incomplete "$SC" "row 1" "control"
use fix; side "$MR_CHAIN" "R[0]['class'] = 'bogus-class'"; resign "$MR_CHAIN"; run_mr; findings_eq '["mission-finding-incomplete"]'
has_fail mission-finding-incomplete "$SC" "row 1" "class"
use fix; side "$MR_CHAIN" "R[1]['class'] = 'authority-bypass'"; resign "$MR_CHAIN"; run_mr; findings_eq '["mission-finding-incomplete"]'
has_fail mission-finding-incomplete "$SC" "row 2" "field class" "an advisory accepts row is class provenance"
use fix; side "$MR_CHAIN" "R[0]['consumers'] = []"; resign "$MR_CHAIN"; run_mr; has_fail mission-finding-incomplete "row 1" "consumers"
for v in sidecar-accepts sidecar-deleted preinstall-line; do
  use "$v"; run_mr; findings_eq '["mission-finding-incomplete"]'
  has_fail mission-finding-incomplete "$MR_CHAIN/verdict.txt" "$MR_CHAIN/result.json" "findings="
done
use preinstall-noline; run_mr
[ "$RC" = 0 ] || fail "pre-install, no line: rc=$RC $ERR"; findings_eq '[]'
jtrue 'd["mission"]["chain_reviews"][0]["sidecar_bound"] is False' "pre-install unbound"
use fix; capture "$MR_CHAIN/result.json" "L[:] = [l for l in L if not l.startswith('findings=')]"; run_mr
[ "$RC" = 1 ] || fail "post-install capture without a findings= line: rc=$RC $ERR"; findings_eq '["mission-finding-incomplete"]'
has_fail mission-finding-incomplete "$MR_CHAIN/verdict.txt" "$MR_CHAIN/result.json" "no findings= line"
UNREAD="unreadable sidecar"
if [ "$(id -u)" = 0 ]; then
  echo "SKIP $(basename "$0"): unreadable-sidecar case (review L14): euid 0 reads a mode-000 file"; UNREAD="unreadable sidecar SKIPPED (euid 0)"
else
  use base; head -1 "$MRFIX/variants/fix/home/$SC" > "$H/$SC"; chmod 000 "$H/$SC"; run_mr; chmod 600 "$H/$SC"
  [ "$RC" = 1 ] || fail "unreadable sidecar beside findings=none: rc=$RC $ERR"; findings_eq '["mission-finding-incomplete"]'
  has_fail mission-finding-incomplete "$SC" "unreadable"
  jtrue 'd["mission"]["chain_reviews"][0]["sidecar_bound"] is False' "unreadable sidecar unbound"
fi
# the mission= line
mv_() { run_mr; has_fail mission-verdict-missing "$MR_CHAIN/verdict.txt" "$@"; jtrue 'd["provenance"]["mission"] == "self"' "self beside mission-verdict-missing"; }
use base; vedit "$MR_CHAIN/verdict.txt" "L[:] = [l for l in L if not l.startswith('mission=')]"; mv_
use base; vedit "$MR_CHAIN/verdict.txt" "L.insert(1, 'mission=APPROVE $S_M1')"; mv_
use base; vedit "$MR_CHAIN/verdict.txt" "L[:] = [('mission=APPROVE $S_M2' if l.startswith('mission=') else l) for l in L]"; mv_
use base; capture "$MR_CHAIN/result.json" "L[:] = [('mission=FIX $S_M1' if l.startswith('mission=') else l) for l in L]"; mv_ "$MR_CHAIN/result.json"
use base; setline Review "Review: $MR_CHAIN/verdict.txt reviewer-session=$S_M1"; mv_ "no result= capture"
# R4: finding ids unique across the note's chain-review sidecars (r8 F46; r9 F50)
use reused-id; run_mr; has_fail mission-finding-incomplete "F1" "$SC" "notes/reviews/chain-r2/verdict.txt.findings.jsonl"
use reused-id; side notes/reviews/chain-r2 "R[0]['id'] = 'F7'"; resign notes/reviews/chain-r2; run_mr; no_id mission-finding-incomplete
pass "FIX clean; sidecar absent/empty/field/class/consumers/advisory class; digest x3; pre-install unbound; post-install no findings= line; $UNREAD; mission= x5; re-used id"
