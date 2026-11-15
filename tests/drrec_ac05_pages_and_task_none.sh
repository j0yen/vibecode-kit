#!/usr/bin/env bash
# AC5 — analysis-page-missing; analysis-page-unbound; Task: none with ran =
# task-none-ran; Task: none with a governed Route = task-none-governed-route (exit 1).
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
setup; cp "$LOG" "$T/log.orig"
A="adversarial=$MX uncovered=1"
setline Analysis "Analysis: wwhtbt=ran visions/none.md 5whys=skipped: not a failure seed $A"
out=$(lint 2>&1); rc=$?; [ "$rc" = 1 ] && printf '%s\n' "$out" | grep -q '^FAIL analysis-page-missing: .*visions/none.md' || fail "missing: rc=$rc $out"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" analysis-page-missing
cp "$T/log.orig" "$LOG"; sed -i "/^session: $S_W/d" "$H/visions/wwhtbt-page.md"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" analysis-page-unbound
out=$(lint 2>&1); printf '%s\n' "$out" | grep -q '^FAIL analysis-page-unbound: .*visions/wwhtbt-page.md' || fail "unbound: $out"
cp "$FIX/home/visions/wwhtbt-page.md" "$H/visions/wwhtbt-page.md"
# Task: none + ran, on the governed fixture (other findings may accompany it)
setline Task "Task: none   Consumer: none"
out=$(lint 2>&1); rc=$?; [ "$rc" = 1 ] && printf '%s\n' "$out" | grep -q '^FAIL task-none-ran' || fail "task-none-ran (governed): rc=$rc $out"
# ...and isolated: ungoverned host, Route ungoverned, so task-none-ran is the only finding
setline Route "Route: ungoverned session=$S_DRAFT host=ryzen7"
js=$(lint_ungov --json 2>/dev/null); expect_exact "$?" 1 "$js" task-none-ran
# Task: none + governed Route
cp "$T/log.orig" "$LOG"; setline Task "Task: none   Consumer: none"
setline Analysis "Analysis: wwhtbt=skipped: amendment 5whys=skipped: not a failure seed adversarial=skipped: no review"
setline Review "Review: none"; setline State "State: foo=linted"
out=$(lint 2>&1); rc=$?; [ "$rc" = 1 ] && printf '%s\n' "$out" | grep -q '^FAIL task-none-governed-route' || fail "governed: rc=$rc $out"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" task-none-governed-route
pass
