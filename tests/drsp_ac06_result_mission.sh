#!/usr/bin/env bash
# Known-bad on the result and mission binding (G6.9, G6.10): KB13 J's Review line has no
# result=; KB14 J's result.json gives FIX for a while its file gives APPROVE
# (review-result-mismatch); KB19 J's file mission=FIX J / no mission= line / J's file
# mission=APPROVE J while its result.json says mission=FIX J. Each: base == head bytes,
# exit 1, stale K/a.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
if want KB13; then mut KB13; kb KB13; fi
if want KB14; then mut KB14; kb KB14 review-result-mismatch; fi
for c in KB19-file-fix KB19-file-none KB19-result-fix; do
  want "$c" || continue
  mut "$c"; kb "$c"
done
pass
