#!/usr/bin/env bash
# Repair 4 (the PRD author's addendum 2; followon7/dream/requests/dream-author-lint-contract-repairs-addendum-2.md) — a
# chain review's sidecar row naming the consumer external:<name> that the review's frozen edges header does not declare
# is accepted when the manifest listed right after the review's in scope= has a frozen edges header declaring <name>, a
# repairs row with before = the review's manifest and after = that next manifest names the edges file in changed, and
# that row's author_session is the mission's author, not the reviewer; every other field check stands. The original
# failure moves to JSON findings_historical with declared_by (the manifest and the repairs row). The original (A1723's
# review-13 sidecar rows 1-3 shape: r1's F1 names external:newx, which m1's frozen header does not declare) is
# mission-finding-incomplete. Positive: m2's frozen header declares newx and F1's row (m1 -> m2, the author's) names the
# edges file: clean. Negatives, each mission-finding-incomplete: newx declared two manifests later (m3) only; declared in
# the live header only; F1's row does not name the edges file; the only row naming it is the reviewer's. Over-strict
# control: the installed rule (43d5b39) refuses the positive.
set -uo pipefail
# shellcheck source=tests/dlcr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/dlcr_lib.sh"
setup_mx
SC=notes/reviews/r1/verdict.txt.findings.jsonl
MSG="$SC: row 1: field consumers: not a list of prds members or declared external:<name>"
cx r4-original; run_mr; findings_eq '["mission-finding-incomplete"]'; has_fail mission-finding-incomplete "$MSG"
cx r4-positive; run_mr; clean
jtrue '([(h["id"], h["declared_by"]) for h in d["mission"]["findings_historical"]] == [("mission-finding-incomplete",
        {"external:newx": {"manifest": "'"$M2"'", "repairs_row": 1}})]
       and "external:newx not declared by its review" in d["mission"]["findings_historical"][0]["detail"])' \
  "the late declaration is kept under findings_historical, naming m2 and repairs row 1"
cx r4-later-only; run_mr; findings_eq '["mission-finding-incomplete"]'; has_fail mission-finding-incomplete "$MSG"
cx r4-live-only; run_mr; has_fail mission-finding-incomplete "$MSG"
cx r4-no-row; run_mr; has_fail mission-finding-incomplete "$MSG"
cx r4-reviewer-row; run_mr; has_fail mission-finding-incomplete "$MSG"
# two undeclared external names, only one of them declared at the next freeze: the whole row stays a failure
cx r4-two-names; run_mr; findings_eq '["mission-finding-incomplete"]'; has_fail mission-finding-incomplete "$MSG"
# a row by a session with no author launch row, by another round's reviewer, or for another manifest pair
for c in r4-foreign-row r4-other-reviewer-row r4-wrong-before r4-wrong-after; do
  cx "$c"; run_mr; has_fail mission-finding-incomplete "$MSG"
done
for c in r4-later-only r4-live-only r4-no-row r4-reviewer-row r4-two-names r4-foreign-row r4-other-reviewer-row r4-wrong-before r4-wrong-after; do
  cx "$c"; run_mr; jtrue '"findings_historical" not in d["mission"]' "$c: nothing historical"
done
today r4-positive; findings_eq '["mission-finding-incomplete"]'
pass "review-13 sidecar shape refused; a consumer declared at the next freeze by the author's edges row accepted and kept historical; two manifests later, live header only, no row, the reviewer's row (the reviewer also an admitted author), a second undeclared name, a row by a non-author session, by another round's reviewer, or for another manifest pair refused; the installed rule refuses the positive"
