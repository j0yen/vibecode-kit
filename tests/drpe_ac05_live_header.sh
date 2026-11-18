#!/usr/bin/env bash
# AC5 (R1 held rule, the live-header arm) — on a bound last manifest (m2: r2 launched on it and listed,
# no new manifest frozen), an error that only the LIVE edges header raises is exit-setting, because R1
# holds an error on a bound manifest only "when it is also present in the bound manifest's own frozen
# copies": after the launch the live header gains a packet member, a prds member or an external contract
# that m2 does not list (mission-scope-incomplete "... of the live edges header"), or a contract path
# whose basename is a prds member's or another contract path's (mission-scope-mismatch "live edges
# header"); `--packet-only --pending`, governed, prints each as FAIL (never HELD) and exits 1. Control:
# the same bound note with the live header unchanged exits 0 with no finding, and the full lint on the
# note with the pending entry appended reports the same FAIL lines it always did (exit 1).
set -uo pipefail
# shellcheck source=tests/drpe_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drpe_lib.sh"
setup_pe
nohold() { jtrue '(lambda h: not h)([e for e in d["held_packet_errors"] if "live edges header" in e["detail"]])' "${CASE}: a live-header error held"
  case "$ERR" in *"HELD "*"live edges header"*) fail "${CASE}: a HELD line names the live edges header: $ERR";; esac; }
pe live-bound-none; pk; rc0
jtrue 'd["exit"] == 0 and not d["packet_errors"] and not d["held_packet_errors"] and not d["pending_errors"]' "live-bound-none: clean"
for k in packet:drpe-glossary.md:"packet member" prds:PRD-baz.md:"prds member" contract:hermes-contract.md:"external hermes contract copy"; do
  IFS=: read -r kind base what <<<"$k"
  pe "live-bound-$kind"; pk; rc1
  pfail mission-scope-incomplete "manifest $M2:" "lists no $base" "($what of the live edges header)"
  nohold
  jtrue 'd["exit"] == 1 and "mission-scope-incomplete" in d["findings"]' "live-bound-$kind: exit-setting"
  pe "live-bound-$kind"; full; rc1; has_fail mission-scope-incomplete "manifest $M2:" "lists no $base" "($what of the live edges header)"
done
pe live-bound-clash; pk; rc1
pfail mission-scope-mismatch "manifest $M2: live edges header: contract path contracts/PRD-foo.md and the member PRD-foo.md"; nohold
pe live-bound-dupbase; pk; rc1
pfail mission-scope-mismatch "manifest $M2: live edges header: contract paths contracts/a/hermes.md and contracts/b/hermes.md"; nohold
pass "bound last manifest: live-header packet/prds/contract completeness and contract-basename errors FAIL with exit 1 (none held); unchanged live header exits 0; full lint unchanged"
