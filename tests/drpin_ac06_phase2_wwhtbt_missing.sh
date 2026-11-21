#!/usr/bin/env bash
# AC6 — known-bad control: a copy whose Phase 2 section lacks `/wwhtbt` fails,
# exit 1, naming the missing reference.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drpin_lib.sh"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
awk '/^## Phase 2 — Vision/{f=1;print;next} /^## /{f=0} f{gsub(/`\/wwhtbt`/,"the forward-analysis skill")} {print}' "$SKILL" > "$tmp/SKILL.md"
awk '/^## Phase 2 — Vision/{f=1;next} /^## /{f=0} f' "$tmp/SKILL.md" | grep >/dev/null '`/wwhtbt`' && fail "fixture still has /wwhtbt in Phase 2"
out=$(DREAM_SKILL_MD="$tmp/SKILL.md" bash "$DRIFT" 2>&1); rc=$?
[ "$rc" = 1 ] || fail "rc=$rc (want 1): $out"
printf '%s\n' "$out" | grep >/dev/null '^FAIL Phase 2 does not reference `/wwhtbt`' || fail "no FAIL naming /wwhtbt: $out"
bad=$(printf '%s\n' "$out" | grep '^FAIL' | grep -v '/wwhtbt' || true)
[ -z "$bad" ] || fail "other FAIL lines: $bad"
pass
