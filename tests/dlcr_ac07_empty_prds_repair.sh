#!/usr/bin/env bash
# Repair 8 (the PRD author's addenda 6 and 7; followon7/dream/requests/source-03415-lint-contract-repairs-addendum-6.md
# and -addendum-7.md) — a repaired row answering a finding whose prds list is empty (chain review 20's R20-F2 and R20-F3:
# a finding on the mission's edge map or its binding record that names no PRD and an external with no contract file)
# may name, besides the contract files of the externals the finding names, the mission's edges file or a basename the
# mission's edges header lists in packet. A finding naming a PRD keeps today's set. The findings sidecar's own rule
# (field prds: not a non-empty list, mission-finding-incomplete) is unchanged and stays on every empty-prds case.
# Positives, no repair-grammar: R20-F3's shape, F1's row (m1 -> m2) changes the edges file; R20-F2's shape, it changes
# the consumption record, a packet member. Negatives, repair-grammar: an empty-prds finding whose row changes neither
# (the record listed in packet and moved by an amended row); the record moved but no header lists it in packet; a
# finding naming PRD-bar.md whose row changes only the edges file, or only the record. In every case an amended row of
# the author's declares the rest of what moved m1 -> m2, so F1's row alone decides. A packet entry that is no string is
# edge-grammar, never a traceback. Over-strict control: the installed rule (43d5b39), which demands a contract file of
# the external, refuses both positives.
set -uo pipefail
# shellcheck source=tests/dlcr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/dlcr_lib.sh"
setup_mx
SC=notes/reviews/r1/verdict.txt.findings.jsonl; RP=notes/missions/drmx-mission.repairs.jsonl
NOP="(the contract the finding names, the edges file and its header's packet members: the finding names no PRD)"
for c in r8-edges r8-record; do
  cx "$c"; run_mr; findings_eq '["mission-finding-incomplete"]'; no_id repair-grammar
  has_fail mission-finding-incomplete "$SC: row 1: field prds"
done
cx r8-neither; run_mr; findings_eq '["mission-finding-incomplete", "repair-grammar"]'
has_fail repair-grammar "$RP: row 1: finding F1: changed names none of drmx-mission.edges.jsonl, m.consumption.jsonl $NOP"
cx r8-record-unlisted; run_mr; findings_eq '["mission-finding-incomplete", "repair-grammar"]'
has_fail repair-grammar "$RP: row 1: finding F1: changed names none of drmx-mission.edges.jsonl $NOP"
for c in r8-prd-edges r8-prd-record; do
  cx "$c"; run_mr; findings_eq '["repair-grammar"]'
  has_fail repair-grammar "$RP: row 1: finding F1: changed names none of PRD-bar.md (the PRDs and contract the finding names)"
done
cx r8-packet-malformed; run_mr; findings_eq '["edge-grammar", "mission-finding-incomplete"]'
has_fail edge-grammar "field packet: not a list of basenames"
for c in r8-edges r8-record; do
  today "$c"; findings_eq '["mission-finding-incomplete", "repair-grammar"]'
  has_fail repair-grammar "row 1: finding F1: changed names none of"
done
pass "a finding naming no PRD repairs the edges file (R20-F3) or a packet member (R20-F2); its row changing neither, or a moved record no header lists in packet, refused; a finding naming a PRD whose row changes only the edges file or only the record refused as today; a non-string packet entry is edge-grammar, no traceback; the installed rule refuses both positives"
