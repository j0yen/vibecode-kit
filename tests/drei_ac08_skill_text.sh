#!/usr/bin/env bash
# AC8 (R9, R7) — SKILL.md Phase 2 carries "Mission trace and edge map (before
# decomposition)" naming the edges file, its eight edge fields and three statuses; Phase 4's
# template carries the Mission: line after State: and the record-lines paragraph states the
# continuity rule; the lint header's finding-id list names the seven new ids; history.md
# names R3B3-01 and R3B3-02; tests/dream_analysis_skills_ref.sh exits 0.
# DREAM_SKILL_MD, when set, names the SKILL.md to check.
set -uo pipefail
T_OUT=$(mktemp); trap 'rm -f "$T_OUT"' EXIT
# shellcheck source=tests/drei_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drei_lib.sh"
f="${DREAM_SKILL_MD:-$REPO/skills/dream/SKILL.md}"
[ -r "$f" ] || fail "skill file missing or unreadable: $f"
section() { awk -v h="$1" '/^```/{fence=!fence} !fence&&/^## /{f=(index($0,h)==1);next} f' "$f"; }
p2=$(section '## Phase 2 — Vision' | tr '\n' ' ' | tr -s ' ')
para=$(printf '%s' "$p2" | grep -o 'Mission trace and edge map (before decomposition).*') || fail "Phase 2 lacks the 'Mission trace and edge map (before decomposition)' paragraph"
# shellcheck disable=SC2016
for s in 'notes/missions/<name>.edges.jsonl' outcome invariants prds external producer consumer command trigger authority \
  effect_id recovery_owner postcondition '`known`' '`external`' '`unknown`' owner contract 'not completion'; do
  grep -qF -- "$s" <<<"$para" || fail "Phase 2 edge-map paragraph lacks '$s'"
done
tpl=$(section '## Phase 4 — Persist' | awk '/^```/{n++; next} n==1')
printf '%s\n' "$tpl" | grep -A1 '^State:' | grep >/dev/null '^Mission: ' || fail "Phase 4 template: no Mission: line right after State:"
p4=$(section '## Phase 4 — Persist' | tr '\n' ' ' | tr -s ' ')
grep -qF 'The six record lines' <<<"$p4" || fail "Phase 4: the record-lines paragraph does not say six"
# shellcheck disable=SC2016  # literal backticks of the skill text
grep -qF 'one `Mission:` name and one edge map' <<<"$p4" || fail "Phase 4: no continuity rule (one Mission: name and one edge map)"
hdr=$(sed -n '1,80p' "$LINT")
for id in mission-grammar mission-edges-missing edge-grammar edge-unexplained edge-unknown-unowned edge-node-unlisted mission-prd-unlisted; do
  grep -q -- "$id" <<<"$hdr" || fail "lint header finding-id list lacks $id"
  grep -qF -- "$id" <<<"$p4" || fail "Phase 4 lint step does not name $id"
done
for s in R3B3-01 R3B3-02; do grep -q "$s" "$REPO/skills/dream/history.md" || fail "history.md lacks $s"; done
bash "$REPO/tests/dream_analysis_skills_ref.sh" >"$T_OUT" 2>&1 || fail "dream_analysis_skills_ref.sh: $(tail -3 "$T_OUT")"
pass "Phase 2 paragraph, Phase 4 Mission: line + continuity, header ids, history, skills ref"
