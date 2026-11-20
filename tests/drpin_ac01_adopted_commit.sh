#!/usr/bin/env bash
# AC1 — the landed SKILL.md is commit 11cd41be's two hunks plus R2's one sentence:
# the frontmatter equals the commit's (fable-spawn kept, no model:/effort:), and the
# Phase routing paragraph is the commit's paragraph followed by R2's sentence only.
# DRPIN_DIFF_STRICT=1 also asserts `git diff 11cd41be -- skills/dream/SKILL.md` adds
# only R2's sentence and removes nothing (true at the pin-removal commit; a later
# PRD that edits other phases of the file adds its own hunks).
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drpin_lib.sh"
git -C "$REPO" cat-file -e "$ADOPTED^{commit}" 2>/dev/null || { echo "UNKNOWN commit $ADOPTED not in this clone"; exit 2; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
git -C "$REPO" show "$ADOPTED:skills/dream/SKILL.md" > "$tmp/adopted.md"
[ "$(frontmatter "$SKILL")" = "$(frontmatter "$tmp/adopted.md")" ] || fail "frontmatter differs from $ADOPTED"
frontmatter "$SKILL" | grep >/dev/null -x 'fable-spawn: true' || fail "fable-spawn: true missing"
frontmatter "$SKILL" | grep >/dev/null -E '^(model|effort):' && fail "frontmatter still pins model/effort"
phase_routing "$tmp/adopted.md" > "$tmp/want"
phase_routing "$SKILL" > "$tmp/got"
n=$(wc -l < "$tmp/want")
[ "$n" -gt 0 ] || fail "adopted commit has no Phase routing paragraph"
head -n "$n" "$tmp/got" | cmp -s - "$tmp/want" || fail "Phase routing paragraph's first $n lines differ from $ADOPTED"
extra=$(tail -n +"$((n+1))" "$tmp/got" | tr '\n' ' ' | sed 's/ *$//')
[ "$extra" = "$R2_SENTENCE" ] || fail "lines after the adopted paragraph are not exactly R2's sentence: [$extra]"
grep -q '^\*\*Drafting model:\*\*' "$SKILL" && fail "old Drafting model paragraph still present"
if [ "${DRPIN_DIFF_STRICT:-0}" = 1 ]; then
  d=$(git -C "$REPO" diff "$ADOPTED" -- skills/dream/SKILL.md)
  rem=$(printf '%s\n' "$d" | grep -E '^-' | grep -vE '^--- ' || true)
  [ -z "$rem" ] || fail "strict: diff removes lines: $rem"
  add=$(printf '%s\n' "$d" | grep -E '^\+' | grep -vE '^\+\+\+ ' | sed 's/^+//' | tr '\n' ' ' | sed 's/ *$//')
  [ "$add" = "$R2_SENTENCE" ] || fail "strict: added lines are not exactly R2's sentence: [$add]"
fi
pass "adopted hunks intact + R2 sentence${DRPIN_DIFF_STRICT:+ (strict diff)}"
