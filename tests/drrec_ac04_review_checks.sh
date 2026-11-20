#!/usr/bin/env bash
# AC4 — review-self (reviewer = Route session; Review: none beside reviewed:);
# review-provenance-missing naming session and field (wwhtbt row; another task);
# review-verdict-mismatch naming foo (file FIX beside reviewed:APPROVE or linted).
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
setup; cp "$DEC" "$T/dec.orig"; cp "$LOG" "$T/log.orig"
setline Review "Review: notes/reviews/review-A.txt reviewer-session=$S_DRAFT"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" review-self
cp "$T/log.orig" "$LOG"; setline Review "Review: none"
out=$(lint 2>&1); rc=$?; [ "$rc" = 1 ] && printf '%s\n' "$out" | grep >/dev/null '^FAIL review-self' || fail "none: rc=$rc $out"
cp "$T/log.orig" "$LOG"; sel="r[\"session\"]==\"$S_R1\""
decedit "dict(r,skill='wwhtbt') if $sel else r"
out=$(lint 2>&1); l=$(printf '%s\n' "$out" | grep '^FAIL review-provenance-missing: ') || fail "skill: $out"
printf '%s' "$l" | grep >/dev/null "$S_R1" && printf '%s' "$l" | grep >/dev/null -w skill || fail "skill: session/field not named: $l"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" review-provenance-missing
cp "$T/dec.orig" "$DEC"; decedit "dict(r,task_id='A2') if $sel else r"
out=$(lint 2>&1); l=$(printf '%s\n' "$out" | grep '^FAIL review-provenance-missing: ') || fail "task: $out"
printf '%s' "$l" | grep >/dev/null "$S_R1" && printf '%s' "$l" | grep >/dev/null -w task_id || fail "task: not named: $l"
cp "$T/dec.orig" "$DEC"; printf 'foo APPROVE fable\nfoo FIX fable\n' > "$H/notes/reviews/review-A.txt"
out=$(lint 2>&1); printf '%s\n' "$out" | grep '^FAIL review-verdict-mismatch: ' | grep >/dev/null -w foo || fail "approve-vs-fix: $out"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" review-verdict-mismatch
setline State "State: foo=linted"
out=$(lint 2>&1); l=$(printf '%s\n' "$out" | grep '^FAIL review-verdict-mismatch: ') || fail "linted: $out"
printf '%s' "$l" | grep >/dev/null -w foo && printf '%s' "$l" | grep >/dev/null -w linted || fail "linted: foo/linted not named: $l"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" review-verdict-mismatch
pass
