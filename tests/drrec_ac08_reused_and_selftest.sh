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
# selftest: passes; real files unchanged (checksums of the real PRD home log and
# review log on this host, where present, before and after). The host's decisions log
# is shared: every launcher appends to it, so it may grow while the selftest runs
# (review r23c); it must only have been appended to, by no line of the selftest (its
# temp dirs are drrec-selftest-*, its HOME is under $T).
REALHOME=$(getent passwd "$(id -un)" | cut -d: -f6)
RDEC="$REALHOME/.local/state/skill-routing/decisions.jsonl"
snap() { for f in "$REALHOME/Documents/PRDs/notes/dream-log.md" "$REALHOME/.local/state/dream/review-log.jsonl"; do
  [ -e "$f" ] && sha256sum "$f" || echo "absent $f"; done; }
before=$(snap); if [ -e "$RDEC" ]; then cp "$RDEC" "$T/rdec.before"; else : > "$T/rdec.before"; fi
st=$("$LINT" --selftest 2>&1); rc=$?
after=$(snap)
[ "$rc" = 0 ] || fail "selftest rc=$rc: $(printf '%s\n' "$st" | grep -v '^PASS' | head -20)"
[ "$before" = "$after" ] || fail "real files changed: $before / $after"
why=$(python3 -I - "$T/rdec.before" "$RDEC" "$T" <<'PY'
import os, sys
b = open(sys.argv[1], "rb").read()
a = open(sys.argv[2], "rb").read() if os.path.exists(sys.argv[2]) else b""
if not a.startswith(b):
    print("rewritten, not appended to")
else:
    for ln in a[len(b):].decode("utf-8", "replace").splitlines():
        if "drrec-selftest-" in ln or sys.argv[3] in ln:
            print("an appended line is the selftest's: " + ln[:200])
            break
PY
)
[ -z "$why" ] || fail "real decisions log $RDEC: $why"
[ -z "$(ls -A "$HOME")" ] || fail "private HOME written: $(ls -A "$HOME")"
for id in line-missing route-grammar analysis-grammar review-grammar state-grammar analysis-page-missing \
  persisted-sha-missing review-file-missing review-verdict-mismatch route-provenance-mismatch \
  route-provenance-ambiguous route-ungoverned-on-governed-host task-none-governed-route \
  analysis-provenance-missing analysis-page-unbound task-none-ran review-self review-provenance-missing \
  review-result-mismatch adversarial-missing adversarial-slug-missing adversarial-family-missing adversarial-case-missing; do
  printf '%s\n' "$st" | grep >/dev/null "^PASS refuse:$id" || fail "selftest has no passing refusal fixture for $id"
done
printf '%s\n' "$st" | grep >/dev/null '^PASS pass:checked-' || fail "selftest has no passing result= (checked) fixture"
pass "$(printf '%s\n' "$st" | tail -1)"
