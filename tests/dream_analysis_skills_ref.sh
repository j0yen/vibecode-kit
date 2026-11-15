#!/usr/bin/env bash
# No drift: /dream's vision step hands forward analysis to /wwhtbt and failure
# analysis to /5whysandrhyme (one implementation each); its frontmatter keeps the
# fable-spawn key the spawn gate reads and pins no model or effort, because the
# routing policy (.config/skill-routing/policy.json, launched through
# fable-launch.sh --route-request) is the one source for both (PRD-dream-route-pin-removal).
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
fail=0
printf '%s\n' "$fm" | grep -qE '^fable-spawn: true$' || { echo "FAIL frontmatter missing ^fable-spawn: true$"; fail=1; }
for k in model effort; do
  hit=$(printf '%s\n' "$fm" | grep -nE "^$k:" || true)
  [ -z "$hit" ] || { echo "FAIL frontmatter pins $k (the routing policy is the one source): ${hit//$'\n'/; }"; fail=1; }
done
pins=$(grep -nE 'Fable at max|effort: max|model: fable' "$f" || true)
[ -z "$pins" ] || { echo "FAIL skill text names a Fable/max pin: ${pins//$'\n'/; }"; fail=1; }

p3=$(awk '/^## Phase 3 — Draft/{f=1;next} /^## /{f=0} f' "$f")
for s in 'skill-routing/policy\.json' '--route-request' 'Route: ungoverned'; do
  printf '%s\n' "$p3" | grep -qE -- "$s" || { echo "FAIL Phase 3 does not name $s"; fail=1; }
done

v=$(awk '/^## Phase 2 — Vision/{f=1;next} /^## /{f=0} f' "$f")
for s in '`/wwhtbt`' '`/5whysandrhyme`' 'decisions/\*-wwhtbt.md'; do
  printf '%s\n' "$v" | grep -qE "$s" || { echo "FAIL Phase 2 does not reference $s"; fail=1; }
done
[ "$fail" = 0 ] && echo "PASS dream analysis-skill refs"
exit "$fail"
