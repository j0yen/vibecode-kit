#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the drrec_* tests (PRD-dream-run-record). Each test copies
# tests/fixtures/drrec into a temporary directory, runs with a private HOME (no
# default decisions log there) and mutates one element per case.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$here/.." && pwd)"
LINT="${DRREC_LINT:-$REPO/skills/dream/scripts/dream-run-note-lint.sh}"   # DRREC_LINT: run the tests against another copy (known-bad controls)
FIX="$here/fixtures/drrec"
S_DRAFT=aaaaaaaa-0000-4000-8000-000000000001
S_W=aaaaaaaa-0000-4000-8000-000000000002
S_R1=aaaaaaaa-0000-4000-8000-000000000003
TS=2026-11-15T02:00:00-08:00
MX="notes/reviews/2026-11-15T01:00:00-08:00-adversarial.md"
fail() { echo "FAIL $(basename "$0"): $*"; exit 1; }
pass() { echo "PASS $(basename "$0")${1:+: $1}"; exit 0; }
setup() {
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  cp -r "$FIX/." "$T/"
  mkdir -p "$T/fakehome"
  export HOME="$T/fakehome" ANALYSIS_WIKI_DIR="$T/wiki"
  unset SKILL_ROUTING_DECISIONS
  LOG="$T/home/notes/dream-log.md"; DEC="$T/decisions.jsonl"; H="$T/home"
}
# lint the fixture's last entry; extra args appended
lint() { "$LINT" "$LOG" --last --prd-dir "$H" --decisions "$DEC" "$@"; }
# lint with no --decisions (private HOME has no default log = ungoverned host)
lint_ungov() { "$LINT" "$LOG" --last --prd-dir "$H" "$@"; }
# setline <Kind> <full new line>: replace the entry's `<Kind>:` line (all of them for Review)
setline() { python3 - "$LOG" "$1" "$2" <<'PY'
import sys
p,k,new=sys.argv[1:]
L=open(p).read().split('\n'); out=[]; done=False
for l in L:
    if l.startswith(k+':'):
        if not done: out.append(new) if new else None; done=True
        continue
    out.append(l)
open(p,'w').write('\n'.join(out))
PY
}
# addline <after-Kind> <line>: insert a line after the entry's `<after-Kind>:` line
addline() { python3 - "$LOG" "$1" "$2" <<'PY'
import sys
p,k,new=sys.argv[1:]
L=open(p).read().split('\n'); out=[]
for l in L:
    out.append(l)
    if l.startswith(k+':'): out.append(new)
open(p,'w').write('\n'.join(out))
PY
}
# decrow <session-or-ts selector> <python expr on dict r, returning r or None>
decedit() { python3 - "$DEC" "$1" <<'PY'
import sys,json
p,expr=sys.argv[1:]
out=[]
for l in open(p).read().splitlines():
    r=json.loads(l); r=eval(expr,{'r':r,'dict':dict})
    if r is None: continue
    out.extend(r if isinstance(r,list) else [r])
open(p,'w').write(''.join(json.dumps(x)+'\n' for x in out))
PY
}
# jq-like read of a JSON document on stdin: jget '<python expr on d>'
jget() { python3 -c 'import sys,json; d=json.load(sys.stdin); print(json.dumps(eval(sys.argv[1],{"d":d})))' "$1"; }
# expect_exact <rc> <id> <out-json>: exit rc and findings == [id]
expect_exact() { # rc_got want_rc json id
  [ "$1" = "$2" ] || fail "rc=$1 want $2: $3"
  f=$(printf '%s' "$3" | jget 'd["findings"]') || fail "no JSON: $3"
  [ "$f" = "[\"$4\"]" ] || fail "findings=$f want [\"$4\"]"
}
