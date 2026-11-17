#!/usr/bin/env bash
# Known-bad on unparseable or non-string row fields (G4 never raises, G6.5, G6.6): KB15
# J's row ts absent; J's ts unparseable; K's ts unparseable; another session's review
# launch row with ts absent; the same with a numeric ts; J's row scope numeric. Each:
# base == head bytes, exit 1, stale K/a, no traceback (pair checks every stderr).
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
for c in KB15-j-ts-absent KB15-j-ts-bad KB15-k-ts-bad KB15-other-ts-absent KB15-other-ts-numeric; do
  want "$c" || continue
  mut "$c"; kb "$c"
done
if want KB15-j-scope-numeric; then mut KB15-j-scope-numeric; kb KB15-j-scope-numeric review-scope-mismatch; fi
pass
