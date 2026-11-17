#!/usr/bin/env bash
# Known-bad on activation and listing (G1, G2, G3, G6.3): KB5 activation off (no Mission:
# line; Mission: without scope=; two Mission: lines; an empty scope= item); KB7 J's
# manifest not in scope=; KB8 K's manifest not in scope= (PR #9's pin kept); KB9 J's row
# scope_id is another listed id, not its manifest's (review-scope-mismatch); KB10 one
# listed item unreadable, one malformed (rule inactive, no new finding id).
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
for c in KB5-no-mission KB5-no-scope KB5-two-mission KB5-empty-item KB7 KB8 KB10-unreadable KB10-malformed; do
  want "$c" || continue
  mut "$c"; kb "$c"
done
if want KB10-unreadable || want KB10-malformed; then
  for c in KB10-unreadable KB10-malformed; do
    [ -f "$T/r/$c.head.json.out" ] || continue
    [ "$(jget 'd["findings"]' < "$T/r/$c.head.json.out")" = '["review-snapshot-stale"]' ] || fail "$c: findings $(cat "$T/r/$c.head.json.out")"
  done
fi
if want KB9; then mut KB9; kb KB9 review-scope-mismatch; fi
pass
