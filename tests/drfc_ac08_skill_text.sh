#!/usr/bin/env bash
# AC8 (R10) — SKILL.md Phase 3 carries, after **Review:**, the paragraph "After the first
# systemic finding or material repair": the six classes, a provenance-only repair (`changed`
# naming only the packet files it moved, possibly empty, and `sweep` optional: R3, review L15),
# the sweep over incident edges, same-author feedback, the `before`/`after` hashes, a bounded
# re-review and the reviewer's advisory `accepts` row for an accepted decline; Phase 4's template
# shows `repairs=` and its lint step names the eleven new ids, as does the lint's header list;
# history.md has an entry naming R3B5-05 and the three-round pattern; and
# tests/dream_analysis_skills_ref.sh exits 0. DREAM_SKILL_MD, when set, names the SKILL.md.
# PRD-dream-repairs-file-in-packet R1-R3: the **Whole-chain review paragraph and the repair
# paragraph (each sliced from its bold heading to the next blank line, lines joined) both carry
# R1's sentence, and the whole-chain freeze-member sentence names the repairs file with its
# condition; a paragraph that lacks it is named with the missing clause. An empty DREAM_SKILL_MD
# exits 2 naming it (Technical considerations, edge cases); a missing or unreadable one fails as before.
set -uo pipefail
# shellcheck source=tests/drrp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drrp_lib.sh"
T_OUT=$(mktemp); trap 'rm -f "$T_OUT"' EXIT
if [ "${DREAM_SKILL_MD+set}" = set ]; then f=$DREAM_SKILL_MD; else f="$REPO/skills/dream/SKILL.md"; fi
if [ -z "$f" ]; then echo "ERROR DREAM_SKILL_MD is set to an empty path ('')" >&2; exit 2; fi
[ -r "$f" ] || fail "skill file missing or unreadable: $f"
# R1, R2: the sentence in both paragraphs (a copy in another section satisfies neither)
miss=""
for h in "$RP_H1" "$RP_H2"; do
  p=$(rp_para "$f" "$h")
  if [ -z "$p" ]; then miss="${miss:+$miss | }paragraph '$h' not found"; continue; fi
  m=$(rp_missing "$p")
  [ -z "$m" ] || miss="${miss:+$miss | }paragraph '$h' lacks R1's sentence (missing clause: $m)"
done
p=$(rp_para "$f" "$RP_H1")
fm=$(printf '%s' "$p" | grep -o 'listing every mission PRD[^.]*\.' | head -1)
# shellcheck disable=SC2016
for s in 'the `repairs=` file' 'later than the earliest `before`'; do
  case "$fm" in *"$s"*) ;; *) miss="${miss:+$miss | }paragraph '$RP_H1': the freeze-member sentence ('listing every mission PRD ...') does not name '$s'";; esac
done
[ -z "$miss" ] || fail "$miss"
section() { awk -v h="$1" '/^```/{fence=!fence} !fence&&/^## /{f=(index($0,h)==1);next} f' "$f"; }
p3=$(section '## Phase 3 — Draft' | tr '\n' ' ' | tr -s ' ')
rv=${p3#*\*\*Review:\*\*}
[ "$rv" != "$p3" ] || fail "Phase 3 has no **Review:** paragraph"
par=$(printf '%s' "$rv" | grep -o 'After the first systemic finding or material repair.*') || fail "no 'After the first systemic finding or material repair' paragraph after **Review:**"
# shellcheck disable=SC2016  # literal backticks of the skill text
for s in provenance missing-producer-runner authority-bypass unreachable-transition semantic-incompatibility false-green-acceptance \
  'provenance only' 'failure-class sweep' 'incident' 'same author' '`before`' '`after`' 'bounded re-review' 'advisory' '`accepts`' \
  'declined' 'no blanket hold' '`changed` names only the packet files it moved (it may be empty), and `sweep` is optional'; do
  printf '%s' "$par" | grep >/dev/null -F -- "$s" || fail "the repair paragraph lacks '$s'"
done
p4=$(section '## Phase 4 — Persist' | tr '\n' ' ' | tr -s ' ')
printf '%s' "$p4" | grep >/dev/null -F -- 'repairs=' || fail "Phase 4 does not show repairs="
hdr=$(sed -n '1,90p' "$LINT")
for id in repair-grammar mission-repairs-missing repair-duplicate repair-missing repair-class-mismatch sweep-missing repair-author-mismatch repair-hash-mismatch repair-scope-mismatch affected-consumer-unreviewed repair-declined-unaccepted; do
  printf '%s' "$p4" | grep >/dev/null -F -- "$id" || fail "Phase 4 lint step does not name $id"
  grep -q -- "$id" <<<"$hdr" || fail "lint header finding-id list lacks $id"
done
e=$(awk '/^- \*\*/{if(f)exit; f=0} /^- \*\*.*[Ff]ailure-class sweep/{f=1} f' "$REPO/skills/dream/history.md" | tr '\n' ' ')
[ -n "$e" ] || fail "history.md has no failure-class sweep entry"
for s in R3B5-05 'three rounds'; do printf '%s' "$e" | grep >/dev/null -F -- "$s" || fail "the failure-class sweep history entry lacks '$s'"; done
bash "$REPO/tests/dream_analysis_skills_ref.sh" >"$T_OUT" 2>&1 || fail "dream_analysis_skills_ref.sh: $(tail -3 "$T_OUT")"
pass "R1 sentence in both paragraphs + freeze list, Phase 3 repair paragraph, Phase 4 repairs= + ids, header ids, history, skills ref"
