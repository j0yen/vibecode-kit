#!/usr/bin/env bash
# Five-whys page e784471d mechanism 2 (A1723, consumption row E784-M2): an entry dated at or after CONTROL_MUTANTS_SINCE whose Mission:
# line lists scope= manifests is refused while a control output new in the newest listed manifest (or moved since the previous one) has
# no mutant report there at its script's sha256 (control-mutants-missing), or has one whose summary has SURVIVED above 0 or is absent,
# that holds a SURVIVED row or that ends in a refusing certificate (control-mutant-survived). The page's regression in small: an
# r23-shaped control output alone is refused; with a report that kills M5 and M8 it passes. The meta-negative's indented survivors are
# required and pass; a report of other bytes or one not listed counts as none; an unchanged control is no round read; a changed one
# needs its report whether or not a repairs row declares the change.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
cases cm
pass "$CASES_PASSED cases"
