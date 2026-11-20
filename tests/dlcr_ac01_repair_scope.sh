#!/usr/bin/env bash
# Repair 1 (A1723 decision 3; followon7/dream/requests/source-03415-lint-contract-repairs.md) — a repaired row's `before`
# may be a listed manifest B later than the manifest I its finding's issuing review is bound to, when no chain review is
# bound to a manifest in (I, B] and each of those is the `after` of some repairs row; `after` stays the manifest following
# `before`. Positive, the A1723 round-11b shape (r1 on m1 issues F1 and F2; F1's row m1 -> m2; m2 frozen with no chain
# review; F2's row m2 -> m3; r3 on m3 APPROVE): clean. Negatives: m2 carrying a chain review gives today's
# repair-scope-mismatch (before is not the issuing review's manifest); m2 the after of no repairs row (F1 has no row) gives
# repair-scope-mismatch naming m2; a before earlier than the issuing review's manifest gives today's
# repair-scope-mismatch. Over-strict control: the installed rule (43d5b39, before must be the issuing review's manifest)
# refuses the positive.
set -uo pipefail
# shellcheck source=tests/dlcr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/dlcr_lib.sh"
setup_mx
cx r1-positive; run_mr; clean
cx r1-intermediate-reviewed; run_mr; findings_eq '["repair-scope-mismatch"]'
has_fail repair-scope-mismatch "row 2 (finding F2): before $M2 canonicalizes to" "the issuing review notes/reviews/r1/verdict.txt is bound to"
cx r1-intermediate-undeclared; run_mr; has_id repair-scope-mismatch
has_fail repair-scope-mismatch "row 1 (finding F2): before $M2 is later than the issuing review's manifest" \
  "$M2 between them is the after of no repairs row"
cx r1-before-earlier; run_mr; has_id repair-scope-mismatch
has_fail repair-scope-mismatch "row 2 (finding F2): before $M1 canonicalizes to" "the issuing review notes/reviews/r2/verdict.txt is bound to"
today r1-positive; findings_eq '["repair-scope-mismatch"]'
has_fail repair-scope-mismatch "row 2 (finding F2): before $M2 canonicalizes to" "the issuing review notes/reviews/r1/verdict.txt is bound to"
pass "before after an unreviewed, declared intermediate freeze: clean; intermediate reviewed, intermediate undeclared and before earlier refused; the installed rule refuses the positive"
