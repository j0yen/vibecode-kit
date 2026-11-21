#!/usr/bin/env bash
# AC3 — with DREAM_SKILL_MD unset the drift test exits 0 and prints PASS, and its
# assertions include AC2's grep.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drpin_lib.sh"
out=$(env -u DREAM_SKILL_MD bash "$DRIFT" 2>&1); rc=$?
[ "$rc" = 0 ] || fail "drift test rc=$rc: $out"
printf '%s\n' "$out" | grep >/dev/null '^PASS' || fail "no PASS line: $out"
grep -qF "'Fable at max|effort: max|model: fable'" "$DRIFT" || fail "drift test lacks AC2's grep"
pass
