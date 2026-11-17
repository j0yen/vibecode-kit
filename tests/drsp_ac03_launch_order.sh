#!/usr/bin/env bash
# Known-bad on line order against launch order (G5, G6.5, G6.6): KB4 J's row ts earlier
# than K's; KB11 a bound unlisted review X launched after J gives FIX on a (J(a) = X);
# KB12 an unlisted review launch row later than J whose session no Review line names
# (role review; role omitted); KB21 a listed review Y earlier than J in line order,
# launched after J, FIX on a. Each: base == head bytes, exit 1, stale K/a.
set -uo pipefail
# shellcheck source=tests/drsp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
for c in KB4 KB11 KB12-review KB12-no-role KB21; do
  want "$c" || continue
  mut "$c"; kb "$c"
done
pass "KB4 KB11 KB12 KB21"
