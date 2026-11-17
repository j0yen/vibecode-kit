#!/usr/bin/env bash
# AC3 (R1, R3) — a last manifest whose frozen header names a matrix other than the note's
# adversarial= basename, and a live header that does, are mission-scope-mismatch naming both
# basenames; a live header `matrix` that is empty, not a string, a path, not a `.md` basename, a
# PRD basename or the vision's (a packet member) is edge-grammar naming the field matrix.
set -uo pipefail
# shellcheck source=tests/drmx_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmx_lib.sh"
setup_mx
mx last-differs; run_mr
has_fail mission-scope-mismatch "notes/snapshots/m3/m3.sha256" "$(mxb 10)" "$(mxb 11)"
mx live-differs; run_mr
has_fail mission-scope-mismatch "live edges header" "2027-03-01T23:00:00-08:00-adversarial.md" "$(mxb 11)"
for c in matrix-empty matrix-int matrix-path matrix-not-md matrix-prd matrix-vision; do
  mx "$c"; run_mr; has_fail edge-grammar "field matrix"
done
pass "last header and live header mismatch name both; six bad matrix values are edge-grammar on the field"
