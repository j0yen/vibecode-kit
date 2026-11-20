#!/usr/bin/env bash
# C3 and G9 (gate fix), as amended by PRD-dream-mission-chain-review: the lint's --selftest
# passes and carries the P1, P4, KB1, KB4, KB5, KB6, KB11 and KB13 cases, KB1/KB4/KB11/KB13
# under their R5/R6 outcomes (KB1: a later FIX supersedes the earlier APPROVE, R5, and holds
# the slug, R6, refused once it reaches eligible; KB4: launch order is compared only within one
# manifest index, R2; KB11: a review on an unlisted manifest is no chain review, R2; KB13: no
# result= is mission-verdict-missing, R3); KB5 and KB6 keep PR #9's pin (R9, R5's last
# sentence). SKILL.md's Phase 3 **Review:** paragraph carries, right after "(FIX and REJECT are
# not pinned).", R5's rule (only the latest chain review naming a slug pins it), which REPLACES
# the G9 sentence (R6: the gate fix's G5-G6 supersession branch is replaced); its Phase 4
# provenance-label text says `verified` counts a superseded APPROVE as matched and the JSON
# names it under `superseded`; history.md keeps one gate-fix entry naming A1723 and the
# witness note. DREAM_SKILL_MD, when set, names the SKILL.md to check.
set -uo pipefail
# shellcheck source=tests/drsp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; mkdir -p "$T/fakehome"; export HOME="$T/fakehome"; unset SKILL_ROUTING_DECISIONS
st=$("$LINT" --selftest 2>&1); rc=$?
[ "$rc" = 0 ] || fail "selftest rc=$rc: $(printf '%s\n' "$st" | grep -v '^PASS' | head -20)"
for n in pass:drsp-p1-superseded pass:drsp-p4-b-not-superseded \
         pass:drsp-kb1-j-fix-held refuse:mission-approval-blocked:drsp-kb1-j-fix-eligible \
         pass:drsp-kb4-launch-across-manifests \
         refuse:review-snapshot-stale:drsp-kb5-no-mission refuse:review-snapshot-stale:drsp-kb6-j-legacy \
         pass:drsp-kb11-unlisted-manifest-not-chain refuse:mission-verdict-missing:drsp-kb13-j-no-result; do
  printf '%s\n' "$st" | grep >/dev/null -x "PASS $n" || fail "selftest has no passing case $n"
done
f="${DREAM_SKILL_MD:-$REPO/skills/dream/SKILL.md}"
[ -r "$f" ] || fail "skill file missing or unreadable: $f"
section() { awk -v h="$1" '/^```/{fence=!fence} !fence&&/^## /{f=(index($0,h)==1);next} f' "$f"; }
para() { awk -v s="$1" 'index($0,s)==1{f=1} f&&/^$/{exit} f' | tr '\n' ' ' | tr -s ' '; }
rv=$(section '## Phase 3 — Draft' | para '**Review:**')
# shellcheck disable=SC2016  # literal backticks of the skill text
r5='(FIX and REJECT are not pinned). On a note whose `Mission:` line carries `scope=`, only the latest chain review (in `Review:` line order) whose file names a slug pins that slug; an earlier chain review'"'"'s APPROVE on it is superseded by that later verdict, and under `mission=APPROVE` the whole packet is pinned to that review'"'"'s manifest.'
printf '%s' "$rv" | grep >/dev/null -F -- "$r5" || fail "Phase 3 **Review:** paragraph lacks chain-review R5's sentence after '(FIX and REJECT are not pinned)': $rv"
case "$rv" in *'a gate-fix convention'*) fail "Phase 3 **Review:** paragraph still carries the G9 sentence that chain-review R6 replaces";; esac
p4=$(section '## Phase 4 — Persist' | tr '\n' ' ' | tr -s ' ')
# shellcheck disable=SC2016
printf '%s' "$p4" | grep >/dev/null -F -- '`verified` counts a superseded APPROVE as matched, and the JSON names it under `superseded`' \
  || fail "Phase 4 provenance-label text lacks the superseded sentence"
hist="$REPO/skills/dream/history.md"
n=$(grep -c '^- \*\*.*gate fix, A1723' "$hist")
[ "$n" = 1 ] || fail "history.md: $n gate-fix entries naming A1723, want 1"
e=$(awk '/^- \*\*.*gate fix, A1723/{f=1;print;next} f&&/^- \*\*/{exit} f' "$hist" | tr '\n' ' ')
for s in 'superseded' 'notes/dream-log.md' 'dream-early-integration' 'r9'; do
  printf '%s' "$e" | grep >/dev/null -F -- "$s" || fail "history.md A1723 entry does not name $s: $e"
done
pass "$(printf '%s\n' "$st" | tail -1)"
