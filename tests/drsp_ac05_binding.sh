#!/usr/bin/env bash
# Known-bad on review binding (gate fix Terms "bound review", G5, G6.3, G6.7), as amended by
# PRD-dream-mission-chain-review.
# Unchanged (base == head byte for byte, exit 1, review-snapshot-stale K/a): KB6 J's row role
#   author / role absent (R2: J is no chain review, K stays the latest naming a); KB16 J's
#   Review: line names the Route session / none (review-self; R2 "The existing review-self
#   refusals apply unchanged").
# KB17 K and J one session on two Review: lines. Changed by R5 (the j.txt line, bound to K's
#   row on manifest k, is the latest chain review naming a: its APPROVE is the one pinned, and
#   is stale) and R3 (its mission= line names J, not the line's session K).
# KB18 J's verdict file missing. Changed by R3 (zero mission= lines in J's file:
#   mission-verdict-missing) beside review-file-missing; K's pin stays (J names nothing).
# KB20 an author launch row carries J's session before J's review row. Changed by R5: the
#   binding (m4[-1]) selects J's later review row, J supersedes K: exit 0.
set -uo pipefail
# shellcheck source=tests/drsp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
if want KB6-author; then mut KB6-author; kb KB6-author review-provenance-missing; fi
if want KB6-absent; then mut KB6-absent; kb KB6-absent; fi
if want KB16-route; then mut KB16-route; kb KB16-route review-self; fi
if want KB16-none; then mut KB16-none; kb KB16-none review-self; fi
if want KB17; then
  mut KB17; ch KB17 1 "mission-verdict-missing review-result-mismatch review-snapshot-stale" \
    "review-snapshot-stale: notes/reviews/j.txt: reviewer-session $S_K: slug a: " "mission-verdict-missing: notes/reviews/j.txt: "
fi
if want KB18; then
  mut KB18; ch KB18 1 "mission-verdict-missing review-file-missing review-snapshot-stale" \
    "review-snapshot-stale: notes/reviews/k.txt: reviewer-session $S_K: slug a: " "mission-verdict-missing: notes/reviews/j.txt: "
fi
if want KB20; then mut KB20; ch KB20 0 ""; not_stale_k KB20; fi
pass "KB6 KB16 KB17 KB18 KB20"
