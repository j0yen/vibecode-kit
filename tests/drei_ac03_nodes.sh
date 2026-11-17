#!/usr/bin/env bash
# AC3 (R3, R4) — an endpoint outside prds (PRD-other.md) or an undeclared external
# (external:nobody) is edge-node-unlisted naming the id and the endpoint; an `external`
# edge whose endpoints are both prds members is edge-grammar naming it; a State slug whose
# PRD is not a prds member is mission-prd-unlisted naming the slug (the Mission parse runs
# after the State parse).
set -uo pipefail
# shellcheck source=tests/drei_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drei_lib.sh"
setup_ei
for v in PRD-other.md external:nobody; do
  reset_ei; edge E1 "e['consumer'] = '$v'"
  run_ei; [ "$RC" = 1 ] || fail "consumer $v: rc=$RC"; findings_eq '["edge-node-unlisted"]'
  has_fail edge-node-unlisted "edge E1" "$v"
done
reset_ei; edge E3 "e['consumer'] = 'PRD-a.md'"
run_ei; [ "$RC" = 1 ] || fail "external between prds: rc=$RC"; findings_eq '["edge-grammar"]'
has_fail edge-grammar "E3" "external"
reset_ei; printf '# PRD c (outside the mission)\n' > "$H/built-prds/PRD-c.md"
setline State "State: a=linted b=linted c=linted"
run_ei; [ "$RC" = 1 ] || fail "State slug c: rc=$RC"; findings_eq '["mission-prd-unlisted"]'
has_fail mission-prd-unlisted "slug c"
pass "edge-node-unlisted x2, external edge-grammar, mission-prd-unlisted"
