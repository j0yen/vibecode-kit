#!/usr/bin/env bash
# No drift: /dream's vision step hands forward analysis to /wwhtbt and failure
# analysis to /5whysandrhyme (one implementation each); its frontmatter keeps the
# fable-spawn key the spawn gate reads and pins no model or effort, because the
# routing policy (.config/skill-routing/policy.json, launched through
# fable-launch.sh --route-request) is the one source for both (PRD-dream-route-pin-removal);
# and it carries the run-record text (PRD-dream-run-record R5).
#
# DREAM_SKILL_MD, when set, names the SKILL.md to check (fixtures); default is the
# repository's own file. Exit 0 PASS, 1 a FAIL line per finding, 2 the path is
# empty, missing or unreadable.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "${DREAM_SKILL_MD+set}" = set ]; then f=$DREAM_SKILL_MD; else f="$here/../skills/dream/SKILL.md"; fi
if [ -z "$f" ]; then echo "ERROR DREAM_SKILL_MD is set to an empty path ('')" >&2; exit 2; fi
if [ ! -f "$f" ] || [ ! -r "$f" ]; then echo "ERROR skill file missing or unreadable: $f" >&2; exit 2; fi

fm=$(awk 'NR==1&&$0!="---"{exit} NR==1{next} $0=="---"{exit} {print}' "$f")
# section "<heading prefix>": the lines under a `## ` heading up to the next one; a
# `## ` line inside a ``` fence (the Phase 4 run-note template) is not a heading.
section() { awk -v h="$1" '/^```/{fence=!fence} !fence&&/^## /{f=(index($0,h)==1);next} f' "$f"; }
fail=0
grep -qE '^fable-spawn: true$' <<< "$fm" || { echo "FAIL frontmatter missing ^fable-spawn: true$"; fail=1; }
for k in model effort; do
  hit=$(printf '%s\n' "$fm" | grep -nE "^$k:" || true)
  [ -z "$hit" ] || { echo "FAIL frontmatter pins $k (the routing policy is the one source): ${hit//$'\n'/; }"; fail=1; }
done
pins=$(grep -nE 'Fable at max|effort: max|model: fable' "$f" || true)
[ -z "$pins" ] || { echo "FAIL skill text names a Fable/max pin: ${pins//$'\n'/; }"; fail=1; }

p3=$(section '## Phase 3 — Draft')
for s in 'skill-routing/policy\.json' '--route-request' 'Route: ungoverned'; do
  grep -qE -- "$s" <<< "$p3" || { echo "FAIL Phase 3 does not name $s"; fail=1; }
done

v=$(section '## Phase 2 — Vision')
for s in '`/wwhtbt`' '`/5whysandrhyme`' 'decisions/\*-wwhtbt.md'; do
  grep -qE "$s" <<< "$v" || { echo "FAIL Phase 2 does not reference $s"; fail=1; }
done

# Run record (PRD-dream-run-record R5): Phase 4 template lines, the lint step, the
# Phase 2 run/reuse/skip values and launch recipe, and the Phase 3 adversarial pass
# placed before **Review:**. Presence of the text only; the lint's own fixtures are
# the behavioral control.
p4=$(section '## Phase 4 — Persist')
for s in 'Task:' 'Route:' 'Analysis:' 'Review:' 'State:'; do
  grep -qE -- "^$s " <<< "$p4" || { echo "FAIL Phase 4 template lacks a $s line"; fail=1; }
done
for s in 'adversarial=' 'dream-run-note-lint.sh'; do
  grep -qF -- "$s" <<< "$p4" || { echo "FAIL Phase 4 does not name $s"; fail=1; }
done
for s in '`ran' '`reused' '`skipped' '`inline`' '--session-id'; do
  grep -qF -- "$s" <<< "$v" || { echo "FAIL Phase 2 does not name $s"; fail=1; }
done
adv=$(printf '%s\n' "$p3" | awk '/^\*\*Adversarial pass/{f=1} f&&/^$/{exit} f')
if [ -z "$adv" ]; then
  echo "FAIL Phase 3 has no Adversarial pass paragraph"; fail=1
else
  advj=$(printf '%s\n' "$adv" | tr '\n' ' ' | tr -s ' ')
  for s in '`invariant`' 'still-broken implementation' 'counterexample' 'discriminating check' '`evidence`' \
           'Identity and provenance' 'Boundary environment' 'Evidence interpretation' \
           'Alternative bypasses and ordering' 'Falsifier quality' 'Whole-scope coverage and handoff' \
           '## PRD-<slug>' '### <family name>' 'unconditional fallback:' '`conditional fallback:' \
           '## Uncovered' 'final message'; do
    grep -qiF -- "$s" <<< "$advj" || { echo "FAIL Adversarial pass paragraph does not name $s"; fail=1; }
  done
  a_ln=$(printf '%s\n' "$p3" | grep -n '^\*\*Adversarial pass' | head -1 | cut -d: -f1)
  r_ln=$(printf '%s\n' "$p3" | grep -n '^\*\*Review:\*\*' | head -1 | cut -d: -f1)
  [ -n "$r_ln" ] && [ "$a_ln" -lt "$r_ln" ] || { echo "FAIL Phase 3 Adversarial pass paragraph is not placed before **Review:**"; fail=1; }
fi
[ "$fail" = 0 ] && echo "PASS dream analysis-skill refs"
exit "$fail"
