#!/usr/bin/env bash
# AC2 (R2, R3, R4) — an unbound manifest m2 that is row 1's `after` and defective by its header (a
# prds member it does not list), by its unlisted edges copy, by the omitted repairs file or by the row
# (an empty `sweep`: on finding row 1, and on an added amended row 2): `--packet-only --pending` on the
# defective pending entry exits 1 naming an id for m2 (or its row); the pending entry that carries
# `withdrawn=m2`, the replacement m2r and the rewritten row(s) exits 0, governed and with no decisions
# log, and its mission.withdrawn is exactly [{path m2, scope_id (m2's --scope-id), reason (the first id
# the defective run reported naming m2 or a row naming it), voided_rows (the rows naming m2)}]. With no
# decisions log a finding row's sweep has no finding to check (no chain review binds), so the defective
# finding row exits 0 there and its withdrawal's reason is none (R4); the amended row is checked on
# both hosts.
set -uo pipefail
# shellcheck source=tests/drpe_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drpe_lib.sh"
setup_pe
for k in header edges-unlisted repairs row amended; do
  vr="[1]"; [ "$k" = amended ] && vr="[1, 2]"
  for v in "" "@nolog"; do
    pe "wd0-$k$v"; pk
    if [ "$k$v" = row@nolog ]; then
      rc0; x=none
    else
      rc1
      x=$(printf '%s' "$JS" | python3 -c 'import sys,json,re; d=json.load(sys.stdin); print(next((e["id"] for e in d["packet_errors"] if "notes/snapshots/m2/m2.sha256" in e["detail"] or re.search(r"\brows? (1|2)\b", e["detail"])), ""))')
      [ -n "$x" ] || fail "wd0-$k$v: no packet error names m2 or a row naming it: $ERR"
    fi
    pe "wd1-$k$v"; pk; rc0
    sid=$(scope_of "$M2") || fail "wd1-$k$v: m2 does not canonicalize"
    jtrue "d['mission']['withdrawn'] == [{'path': '$M2', 'scope_id': '$sid', 'reason': '$x', 'voided_rows': $vr}]" "wd1-$k$v: mission.withdrawn"
    echo "ok $k$v reason=$x"
  done
done
pass "five defect kinds x (governed, no log): defective exit 1 (a finding row with no log: exit 0), withdrawn + replaced exit 0 with the computed record"
