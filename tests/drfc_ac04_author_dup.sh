#!/usr/bin/env bash
# AC4 (R4, R1, R2) — row 1's author_session with no author launch row under this Task, or a
# chain reviewer's session (r6 F36), is repair-author-mismatch naming it; an earlier author
# with a launch row and no Route: line passes (the fixture's row 2, r5 A02), while entry 1's
# Route session without its launch row is refused (r2 F10); with no decisions log the Route:
# lines of this and earlier same-Task entries decide (entry 1's Route session passes, the
# unnamed one is refused); a second row for a repaired finding, a third after a decline and a
# repair, or two amended rows of one pair sharing a basename is repair-duplicate; a later
# sidecar re-using an id is mission-finding-incomplete and a re-raise under a new id with its
# own row exits 0 (r7 F43, r8 F46). Declined then repaired: rows 3 and the decline superseded;
# R2 (the following review of every row is the first chain review after its issuing review)
# with R5 (that review bound to an earlier manifest than after is repair-scope-mismatch) refuse
# the repaired row as written, which is r9's open F49 against this AC's "exit 0": asserted as
# the PRD lines decide, fail-closed, and reported.
set -uo pipefail
# shellcheck source=tests/drfc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drfc_lib.sh"
setup_fc
X=eeeeeeee-0000-4000-8000-0000000000ff
use base; redit "R[0]['author_session'] = '$X'"; run_fc; findings_eq '["repair-author-mismatch"]'; has_fail repair-author-mismatch "$X"
use base; redit "R[0]['author_session'] = '$S_F1'"; run_fc; findings_eq '["repair-author-mismatch"]'; has_fail repair-author-mismatch "$S_F1"
use base; run_fc; [ "$RC" = 0 ] || fail "earlier author with its row: rc=$RC $ERR"
use base; decedit "None if r.get('session') == '$S_FA0' else r"; run_fc; has_fail repair-author-mismatch "$S_FA0"
use base; _e2 set Route "Route: ungoverned session=$S_FA host=fixture"; run_fc_ungov; has_fail repair-author-mismatch "$S_FAX"
if printf '%s\n' "$ERR" | grep '^FAIL repair-author-mismatch' | grep -q "session $S_FA0"; then fail "ungoverned: entry 1's Route session refused: $ERR"; fi
use base; redit "R.append(dict(R[0]))"; run_fc; has_fail repair-duplicate "F1"
use declined-repaired; redit "R.append(dict(R[2]))"; run_fc; has_fail repair-duplicate "F1"
use amended; redit "R.append(dict(R[2]))"; run_fc; has_fail repair-duplicate "PRD-a.md"
use reraised-same; run_fc; has_fail mission-finding-incomplete "F1" "$R1D/verdict.txt.findings.jsonl" "$R2D/verdict.txt.findings.jsonl"
use reraised-new; run_fc; [ "$RC" = 0 ] || fail "re-raise under a new id: rc=$RC $ERR"; findings_eq '[]'
use declined-repaired; run_fc
rep 'm["rows"] == 3 and m["declined"][0]["superseded"] is True and m["repaired"] == 2' "declined then repaired: rows 3, superseded"
findings_eq '["repair-scope-mismatch"]'; has_fail repair-scope-mismatch "row 3"
pass "author x4, ungoverned lineage; duplicates x3; re-used and new id; declined then repaired (F49 literal)"
