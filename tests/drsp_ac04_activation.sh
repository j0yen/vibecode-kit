#!/usr/bin/env bash
# Known-bad on activation and listing (gate fix G1, G2, G3, G6.3), as amended by
# PRD-dream-mission-chain-review.
# Unchanged (base == head byte for byte, exit 1, review-snapshot-stale K/a): KB5 activation
#   off (no Mission: line; Mission: without scope=; two Mission: lines; an empty scope= item:
#   R9, PR #9's pin is unchanged without a scope).
# KB8 K's manifest not in scope=: K's pin is kept (R5: "A review that is not a chain review ...
#   keeps PR #9's pin unchanged"), and, changed by PRD-dream-failure-class-sweep R5 ("before and
#   after are consecutive manifests of the Mission: line's scope= list"), the copy's amended row
#   whose before is k is repair-scope-mismatch naming row 1.
# KB7 J's manifest not in scope=. Changed by R3 (the mission verdict is the last chain review
#   of the LAST listed manifest: K's mission=APPROVE on k) and R5 (mission=APPROVE pins the
#   packet to k: PRD-a.md and the repairs file, which k does not list, are
#   mission-snapshot-stale); K's own pin stays (K is the latest chain review naming a); and,
#   changed by PRD-dream-failure-class-sweep R5 (after "must be a listed manifest later than
#   before"), the copy's amended row whose after is j is repair-scope-mismatch naming row 1.
# KB9 J's row scope_id is K's listed id. Changed by R2 (J's row matches index 0 by scope_id, so
#   J is a chain review of k) and R5 (J supersedes K's pin): review-scope-mismatch alone.
# KB10 one listed item unreadable / malformed. Changed by R1 (every listed manifest must
#   canonicalize: mission-scope-mismatch naming it) and R5: K's pin superseded.
set -uo pipefail
# shellcheck source=tests/drsp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
for c in KB5-no-mission KB5-no-scope KB5-two-mission KB5-empty-item; do
  want "$c" || continue
  # edge-map R1: no edges= (KB5-no-scope), a second Mission: line, an empty scope= item are mission-grammar
  case "$c" in KB5-no-scope|KB5-two-mission|KB5-empty-item) GRAMMAR=1;; *) GRAMMAR=0;; esac
  mut "$c"; kb "$c"
done
GRAMMAR=0
if want KB8; then
  mut KB8; ch KB8 1 "repair-scope-mismatch review-snapshot-stale" \
    "review-snapshot-stale: notes/reviews/k.txt: reviewer-session $S_K: slug a: " "repair-scope-mismatch: row 1: before notes/snapshots/k/snapshot.sha256"
fi
if want KB7; then
  mut KB7; ch KB7 1 "mission-snapshot-stale repair-scope-mismatch review-snapshot-stale" "repair-scope-mismatch: row 1: after notes/snapshots/j/snapshot.sha256" \
    "review-snapshot-stale: notes/reviews/k.txt: reviewer-session $S_K: slug a: " "mission-snapshot-stale: PRD-a.md: " \
    "mission-snapshot-stale: drsp-fixture.repairs.jsonl: "
fi
if want KB9; then mut KB9; ch KB9 1 "review-scope-mismatch" "review-scope-mismatch: notes/reviews/j.txt: "; not_stale_k KB9; fi
if want KB10-unreadable; then
  mut KB10-unreadable; ch KB10-unreadable 1 "mission-scope-mismatch" "manifest notes/snapshots/missing/snapshot.sha256" "unreadable"
  not_stale_k KB10-unreadable
fi
if want KB10-malformed; then
  mut KB10-malformed; ch KB10-malformed 1 "mission-scope-mismatch" "manifest notes/snapshots/bad/snapshot.sha256" "line-rule"
  not_stale_k KB10-malformed
fi
pass "KB5 KB7 KB8 KB9 KB10"
