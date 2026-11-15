#!/usr/bin/env bash
# AC1 — wwhtbt=ran <page> with only a denied wwhtbt row for the task, or only a
# launch row for another task: FAIL analysis-provenance-missing naming wwhtbt and
# the task (exit 1). With a launch row whose session the page names: OK, exit 0.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
setup
out=$(lint 2>&1); rc=$?
[ "$rc" = 0 ] && [ "$out" = "OK $TS" ] || fail "base: rc=$rc out=$out"
cp "$DEC" "$T/dec.orig"
decedit 'None if (r["skill"]=="wwhtbt" and r["decision"]=="launch" and r["task_id"]=="A1") else r'
out=$(lint 2>&1); rc=$?
[ "$rc" = 1 ] || fail "denied-only: rc=$rc out=$out"
printf '%s\n' "$out" | grep -E '^FAIL analysis-provenance-missing: ' | grep -q wwhtbt || fail "denied-only: no FAIL naming wwhtbt: $out"
printf '%s\n' "$out" | grep -E '^FAIL analysis-provenance-missing: ' | grep -q 'A1' || fail "denied-only: task not named: $out"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" analysis-provenance-missing
cp "$T/dec.orig" "$DEC"
decedit 'dict(r,task_id="A2") if (r["skill"]=="wwhtbt" and r["task_id"]=="A1") else r'
out=$(lint 2>&1); rc=$?
[ "$rc" = 1 ] || fail "other-task: rc=$rc out=$out"
printf '%s\n' "$out" | grep -E '^FAIL analysis-provenance-missing: ' | grep -q 'wwhtbt' || fail "other-task: $out"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" analysis-provenance-missing
pass
