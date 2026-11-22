#!/usr/bin/env bash
# Five-whys page e784471d mechanism 2 (A1723, consumption row E784-M2): an entry dated at or after CONTROL_MUTANTS_SINCE (the latest of
# its header ts, its Route decision= and its bound review launches) whose Mission: line lists scope= manifests is refused while a round
# control output (new in the newest listed manifest, or moved since the manifest the Task's previous entry lists last) has no mutant
# report there at a script's sha256 or names no script (control-mutants-missing), or a report read there fails: no or several summary
# lines, SURVIVED above 0, no mutant or fewer KILLED than run, a SURVIVED row outside the meta-negative, no certificate or one of other
# text (control-mutant-survived). The page's regression in small: an r23-shaped control output alone is refused; with a report that
# kills M5 and M8 it passes. A control output is found by a control script's header or a `controls verdict:` line as well as by its
# name; a round member whose freeze copy is absent or moved is refused when it is a control output by path or by its copy. Review
# lint-e784's counterexamples (F1-F7) each have a case.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
cases cm
pass "$CASES_PASSED cases"
