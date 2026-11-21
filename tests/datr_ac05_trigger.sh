#!/usr/bin/env bash
# AC5 (R5) — for each trigger class (recurring-failure, failed-acceptance, consequential-obstacle): a
# bound page, an inline value, denied-row skips (corroborated outage, outage followed by a
# 5whysandrhyme launch, fixable request, live worker), a cross-task reuse with and without its page:
# ref, and a page bound to another task's row; and transient with inline, `skipped: transient` and a
# page: only the bound page, the corroborated skip, the cited reuse and transient's two values pass;
# the rest give analysis-trigger-unmet (beside today's analysis-page-unbound for the unbound page).
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
cases ac05
pass "$CASES_PASSED cases"
