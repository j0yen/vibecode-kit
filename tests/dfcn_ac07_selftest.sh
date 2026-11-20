#!/usr/bin/env bash
# PRD-dream-finding-consumption AC 7 — the lint's --selftest holds every Cited-tree (43d5b39) PASS line verbatim, has no FAIL, and adds one
# dfcn-<case> line per R1-R8 refusal, each `PASS refuse:<id>:dfcn-<case>` (the selftest's refuse() and check_mode() require the exact finding-id set):
# consumption-missing (R1); consumption-grammar (R2); consumption-binding-invalid, consumption-binding-not-discriminating, consumption-repair-unbound,
# consumption-repair-unproven, consumption-residual-unaccepted (a residual whose accepted_by has no review launch row), consumption-pending-overdue and
# canonical-unavailable as an authoring-mode refusal (R3); consumption-receipt-only (R4); consumption-finding-unbound, consumption-page-stale and
# consumption-page-unparsed (R5); falsifier-not-first (R6); consumption-blocked (R7); and in check mode (R8) consumption-context-missing,
# consumption-repair-open, consumption-finding-unbound for a --page the record does not bind, and exit 2 without wm-asks; plus passing dfcn fixtures
# in both modes.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"           # LINT, base_lint (the Cited tree 43d5b39, read by git at run time), fail, pass
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; mkdir -p "$T/fakehome"; export HOME="$T/fakehome"; unset SKILL_ROUTING_DECISIONS
base_lint "$T/base.sh"
bash "$T/base.sh" --selftest > "$T/base.out" 2>&1 || fail "43d5b39 selftest exit $?"
bash "$LINT" --selftest > "$T/head.out" 2>&1 || fail "selftest exit $?: $(grep -v '^PASS' "$T/head.out" | head -5)"
grep -qE '^(FAIL|ERROR)' "$T/head.out" && fail "selftest FAIL lines: $(grep -E '^(FAIL|ERROR)' "$T/head.out" | head -3)"
nb=0
while IFS= read -r l; do grep -qxF -- "$l" "$T/head.out" || fail "43d5b39 PASS line missing: $l"; nb=$((nb+1)); done < <(grep '^PASS ' "$T/base.out")
for id in consumption-missing consumption-grammar consumption-binding-invalid consumption-binding-not-discriminating consumption-repair-unbound \
          consumption-repair-unproven consumption-pending-overdue canonical-unavailable consumption-receipt-only consumption-finding-unbound \
          consumption-page-stale consumption-page-unparsed falsifier-not-first consumption-blocked; do
  grep -qE "^PASS refuse:$id:dfcn-" "$T/head.out" || fail "no authoring-mode dfcn refusal line for $id"
done
grep -qxF 'PASS refuse:consumption-residual-unaccepted:dfcn-residual-without-a-review-launch-row' "$T/head.out" \
  || fail "no dfcn line for a residual whose accepted_by has no review launch row"
for l in 'PASS refuse:consumption-context-missing:dfcn-check-context-missing' 'PASS refuse:consumption-repair-open:dfcn-check-repair-open' \
         'PASS refuse:consumption-finding-unbound:dfcn-check-page-the-record-does-not-bind' \
         'PASS refuse:canonical-unavailable:dfcn-check-canonical-unavailable-exits-2'; do
  grep -qxF -- "$l" "$T/head.out" || fail "no check-mode line: $l"
done
grep -qxF 'PASS pass:dfcn-consumed' "$T/head.out" || fail "no passing authoring-mode dfcn fixture"
grep -qxF 'PASS pass:dfcn-check-consumed' "$T/head.out" || fail "no passing check-mode dfcn fixture"
pass "$nb 43d5b39 PASS lines kept; $(grep -c '^PASS .*dfcn-' "$T/head.out") dfcn lines"
