#!/usr/bin/env bash
# AC3 (R1, R3) — a last manifest whose frozen header names a matrix other than the note's
# adversarial= basename, and a live header that does, are mission-scope-mismatch naming both
# basenames; a live header `matrix` that is empty, not a string, a path, not a `.md` basename, a
# PRD basename or the vision's (a packet member) is edge-grammar naming the field matrix; so is a
# `matrix` naming the header's own external contract ("an external contract member"), and, on an
# edges file named with .md checked by --edges, one naming the edges file itself ("an edges file member").
set -uo pipefail
# shellcheck source=tests/drmx_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmx_lib.sh"
setup_mx
mx last-differs; run_mr
has_fail mission-scope-mismatch "notes/snapshots/m3/m3.sha256" "$(mxb 10)" "$(mxb 11)"
mx live-differs; run_mr
has_fail mission-scope-mismatch "live edges header" "2026-11-18T23:00:00-08:00-adversarial.md" "$(mxb 11)"
for c in matrix-empty matrix-int matrix-path matrix-not-md matrix-prd matrix-vision; do
  mx "$c"; run_mr; has_fail edge-grammar "field matrix"
done
mx matrix-contract; run_mr
has_fail edge-grammar "field matrix" "'hermes-contract.md' is the basename of an external contract member"
mx matrix-edges-file; ERR=$("$LINT" --edges "$W/home/notes/missions/drmx-self-edges.md" 2>&1); RC=$?; no_tb
[ "$RC" = 1 ] || fail "matrix-edges-file: rc=$RC (want 1): $ERR"
has_fail edge-grammar "field matrix" "'drmx-self-edges.md' is the basename of an edges file member"
pass "last header and live header mismatch name both; eight bad matrix values (the own contract and edges file among them) are edge-grammar on the field"
