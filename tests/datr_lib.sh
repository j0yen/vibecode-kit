#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the datr_* tests (PRD-dream-analysis-trigger-record). The cases live in
# tests/fixtures/datr/dfx.py (built with the lint's own selftest helpers, or from the checked-in
# drfc mission); `cases <prefix>` lints every case of one AC with the real lint script, a private
# HOME and a working directory that is neither the home nor any manifest's.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$here/.." && pwd)"
LINT="${DATR_LINT:-$REPO/skills/dream/scripts/dream-run-note-lint.sh}"   # DATR_LINT: run the cases against another copy (known-bad controls)
DFX="$here/fixtures/datr/dfx.py"
BASE_SHA=43d5b39eb7aa80805dbfe9bc03f43c7fc28045de                       # the Cited-tree of PRD-dream-analysis-trigger-record
fail() { echo "FAIL $(basename "$0"): $*"; exit 1; }
pass() { echo "PASS $(basename "$0")${1:+: $1}"; exit 0; }
# cases <prefix>: every case of the prefix must PASS (exact exit, exact finding-id set, the AC's JSON predicate, the named detail)
cases() {
  local out rc
  out=$(python3 -I "$DFX" --run "$1" "$LINT" 2>&1); rc=$?
  [ "$rc" = 0 ] || fail "$(printf '%s\n' "$out" | grep -v '^PASS' | head -20)"
  CASES_PASSED=$(printf '%s\n' "$out" | grep -c '^PASS')
}
# base_lint <path>: the Cited-tree's lint, read by git at run time (never a checked-in copy)
base_lint() { git -C "$REPO" show "$BASE_SHA:skills/dream/scripts/dream-run-note-lint.sh" > "$1" 2>/dev/null \
  || fail "git show $BASE_SHA:skills/dream/scripts/dream-run-note-lint.sh failed"; }
