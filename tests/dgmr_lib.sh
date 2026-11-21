#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the dgmr_* tests (PRD-dream-generation-aware-mission-records; R1, the legacy
# matrix, and R4, path keys, are built; R2, R3 and R5 are not). Reuses the drmx, drmr and drrec
# helpers (setup_mr's private HOME, lint, run_mr, findings_eq, has_id, no_id, has_fail, jtrue, clean,
# compat). `gx <case>` builds one case of tests/fixtures/dgmr/gfx.py into $W and points LOG, DEC and H
# at it. BASE43 is vibecode-kit 43d5b39, the installed tree these rules extend; base43_lint writes its
# lint to $T/base43.sh. DRREC_LINT runs the tests against another copy (known-bad controls).
# shellcheck source=tests/drmx_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmx_lib.sh"
GXFIX="$here/fixtures/dgmr"
GFX="$GXFIX/gfx.py"
BASE43=43d5b39eb7aa80805dbfe9bc03f43c7fc28045de
gx() { rm -rf "${W:?}"; python3 -I "$GFX" "$1" "$W" || fail "fixture $1 did not build"
  LOG="$W/home/notes/dream-log.md"; DEC="$W/decisions.jsonl"; H="$W/home"; CASE=$1; }
base43_lint() { git -C "$REPO" show "$BASE43:skills/dream/scripts/dream-run-note-lint.sh" > "$T/base43.sh" 2>/dev/null \
  || fail "git show $BASE43:skills/dream/scripts/dream-run-note-lint.sh failed"; }
# rep '<python expression on m (the mission.repairs object)>' [message]
rep() { jtrue "isinstance(d['mission'].get('repairs'), dict) and (lambda m: $1)(d['mission']['repairs'])" "${2:-repairs: $1}"; }
# gmxb <day> <hour>: the basename of a fixture matrix written at <hour>:00 on <day>
gmxb() { printf '%sT%02d:00:00-08:00-adversarial.md' "$1" "$2"; }
OLD_DAY=2026-11-17
# the drmx fixture day (mfx.DAY), re-dated by PRD-dream-analysis-trigger-record R7 before its cutover
NEW_DAY=$(sed -n 's/^DAY = "\(.*\)"$/\1/p' "$here/fixtures/drmx/mfx.py")
