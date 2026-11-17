#!/usr/bin/env bash
# AC2 (R3, R5) — the fixture's unknown edge E4 without an owner (deleted, emptied) is
# edge-unknown-unowned naming E4; with its owner the note lints clean, mission.unknown_edges
# lists exactly E4, mission.edges.unknown is 1 and provenance.mission is self (an author
# label never raises it: a header key "reviewed": true changes nothing).
set -uo pipefail
# shellcheck source=tests/drei_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drei_lib.sh"
setup_ei
for m in "del e['owner']" "e['owner'] = ''" "e['owner'] = '   '"; do
  reset_ei; edge E4 "$m"
  run_ei; [ "$RC" = 1 ] || fail "E4 [$m]: rc=$RC"; findings_eq '["edge-unknown-unowned"]'
  has_fail edge-unknown-unowned "edge E4"
done
reset_ei; run_ei; [ "$RC" = 0 ] || fail "owned: rc=$RC: $ERR"; findings_eq '[]'
printf '%s' "$JS" | python3 -c '
import sys, json
d = json.load(sys.stdin); m = d["mission"]
assert m["unknown_edges"] == ["E4"], m
assert m["edges"] == {"total": 4, "known": 2, "external": 1, "unknown": 1}, m["edges"]
assert m["name"] == "drei-mission" and m["edges_file"] == "notes/missions/drei-mission.edges.jsonl", m
assert m["prds"] == 2 and m["inherited_from"] is None and m["scope"] == [] and m["single_component"] is None, m
assert d["provenance"]["mission"] == "self", d["provenance"]
' || fail "owned JSON: $JS"
reset_ei; header "h['reviewed'] = True"
run_ei; [ "$RC" = 0 ] && [ "$(printf '%s' "$JS" | jget 'd["provenance"]["mission"]')" = '"self"' ] || fail "author label: rc=$RC $JS"
pass "unowned refused x3; owned: unknown_edges [E4], provenance.mission self"
