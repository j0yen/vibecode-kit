#!/usr/bin/env bash
# AC4 (R4, R5, R5b) — first group, each exit 0 with no finding: a row across two headers naming
# different matrices with `changed` naming the old and the new, the old only, the new only or
# neither; and a PRD added at the second freeze (m1 [foo] with x1 holding foo, m2 [foo, bar]).
# Second group, each refused with the manifest path in the detail: m1 listing no matrix
# (mission-scope-incomplete), m1's matrix copy with no sections or missing the batch slug bar
# (adversarial-slug-missing), with a family heading missing (adversarial-family-missing), or
# differing from the digest m1 lists (adversarial-missing).
set -uo pipefail
# shellcheck source=tests/drmx_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmx_lib.sh"
setup_mx
for c in two-both two-old two-new two-neither added-prd; do mx "$c"; run_mr; clean; done
M1="manifest notes/snapshots/m1/m1.sha256:"
mx m1-no-matrix; run_mr; has_fail mission-scope-incomplete "$M1" "lists no $(mxb 9)" "matrix named by the frozen edges header"
mx m1-no-sections; run_mr; has_fail adversarial-slug-missing "$M1" "PRD-foo"; has_fail adversarial-slug-missing "$M1" "PRD-bar"
mx m1-missing-slug; run_mr; has_fail adversarial-slug-missing "$M1" "PRD-bar"
printf '%s\n' "$ERR" | grep -q "^FAIL adversarial-slug-missing: $M1 .*PRD-foo" && fail "m1-missing-slug: foo reported: $ERR"
mx m1-bad-grammar; run_mr; has_fail adversarial-family-missing "$M1" "Falsifier quality"
mx m1-wrong-digest; run_mr; has_fail adversarial-missing "$M1" "$(mxb 9)" "differs"
pass "renamed-matrix rows (both, old, new, neither) and an added PRD pass; no matrix, no sections, missing slug, bad grammar, wrong digest refused per manifest"
