#!/usr/bin/env bash
# AC8 (R6) — DREAM_SKILL_MD empty, missing or unreadable: exit 2, message names the path.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drpin_lib.sh"
tmp=$(mktemp -d); trap 'chmod -R u+rw "$tmp"; rm -rf "$tmp"' EXIT
out=$(DREAM_SKILL_MD='' bash "$DRIFT" 2>&1); rc=$?
[ "$rc" = 2 ] || fail "empty: rc=$rc: $out"
printf '%s\n' "$out" | grep -qF "''" || fail "empty: message does not name the empty path: $out"
out=$(DREAM_SKILL_MD="$tmp/nope/SKILL.md" bash "$DRIFT" 2>&1); rc=$?
[ "$rc" = 2 ] || fail "missing: rc=$rc: $out"
printf '%s\n' "$out" | grep -qF "$tmp/nope/SKILL.md" || fail "missing: path not named: $out"
note=""
if [ "$(id -u)" != 0 ]; then
  cp "$SKILL" "$tmp/unreadable.md"; chmod 000 "$tmp/unreadable.md"
  out=$(DREAM_SKILL_MD="$tmp/unreadable.md" bash "$DRIFT" 2>&1); rc=$?
  [ "$rc" = 2 ] || fail "unreadable: rc=$rc: $out"
  printf '%s\n' "$out" | grep -qF "$tmp/unreadable.md" || fail "unreadable: path not named: $out"
else note="unreadable case skipped as root"; fi
pass "$note"
