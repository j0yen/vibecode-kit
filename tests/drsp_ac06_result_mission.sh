#!/usr/bin/env bash
# Known-bad on the result and mission binding (gate fix G6.9, G6.10), as amended by
# PRD-dream-mission-chain-review; each is still refused, now for the chain-review reason, and
# R5 supersedes K's pin in each (J is the latest chain review naming a).
# KB13 J's Review: line has no result=. Changed by R3 ("one without it is
#   mission-verdict-missing naming the file and 'no result= capture'").
# KB14 J's result.json gives FIX for a while its file gives APPROVE: review-result-mismatch
#   (unchanged id), K's pin superseded by R5.
# KB19 J's file mission=FIX J / no mission= line / J's result mission=FIX J under the file's
#   APPROVE. Changed by R3 (zero lines, or a capture line differing from the file's, is
#   mission-verdict-missing naming the file and the result path); the file's mission=FIX also
#   needs its sidecar (R4: mission-finding-incomplete).
set -uo pipefail
# shellcheck source=tests/drsp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
if want KB13; then mut KB13; ch KB13 1 "mission-verdict-missing" "notes/reviews/j.txt" "no result= capture"; not_stale_k KB13; fi
if want KB14; then mut KB14; ch KB14 1 "review-result-mismatch" "review-result-mismatch: notes/reviews/j.txt: "; not_stale_k KB14; fi
if want KB19-file-fix; then
  mut KB19-file-fix; ch KB19-file-fix 1 "mission-finding-incomplete mission-verdict-missing" \
    "mission-verdict-missing: notes/reviews/j.txt: result notes/reviews/j.json" "mission-finding-incomplete: notes/reviews/j.txt.findings.jsonl"
  not_stale_k KB19-file-fix
fi
if want KB19-file-none; then mut KB19-file-none; ch KB19-file-none 1 "mission-verdict-missing" "mission-verdict-missing: notes/reviews/j.txt: 0 mission= line"; not_stale_k KB19-file-none; fi
if want KB19-result-fix; then
  mut KB19-result-fix; ch KB19-result-fix 1 "mission-verdict-missing" "mission-verdict-missing: notes/reviews/j.txt: result notes/reviews/j.json"
  not_stale_k KB19-result-fix
fi
pass "KB13 KB14 KB19"
