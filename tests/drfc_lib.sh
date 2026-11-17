#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the drfc_* tests (PRD-dream-failure-class-sweep). Reuses the drmr and
# drrec helpers (lint, lint_ungov, decedit, jget, fail, pass, findings_eq, has_id, no_id,
# has_fail, jtrue, vedit, capture, resign, side). `use <variant>` copies tests/fixtures/drfc
# (the passing repaired mission: entry 1 the FIX round, entry 2 the re-review) into a
# temporary directory with a private HOME and overlays tests/fixtures/drfc/variants/<variant>/,
# so each case is one named variant plus one mutation. The note has two entries; the
# st2/ml2/rv2del helpers edit the last one. DRREC_LINT runs the tests against another copy.
# shellcheck source=tests/drmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmr_lib.sh"
FCFIX="$here/fixtures/drfc"
S_FA0=eeeeeeee-0000-4000-8000-000000000001   # entry 1's Route session (author row)
S_FAX=eeeeeeee-0000-4000-8000-000000000002   # an earlier author: launch row, named by no Route: line
S_FA=eeeeeeee-0000-4000-8000-000000000003    # entry 2's Route session
S_F1=eeeeeeee-0000-4000-8000-000000000004    # chain review r1 (before)
S_F2=eeeeeeee-0000-4000-8000-000000000005    # chain review r2 (after)
S_F3=eeeeeeee-0000-4000-8000-000000000006    # chain review r3 (third, or a same-manifest re-review)
S_FB=eeeeeeee-0000-4000-8000-000000000007    # a bounded re-review (AC 5)
FC_E1_TS=2027-02-01T08:20:00-08:00
BEF=notes/snapshots/before/before.sha256
AFT=notes/snapshots/after/after.sha256
THR=notes/snapshots/third/third.sha256
R1D=notes/reviews/r1; R2D=notes/reviews/r2; R3D=notes/reviews/r3
FC_EB=drfc-mission.edges.jsonl
FC_RB=drfc-mission.repairs.jsonl
FC_RP=notes/missions/$FC_RB
FC_MXB=2027-02-01T08:30:00-08:00-adversarial.md
ST2_ALL="a=linted a=reviewed:FIX a=reviewed:APPROVE a=eligible b=linted b=reviewed:FIX b=reviewed:APPROVE b=eligible c=linted c=reviewed:FIX c=reviewed:APPROVE c=eligible d=linted d=reviewed:APPROVE d=reviewed:APPROVE d=eligible"
setup_fc() { setup_mr; }
# use <base|variant>: a fresh copy of the passing fixture, the named variant overlaid
use() {
  rm -rf "${W:?}"; mkdir -p "$W"; cp -r "$FCFIX/home" "$W/home"; cp "$FCFIX/decisions.jsonl" "$DEC"
  if [ "$1" != base ]; then
    [ -d "$FCFIX/variants/$1" ] || fail "no variant $1"
    cp -r "$FCFIX/variants/$1/home/." "$W/home/"; cp "$FCFIX/variants/$1/decisions.jsonl" "$DEC"
  fi
}
run_fc() { run_mr; }
run_fc_ungov() { run_mr_ungov; }
# last-entry editors: <Kind> lines of the note's last `## ` entry
_e2() { python3 - "$LOG" "$@" <<'PY'
import sys
p, op, k = sys.argv[1:4]; arg = sys.argv[4] if len(sys.argv) > 4 else ""
L = open(p, encoding="utf-8").read().split("\n")
s = max(i for i, l in enumerate(L) if l.startswith("## "))
out = L[:s]
for l in L[s:]:
    if l.startswith(k + ":"):
        if op == "set":
            out.append(arg); op = "done"
            continue
        if op == "done":
            continue
        if op == "del" and arg in l:
            continue
        if op == "app":
            out.append(l + arg)
            continue
    out.append(l)
open(p, "w", encoding="utf-8").write("\n".join(out))
PY
}
st2() { _e2 set State "State: $*"; }          # st2 <tokens>: the last entry's State: line
ml2() { _e2 set Mission "$1"; }               # ml2 <line>: the last entry's Mission: line
rv2del() { _e2 del Review "$1"; }             # rv2del <substring>: drop the last entry's Review: lines carrying it
# redit <python statement on R (list of repairs rows)>: edit the repairs file in the copy
redit() { python3 - "$H/$FC_RP" "$1" <<'PY'
import sys, json
p, stmt = sys.argv[1:]
R = [json.loads(l) for l in open(p).read().splitlines() if l.strip()]; exec(stmt, {"R": R})
open(p, "w").write("".join(json.dumps(r) + "\n" for r in R))
PY
  repin "$FC_RP"
}
# repin <live rel>: re-freeze a pinned file as if written before the last freeze: the last
# manifest of the last entry's scope= that lists its basename gets the live bytes (the frozen
# copy beside it, its digest line) and its decisions rows the new scope_id
repin() { local m b; b=$(basename "$1")
  m=$(python3 - "$LOG" "$H" "$b" <<'PY'
import sys, os
log, home, b = sys.argv[1:]
L = open(log).read().split("\n"); s = max(i for i, l in enumerate(L) if l.startswith("## "))
ml = [l for l in L[s:] if l.startswith("Mission:")]
sc = [t[len("scope="):].split(",") for t in (ml[0].split() if ml else []) if t.startswith("scope=")]
for m in reversed(sc[0] if sc else []):
    if any(l.endswith("  " + b) for l in open(os.path.join(home, m)).read().splitlines()):
        print(m)
        break
PY
)
  [ -n "$m" ] || return 0
  cp "$H/$1" "$H/$(dirname "$m")/$b"
  mansign "$m" "L[:] = [('$(digest "$1")  $b' if l.endswith('  $b') else l) for l in L]"
}
# mansign <manifest rel> <python statement on L (manifest lines)>: edit a manifest and re-record
# every decisions row whose scope names it with the lint's own --scope-id
mansign() { python3 - "$H/$1" "$2" <<'PY' || fail "mansign $1"
import sys
p, stmt = sys.argv[1:]
L = open(p).read().splitlines(); exec(stmt, {"L": L}); open(p, "w").write("".join(l + "\n" for l in L))
PY
  local id; id=$("$LINT" --scope-id "$H/$1") || fail "mansign $1: --scope-id: $id"
  decedit "dict(r, scope_id='$id') if r.get('scope') == '$1' else r"
}
# digest <rel>: sha256 of a file in the copy
digest() { sha256sum "$H/$1" | cut -d' ' -f1; }
# rep '<python expression on m (the mission.repairs object)>' [message]
rep() { jtrue "isinstance(d['mission'].get('repairs'), dict) and (lambda m: $1)(d['mission']['repairs'])" "${2:-repairs: $1}"; }
