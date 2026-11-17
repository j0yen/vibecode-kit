#!/usr/bin/env bash
# AC3 (R1, R5) — row 1's changed without b, or without the edges file, is repair-hash-mismatch
# naming it (changed but undeclared); a's digest moving into a third manifest with no row is
# repair-hash-mismatch naming a, cleared by an amended row naming a (r6 F37); the repairs file
# itself is exempt only for a pair whose rows it holds (review L13): the three variant with F4's
# (after, third) row removed and row 1 rewritten, re-frozen into third, is repair-hash-mismatch
# naming the repairs file between after and third (beside F4's repair-missing); changed [matrix]
# alone with the matrix moved and a, b byte-identical is repair-grammar naming F1, a and b
# (r8 F45), [b, matrix] passes; c added unmoved is repair-hash-mismatch naming c (claimed
# changed, digests equal); changed emptied while repaired, no before, or an unknown finding is
# repair-grammar; a declined row with a reason fires no repair-grammar and no
# repair-hash-mismatch (r2 F05), also with changed emptied (its dependents stay held, AC 6).
set -uo pipefail
# shellcheck source=tests/drfc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drfc_lib.sh"
setup_fc
use base; redit "R[0]['changed'] = ['PRD-a.md', '$FC_EB']"; run_fc; findings_eq '["repair-hash-mismatch"]'
has_fail repair-hash-mismatch "PRD-b.md" "changed but undeclared"
use base; redit "R[0]['changed'] = ['PRD-a.md', 'PRD-b.md']"; run_fc; findings_eq '["repair-hash-mismatch"]'
has_fail repair-hash-mismatch "$FC_EB" "changed but undeclared"
use amended; run_fc; [ "$RC" = 0 ] || fail "amended row: rc=$RC $ERR"
rep 'm["amended"] == [{"reason": "PRD a re-worded after review r2", "changed": ["PRD-a.md"], "before": "'"$AFT"'", "after": "'"$THR"'"}]' "amended listed"
use amended; redit "del R[2]"; run_fc; findings_eq '["repair-hash-mismatch"]'; has_fail repair-hash-mismatch "PRD-a.md" "changed but undeclared"
use three; redit "del R[2]; R[0]['sweep'] = list(reversed(R[0]['sweep']))"; run_fc
findings_eq '["repair-missing", "repair-hash-mismatch"]'; has_fail repair-missing "F4"
has_fail repair-hash-mismatch "$FC_RB: changed but undeclared between $AFT and $THR"
use matrix-only; run_fc; findings_eq '["repair-grammar"]'; has_fail repair-grammar "F1" "PRD-a.md" "PRD-b.md"
use matrix-b; run_fc; [ "$RC" = 0 ] || fail "[b, matrix]: rc=$RC $ERR"; findings_eq '[]'
use base; redit "R[0]['changed'].append('PRD-c.md')"; run_fc; findings_eq '["repair-hash-mismatch"]'
has_fail repair-hash-mismatch "PRD-c.md" "claimed changed, digests equal"
use base; redit "R[0]['changed'] = []"; run_fc; has_fail repair-grammar "F1" "changed"
use base; redit "del R[0]['before']"; run_fc; has_fail repair-grammar "before"
use base; redit "R[0]['finding'] = 'F98'"; run_fc; has_fail repair-grammar "F98"
use base; redit "R[0].update(disposition='declined', reason='the runner exists already')"; run_fc
no_id repair-grammar; no_id repair-hash-mismatch
use base; redit "R[0].update(disposition='declined', reason='the runner exists already', changed=[])"; run_fc; no_id repair-grammar
pass "undeclared b, edges; amended clears a; repairs file on a row-less pair; matrix alone; [b, matrix]; c claimed; grammar x3; declined"
