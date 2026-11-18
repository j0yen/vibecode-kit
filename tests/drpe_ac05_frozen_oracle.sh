#!/usr/bin/env bash
# AC5 (R1 held rule) — the frozen-evaluation oracle. R1 holds an error on a bound manifest "only when it is
# also present in the bound manifest's own frozen copies (... which record the state when its review
# launched)". tests/fixtures/drpe/oracle.py rebuilds that state for B, the latest bound manifest whose launch
# state is its own: the entries recorded before B's latest launch, the evaluated entry as it stood then
# (scope= cut after B, the repairs= and withdrawn= in force, the reviews launched before it and the review
# launching on B, which has no finding yet), B's frozen packet files under the names in force then, and the
# decisions log up to that launch. It runs the full lint (not --packet-only) on that copy: every
# --packet-only error is HELD iff that evaluation reports the same defect (finding id and object), and every
# other error sets the exit; the states it cannot rebuild are classified by their own R1/R5 sentence. The
# oracle reads only the lint's command line, never its held logic.
# Corpus: every tests/fixtures/drpe/pfx.py case with --pending and with the pending entry appended (--last);
# every tests/fixtures/drmx/mfx.py case (--last); every checked-in compatibility note (--last); and, when
# DRPE_ORACLE_ROOTS names a file of `<label> <log> <home> <decisions>` lines, those roots (--last).
set -uo pipefail
# shellcheck source=tests/drpe_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drpe_lib.sh"
setup_pe
ORC="$PEFIX/oracle.py"
red=0
: > "$T/oracle.log"
# orc <label> <oracle args...>: one oracle run; prints ok or RED (with the disagreeing lines)
orc() { local label=$1 out rc; shift
  out=$(python3 -I "$ORC" "$LINT" "$@" --label "$label" 2>&1); rc=$?
  printf '%s\n' "$out" >> "$T/oracle.log"
  if [ "$rc" = 0 ]; then echo "ok  $label"; else echo "RED $label (rc=$rc)"; printf '%s\n' "$out" | grep -v '^  ok '; red=1; fi; }
for c in $(python3 -I "$PFX" --list); do
  pe "$c"; dl=$DEC; [ -f "$dl" ] || dl=-
  orc "pfx:$c:pending" "$LOG" "$H" "$dl" --pending "$P"
  appended; orc "pfx:$c:last" "$LOG" "$H" "$dl"
done
for c in $(python3 -I "$MFX" --list); do
  mx "$c"; orc "mfx:$c" "$LOG" "$H" "$DEC"
done
out=$(python3 -I "$ORC" --corpus "$here/fixtures" "$LINT" 2>&1); rc=$?
printf '%s\n' "$out" >> "$T/oracle.log"
if [ "$rc" = 0 ]; then echo "ok  checked-in notes ($(printf '%s\n' "$out" | grep -c '^[^ ]'))"
else echo "RED checked-in notes (rc=$rc)"; printf '%s\n' "$out" | grep -v '^  ok '; red=1; fi
if [ -n "${DRPE_ORACLE_ROOTS:-}" ]; then
  while read -r label log home dec; do
    [ -n "$label" ] && orc "root:$label" "$log" "$home" "$dec"
  done < "$DRPE_ORACLE_ROOTS"
fi
# every state the oracle classifies by its sentence instead of a reconstruction is exercised by some case
for why in "S3 mission-withdrawn-bound" "S3/S5 names a withdrawn manifest" "S4 mission-grammar" "S4 names no manifest" \
           "S5 names an unbound or pending manifest" "R3 names a bound manifest edited or deleted" \
           "S2/R-5 the repairs copy beside B is listed but absent or differs" \
           "S2 a row of the current repairs file, renamed since B's launch" \
           "R-1 no readable frozen header: a need no header supplies" \
           "R-1 no readable frozen header: a live-header defect" "present in the frozen evaluation" \
           "absent from the frozen evaluation"; do
  grep -qF "($why" "$T/oracle.log" || { echo "RED scope: no case reaches '$why'"; red=1; }
done
[ "$red" = 0 ] || fail "frozen-evaluation oracle: RED above"
pass "frozen-evaluation oracle: every --packet-only error over the pfx cases (--pending and --last), the mfx cases and the checked-in notes is HELD exactly when B's launch-state reconstruction reports the same defect"
