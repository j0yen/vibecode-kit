#!/usr/bin/env bash
# AC6 (R6, R1 id list) — every drmr_ac08 and drfc_ac08 assertion still passes (both run and exit
# 0); SKILL.md Phase 3 carries the **Pre-launch packet check paragraph between the whole-chain
# review and **Adversarial pass**, and both the whole-chain review paragraph and the repair
# paragraph point at it by naming `--packet-only --pending`; that paragraph holds each item R6
# lists: the pending entry's lines (Task:, Mission:, full Analysis:, State: with the re-listed
# reviews' reviewed: tokens and the header-member rule, Route:, and the Review: lines re-listed in
# their order then this run's in launch order), never appended as a draft, a defect fixed before a
# new freeze, the command after each freeze and before its reviewer, withdrawn= with a corrected
# replacement, a defect beside the manifest fixed by placing the copy, held errors and refused new
# ones, and the packet obligations once (the matrix rule naming its PRD, a later matrix, a section
# for every header PRD qualifying "for each PRD in the batch", the repairs-file sentence word for
# word, `sweep` on `amended` rows, the sidecar digest checked before the Review: line, findings=none
# only with no sidecar file); the reviewer prompt says no findings means no file; Phase 4 shows
# withdrawn=, its Review: bullet carries the re-list sentence and its lint step names
# mission-withdrawn-bound, which the lint header list and MISSION_IDS carry; history.md has one
# entry naming dream-packet-errors-while-repairable; tests/dream_analysis_skills_ref.sh exits 0.
set -uo pipefail
# shellcheck source=tests/drpe_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drpe_lib.sh"
# shellcheck source=tests/drrp_lib.sh
. "$here/drrp_lib.sh"
f="$REPO/skills/dream/SKILL.md"
for t in drmr_ac08_skill_text drfc_ac08_skill_text; do
  out=$(bash "$here/$t.sh" 2>&1) || fail "$t.sh: $out"
done
section() { awk -v h="$1" '/^```/{fence=!fence} !fence&&/^## /{f=(index($0,h)==1);next} f' "$f"; }
p3=$(section '## Phase 3 — Draft' | tr '\n' ' ' | tr -s ' ')
H='**Pre-launch packet check'
pp=$(rp_para "$f" "$H")
[ -n "$pp" ] || fail "SKILL.md has no '$H' paragraph"
case "$p3" in *"$H"*) ;; *) fail "the '$H' paragraph is not in Phase 3";; esac
order=$(printf '%s' "$p3" | grep -o 'Whole-chain review (before the first independent review).*' | grep -o '\*\*Pre-launch packet check.*' | grep -c '\*\*Adversarial pass')
[ "$order" = 1 ] || fail "the '$H' paragraph is not between the whole-chain review and **Adversarial pass**"
for h in "$RP_H1" "$RP_H2"; do
  case "$(rp_para "$f" "$h")" in *'--packet-only --pending'*) ;; *) fail "paragraph '$h' does not name --packet-only --pending";; esac
done
# shellcheck disable=SC2016  # literal backticks of the skill text
for s in 'pending entry' '`Task:`' '`Mission:`' 'full `Analysis:`' '`State:`' '`Route:`' 'never appended to the log as a draft' \
  'repeating the re-listed reviews'"'"' `reviewed:` tokens' 'a header member that reached no state in this run is not named before launch' \
  'enters the Phase 4 `State:` through the `reviewed:` token its verdict gives' \
  'the chain reviews listed by the last same-Task entry that carries the `Mission:` line, re-listed in their order, then this run'"'"'s returned chain reviews in launch order' \
  'a defect is fixed before a new freeze, never in the live file alone' \
  'scripts/dream-run-note-lint.sh notes/dream-log.md --last --packet-only --pending' 'after each freeze and before launching its reviewer' \
  '`withdrawn=' 'unbound' 'corrected replacement' 'by placing the copy, not by a same-content replacement' \
  'is held and reported' 'held_packet_errors' 'refused until the author keeps the old name' \
  'a new matrix name that a bound manifest lists no copy of' 'mission-withdrawn-bound' \
  'packet obligations' 'dream-matrix-per-manifest' 'later than the previous entry' \
  'a `## PRD-<slug>` section for every PRD the last manifest'"'"'s edges header lists' 'for each PRD in the batch' \
  "$RP_SENTENCE" '`sweep` on `amended` rows' 'sidecar' \
  'checks its digest against the `findings=` line before writing the `Review:` line' '`findings=none` only when no sidecar file exists'; do
  case "$pp" in *"$s"*) ;; *) fail "the '$H' paragraph lacks '$s'";; esac
done
case "$(rp_para "$f" "$RP_H1")" in *'no findings means no file'*) ;; *) fail "the reviewer prompt (whole-chain review paragraph) does not say no findings means no file";; esac
p4=$(section '## Phase 4 — Persist' | tr '\n' ' ' | tr -s ' ')
# shellcheck disable=SC2016
for s in '[withdrawn=<manifest>[,<manifest>...]]' \
  'a later entry of a mission re-lists the earlier entry'"'"'s chain reviews before its own, because the lint reads chain reviews only from the linted entry, and that entry'"'"'s `State:` repeats their `reviewed:` tokens' \
  'mission-withdrawn-bound'; do
  case "$p4" in *"$s"*) ;; *) fail "Phase 4 lacks '$s'";; esac
done
rvb=$(section '## Phase 4 — Persist' | awk '/^- `Review:`/{f=1} f&&/^- `State:`/{exit} f' | tr '\n' ' ' | tr -s ' ')
case "$rvb" in *'re-lists the earlier entry'*) ;; *) fail "the Phase 4 \`Review:\` bullet lacks the re-list sentence";; esac
hdr=$(sed -n '1,90p' "$LINT")
grep -q -- mission-withdrawn-bound <<<"$hdr" || fail "lint header finding-id list lacks mission-withdrawn-bound"
python3 - "$LINT" <<'PY' || fail "MISSION_IDS lacks mission-withdrawn-bound"
import re, sys
m = re.search(r"^MISSION_IDS = \(([^)]*)\)", open(sys.argv[1], encoding="utf-8").read(), re.M)
sys.exit(0 if m and '"mission-withdrawn-bound"' in m.group(1) else 1)
PY
e=$(awk '/^- \*\*/{n++} n{print n "\t" $0}' "$REPO/skills/dream/history.md" | awk -F'\t' '{a[$1]=a[$1] " " $2} END{for(k in a) print a[k]}' | grep -F 'dream-packet-errors-while-repairable')
[ "$(printf '%s\n' "$e" | grep -c .)" = 1 ] || fail "history.md: want one entry naming dream-packet-errors-while-repairable, got: $e"
setup_pe
for c in ok-three ok-three-hm ok-first; do pe "$c"; pk; rc0; done
out=$(bash "$REPO/tests/dream_analysis_skills_ref.sh" 2>&1) || fail "dream_analysis_skills_ref.sh: $out"
pass "drmr_ac08 + drfc_ac08 pass; Phase 3 pre-launch paragraph with every R6 item; Phase 4 withdrawn=, re-list, id; header + MISSION_IDS; history; notes that follow the text exit 0; skills ref"
