#!/usr/bin/env bash
# Repair 7 (the PRD author's addendum 5; followon7/dream/requests/source-03415-lint-contract-repairs-addendum-5.md) — a
# review file's line is a verdict line only when its first token is a PRD slug ([a-z0-9][a-z0-9-]*). Positive: chain
# review 19's shape, a markdown table row `| FIX and UNKNOWN hold; ... |` beside the real verdict lines, in the review
# file and in its result= capture, with a prose line whose first token looks like a slug: clean, none of
# review-scope-mismatch, review-result-mismatch or review-verdict-mismatch for slug `|`. Negatives, unchanged beside the same row: a scoped slug's FIX with no State
# token (review-verdict-mismatch naming it); a valid slug outside the scope (review-scope-mismatch naming it); a real
# verdict line absent from the result= capture (review-result-mismatch naming it). Over-strict control: the installed
# rule (43d5b39), which reads every line whose second token is a verdict word as a verdict line, refuses the positive
# with the three findings for slug `|`.
set -uo pipefail
# shellcheck source=tests/drsc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsc_lib.sh"
setup_v
NL=$'\n'
ROW='| FIX and UNKNOWN hold; only explicitly free proceeds | Met. The gate stops a held target beside a free one |'
STATE="State: rs-alpha=linted rs-alpha=reviewed:APPROVE rs-beta=linted rs-beta=reviewed:APPROVE"
run() { JS=$(lint --json 2>"$T/err"); RC=$?; no_traceback "$(cat "$T/err")"; OUT=$(lint 2>&1); }
none_for_bar() { printf '%s\n' "$OUT" | grep -F 'slug=|' && fail "$1: a finding names slug |: $OUT"
  printf '%s\n' "$OUT" | grep -F 'PRD-|.md' && fail "$1: a finding names PRD-|.md: $OUT"; return 0; }
PROSE='the table below restates the ruling'   # prose whose first token looks like a slug: no verdict word, no verdict line
# positive: the row in the review file and in the reviewer's final message
verdicts "# verdicts (Repair 7)${NL}rs-alpha APPROVE fable${NL}rs-beta APPROVE fable${NL}${PROSE}${NL}${ROW}${NL}" \
  "Review done.${NL}rs-alpha APPROVE fable${NL}rs-beta APPROVE fable${NL}${PROSE}${NL}${ROW}" "$STATE"
run; [ "$RC" = 0 ] || fail "positive: rc=$RC: $OUT"
[ "$(printf '%s' "$JS" | jget 'd["findings"]')" = "[]" ] || fail "positive: findings: $JS"; none_for_bar positive
# the row in the review file only (the reviewer's final message carries only the verdict lines)
reset_v; verdicts "rs-alpha APPROVE fable${NL}${ROW}${NL}rs-beta APPROVE fable${NL}" \
  "rs-alpha APPROVE fable${NL}rs-beta APPROVE fable" "$STATE"
run; [ "$RC" = 0 ] || fail "file-only row: rc=$RC: $OUT"; none_for_bar file-only
# negative 1: a scoped slug's FIX, no State token for it
reset_v; verdicts "rs-alpha FIX fable${NL}rs-beta APPROVE fable${NL}${ROW}${NL}" \
  "rs-alpha FIX fable${NL}rs-beta APPROVE fable" "State: rs-beta=linted rs-beta=reviewed:APPROVE"
run; [ "$RC" = 1 ] || fail "negative 1: rc=$RC: $OUT"
l=$(findline review-verdict-mismatch "$OUT") || fail "negative 1: no review-verdict-mismatch: $OUT"
printf '%s' "$l" | grep >/dev/null -F 'rs-alpha' || fail "negative 1: rs-alpha not named: $l"; none_for_bar negative-1
# negative 2: a valid slug outside the scope
reset_v; verdicts "rs-alpha APPROVE fable${NL}rs-beta APPROVE fable${NL}rs-gamma APPROVE fable${NL}${ROW}${NL}" \
  "rs-alpha APPROVE fable${NL}rs-beta APPROVE fable${NL}rs-gamma APPROVE fable" "$STATE"
run; [ "$RC" = 1 ] || fail "negative 2: rc=$RC: $OUT"
l=$(findline review-scope-mismatch "$OUT") || fail "negative 2: no review-scope-mismatch: $OUT"
printf '%s' "$l" | grep >/dev/null -F 'rs-gamma' || fail "negative 2: rs-gamma not named: $l"; none_for_bar negative-2
# negative 3: a real verdict line the result= capture does not carry
reset_v; verdicts "rs-alpha APPROVE fable${NL}rs-beta APPROVE fable${NL}${ROW}${NL}" "rs-alpha APPROVE fable" "$STATE"
run; [ "$RC" = 1 ] || fail "negative 3: rc=$RC: $OUT"
l=$(findline review-result-mismatch "$OUT") || fail "negative 3: no review-result-mismatch: $OUT"
printf '%s' "$l" | grep >/dev/null -F 'file-not-in-result: rs-beta APPROVE fable' || fail "negative 3: rs-beta not named: $l"
none_for_bar negative-3
# over-strict: the installed rule reads the row as the verdict FIX for slug | and refuses the positive
git -C "$REPO" show 43d5b39:skills/dream/scripts/dream-run-note-lint.sh > "$T/base43.sh" 2>/dev/null || fail "git show 43d5b39 failed"
chmod +x "$T/base43.sh"
reset_v; verdicts "# verdicts (Repair 7)${NL}rs-alpha APPROVE fable${NL}rs-beta APPROVE fable${NL}${ROW}${NL}" \
  "rs-alpha APPROVE fable${NL}rs-beta APPROVE fable" "$STATE"
keep=$LINT; LINT="$T/base43.sh"; run; LINT=$keep
[ "$RC" = 1 ] || fail "over-strict: the installed rule accepts the positive: $OUT"
for id in review-scope-mismatch review-result-mismatch review-verdict-mismatch; do
  findline "$id" "$OUT" | grep >/dev/null -F '|' || fail "over-strict: no $id naming |: $OUT"
done
pass "a table row beside the verdict lines is prose (in the review file and its result= capture); a scoped slug's FIX with no State token, a slug outside the scope and a verdict line missing from result= are still refused; the installed rule refuses the positive"
