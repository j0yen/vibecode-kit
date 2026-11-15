#!/usr/bin/env bash
# AC5 — known-bad control: a copy with `model: fable` in the frontmatter fails,
# exit 1, every FAIL line naming model.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drpin_lib.sh"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
fm_insert "$SKILL" 'model: fable' > "$tmp/SKILL.md"
frontmatter "$tmp/SKILL.md" | grep -qx 'model: fable' || fail "fixture did not insert the pin"
out=$(DREAM_SKILL_MD="$tmp/SKILL.md" bash "$DRIFT" 2>&1); rc=$?
[ "$rc" = 1 ] || fail "rc=$rc (want 1): $out"
printf '%s\n' "$out" | grep -q '^FAIL.*model' || fail "no FAIL naming model: $out"
bad=$(printf '%s\n' "$out" | grep '^FAIL' | grep -v model || true)
[ -z "$bad" ] || fail "FAIL line not about model: $bad"
pass
