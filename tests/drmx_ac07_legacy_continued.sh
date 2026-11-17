#!/usr/bin/env bash
# AC7 (R2, R4) — a manifest first listed by an `adversarial=skipped:` entry and reviewed in a later
# entry naming a matrix (the drmr/variants/prefix shape): listing that matrix passes, not listing
# it is mission-scope-incomplete naming it and "matrix named by adversarial= (the header names
# none)"; a legacy cross-entry pair (entry 1's m1 with x1, entry 2's m2 with x2) whose row names
# the old and the new matrix in `changed` passes.
set -uo pipefail
# shellcheck source=tests/drmx_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmx_lib.sh"
setup_mx
mx prefix-listed; run_mr; clean
mx prefix-unlisted; run_mr
has_fail mission-scope-incomplete "manifest notes/snapshots/m1/m1.sha256:" "lists no $(mxb 13)" "matrix named by adversarial= (the header names none)"
mx legacy-pair; run_mr; clean
jtrue 'd["provenance"]["mission"] == "verified"' "legacy pair verified"
pass "skipped-first-entry manifest listed / unlisted; legacy cross-entry pair with old and new matrix in changed"
