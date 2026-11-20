#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the drmr_* tests (PRD-dream-mission-chain-review). Reuses the drrec
# helpers (lint, lint_ungov, setline, addline, decedit, jget, fail, pass). `use <variant>`
# copies tests/fixtures/drmr (the passing bound mission) into a temporary directory with a
# private HOME and overlays tests/fixtures/drmr/variants/<variant>/ (its decisions.jsonl and,
# when the variant has a home/, the home files that differ; a failed copy fails the test), so
# each case is one named variant plus one mutation.
# DRREC_LINT runs the tests against another copy.
# shellcheck source=tests/drrec_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
MRFIX="$here/fixtures/drmr"
S_MAUTH=dddddddd-0000-4000-8000-000000000001
S_M1=dddddddd-0000-4000-8000-000000000002
S_M2=dddddddd-0000-4000-8000-000000000003
S_M0=dddddddd-0000-4000-8000-000000000004
MR_TS=2026-11-17T12:00:00-08:00
MR_E1_TS=2026-11-17T08:00:00-08:00
MR_MXB=2026-11-17T09:10:00-08:00-adversarial.md
MR_EB=drmr-mission.edges.jsonl
MR_RB=drmr-mission.repairs.jsonl
MR_MAN=notes/snapshots/mission.sha256
MR_CHAIN=notes/reviews/chain
ST_ALL="a=linted a=reviewed:APPROVE b=linted b=reviewed:APPROVE c=linted c=reviewed:APPROVE"
PRED_SHA=373ff679da9fbed12109fdb3da2a7a8fbd330748
PRED_LINT_SHA=acde611f76e97563c37cb3ea1c6463cdfbf2fa97654478eb6b9f6de49daeffe9
command -v python3 >/dev/null 2>&1 || fail "python3 is required (never a skip)"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required (never a skip)"
setup_mr() {
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  mkdir -p "$T/fakehome"
  export HOME="$T/fakehome" ANALYSIS_WIKI_DIR="$T/wiki"
  unset SKILL_ROUTING_DECISIONS
  W="$T/w"; LOG="$W/home/notes/dream-log.md"; DEC="$W/decisions.jsonl"; H="$W/home"
}
# use <base|variant>: a fresh copy of the passing fixture, the named variant overlaid
use() {
  rm -rf "${W:?}"; mkdir -p "$W"; cp -r "$MRFIX/home" "$W/home"; cp "$MRFIX/decisions.jsonl" "$DEC"
  if [ "$1" != base ]; then
    [ -d "$MRFIX/variants/$1" ] || fail "no variant $1"
    if [ -d "$MRFIX/variants/$1/home" ]; then   # later-unlisted overlays its decisions.jsonl only
      cp -r "$MRFIX/variants/$1/home/." "$W/home/" || fail "variant $1: home overlay copy failed"
    fi
    cp "$MRFIX/variants/$1/decisions.jsonl" "$DEC" || fail "variant $1: decisions.jsonl copy failed"
  fi
}
# run_mr: lint --json; sets RC, JS, ERR; a traceback fails the test
run_mr() { JS=$(lint --json 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_tb; }
run_mr_ungov() { JS=$(lint_ungov --json 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_tb; }
no_tb() { case "$ERR" in *Traceback*) fail "traceback: $ERR";; esac; }
findings_eq() { local f; f=$(printf '%s' "$JS" | jget 'd["findings"]') || fail "no JSON (rc=$RC): $ERR"
  [ "$f" = "$1" ] || fail "findings=$f want $1 (rc=$RC): $ERR"; }
has_id() { printf '%s' "$JS" | jget 'd["findings"]' | grep >/dev/null -F "\"$1\"" || fail "findings lack $1 (rc=$RC): $ERR"; }
no_id() { printf '%s' "$JS" | jget 'd["findings"]' | grep >/dev/null -F "\"$1\"" && fail "findings carry $1 (rc=$RC): $ERR"; return 0; }
# has_fail <id> <substring...>: one FAIL <id> line carrying every substring
has_fail() { local id=$1; shift
  python3 - "$ERR" "$id" "$@" <<'PY' || fail "no FAIL $id line carrying [$*]: $ERR"
import sys
err, fid, subs = sys.argv[1], sys.argv[2], sys.argv[3:]
ok = any(l.startswith(f"FAIL {fid}: ") and all(s in l for s in subs) for l in err.split("\n"))
sys.exit(0 if ok else 1)
PY
}
# jtrue '<python expression on d>' [message]: the head JSON satisfies the expression
jtrue() { printf '%s' "$JS" | python3 -c 'import sys,json; d=json.load(sys.stdin); sys.exit(0 if eval(sys.argv[1]) else 1)' "$1" \
  || fail "${2:-JSON check} failed: $1: $(printf '%s' "$JS" | jget 'd.get("mission")') findings=$(printf '%s' "$JS" | jget 'd["findings"]')"; }
# state <tokens>: the entry's State: line
state() { setline State "State: $*"; }
# vline <rel> <python statement on L (list of lines)>: edit a text file's lines in the copy
vedit() { python3 - "$H/$1" "$2" <<'PY'
import sys
p, stmt = sys.argv[1:]
L = open(p, encoding="utf-8").read().split("\n"); exec(stmt, {"L": L}); open(p, "w", encoding="utf-8").write("\n".join(L))
PY
}
# capture <result rel> <python statement on L (list of result text lines)>: edit a result= capture
capture() { python3 - "$H/$1" "$2" <<'PY'
import sys, json
p, stmt = sys.argv[1:]
d = json.load(open(p)); L = d["result"].split("\n"); exec(stmt, {"L": L}); d["result"] = "\n".join(L)
open(p, "w").write(json.dumps(d) + "\n")
PY
}
# resign <review dir rel>: rewrite the capture's findings= line to the sidecar's current sha256
resign() { local h; h=$(sha256sum "$H/$1/verdict.txt.findings.jsonl" | cut -d' ' -f1)
  capture "$1/result.json" "L[:] = [('findings=$h' if l.startswith('findings=') else l) for l in L]"; }
# side <review dir rel> <python statement on R (list of row dicts)>: edit a findings sidecar
side() { python3 - "$H/$1/verdict.txt.findings.jsonl" "$2" <<'PY'
import sys, json
p, stmt = sys.argv[1:]
R = [json.loads(l) for l in open(p).read().splitlines() if l.strip()]; exec(stmt, {"R": R})
open(p, "w").write("".join(json.dumps(r) + "\n" for r in R))
PY
}
