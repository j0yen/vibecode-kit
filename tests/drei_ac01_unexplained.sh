#!/usr/bin/env bash
# AC1 (PRD-dream-mission-edge-map R3) — a known edge with any of its eight fields emptied,
# or its producer or consumer UNKNOWN (R3: UNKNOWN as an endpoint of a known or external edge;
# the consumer case is review L8), is edge-unexplained naming the edge id and that field (exact
# findings, exit 1); the same field refilled with a prds member lints clean and
# mission.edges.known counts the edge. Known-bad controls: a lint that checks only some
# fields, or accepts UNKNOWN on a known edge, passes one of these mutations.
set -uo pipefail
# shellcheck source=tests/drei_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drei_lib.sh"
setup_ei
run_ei; [ "$RC" = 0 ] || fail "passing fixture rc=$RC: $ERR"; findings_eq '[]'
n=0
for f in producer consumer command trigger authority effect_id recovery_owner postcondition; do
  reset_ei; edge E1 "e['$f'] = ''"
  run_ei; [ "$RC" = 1 ] || fail "E1.$f emptied: rc=$RC"; findings_eq '["edge-unexplained"]'
  has_fail edge-unexplained "edge E1: $f"
  n=$((n+1))
done
reset_ei; edge E3 "e['authority'] = ''"
run_ei; [ "$RC" = 1 ] || fail "E3.authority emptied (external): rc=$RC"; findings_eq '["edge-unexplained"]'
has_fail edge-unexplained "edge E3: authority"
reset_ei; edge E1 "e['producer'] = 'UNKNOWN'"
run_ei; [ "$RC" = 1 ] || fail "E1 producer UNKNOWN: rc=$RC"; findings_eq '["edge-unexplained"]'
has_fail edge-unexplained "edge E1: producer" "UNKNOWN"
reset_ei; edge E1 "e['consumer'] = 'UNKNOWN'"
run_ei; [ "$RC" = 1 ] || fail "E1 consumer UNKNOWN: rc=$RC"; findings_eq '["edge-unexplained"]'
has_fail edge-unexplained "edge E1: consumer" "UNKNOWN"
# refilled with a prds member: clean, counted as known
reset_ei; edge E1 "e['producer'] = 'PRD-b.md'"
run_ei; [ "$RC" = 0 ] || fail "E1 producer refilled: rc=$RC: $ERR"; findings_eq '[]'
[ "$(printf '%s' "$JS" | jget 'd["mission"]["edges"]')" = '{"total": 4, "known": 2, "external": 1, "unknown": 1}' ] \
  || fail "edges counts after refill: $(printf '%s' "$JS" | jget 'd["mission"]')"
pass "$n fields + external field + UNKNOWN producer and consumer refused; refill counted"
