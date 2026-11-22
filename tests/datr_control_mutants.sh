#!/usr/bin/env bash
# Five-whys page e784471d mechanism 2 (A1723, consumption row E784-M2): an entry dated at or after CONTROL_MUTANTS_SINCE (the latest of
# its header ts, its Route decision= and its bound review launches) whose Mission: line lists scope= manifests is refused while a round
# control output (new in the newest listed manifest, or moved since the manifest the base entry lists last: the Task's last earlier entry
# dated before CONTROL_MUTANTS_SINCE, so a refused or never-read round stays owed at the next entry) has no mutant
# report there at a script's sha256 or names no script (control-mutants-missing), or a report read there fails: no or several summary
# lines, SURVIVED above 0, no mutant or fewer KILLED than run, a SURVIVED row outside the meta-negative, no certificate or one of other
# text (control-mutant-survived). The page's regression in small: an r23-shaped control output alone is refused; with a report that
# kills M5 and M8 it passes. A control output is found by a control script's header or a `controls verdict:` line (or `<word> verdict:
# discriminates` / `DOES NOT DISCRIMINATE`, the r10f1 readback fixture's) as well as by its name; a round member that is not a script nor a
# PRD file whose freeze copy is absent or moved is refused whatever its name. Review lint-e784's counterexamples (F1-F7) and review
# lint-e784b's (N1-N3) each have a case.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
cases cm
pass "$CASES_PASSED cases"
