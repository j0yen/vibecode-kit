#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the drrp_* tests (PRD-dream-repairs-file-in-packet). Reuses the drfc,
# drmr and drrec helpers (use, run_fc, mansign, redit, repin, findings_eq, has_fail, ...).
# RP_SENTENCE is R1's sentence; RP_CLAUSES are its clauses in order, so a check can name the
# clause a paragraph lacks. rp_para <SKILL.md> <heading> prints the paragraph that starts with
# the bold heading, up to the next blank line, joined to one line with whitespace normalized.
# shellcheck source=tests/drfc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drfc_lib.sh"
# shellcheck disable=SC2016  # literal backticks of the skill text
RP_SENTENCE='Once any repairs row exists, the repairs file is a packet member: list its basename in every `scope=` manifest later than the earliest `before` any row names, including that row'"'"'s own `after`, so write the row (it names `after` by path) before freezing `after`.'
# shellcheck disable=SC2016
RP_CLAUSES=('Once any repairs row exists, the repairs file is a packet member:'
            'list its basename in every `scope=` manifest'
            'later than the earliest `before` any row names'
            'including that row'"'"'s own `after`'
            'so write the row (it names `after` by path) before freezing `after`.')
RP_H1='**Whole-chain review'
RP_H2='**After the first systemic finding or material repair:**'
rp_para() { awk -v h="$2" 'index($0,h)==1{f=1} f&&/^[[:space:]]*$/{exit} f' "$1" | tr '\n' ' ' | sed 's/[[:space:]]\{1,\}/ /g; s/ $//'; }
# rp_missing <joined paragraph>: the clauses of R1's sentence the paragraph lacks ('; '-joined),
# empty when the whole sentence is present
rp_missing() { local p=$1 c out=""
  case "$p" in *"$RP_SENTENCE"*) return 0;; esac
  for c in "${RP_CLAUSES[@]}"; do case "$p" in *"$c"*) ;; *) out="${out:+$out; }'$c'";; esac; done
  [ -n "$out" ] || out="'the clauses in R1's order'"
  printf '%s' "$out"
}
