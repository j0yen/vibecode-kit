#!/usr/bin/env bash
# Five-whys page e784471d mechanism 3 (lint part; A1723, consumption row E784-M3): the R4 floor reads each State: slug's consecutive
# FIX or REJECT verdicts since its last APPROVE across notes/reviews/, not only those of sessions launched after the Task's previous
# entry, among the sessions launched by the entry's own time. The page's fixture, in small: an entry whose previous entry came after
# four FIX reviews of its slug, `Failure: none`, gives failure-class-mismatch; the line at the floor passes; an APPROVE ends the streak;
# one FIX sets no floor; a REJECT sets failed-acceptance; a session with a FIX beside an APPROVE counts as a FIX; an APPROVE or a FIX
# launched after the entry neither lowers nor raises it; another slug's streak sets nothing. Review lint-e784 F7: a session with no
# launch time adds its FIX and never resets with an APPROVE; one launched at the entry's own time counts; the higher floor stands.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
cases fs
pass "$CASES_PASSED cases"
