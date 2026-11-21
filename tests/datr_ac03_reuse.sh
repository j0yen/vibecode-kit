#!/usr/bin/env bash
# AC3 (R3) — reuses whose digest and manifest verify (a home input, an absolute input outside the home,
# with and without the entry's seed file), whose page or a cited input (home or absolute) changed a byte,
# whose manifest omits a page-cited path or the seed, is absent, empty or outside the home, a reuse with
# no sha256=/inputs=, and a page bound to no wwhtbt launch row, each linted from a working directory
# that is neither the home nor the manifest's: only the verified ones pass (reuse.verified true);
# the rest give analysis-reuse-stale, analysis-reuse-incomplete, analysis-grammar or
# analysis-provenance-missing, each naming its cause.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
cases ac03
pass "$CASES_PASSED cases"
