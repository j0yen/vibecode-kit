#!/usr/bin/env bash
# Repair 5 (the PRD author's addendum 3; followon7/dream/requests/dream-author-lint-contract-repairs-addendum-3.md) — a
# post-review run-note entry may name the previous entry's matrix when (a) its Analysis: adversarial= path and uncovered=
# equal the previous entry's, (b) its Mission: scope= equals the previous entry's (nothing added), and (c) its Review:
# lines are the previous entry's plus at least one new line, each new line's launch row having role review and the
# scope_id of the last listed manifest. The original (A1723's review-14 shape: the 1:53:07 AM entry over the 1:22:59 AM
# entry, both naming one matrix) is analysis-grammar. Positive: the pre-review entry (13:00) and the post-review entry
# (14:00, adding r3's line) name the 11:00 matrix: clean. Negatives, each analysis-grammar: a manifest added to scope=;
# no new Review: line; the new line's launch row names m1's scope_id; uncovered= changed. Over-strict control: the
# installed rule (43d5b39) refuses the positive.
set -uo pipefail
# shellcheck source=tests/dlcr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/dlcr_lib.sh"
setup_mx
MSG="is not later than the previous entry 2026-11-18T13:00:00-08:00 (an earlier run's matrix)"
cx r5-positive; run_mr; clean
for c in r5-scope-added r5-no-new-review r5-other-scope-id r5-uncovered-changed r5-older-matrix r5-old-line-dropped r5-new-line-author-role r5-prev-other-task r5-scope-dropped; do
  cx "$c"; run_mr; has_fail analysis-grammar "$MSG"
done
cx r5-no-new-review; run_mr; findings_eq '["analysis-grammar"]'
cx r5-uncovered-changed; run_mr; findings_eq '["analysis-grammar"]'
cx r5-prev-other-task; run_mr; findings_eq '["analysis-grammar"]'
# r5-scope-dropped also carries mission-grammar (its scope= does not begin with the previous entry's list)
today r5-positive; findings_eq '["analysis-grammar"]'; has_fail analysis-grammar "$MSG"
pass "review-14 entry shape accepted when its matrix, scope and reviews carry over and a new review of the last manifest is added; scope added, no new review, another scope_id, uncovered changed, an older matrix, a dropped earlier review line and a new line whose latest launch row is an author row, a previous entry of another task, a previous scope without m1 refused; the installed rule refuses the positive"
