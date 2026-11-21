#!/usr/bin/env bash
# AC6 (R1) — two Mission: lines, a spaced name, an unknown key=value token or no edges=
# anywhere is mission-grammar naming the token; in the two-entry note (entry 1 with
# Mission: and scope=, entry 2 same Task: naming a prds member eligible) entry 2 without
# the line is mission-grammar naming entry 1's timestamp, also when the live header drops
# that PRD and entry 1's State: names only b (entry 1's frozen copy alone keeps it in the
# continuity set), or entry 1 carries no scope= (its State: slugs alone keep it); with the
# line entry 2 inherits edges= and scope= (inherited_from = entry 1); an explicit different
# edges= is mission-grammar naming the token.
set -uo pipefail
# shellcheck source=tests/drei_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drei_lib.sh"
setup_ei
GOOD="Mission: $EI_NAME edges=$EI_EDGES"
reset_ei; addline Mission "$GOOD"
run_ei; [ "$RC" = 1 ] || fail "two lines: rc=$RC"; findings_eq '["mission-grammar"]'; has_fail mission-grammar "Mission:"
reset_ei; setline Mission "Mission: drei mission edges=$EI_EDGES"
run_ei; [ "$RC" = 1 ] || fail "spaced name: rc=$RC"; has_fail mission-grammar "'mission'"
reset_ei; setline Mission "$GOOD foo=bar"
run_ei; [ "$RC" = 1 ] || fail "foo=bar: rc=$RC"; findings_eq '["mission-grammar"]'; has_fail mission-grammar "'foo=bar'"
reset_ei; setline Mission "Mission: $EI_NAME"
run_ei; [ "$RC" = 1 ] || fail "no edges=: rc=$RC"; findings_eq '["mission-grammar"]'; has_fail mission-grammar "edges="
# two entries: entry 2 without the line names a (a prds member, eligible)
reset_ei; two_entry
run_ei; [ "$RC" = 1 ] || fail "entry 2 without the line: rc=$RC"; findings_eq '["mission-grammar"]'
has_fail mission-grammar "$EI_TS" "a"
# drop_a: the live header drops PRD-a.md (and the edges naming it)
drop_a() { python3 - "$EF" <<'PY'
import sys, json
p = sys.argv[1]; L = [json.loads(l) for l in open(p).read().splitlines() if l.strip()]
L[0]["prds"] = ["PRD-b.md"]
L = [L[0]] + [e for e in L[1:] if "PRD-a.md" not in (e["producer"], e["consumer"])]
open(p, "w").write("".join(json.dumps(x) + "\n" for x in L))
PY
}
# entry1 <Kind> <full new line>: replace entry 1's (the note's first) <Kind>: line
entry1() { python3 - "$LOG" "$1" "$2" <<'PY'
import sys
p, k, new = sys.argv[1:]
L = open(p).read().split("\n"); L[min(i for i, l in enumerate(L) if l.startswith(k + ":"))] = new
open(p, "w").write("\n".join(L))
PY
}
# the live header drops a and entry 1's State: names only b: entry 1's frozen copy (scope=
# drei-m1, which lists PRD-a.md) is the one continuity leg that keeps a
reset_ei; two_entry; entry1 State "State: b=linted"; drop_a
run_ei; [ "$RC" = 1 ] || fail "live header drops a, entry 1 State: b only: rc=$RC"; findings_eq '["mission-grammar"]'
has_fail mission-grammar "entry $EI_TS carries" "State: names a (a member of that mission)"
# the live header drops a and entry 1 carries no scope= (no frozen copy is read): entry 1's
# State: slugs are the one continuity leg that keeps a
reset_ei; two_entry; entry1 Mission "$GOOD"; drop_a
run_ei; [ "$RC" = 1 ] || fail "live header drops a, entry 1 without scope=: rc=$RC"; findings_eq '["mission-grammar"]'
has_fail mission-grammar "entry $EI_TS carries" "State: names a (a member of that mission)"
# with the line: entry 2 inherits edges= and scope=
reset_ei; two_entry; python3 - "$LOG" <<'PY'
import sys
p = sys.argv[1]; L = open(p).read().split("\n")
i = max(k for k, l in enumerate(L) if l.startswith("State:")); L.insert(i + 1, "Mission: drei-mission"); open(p, "w").write("\n".join(L))
PY
run_ei
printf '%s' "$JS" | python3 -c '
import sys, json
d = json.load(sys.stdin); m = d["mission"]
assert "mission-grammar" not in d["findings"] and "mission-edges-missing" not in d["findings"], d["findings"]
assert m["name"] == "drei-mission" and m["edges_file"] == "notes/missions/drei-mission.edges.jsonl", m
assert m["inherited_from"] == "2026-11-16T10:00:00-08:00", m
assert m["scope"] == ["notes/snapshots/drei-m1/snapshot.sha256"], m
' || fail "inheritance: $JS ($ERR)"
# an explicit edges= naming another path than entry 1's
reset_ei; two_entry; cp "$EF" "$H/notes/missions/other.edges.jsonl"; python3 - "$LOG" <<'PY'
import sys
p = sys.argv[1]; L = open(p).read().split("\n")
i = max(k for k, l in enumerate(L) if l.startswith("State:")); L.insert(i + 1, "Mission: drei-mission edges=notes/missions/other.edges.jsonl"); open(p, "w").write("\n".join(L))
PY
run_ei; printf '%s' "$JS" | jget 'd["findings"]' | grep >/dev/null -F '"mission-grammar"' || fail "other edges=: $ERR"
has_fail mission-grammar "edges=notes/missions/other.edges.jsonl"
pass "mission-grammar x4 on one entry, continuity x3, inheritance, edges= change refused"
