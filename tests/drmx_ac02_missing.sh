#!/usr/bin/env bash
# AC2 (R2, R4b, R5) — a manifest whose frozen header names a matrix it does not list is
# mission-scope-incomplete naming the basename, the manifest and "matrix named by the frozen edges
# header"; a legacy header (no `matrix`) whose manifest lacks the matrix R2's fallback names is
# mission-scope-incomplete naming it and "matrix named by adversarial= (the header names none)";
# and tests/drmr_ac02_scope.sh (the predecessor's non-matrix assertions) still passes.
set -uo pipefail
# shellcheck source=tests/drmx_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmx_lib.sh"
setup_mx
mx missing-header; run_mr
has_fail mission-scope-incomplete "manifest notes/snapshots/m2/m2.sha256:" "lists no $(mxb 10)" "matrix named by the frozen edges header"
mx missing-legacy; run_mr
has_fail mission-scope-incomplete "manifest notes/snapshots/m1/m1.sha256:" "lists no $(mxb 9)" "matrix named by adversarial= (the header names none)"
printf '%s\n' "$ERR" | grep -q 'matrix of the frozen edges header' && fail "legacy: the old rule text is still printed: $ERR"
out=$(bash "$REPO/tests/drmr_ac02_scope.sh" 2>&1) || fail "tests/drmr_ac02_scope.sh: $out"
pass "header-named and adversarial=-named matrix refusals name their rule; drmr_ac02 passes"
