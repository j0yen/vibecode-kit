#!/usr/bin/env bash
# AC5 (R1, R2) — linted from / (paths resolve against the PRD home, never the cwd): edges=
# naming an absent, empty, unreadable or header-only file, a file whose first line is not a
# header, or (two-entry note) entry 1's frozen edges copy altered or removed is exit 1
# mission-edges-missing naming the path, never exit 0 or a traceback; a non-JSON line, a
# repeated id, a status outside the three, a header mission unlike the line's name, an
# empty outcome, invariants or prds, or single_component beside more than one prds member (R2:
# admitted only with one; review L9) is edge-grammar naming the line and the field.
set -uo pipefail
# shellcheck source=tests/drei_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drei_lib.sh"
not_root
setup_ei
run_root() { JS=$(cd / && "$LINT" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --json 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_tb; }
run_root; [ "$RC" = 0 ] || fail "passing fixture from /: rc=$RC: $ERR"
miss() { # <case> <path substring>
  run_root; [ "$RC" = 1 ] || fail "$1: rc=$RC (never 0): $ERR"
  printf '%s' "$JS" | jget 'd["findings"]' | grep >/dev/null -F '"mission-edges-missing"' || fail "$1: no mission-edges-missing: $ERR"
  has_fail mission-edges-missing "$2"
}
reset_ei; setline Mission "Mission: $EI_NAME edges=notes/missions/none.edges.jsonl"
miss absent notes/missions/none.edges.jsonl
reset_ei; : > "$EF"; miss empty "$EI_EDGES"
reset_ei; chmod 000 "$EF"; miss unreadable "$EI_EDGES"; chmod 644 "$EF"
reset_ei; head -1 "$EF" > "$T/h1"; cp "$T/h1" "$EF"; miss header-only "$EI_EDGES"
reset_ei; python3 - "$EF" <<'PY'
import sys
p = sys.argv[1]; L = open(p).read().split("\n"); L[0], L[1] = L[1], L[0]; open(p, "w").write("\n".join(L))
PY
miss first-line-not-header "$EI_EDGES"
reset_ei; two_entry; printf 'x' >> "$H/notes/snapshots/drei-m1/drei-mission.edges.jsonl"
miss frozen-copy-altered notes/snapshots/drei-m1/drei-mission.edges.jsonl
reset_ei; two_entry; rm "${H:?}/notes/snapshots/drei-m1/drei-mission.edges.jsonl"
miss frozen-copy-removed notes/snapshots/drei-m1/drei-mission.edges.jsonl
# edge-grammar, by line and field
gram() { # <case> <line> <field> [exact]
  run_root; [ "$RC" = 1 ] || fail "$1: rc=$RC"
  if [ "${4:-}" = exact ]; then findings_eq '["edge-grammar"]'; fi
  has_fail edge-grammar "line $2" "field $3"
}
reset_ei; python3 - "$EF" <<'PY'
import sys
p = sys.argv[1]; L = open(p).read().split("\n"); L.insert(2, "this line is not JSON"); open(p, "w").write("\n".join(L))
PY
gram non-json 3 "(not a JSON object)" exact
reset_ei; edge E2 "e['id'] = 'E1'"; gram repeated-id 3 id exact
reset_ei; edge E2 "e['status'] = 'maybe'"; gram bad-status 3 status exact
reset_ei; header "h['mission'] = 'another-mission'"; gram header-mission 1 mission exact
reset_ei; header "h['outcome'] = ''"; gram empty-outcome 1 outcome exact
reset_ei; header "h['invariants'] = []"; gram empty-invariants 1 invariants exact
reset_ei; header "h['prds'] = []"; gram empty-prds 1 prds
reset_ei; header "h['single_component'] = 'one component, two prds'"; gram single-component-two-prds 1 single_component exact
has_fail edge-grammar "beside 2 prds members"
pass "mission-edges-missing x7 from /, edge-grammar x8"
