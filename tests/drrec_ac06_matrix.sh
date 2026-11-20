#!/usr/bin/env bash
# AC6 — a matrix meeting R10 is labelled adversarial: self; a two-slug matrix whose
# first section lacks a family heading the second has fails naming the first slug;
# a conditional-fallback prefix outside the bypass family fails case-missing.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
setup; M="$H/$MX"; cp "$M" "$T/mx.orig"
js=$(lint --json 2>/dev/null); rc=$?
[ "$rc" = 0 ] && [ "$(printf '%s' "$js" | jget 'd["provenance"]["adversarial"]')" = '"self"' ] || fail "self: rc=$rc $js"
# two slugs: bar's section complete; foo's Falsifier quality heading demoted to prose
python3 - "$M" <<'PY'
import sys,re
p=sys.argv[1]; s=open(p).read()
pre,rest=s.split('## PRD-foo\n',1); body,unc=rest.split('## Uncovered\n',1)
foo=body.replace('### Falsifier quality\n','Falsifier quality, as a table without its heading:\n')
pre='# Adversarial matrix\n\nFamilies: Identity and provenance; Boundary environment; Evidence interpretation; Alternative bypasses and ordering; Falsifier quality; Whole-scope coverage and handoff.\n\n'
open(p,'w').write(pre+'## PRD-foo\n'+foo+'## PRD-bar\n'+body+'## Uncovered\n'+unc)
PY
setline State "State: foo=linted foo=reviewed:APPROVE bar=linted"
out=$(lint 2>&1); l=$(printf '%s\n' "$out" | grep '^FAIL adversarial-family-missing: ') || fail "family: $out"
printf '%s' "$l" | grep >/dev/null -w foo && printf '%s' "$l" | grep >/dev/null -i 'falsifier quality' || fail "family: slug/family not named: $l"
printf '%s' "$l" | grep >/dev/null -w bar && fail "family: bar named: $l"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" adversarial-family-missing
# conditional fallback prefix in the family after the bypass heading only
cp "$T/mx.orig" "$M"; setline State "State: foo=linted foo=reviewed:APPROVE"
python3 - "$M" <<'PY'
import sys
p=sys.argv[1]; s=open(p).read()
s=s.replace('| conditional fallback: R3 | reads legacy when none fresh |','| R3 legacy read | reads legacy when none fresh |')
s=s.replace('| AC4 | test passes vacuously |','| conditional fallback: AC4 | test passes vacuously |')
s=s.replace('The six families below','The conditional case and the six families below')
open(p,'w').write(s)
PY
grep -q '^| conditional fallback: AC4' "$M" || fail "fixture edit failed"
out=$(lint 2>&1); printf '%s\n' "$out" | grep >/dev/null '^FAIL adversarial-case-missing: conditional-fallback' || fail "case: $out"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" adversarial-case-missing
pass
