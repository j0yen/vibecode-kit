#!/usr/bin/env bash
# AC1 (R1, R2) — the PRD's AC 1 defects (Technical considerations), each a pending entry on a note
# whose last entry is an earlier run's unless the shape is a first run (tests/fixtures/drpe/pfx.py),
# run through `--last --packet-only --pending <file>` governed and with no decisions log: each exits 1
# naming its finding id (or, for a pending-file exit, the line, slug, or file and manifest); a matrix
# rename names the bound manifest m1; a forgotten row is repair-missing governed, and the no-log run
# reports no repair-missing. The finding-row defects (a forgotten row, a short sweep under a live-file
# repairs line, a frozen row edited in place) run governed only: with no decisions log no chain review
# binds, so no finding exists for a row to answer. A pending entry with no Task: line, no Mission:
# line, or a Task: line without Consumer: exits 1 naming the line (R1: "exits 1 naming the line").
set -uo pipefail
# shellcheck source=tests/drpe_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drpe_lib.sh"
setup_pe
X1=2027-03-01T11:00:00-08:00-adversarial.md; X2=2027-03-01T13:00:00-08:00-adversarial.md; X2I=2027-03-01T12:00:00-08:00-adversarial.md
for v in "" "@nolog"; do
  pe "d-same-id$v"; pk; rc1; pfail mission-scope-mismatch "$M2" "notes/snapshots/m2b/m2b.sha256"
  for n in absent empty title; do pe "d-norepairs-$n$v"; pk; rc1; pfail mission-scope-incomplete "manifest $M2:" "lists no $PE_REP"; done
  pe "d-duplicate$v"; pk; rc1; pfail repair-duplicate "finding F1"
  pe "d-changed-absent$v"; pk; rc1; pfail repair-hash-mismatch "PRD-qux.md" "absent from before $M1"
  pe "d-first-missing-prd$v"; pk; rc1; pfail mission-scope-incomplete "manifest $M1:" "lists no PRD-bar.md"
  pe "d-rename-legacy$v"; pk; rc1; pfail mission-scope-incomplete "manifest $M1:" "lists no $X2I" "matrix named by adversarial="
  pe "d-repairs-omitted$v"; pk; rc1; pfail mission-scope-incomplete "manifest $M2:" "lists no $PE_REP"
  pe "d-amended-nosweep$v"; pk; rc1; pfail sweep-missing "amended row"
  pe "d-matrix-grammar$v"; pk; rc1; pfail adversarial-family-missing "$X2" "Falsifier quality"
  pe "d-analysis-malformed$v"; pk; rc1; ppend "Analysis:"
  pe "d-analysis-absent$v"; pk; rc1; ppend "no Analysis: line"
  pe "d-state-absent$v"; pk; rc1; ppend "no State: line"
  pe "d-task-absent$v"; pk; rc1; ppend "line: no Task: line in the pending entry"
  pe "d-mission-absent$v"; pk; rc1; ppend "line: no Mission: line in the pending entry"
  pe "d-task-malformed$v"; pk; rc1; ppend "line: Task: the line lacks"
  pe "d-first-skipped$v"; pk; rc1; pfail adversarial-missing "adversarial=skipped:"
  pe "d-state-short$v"; pk; rc1; ppend "slug bar"
  pe "d-recency-same$v"; pk; rc1; ppend "Analysis:" "$X1" "not later than the previous entry"
  pe "d-recency-new-name$v"; pk; rc1; ppend "Analysis:" "2027-03-01T11:30:00-08:00-adversarial.md" "not later than the previous entry"
  pe "d-header-member$v"; pk; rc1; pfail adversarial-slug-missing "PRD-bar"
  pe "d-header-member-hm$v"; pk; rc1; pfail adversarial-slug-missing "manifest $M1:" "PRD-bar"
  pe "d-live-row-fixed$v"; pk; rc1; ppend "notes/missions/$PE_REP" "$M2"
  pe "d-live-matrix-fixed$v"; pk; rc1; ppend "notes/reviews/$X2" "$M2"
  pe "d-live-edges-fixed$v"; pk; rc1; ppend "notes/missions/$PE_EB" "$M2"
done
# governed only: a finding row's sweep is checked against the finding a bound chain review issued, and
# with no decisions log no chain review binds (chain-review R2), so these rows have no finding to check
pe d-forgot-row; pk; rc1; pfail repair-missing "finding F1"
pe d-live-repairs-line; pk; rc1; pfail sweep-missing "row 1"
pe d-row-edited; pk; rc1; pfail sweep-missing "row 1"
pe d-forgot-row@nolog; pk; no_id repair-missing; printf '%s\n' "$ERR" | grep -q 'repair-missing' && fail "no-log run names repair-missing: $ERR"
pass "AC 1 defects governed and with no log: each exits 1 naming its id, line, slug or file; forgotten row governed only"
