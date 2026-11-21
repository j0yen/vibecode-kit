#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the drmx_* tests (PRD-dream-matrix-per-manifest). Reuses the drmr and drrec
# helpers (setup_mr's private HOME, lint, run_mr, findings_eq, has_id, no_id, has_fail, jtrue).
# `mx <case>` builds one case of tests/fixtures/drmx/mfx.py (a mission whose matrices and edge maps
# come from the lint's own selftest helpers) into $W and points LOG, DEC and H at it.
# BASE_SHA is every successor PRD's Cited-tree; base_lint writes that tree's lint to $T/base.sh.
# shellcheck source=tests/drmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmr_lib.sh"
MXFIX="$here/fixtures/drmx"
MFX="$MXFIX/mfx.py"
BASE_SHA=8559929e31f99a960eb4f6f156bb4f1da0c731ee
setup_mx() { setup_mr; }
mx() { rm -rf "${W:?}"; python3 -I "$MFX" "$1" "$W" || fail "fixture $1 did not build"
  LOG="$W/home/notes/dream-log.md"; DEC="$W/decisions.jsonl"; H="$W/home"; CASE=$1; }
base_lint() { git -C "$REPO" show "$BASE_SHA:skills/dream/scripts/dream-run-note-lint.sh" > "$T/base.sh" 2>/dev/null \
  || fail "git show $BASE_SHA:skills/dream/scripts/dream-run-note-lint.sh failed"; }
# mxb <hour>: the basename of the fixture matrix written at <hour>:00 on the fixture day
mxb() { printf '2026-11-18T%02d:00:00-08:00-adversarial.md' "$1"; }
# clean: exit 0, no finding
clean() { [ "$RC" = 0 ] || fail "${CASE}: rc=$RC (want 0): $ERR"; findings_eq '[]'; }
# compat <base lint> <head lint> <report file> [<python predicate on (tag, mode, entry) naming a note
# whose output may differ>]: lint every checked-in compatibility note (tests/fixtures/drrec, drei,
# drsp, drmr and drfc with every variant materialized as `use` does) at every entry and --last, in
# text and --json, with both lints and a private HOME; writes one line per difference to the report
# and returns 1 when any difference is outside the predicate
compat() { python3 -I "$MXFIX/compat.py" "$here/fixtures" "$1" "$2" "$3" "${4:-False}"; }
