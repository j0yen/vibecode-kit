#!/usr/bin/env bash
# AC4 (R1) — drift between the pre-launch command and the full lint. For every fixture of this PRD
# (tests/fixtures/drpe/pfx.py, governed) and of its siblings (tests/fixtures/drmx/mfx.py, the drfc
# notes S3 reuses, and any later builder under tests/fixtures/*/ that names itself in DRIFT_BUILDERS
# below), `--packet-only --pending P` (exit-setting plus held findings) is compared with the full lint
# on the note with P appended as its last entry, filtered to the packet ids (a sibling note is split:
# its last entry is P, the rest the note). The two agree, (id, detail) for (id, detail), except the
# designed deltas of R1, which this test asserts each occur: in the pre-launch output only, a
# repair-missing for the review about to launch, an adversarial-missing for adversarial=skipped:
# beside the review about to launch, an adversarial-slug-missing for a prds member of the last
# manifest's frozen header, and the PENDING exits that carry no finding id (a missing pending line,
# the matrix-recency check on the pending Analysis: line, a slug a pending Review: file names outside
# the pending State:, a live packet file whose digest differs from the unbound last manifest's).
set -uo pipefail
# shellcheck source=tests/drpe_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drpe_lib.sh"
setup_pe
SEEN="$T/seen"; : > "$SEEN"
# split: the built note's last entry becomes $P, the note keeps the rest (removed when nothing is left)
split() { python3 - "$LOG" "$P" <<'PY' || fail "split $CASE"
import sys, os, re
log, pend = sys.argv[1:]
t = open(log, encoding="utf-8").read()
hs = [m.start() for m in re.finditer(r"^## \S+  /dream  vision-", t, re.M)]
open(pend, "w", encoding="utf-8").write(t[hs[-1]:])
rest = t[:hs[-1]]
if hs[:-1]:
    open(log, "w", encoding="utf-8").write(rest)
else:
    os.remove(log)
PY
}
compare() { python3 - "$PACKET_IDS" "$SEEN" "$CASE" "$1" "$2" "$3" <<'PY' || fail "$CASE: pre-launch and full lint disagree beyond the designed deltas (see above)"
import sys, json
pk_ids, seen, case, pj, perr, ferr = sys.argv[1].split(), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
d = json.loads(pj)
p = [(e["id"], e["detail"]) for e in d["packet_errors"] + d["held_packet_errors"]]
pend = d["pending_errors"]
f = []
for l in ferr.split("\n"):
    if l.startswith("FAIL "):
        fid, _, det = l[5:].partition(": ")
        if fid in pk_ids:
            f.append((fid, det))
ps, fs = set(p), set(f)
bad = []
out = open(seen, "a")
for fid, det in sorted(ps - fs):
    if fid == "repair-missing" and "the review about to launch" in det:
        out.write("delta:repair-missing\n")
    elif fid == "adversarial-missing" and "the review about to launch" in det:
        out.write("delta:adversarial-missing\n")
    elif fid == "adversarial-slug-missing" and "header prds member" in det:
        out.write("delta:header-slug\n")
    else:
        bad.append(f"pre-launch only: {fid}: {det}")
for fid, det in sorted(fs - ps):
    bad.append(f"full lint only: {fid}: {det}")
for e in pend:
    out.write(f"pending:{e['what']}\n")
if bad:
    print(f"{case}:\n  " + "\n  ".join(bad))
    sys.exit(1)
PY
}
run_case() { local pj perr ferr
  pk; pj=$JS; perr=$ERR
  [ -n "$pj" ] || fail "$CASE: no pre-launch JSON (rc=$RC): $ERR"
  full; ferr=$ERR
  compare "$pj" "$perr" "$ferr"
}
n=0
while IFS= read -r c; do pe "$c"; run_case; n=$((n+1)); done < <(python3 -I "$PFX" --list)
DRIFT_BUILDERS=("$MFX")
for extra in "$here"/fixtures/*/drift-builder.py; do [ -f "$extra" ] && DRIFT_BUILDERS+=("$extra"); done
for bld in "${DRIFT_BUILDERS[@]}"; do
  while IFS= read -r c; do
    rm -rf "${W:?}"; python3 -I "$bld" "$c" "$W" || fail "$bld $c did not build"
    LOG="$W/home/notes/dream-log.md"; DEC="$W/decisions.jsonl"; H="$W/home"; P="$W/pending.md"; CASE="$(basename "$(dirname "$bld")")/$c"
    split; run_case; n=$((n+1))
  done < <(python3 -I "$bld" --list)
done
for v in base three declined amended; do
  rm -rf "${W:?}"; mkdir -p "$W"; cp -r "$here/fixtures/drfc/home" "$W/home"; cp "$here/fixtures/drfc/decisions.jsonl" "$W/decisions.jsonl"
  if [ "$v" != base ]; then cp -r "$here/fixtures/drfc/variants/$v/home/." "$W/home/"; cp "$here/fixtures/drfc/variants/$v/decisions.jsonl" "$W/decisions.jsonl"; fi
  LOG="$W/home/notes/dream-log.md"; DEC="$W/decisions.jsonl"; H="$W/home"; P="$W/pending.md"; CASE="drfc/$v"
  split; run_case; n=$((n+1))
done
for k in delta:repair-missing delta:adversarial-missing delta:header-slug pending:line pending:slug pending:digest; do
  grep -qx "$k" "$SEEN" || fail "designed delta $k never occurred over the $n fixtures"
done
pass "$n fixtures: pre-launch equals the full lint on the appended note except the asserted designed deltas"
