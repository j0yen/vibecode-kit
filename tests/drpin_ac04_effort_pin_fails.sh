#!/usr/bin/env bash
# AC4 — known-bad control: a copy with `effort: max` in the frontmatter fails,
# exit 1, every FAIL line naming effort.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drpin_lib.sh"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
fm_insert "$SKILL" 'effort: max' > "$tmp/SKILL.md"
frontmatter "$tmp/SKILL.md" | grep >/dev/null -x 'effort: max' || fail "fixture did not insert the pin"
out=$(DREAM_SKILL_MD="$tmp/SKILL.md" bash "$DRIFT" 2>&1); rc=$?
[ "$rc" = 1 ] || fail "rc=$rc (want 1): $out"
printf '%s\n' "$out" | grep >/dev/null '^FAIL.*effort' || fail "no FAIL naming effort: $out"
bad=$(printf '%s\n' "$out" | grep '^FAIL' | grep -v effort || true)
[ -z "$bad" ] || fail "FAIL line not about effort: $bad"
pass
