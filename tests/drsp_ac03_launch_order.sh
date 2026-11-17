#!/usr/bin/env bash
# Known-bad on line order against launch order (gate fix G5, G6.5, G6.6), as amended by
# PRD-dream-mission-chain-review.
# KB4 J's row ts earlier than K's. Changed by chain-review R2 ("Among chain reviews matching
#   one index, Review: line order must be non-decreasing in the ts"; K and J match different
#   indexes, so the index order decides) and R5 (J supersedes K): exit 0.
# KB11 a bound review X on an unlisted manifest, launched after J, FIX on a. Changed by R2
#   (chain reviews are those whose scope_id equals a listed mission scope id; X is none, and
#   PR #9 pins no FIX) and R5: exit 0, X is not in chain_reviews.
# KB12-review an unlisted launch row (role review, J's listed scope id) later than J that no
#   Review: line names. Changed by R8 (unlisted_review_sessions) and R6 ("an unlisted later
#   review <session>" holds every prds member when it is the latest-launched review of the
#   last listed manifest): exit 0 with every member held; with a=eligible (KB12-eligible)
#   mission-approval-blocked naming slug a and the session.
# KB12-no-role the same row without role. Changed by R8's filter (role review): no report, no
#   hold, exit 0.
# KB21 a listed review Y (manifest y between k and j) before J in line order, launched after
#   J, FIX on a, no mission= line. Changed by R3 (a chain review's file holds exactly one
#   mission= line): mission-verdict-missing naming y.txt; R5 supersedes K's pin. Also changed by
#   PRD-dream-failure-class-sweep R5 ("before and after are consecutive manifests of the
#   Mission: line's scope= list"; the complement "runs over every consecutive pair"): the copy's
#   amended row k -> j is no longer consecutive (repair-scope-mismatch naming row 1) and a's
#   digest moving between k and y is declared by no row (repair-hash-mismatch naming PRD-a.md).
set -uo pipefail
# shellcheck source=tests/drsp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
if want KB4; then mut KB4; ch KB4 0 ""; not_stale_k KB4; fi
if want KB11; then
  mut KB11; ch KB11 0 ""; not_stale_k KB11
  jq_ KB11 '"'"$S_X"'" not in [x["session"] for x in m["chain_reviews"]]' "X is no chain review"
fi
if want KB12-review; then
  mut KB12-review; ch KB12-review 0 ""; not_stale_k KB12-review
  jq_ KB12-review '[x["session"] for x in m["unlisted_review_sessions"]]==[U] and sorted(dep)==["a","b","c"] and all(("unlisted later review "+U) in v for v in dep.values())' "every member held by U"
  mut KB12-eligible; ch KB12-eligible 1 "mission-approval-blocked" "slug a" "unlisted later review $S_U"
fi
if want KB12-no-role; then
  mut KB12-no-role; ch KB12-no-role 0 ""; not_stale_k KB12-no-role
  jq_ KB12-no-role 'm["unlisted_review_sessions"]==[] and "a" not in dep' "no report, a not held"
fi
if want KB21; then
  mut KB21; ch KB21 1 "mission-verdict-missing repair-hash-mismatch repair-scope-mismatch" "mission-verdict-missing: notes/reviews/y.txt: " \
    "repair-scope-mismatch: row 1: " "repair-hash-mismatch: PRD-a.md: changed but undeclared between notes/snapshots/k/snapshot.sha256 and notes/snapshots/y/snapshot.sha256"
  not_stale_k KB21
fi
pass "KB4 KB11 KB12 KB21"
