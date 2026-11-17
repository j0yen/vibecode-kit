#!/usr/bin/env bash
# Known-bad KB1-KB3 (G5, G6.4, G6.8): each a P1 mutation that keeps K's pin on a.
# KB1 J's last verdict for a is FIX; KB2 a's bytes change again after J's freeze (K and J
# both stale); KB3 J's file names b and c only. Each: base == head byte for byte (text and
# --json), exit 1, review-snapshot-stale naming K and slug a.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
if want KB1; then mut KB1; kb KB1; fi
if want KB2; then
  mut KB2; kb KB2
  printf '%s\n' "$OUT" | grep -qF "FAIL review-snapshot-stale: notes/reviews/j.txt: reviewer-session $S_J: slug a: " || fail "KB2: J's pin not stale: $OUT"
fi
if want KB3; then mut KB3; kb KB3; fi
pass
