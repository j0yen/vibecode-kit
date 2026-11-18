#!/usr/bin/env bash
# AC3 (R2, R3, R5) — a bound m2 (a Review: line and launch row, a launch row alone, edited after its
# launch, deleted after its launch) carried in withdrawn=: `--packet-only --pending` and the full lint
# on the note with the pending entry appended each exit 1 with mission-withdrawn-bound naming m2 and the
# reviewer session, m2's own finding (it omits the repairs file) still reported, m2 absent from
# mission.withdrawn; a second occurrence of the withdrawn path in scope= and a withdrawn= that drops an
# inherited path (E1 withdrew m0) are mission-scope-mismatch naming the path, exit 1.
set -uo pipefail
# shellcheck source=tests/drpe_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drpe_lib.sh"
setup_pe
R2=cccccccc-0000-4000-8000-000000000004
for h in review launch edited deleted; do
  pe "bound-$h"; pk; rc1; pfail mission-withdrawn-bound "$M2" "$R2"
  case "$h" in
    deleted) line "" "mission-scope-mismatch" "$M2" ;;
    *) line "" "mission-scope-incomplete" "manifest $M2:" "lists no $PE_REP" ;;
  esac
  jtrue 'not (d.get("mission") or {}).get("withdrawn")' "bound-$h: mission.withdrawn empty"
  pe "bound-$h"; full; rc1; has_fail mission-withdrawn-bound "$M2" "$R2"
  jtrue 'not (d.get("mission") or {}).get("withdrawn")' "bound-$h full: mission.withdrawn empty"
done
pe bound-twice; pk; rc1; pfail mission-scope-mismatch "$M2" "second occurrence"
pe bound-twice; full; rc1; has_fail mission-scope-mismatch "$M2" "second occurrence"
pe bound-dropped; pk; rc1; pfail mission-scope-mismatch "notes/snapshots/m0/m0.sha256" "inherited"
pe bound-dropped; full; rc1; has_fail mission-scope-mismatch "notes/snapshots/m0/m0.sha256" "inherited"
pass "bound (review, launch, edited, deleted) refused naming session, still reporting its finding; second occurrence and dropped inherited path refused"
