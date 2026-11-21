#!/usr/bin/env bash
# AC3 — route provenance: unequal route/effort/task_id named on one FAIL line; a
# wwhtbt row names skill; a row lacking task_id names task_id; two matching rows
# are ambiguous; Route: ungoverned beside a --decisions file is refused.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
setup; cp "$DEC" "$T/dec.orig"; cp "$LOG" "$T/log.orig"
sel="r[\"session\"]==\"$S_DRAFT\""
decedit "dict(r,route='sonnet-medium',effort='medium',task_id='A2') if $sel else r"
out=$(lint 2>&1); rc=$?
[ "$rc" = 1 ] || fail "fields: rc=$rc $out"
l=$(printf '%s\n' "$out" | grep '^FAIL route-provenance-mismatch: ') || fail "fields: no FAIL: $out"
[ "$(printf '%s\n' "$l" | wc -l)" = 1 ] || fail "fields: more than one FAIL line: $l"
for w in route effort task_id; do printf '%s' "$l" | grep >/dev/null -w "$w" || fail "fields: $w not named: $l"; done
printf '%s' "$l" | grep >/dev/null -w model && fail "fields: model named though equal: $l"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" route-provenance-mismatch
cp "$T/dec.orig" "$DEC"; decedit "dict(r,skill='wwhtbt') if $sel else r"
out=$(lint 2>&1); printf '%s\n' "$out" | grep '^FAIL route-provenance-mismatch: ' | grep >/dev/null -w skill || fail "skill: $out"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" route-provenance-mismatch
cp "$T/dec.orig" "$DEC"; decedit "{k:v for k,v in r.items() if k!='task_id'} if $sel else r"
out=$(lint 2>&1); printf '%s\n' "$out" | grep '^FAIL route-provenance-mismatch: ' | grep >/dev/null -w task_id || fail "absent task_id: $out"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" route-provenance-mismatch
cp "$T/dec.orig" "$DEC"; decedit "[r,dict(r,account='lane-z')] if $sel else r"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" route-provenance-ambiguous
cp "$T/dec.orig" "$DEC"; setline Route "Route: ungoverned session=$S_DRAFT host=ryzen7"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" route-ungoverned-on-governed-host
cp "$T/log.orig" "$LOG"; setline Route "Route: fable-xhigh claude-fable-5-1 xhigh session=$S_DRAFT decision=2026-11-15T00:11:00-08:00"
out=$(lint 2>&1); printf '%s\n' "$out" | grep '^FAIL route-provenance-mismatch: ' | grep >/dev/null -w decision || fail "no row: decision not named: $out"
pass
