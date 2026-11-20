#!/usr/bin/env bash
# PRD-dream-finding-consumption AC 3 (R3 residual, R4, R8), in both modes: a residual accepted by an independent review session of the Task passes;
# one accepted by the author lineage, by a role-less session, by a review of another Task, or with no `accepts <id>` line gives
# consumption-residual-unaccepted and leaves its finding unconsumed; receipt-only rows (a session, a run id, a report) give consumption-receipt-only;
# check mode without --reviews or --prd-home gives consumption-context-missing. Check mode: tests/fixtures/dfcn/dfcnfx.py's ac03- cases. Authoring
# mode: tests/fixtures/dfcn/dfcnlog.py's ac03a- cases, the same rows in the record a run note's Consumption: line names (R1), linted by
# `--last --json` with the home's notes/reviews and the run's decisions log as the context.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; repo="$(dirname "$here")"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/check" "$T/authoring"
out="$(python3 -I "$here/fixtures/dfcn/dfcnfx.py" --run ac03- "$repo/skills/dream/scripts/dream-run-note-lint.sh" "$T/check" 2>&1)"; rc=$?
[ "$rc" = 0 ] || { echo "FAIL $(basename "$0") (check mode): $(printf '%s\n' "$out" | grep -v '^PASS' | head -20)"; exit 1; }
out2="$(python3 -I "$here/fixtures/dfcn/dfcnlog.py" --run ac03a- "$repo/skills/dream/scripts/dream-run-note-lint.sh" "$T/authoring" 2>&1)"; rc=$?
[ "$rc" = 0 ] || { echo "FAIL $(basename "$0") (authoring mode): $(printf '%s\n' "$out2" | grep -v '^PASS' | head -20)"; exit 1; }
echo "PASS $(basename "$0"): $(printf '%s\n' "$out" | grep -c '^PASS') cases (check mode), $(printf '%s\n' "$out2" | grep -c '^PASS') cases (authoring mode)"
