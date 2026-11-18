#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the drpe_* tests (PRD-dream-packet-errors-while-repairable). Reuses the drmx,
# drmr and drrec helpers. `pe <case>[@nolog]` builds one case of tests/fixtures/drpe/pfx.py into $W:
# the PRD home $H, its note $LOG (absent, empty or title-only for the first-run shapes), the private
# decisions log $DEC (absent for @nolog cases) and the pending entry $P, never appended to the note.
# pk runs `--last --packet-only --pending $P --json` (with --decisions when the case has a log) and
# sets RC, JS (stdout JSON) and ERR (the FAIL / HELD / PENDING text lines); full appends $P to a copy
# of the note as its last entry and runs the full lint on it, setting the same variables.
# shellcheck source=tests/drmx_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmx_lib.sh"
PEFIX="$here/fixtures/drpe"
PFX="$PEFIX/pfx.py"
PE_REP=drpe-mission.repairs.jsonl
PE_EB=drpe-mission.edges.jsonl
M1=notes/snapshots/m1/m1.sha256; M2=notes/snapshots/m2/m2.sha256; M3=notes/snapshots/m3/m3.sha256
M2R=notes/snapshots/m2r/m2r.sha256
PACKET_IDS="mission-grammar mission-edges-missing mission-scope-mismatch mission-scope-incomplete mission-withdrawn-bound edge-grammar edge-unexplained edge-unknown-unowned edge-node-unlisted mission-prd-unlisted repair-grammar mission-repairs-missing repair-duplicate repair-missing repair-class-mismatch sweep-missing repair-author-mismatch repair-hash-mismatch repair-scope-mismatch adversarial-missing adversarial-slug-missing adversarial-family-missing adversarial-case-missing"
setup_pe() { setup_mr; }
pe() { rm -rf "${W:?}"; python3 -I "$PFX" "$1" "$W" || fail "fixture $1 did not build"
  LOG="$W/home/notes/dream-log.md"; DEC="$W/decisions.jsonl"; H="$W/home"; P="$W/pending.md"; CASE=$1; }
decargs() { if [ -f "$DEC" ]; then printf '%s\n' --decisions "$DEC"; fi; }
pk() { local d; mapfile -t d < <(decargs)
  JS=$("$LINT" "$LOG" --last --packet-only --pending "$P" --prd-dir "$H" "${d[@]}" --json 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_tb; }
appended() { mkdir -p "$(dirname "$LOG")"; { if [ -s "$LOG" ]; then cat "$LOG"; echo; fi; cat "$P"; } > "$T/app.md"; cp "$T/app.md" "$LOG"; }
full() { local d; mapfile -t d < <(decargs); appended
  JS=$("$LINT" "$LOG" --last --prd-dir "$H" "${d[@]}" --json 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_tb; }
# line <prefix> <substring...>: one stderr line starting with <prefix> carries every substring
line() { local pre=$1; shift
  python3 - "$ERR" "$pre" "$@" <<'PY' || fail "${CASE}: no '$pre' line carrying [$*] (rc=$RC): $ERR"
import sys
err, pre, subs = sys.argv[1], sys.argv[2], sys.argv[3:]
sys.exit(0 if any(l.startswith(pre) and all(s in l for s in subs) for l in err.split("\n")) else 1)
PY
}
pfail() { local id=$1; shift; line "FAIL $id: " "$@"; }     # an exit-setting packet finding
pheld() { local id=$1; shift; line "HELD $id: " "$@"; }     # a held packet finding
ppend() { line "PENDING " "$@"; }                           # a pending-file exit (no finding id)
rc1() { [ "$RC" = 1 ] || fail "${CASE}: rc=$RC (want 1): $ERR"; }
rc0() { [ "$RC" = 0 ] || fail "${CASE}: rc=$RC (want 0): $ERR"; }
scope_of() { "$LINT" --scope-id "$H/$1"; }
