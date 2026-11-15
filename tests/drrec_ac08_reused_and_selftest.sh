#!/usr/bin/env bash
# AC8 — reused page under the gated wiki decisions/: wwhtbt gated, no row; a reused
# page elsewhere naming A1 and its wwhtbt row's session: boundary, and with that row
# removed analysis-provenance-missing; --selftest passes every fixture and changes
# no real file.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
setup; cp "$DEC" "$T/dec.orig"
A="adversarial=$MX uncovered=1"
setline Analysis "Analysis: wwhtbt=reused $T/wiki/decisions/2026-11-01-fixture-wwhtbt.md 5whys=skipped: not a failure seed $A"
js=$(lint --json 2>/dev/null); rc=$?
[ "$rc" = 0 ] && [ "$(printf '%s' "$js" | jget 'd["provenance"]["wwhtbt"]')" = '"gated"' ] || fail "gated: rc=$rc $js"
[ "$(printf '%s' "$js" | jget 'd["analysis"]["wwhtbt"]["kind"]')" = '"reused"' ] || fail "gated kind: $js"
printf '# earlier page\ntask: A1\nsession: %s\n' "$S_W" > "$H/visions/old-wwhtbt.md"
setline Analysis "Analysis: wwhtbt=reused visions/old-wwhtbt.md 5whys=skipped: not a failure seed $A"
js=$(lint --json 2>/dev/null); rc=$?
[ "$rc" = 0 ] && [ "$(printf '%s' "$js" | jget 'd["provenance"]["wwhtbt"]')" = '"boundary"' ] || fail "boundary A1: rc=$rc $js"
setline Analysis "Analysis: wwhtbt=reused visions/reused-page.md 5whys=skipped: not a failure seed $A"
js=$(lint --json 2>/dev/null); rc=$?
[ "$rc" = 0 ] && [ "$(printf '%s' "$js" | jget 'd["provenance"]["wwhtbt"]')" = '"boundary"' ] || fail "boundary A7: rc=$rc $js"
decedit 'None if r["task_id"]=="A7" else r'
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" analysis-provenance-missing
# selftest: passes; real files unchanged (checksums of the real PRD home log,
# review log and decisions log on this host, where present, before and after)
REALHOME=$(getent passwd "$(id -un)" | cut -d: -f6)
snap() { for f in "$REALHOME/Documents/PRDs/notes/dream-log.md" "$REALHOME/.local/state/dream/review-log.jsonl" \
  "$REALHOME/.local/state/skill-routing/decisions.jsonl"; do [ -e "$f" ] && sha256sum "$f" || echo "absent $f"; done; }
before=$(snap)
st=$("$LINT" --selftest 2>&1); rc=$?
after=$(snap)
[ "$rc" = 0 ] || fail "selftest rc=$rc: $(printf '%s\n' "$st" | grep -v '^PASS' | head -20)"
[ "$before" = "$after" ] || fail "real files changed: $before / $after"
[ -z "$(ls -A "$HOME")" ] || fail "private HOME written: $(ls -A "$HOME")"
for id in line-missing route-grammar analysis-grammar review-grammar state-grammar analysis-page-missing \
  persisted-sha-missing review-file-missing review-verdict-mismatch route-provenance-mismatch \
  route-provenance-ambiguous route-ungoverned-on-governed-host task-none-governed-route \
  analysis-provenance-missing analysis-page-unbound task-none-ran review-self review-provenance-missing \
  review-result-mismatch adversarial-missing adversarial-slug-missing adversarial-family-missing adversarial-case-missing; do
  printf '%s\n' "$st" | grep -q "^PASS refuse:$id" || fail "selftest has no passing refusal fixture for $id"
done
printf '%s\n' "$st" | grep -q '^PASS pass:checked-' || fail "selftest has no passing result= (checked) fixture"
pass "$(printf '%s\n' "$st" | tail -1)"
