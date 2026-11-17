#!/usr/bin/env bash
# AC6 (R6) — in the FIX fixture (finding F1 on a, consumers [external:x], edge E1 a -> b in
# the frozen edges copy) a or b eligible is mission-approval-blocked naming the slug, the
# finding and, for b, the edge; c eligible exits 0 with provenance.mission self and
# dependent_slugs [a, b]; in the per-PRD-FIX variant (a FIX under mission=APPROVE), or with
# a's line in no verdict file, eligible a is blocked naming "per-PRD verdict FIX" or "no
# per-PRD verdict"; c passes and the dependents are [a, b] (no blanket hold).
set -uo pipefail
# shellcheck source=tests/drmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmr_lib.sh"
setup_mr
FIXST="a=linted a=reviewed:FIX b=linted b=reviewed:APPROVE c=linted c=reviewed:APPROVE"
deps() { jtrue '[x["slug"] for x in d["mission"]["dependent_slugs"]] == ["a", "b"]' "dependent_slugs [a, b]"; }
use fix; state "$FIXST a=eligible"; run_mr; findings_eq '["mission-approval-blocked"]'; has_fail mission-approval-blocked "slug a" "F1"
use fix; state "$FIXST b=eligible"; run_mr; findings_eq '["mission-approval-blocked"]'; has_fail mission-approval-blocked "slug b" "F1" "E1"
use fix; state "$FIXST c=eligible"; run_mr
[ "$RC" = 0 ] || fail "FIX, c eligible: rc=$RC $ERR"; findings_eq '[]'; jtrue 'd["provenance"]["mission"] == "self"'; deps
use perprd-fix; state "$FIXST a=eligible"; run_mr; has_fail mission-approval-blocked "slug a" "per-PRD verdict FIX"
use perprd-fix; state "$FIXST c=eligible"; run_mr; [ "$RC" = 0 ] || fail "per-PRD FIX, c eligible: rc=$RC $ERR"; deps
use base
vedit "$MR_CHAIN/verdict.txt" "L[:] = [l for l in L if not l.startswith('a APPROVE')]"
capture "$MR_CHAIN/result.json" "L[:] = [l for l in L if not l.startswith('a APPROVE')]"
state "a=linted a=eligible b=linted b=reviewed:APPROVE c=linted c=reviewed:APPROVE c=eligible"; run_mr
findings_eq '["mission-approval-blocked"]'; has_fail mission-approval-blocked "slug a" "no per-PRD verdict"
if printf '%s\n' "$ERR" | grep -q 'slug c'; then fail "c blocked: $ERR"; fi
pass "finding + one-hop held; c free; per-PRD FIX and no per-PRD verdict held"
