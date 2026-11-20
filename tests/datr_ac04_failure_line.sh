#!/usr/bin/env bash
# AC4 (R4) — covered entries with each Failure: class, `none`, an unknown class, a class without a ref,
# a ref outside the routing policy's evidence.ref_pattern and a placeholder ref, no Failure: line, and
# none/other/failed-acceptance beside a REJECT or a second FIX in verdict files under notes/reviews/
# bound by review launch rows, named on Review: or omitted (a result.json capture in a subdirectory
# included); a first FIX and an unbound author file set no floor: valid lines pass, bad ones give
# failure-grammar, the absent line line-missing and a class below the floor failure-class-mismatch.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
cases ac04
pass "$CASES_PASSED cases"
