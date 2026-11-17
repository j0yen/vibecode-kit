#!/usr/bin/env bash
# AC8 (R10) — SKILL.md Phase 3 carries, after **Review:**, the paragraph "After the first
# systemic finding or material repair": the six classes, a provenance-only repair (`changed`
# naming only the packet files it moved, possibly empty, and `sweep` optional: R3, review L15),
# the sweep over incident edges, same-author feedback, the `before`/`after` hashes, a bounded
# re-review and the reviewer's advisory `accepts` row for an accepted decline; Phase 4's template
# shows `repairs=` and its lint step names the eleven new ids, as does the lint's header list;
# history.md has an entry naming R3B5-05 and the three-round pattern; and
# tests/dream_analysis_skills_ref.sh exits 0. DREAM_SKILL_MD, when set, names the SKILL.md.
set -uo pipefail
# shellcheck source=tests/drfc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drfc_lib.sh"
T_OUT=$(mktemp); trap 'rm -f "$T_OUT"' EXIT
f="${DREAM_SKILL_MD:-$REPO/skills/dream/SKILL.md}"
[ -r "$f" ] || fail "skill file missing or unreadable: $f"
section() { awk -v h="$1" '/^```/{fence=!fence} !fence&&/^## /{f=(index($0,h)==1);next} f' "$f"; }
p3=$(section '## Phase 3 — Draft' | tr '\n' ' ' | tr -s ' ')
rv=${p3#*\*\*Review:\*\*}
[ "$rv" != "$p3" ] || fail "Phase 3 has no **Review:** paragraph"
par=$(printf '%s' "$rv" | grep -o 'After the first systemic finding or material repair.*') || fail "no 'After the first systemic finding or material repair' paragraph after **Review:**"
# shellcheck disable=SC2016  # literal backticks of the skill text
for s in provenance missing-producer-runner authority-bypass unreachable-transition semantic-incompatibility false-green-acceptance \
  'provenance only' 'failure-class sweep' 'incident' 'same author' '`before`' '`after`' 'bounded re-review' 'advisory' '`accepts`' \
  'declined' 'no blanket hold' '`changed` names only the packet files it moved (it may be empty), and `sweep` is optional'; do
  printf '%s' "$par" | grep -qF -- "$s" || fail "the repair paragraph lacks '$s'"
done
p4=$(section '## Phase 4 — Persist' | tr '\n' ' ' | tr -s ' ')
printf '%s' "$p4" | grep -qF -- 'repairs=' || fail "Phase 4 does not show repairs="
hdr=$(sed -n '1,90p' "$LINT")
for id in repair-grammar mission-repairs-missing repair-duplicate repair-missing repair-class-mismatch sweep-missing repair-author-mismatch repair-hash-mismatch repair-scope-mismatch affected-consumer-unreviewed repair-declined-unaccepted; do
  printf '%s' "$p4" | grep -qF -- "$id" || fail "Phase 4 lint step does not name $id"
  grep -q -- "$id" <<<"$hdr" || fail "lint header finding-id list lacks $id"
done
e=$(awk '/^- \*\*/{if(f)exit; f=0} /^- \*\*.*[Ff]ailure-class sweep/{f=1} f' "$REPO/skills/dream/history.md" | tr '\n' ' ')
[ -n "$e" ] || fail "history.md has no failure-class sweep entry"
for s in R3B5-05 'three rounds'; do printf '%s' "$e" | grep -qF -- "$s" || fail "the failure-class sweep history entry lacks '$s'"; done
bash "$REPO/tests/dream_analysis_skills_ref.sh" >"$T_OUT" 2>&1 || fail "dream_analysis_skills_ref.sh: $(tail -3 "$T_OUT")"
pass "Phase 3 repair paragraph, Phase 4 repairs= + ids, header ids, history, skills ref"
