#!/usr/bin/env bash
# PRD-dream-finding-consumption AC 4 (R7 scoped hold, R6 placement, R1's record line) — PRDs X (first) and Y (Depends-on X), both eligible on a run
# note dated on the cutover; Hermes' case-11 command (`dream-run-note-lint.sh <home>/notes/dream-log.md --last --json`) holds exactly the slugs R7
# names: an unconsumed row naming X holds X, here or in an earlier entry of the Task, until a later record binds that page and finding as consumed (a
# pending row does not); another Task's rows hold nothing; a pending row with ask and successor holds no slug unless it names X; a row naming neither
# holds every slug; an overdue pending row gives consumption-pending-overdue; a covered entry's WWHTBT skip and an unbound falsifier hold the first
# PRD (X) until a later entry runs or reuses WWHTBT; a trigger-class 5whys skip holds every slug until a later entry binds a 5whysandrhyme page; a
# falsifier on AC 3 or on Y gives falsifier-not-first; a covered entry after an open earlier record needs its Consumption: line, an uncovered one not.
# Each case states its exact exit, finding-id set and `consumption.held` slugs (tests/fixtures/dfcn/dfcnlog.py).
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; repo="$(dirname "$here")"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
out="$(python3 -I "$here/fixtures/dfcn/dfcnlog.py" --run ac04- "$repo/skills/dream/scripts/dream-run-note-lint.sh" "$T" 2>&1)"; rc=$?
[ "$rc" = 0 ] || { echo "FAIL $(basename "$0"): $(printf '%s\n' "$out" | grep -v '^PASS' | head -20)"; exit 1; }
echo "PASS $(basename "$0"): $(printf '%s\n' "$out" | grep -c '^PASS') cases (the case-11 command, --last --json)"
