#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the drei_* tests (PRD-dream-mission-edge-map). Reuses the drrec helpers
# (lint, lint_ungov, setline, addline, decedit, jget, fail, pass) unchanged and copies
# tests/fixtures/drei (one passing mission home: a run note with a Mission: line, its edges
# file, two PRD stubs, one author row) into a temporary directory with a private HOME, so
# each case mutates one element. DRREC_LINT runs the tests against another copy.
# shellcheck source=tests/drrec_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
EIFIX="$here/fixtures/drei"
S_EAUTH=eeeeeeee-0000-4000-8000-000000000001
EI_TS=2026-11-16T10:00:00-08:00
EI_TS2=2026-11-16T11:00:00-08:00
EI_NAME=drei-mission
EI_EDGES=notes/missions/drei-mission.edges.jsonl
EI_M1=notes/snapshots/drei-m1/snapshot.sha256
PRED_SHA=373ff679da9fbed12109fdb3da2a7a8fbd330748
PRED_LINT_SHA=acde611f76e97563c37cb3ea1c6463cdfbf2fa97654478eb6b9f6de49daeffe9
command -v python3 >/dev/null 2>&1 || fail "python3 is required (never a skip)"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required (never a skip)"
setup_ei() {
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  cp -r "$EIFIX/." "$T/"
  mkdir -p "$T/fakehome"
  export HOME="$T/fakehome" ANALYSIS_WIKI_DIR="$T/wiki"
  unset SKILL_ROUTING_DECISIONS
  LOG="$T/home/notes/dream-log.md"; DEC="$T/decisions.jsonl"; H="$T/home"; EF="$H/$EI_EDGES"
  cp -r "$T/home" "$T/home.orig"; cp "$DEC" "$T/dec.orig"
}
# reset_ei: restore the copied fixture
reset_ei() { rm -rf "${H:?}"; cp -r "$T/home.orig" "$H"; cp "$T/dec.orig" "$DEC"; }
# two_entry: use the two-entry note (entry 1 with Mission: and scope=, entry 2 same Task:
# without the line, a=eligible) as the log
two_entry() { cp "$H/notes/dream-log-two.md" "$LOG"; }
# edge <id> <python statement on e>: edit one edge object of the live edges file
edge() { python3 - "$EF" "$1" "$2" <<'PY'
import sys, json
p, eid, stmt = sys.argv[1:]
L = open(p, encoding="utf-8").read().split("\n"); out = []
for i, l in enumerate(L):
    if i > 0 and l.strip():
        e = json.loads(l)
        if e.get("id") == eid:
            exec(stmt, {"e": e}); l = json.dumps(e)
    out.append(l)
open(p, "w", encoding="utf-8").write("\n".join(out))
PY
}
# header <python statement on h>: edit the header object (line 1) of the live edges file
header() { python3 - "$EF" "$1" <<'PY'
import sys, json
p, stmt = sys.argv[1:]
L = open(p, encoding="utf-8").read().split("\n")
h = json.loads(L[0]); exec(stmt, {"h": h}); L[0] = json.dumps(h)
open(p, "w", encoding="utf-8").write("\n".join(L))
PY
}
# run_ei: lint the current note with --json; sets RC, JS (stdout), ERR (stderr)
run_ei() { JS=$(lint --json 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_tb; }
not_root() { [ "$(id -u)" != 0 ] || fail "euid 0: root reads a mode-000 file, so this case would be vacuous"; }
no_tb() { case "$ERR" in *Traceback*) fail "traceback: $ERR";; esac; }
# findings_eq <want python list literal>: exact findings list of $JS
findings_eq() { local f; f=$(printf '%s' "$JS" | jget 'd["findings"]') || fail "no JSON (rc=$RC): $ERR"
  [ "$f" = "$1" ] || fail "findings=$f want $1 (rc=$RC): $ERR"; }
# has_fail <id> <substring...>: a FAIL <id> line on stderr carrying every substring
has_fail() { local id=$1 l; shift; l=$(printf '%s\n' "$ERR" | grep "^FAIL $id: ") || fail "no FAIL $id line: $ERR"
  for s in "$@"; do printf '%s\n' "$l" | grep -qF -- "$s" || fail "FAIL $id lines lack '$s': $l"; done; }
