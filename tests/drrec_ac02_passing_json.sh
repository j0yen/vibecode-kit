#!/usr/bin/env bash
# AC2 — a grammatical entry with fixture pages, matrix, verdict file and rows:
# OK <ts>, exit 0; --json prints one object with exit 0, empty findings, trust
# same-uid, adversarial beside analysis, and the provenance labels.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
setup
out=$(lint); rc=$?
[ "$rc" = 0 ] && [ "$out" = "OK $TS" ] || fail "text: rc=$rc out=$out"
js=$(lint --json 2>/dev/null); rc=$?
[ "$rc" = 0 ] || fail "json rc=$rc"
printf '%s' "$js" | python3 -c '
import sys,json
d=json.load(sys.stdin)
want={"route":"boundary","wwhtbt":"boundary","fivewhys":"self","adversarial":"self","reviews":"self","states":"self"}
assert d["exit"]==0 and d["findings"]==[], d
assert d["trust"]=="same-uid", d["trust"]
assert "adversarial" in d and "analysis" in d and set(d["analysis"])=={"wwhtbt","fivewhys"}, d["analysis"]
for k,v in want.items(): assert d["provenance"][k]==v,(k,d["provenance"])
assert d["ts"]=="2026-11-15T02:00:00-08:00" and d["task"]=="A1" and d["consumer"]=="hermes"
assert d["analysis"]["wwhtbt"]=={"kind":"ran","value":"visions/wwhtbt-page.md"}, d["analysis"]
assert d["analysis"]["fivewhys"]["kind"]=="skipped"
assert d["adversarial"]["kind"]=="matrix" and d["adversarial"]["uncovered"]==1
assert d["states"]=={"foo":["linted","reviewed:APPROVE"]}, d["states"]
assert d["route"]["route"]=="fable-xhigh" and d["route"]["model_id"]=="claude-fable-5-1"
assert d["decisions_malformed"]==0
' || fail "json shape: $js"
[ "$(printf '%s' "$js" | python3 -c 'import sys; print(len(sys.stdin.read().strip().splitlines()))')" = 1 ] || fail "not one JSON line"
pass
