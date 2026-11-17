#!/usr/bin/env bash
# Known-bad KB1-KB3 (gate fix G5, G6.4, G6.8), as amended by PRD-dream-mission-chain-review.
# KB1 J's last verdict for a is FIX. Changed by chain-review R5 ("an earlier chain review's
#   APPROVE on the same slug is superseded by that later verdict and is not pinned") and R6
#   (a slug whose per-PRD verdict in the latest chain review naming it is FIX is dependent):
#   exit 0, K's APPROVE superseded by J, a held "per-PRD verdict FIX"; with a=eligible
#   (KB1-eligible) mission-approval-blocked naming slug a and the reason.
# KB2 a's bytes change again after J's freeze. Changed by R5: K's pin is superseded (J is the
#   latest chain review naming a), J's own pin stays (review-snapshot-stale J/a), and J's
#   mission=APPROVE pins the packet (mission-snapshot-stale PRD-a.md).
# KB3 J's file names b and c only: unchanged (K is the latest chain review naming a, R5 keeps
#   PR #9's pin there): base == head byte for byte, exit 1, review-snapshot-stale K/a.
set -uo pipefail
# shellcheck source=tests/drsp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
if want KB1; then
  mut KB1; ch KB1 0 ""; not_stale_k KB1; jq_ KB1 'dep.get("a")=="per-PRD verdict FIX"' "a held per-PRD verdict FIX"
  mut KB1-eligible; ch KB1-eligible 1 "mission-approval-blocked" "slug a" "per-PRD verdict FIX"; not_stale_k KB1-eligible
fi
if want KB2; then
  mut KB2; ch KB2 1 "mission-snapshot-stale review-snapshot-stale" \
    "review-snapshot-stale: notes/reviews/j.txt: reviewer-session $S_J: slug a: " "mission-snapshot-stale: PRD-a.md: "
  not_stale_k KB2
fi
if want KB3; then mut KB3; kb KB3; fi
pass "KB1 KB2 KB3"
