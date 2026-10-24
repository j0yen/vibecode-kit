#!/usr/bin/env bash
# No drift: /dream's vision step hands forward analysis to /wwhtbt and failure
# analysis to /5whysandrhyme (one implementation each), and its frontmatter keeps
# the Fable max pin + fable-spawn key the spawn gate reads.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
f="$here/../skills/dream/SKILL.md"
fm=$(awk 'NR==1&&$0!="---"{exit} NR==1{next} $0=="---"{exit} {print}' "$f")
fail=0
for k in '^model: fable$' '^effort: max$' '^fable-spawn: true$'; do
  printf '%s\n' "$fm" | grep -qE "$k" || { echo "FAIL frontmatter missing $k"; fail=1; }
done
v=$(awk '/^## Phase 2 — Vision/{f=1;next} /^## /{f=0} f' "$f")
for s in '`/wwhtbt`' '`/5whysandrhyme`' 'decisions/\*-wwhtbt.md'; do
  printf '%s\n' "$v" | grep -qE "$s" || { echo "FAIL Phase 2 does not reference $s"; fail=1; }
done
[ "$fail" = 0 ] && echo "PASS dream analysis-skill refs"
exit "$fail"
