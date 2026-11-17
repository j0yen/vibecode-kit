#!/usr/bin/env bash
# AC6 (R6) — SKILL.md Phase 2 (mission trace paragraph) names the optional header `matrix`;
# Phase 3 states the per-manifest rule (the header's `matrix` names the matrix current at each
# freeze, a repair round writes a new matrix and updates `matrix` before freezing), the last-matrix
# rule (adversarial= names the last), the legacy rule (a manifest whose header has no `matrix` keeps
# the matrix of the entry that first listed it; a continued legacy mission writes the new run's
# matrix, later than the previous entry) and the edges basename in the repair row's `changed`;
# history.md has one entry naming PRD dream-matrix-per-manifest; a note that follows the text lints
# clean (run3 with header matrices, and a legacy-headed mission continued in a later run entry), one
# that renames the matrix in one run entry with no header `matrix` gets mission-scope-incomplete
# naming adversarial= as the rule; tests/dream_analysis_skills_ref.sh exits 0.
set -uo pipefail
# shellcheck source=tests/drmx_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmx_lib.sh"
f="$REPO/skills/dream/SKILL.md"
section() { awk -v h="$1" '/^```/{fence=!fence} !fence&&/^## /{f=(index($0,h)==1);next} f' "$f"; }
para() { printf '%s\n' "$1" | awk -v h="$2" 'index($0,h)==1{f=1} f&&/^[[:space:]]*$/{exit} f' | tr '\n' ' ' | sed 's/[[:space:]]\{1,\}/ /g'; }
p2=$(para "$(section '## Phase 2 — Vision')" '**Mission trace and edge map')
[ -n "$p2" ] || fail "Phase 2 has no mission trace paragraph"
# shellcheck disable=SC2016  # literal backticks of the skill text
for s in 'optional `matrix`' 'the basename of the adversarial matrix current at that freeze'; do
  case "$p2" in *"$s"*) ;; *) fail "Phase 2 mission trace paragraph lacks '$s'";; esac
done
adv=$(para "$(section '## Phase 3 — Draft')" '**Adversarial pass')
# shellcheck disable=SC2016
for s in 'One file per review round' 'names the matrix current at each freeze' 'writes a new matrix and updates `matrix` before freezing' \
  'the note'"'"'s `adversarial=` names the last' 'keeps the matrix of the entry that first listed it' 'later than the previous entry' \
  'lists the edges basename' 'repair-hash-mismatch'; do
  case "$adv" in *"$s"*) ;; *) fail "Phase 3 Adversarial pass paragraph lacks '$s'";; esac
done
e=$(awk '/^- \*\*/{n++} n{print n "\t" $0}' "$REPO/skills/dream/history.md" | awk -F'\t' '{a[$1]=a[$1] " " $2} END{for(k in a) print a[k]}' | grep -F 'dream-matrix-per-manifest')
[ "$(printf '%s\n' "$e" | grep -c .)" = 1 ] || fail "history.md: want one entry naming dream-matrix-per-manifest, got: $e"
setup_mx
for c in run3 legacy-pair; do mx "$c"; run_mr; clean; done
mx rename-no-header; run_mr
has_fail mission-scope-incomplete "manifest notes/snapshots/m1/m1.sha256:" "lists no $(mxb 10)" "matrix named by adversarial= (the header names none)"
out=$(bash "$REPO/tests/dream_analysis_skills_ref.sh" 2>&1) || fail "dream_analysis_skills_ref.sh: $out"
pass "Phase 2 + Phase 3 per-manifest, last, legacy and edges rules; history; text-following notes clean; violation named; drift test"
