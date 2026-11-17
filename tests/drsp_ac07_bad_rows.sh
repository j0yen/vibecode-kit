#!/usr/bin/env bash
# Known-bad on unparseable or non-string row fields (gate fix G4 never raises, G6.5, G6.6), as
# amended by PRD-dream-mission-chain-review. No traceback in any case (pair checks every
# stderr); R5 supersedes K's pin in each (J is the latest chain review naming a).
# KB15-j-ts-absent / -j-ts-bad / -k-ts-bad: the review's launch ts is absent or unparseable.
#   Changed by R3's sidecar binding: SIDECAR_BINDING_SINCE "excuses only the absence of the
#   line" for "a chain review whose launch row ts is earlier than it"; an absent or
#   unparseable ts is not earlier (an ambiguity resolved fail-closed), so the capture with no
#   findings= line is mission-finding-incomplete naming the file and the result path.
# KB15-other-ts-absent / -numeric: another session's review launch row on J's listed scope id,
#   no Review: line, ts absent or numeric. Changed by R8 (unlisted_review_sessions) and R6
#   (the latest-launched review of the last manifest holds every member; a row whose ts cannot
#   be ordered is taken as the latest, fail-closed): exit 0, every member held.
# KB15-j-scope-numeric: J's row scope is a number: review-scope-mismatch (unchanged id); J
#   still binds by its scope_id (R2), so K's pin is superseded.
set -uo pipefail
# shellcheck source=tests/drsp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
for c in KB15-j-ts-absent:j KB15-j-ts-bad:j KB15-k-ts-bad:k; do
  n=${c%%:*}; f=${c##*:}
  want "$n" || continue
  mut "$n"; ch "$n" 1 "mission-finding-incomplete" "mission-finding-incomplete: notes/reviews/$f.txt: result notes/reviews/$f.json: no findings= line"
  not_stale_k "$n"
done
for c in KB15-other-ts-absent KB15-other-ts-numeric; do
  want "$c" || continue
  mut "$c"; ch "$c" 0 ""; not_stale_k "$c"
  jq_ "$c" 'sorted(dep)==["a","b","c"] and all(("unlisted later review "+U) in v for v in dep.values())' "every member held by U"
done
if want KB15-j-scope-numeric; then
  mut KB15-j-scope-numeric; ch KB15-j-scope-numeric 1 "review-scope-mismatch" "the row's scope is absent or not a path"
  not_stale_k KB15-j-scope-numeric
fi
pass "KB15"
