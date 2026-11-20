#!/usr/bin/env bash
# AC7 (R6, R3) — `--edges <file> --prds PRD-a.md --json` with no log fills the mission block
# (other blocks null) and its exit matches the file (0 clean, 1 with a refused edge); --edges
# beside a log path, --matrix or --scope-id is exit 2; five thousand generated edges lint in
# under ten seconds on this builder with exit 0 and edges.total 5000; under Route: ungoverned
# with no decisions log, an emptied known-edge field still fires edge-unexplained.
set -uo pipefail
# shellcheck source=tests/drei_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drei_lib.sh"
setup_ei
js=$("$LINT" --edges "$EF" --prds PRD-a.md --json 2>"$T/err"); rc=$?; ERR=$(cat "$T/err"); no_tb
[ "$rc" = 0 ] || fail "--edges clean: rc=$rc $ERR"
printf '%s' "$js" | python3 -c '
import sys, json
d = json.load(sys.stdin)
assert d["exit"] == 0 and d["findings"] == [] and d["trust"] == "same-uid", d
m = d["mission"]
assert m["edges"] == {"total": 4, "known": 2, "external": 1, "unknown": 1} and m["unknown_edges"] == ["E4"] and m["prds"] == 2, m
for k in ("route", "analysis", "adversarial", "reviews", "states", "ts", "task"):
    assert d[k] is None, (k, d[k])
' || fail "--edges JSON: $js"
txt=$("$LINT" --edges "$EF" 2>&1); rc=$?
[ "$rc" = 0 ] && [ "$txt" = "OK edges $EF known=2 external=1 unknown=1" ] || fail "--edges text: rc=$rc $txt"
edge E1 "e['trigger'] = ''"
js=$("$LINT" --edges "$EF" --json 2>"$T/err"); rc=$?
[ "$rc" = 1 ] && [ "$(printf '%s' "$js" | jget 'd["findings"]')" = '["edge-unexplained"]' ] || fail "--edges refused edge: rc=$rc $js"
grep -q '^FAIL edge-unexplained: .*edge E1: trigger' "$T/err" || fail "--edges FAIL line: $(cat "$T/err")"
js=$("$LINT" --edges "$EF" --prds PRD-zz.md --json 2>/dev/null); rc=$?
if ! { [ "$rc" = 1 ] && printf '%s' "$js" | jget 'd["findings"]' | grep >/dev/null -F '"mission-prd-unlisted"'; }; then fail "--prds outside prds: rc=$rc $js"; fi
reset_ei
for args in "$LOG --edges $EF" "--edges $EF --matrix $EF --states a=linted" "--edges $EF --scope-id $H/$EI_M1"; do
  # shellcheck disable=SC2086  # word splitting of the argument list is intended
  "$LINT" $args >"$T/o" 2>"$T/e"; rc=$?
  if ! { [ "$rc" = 2 ] && [ ! -s "$T/o" ] && grep -q '^ERROR ' "$T/e"; }; then fail "mixed [$args]: rc=$rc $(cat "$T/o" "$T/e")"; fi
done
# five thousand edges, linear pass
python3 - "$EF" "$T/big.jsonl" <<'PY'
import sys, json
h = json.loads(open(sys.argv[1]).readline())
f8 = ("command", "trigger", "authority", "effect_id", "recovery_owner", "postcondition")
with open(sys.argv[2], "w") as out:
    out.write(json.dumps(h) + "\n")
    for i in range(5000):
        e = {"id": f"G{i}", "status": "known", "producer": "PRD-a.md", "consumer": "PRD-b.md"}
        e.update({k: f"{k} {i}" for k in f8})
        out.write(json.dumps(e) + "\n")
PY
t0=$(date +%s%N); js=$("$LINT" --edges "$T/big.jsonl" --json 2>"$T/err"); rc=$?; t1=$(date +%s%N)
ms=$(( (t1 - t0) / 1000000 ))
[ "$rc" = 0 ] && [ "$(printf '%s' "$js" | jget 'd["mission"]["edges"]["total"]')" = 5000 ] || fail "5000 edges: rc=$rc $(head -c 300 "$T/err")"
[ "$ms" -lt 10000 ] || fail "5000 edges took ${ms} ms (bound 10000)"
echo "ok 5000 edges in ${ms} ms on $(hostname)"
# ungoverned host (no decisions log in the private HOME): the edge checks still run
reset_ei; setline Route "Route: ungoverned session=$S_EAUTH host=$(hostname)"; edge E2 "e['postcondition'] = ''"
JS=$(lint_ungov --json 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_tb
[ "$RC" = 1 ] || fail "ungoverned: rc=$RC $ERR"; findings_eq '["edge-unexplained"]'; has_fail edge-unexplained "edge E2: postcondition"
pass "--edges JSON/text/exit, mixed modes exit 2, 5000 edges ${ms} ms, ungoverned edge-unexplained"
