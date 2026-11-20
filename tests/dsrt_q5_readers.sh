#!/usr/bin/env bash
# Q5 (A1723 source request 6, ruled A): the lint's other readers of a review row's scope follow --scope-root too. For
# each, the A1113 shape (the row's scope absolute under another host's root, absent here; the file at the same relative
# path under the PRD home) lints with the map exactly as the relative original does (exit code, FAIL lines, JSON apart
# from scope_roots and reviews[].scope_read), and without the map it does not.
#   sweep (affected-consumer-unreviewed): the drfc bounded re-review listing b at its after digest. A mapped read binds
#     by content only: with the row's scope_id moved to an unlisted id, the mapped digests are not used and the finding
#     fires, while the relative original keeps today's reading (the literal file's digests count)
#   pins (reviews[].superseded): the drmr superseded variant, every review row mapped
#   trigger (the review snapshot an earlier entry binds, R1 of PRD-dream-analysis-trigger-record): the datr snapshot
#     case with s0 pinning foo's current bytes, so the entry is uncovered and its free-text skip stands; unmapped, the
#     snapshot is unreadable, the entry new material and the skip refused
set -uo pipefail
# shellcheck source=tests/drfc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drfc_lib.sh"
ABS="$here/fixtures/dsrt/absscope.py"
setup_fc
TP=$(cd "$T" && pwd -P)
XR="$TP/carbon/prds-clone"           # the recorded root: another host's PRD home, absent here
mapped() { JS=$(lint --json --scope-root "$XR=$H" 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_tb; }
strip() { printf '%s' "$1" | python3 -c 'import sys,json
d = json.load(sys.stdin); d.pop("scope_roots", None)
for r in d.get("reviews") or []:
    r.pop("scope_read", None)
print(json.dumps(d, sort_keys=True))'; }
fails() { printf '%s\n' "$1" | grep '^FAIL ' || true; }
keep() { O_RC=$RC; O_JS=$JS; O_ERR=$ERR; }
same() { # <case>: this run is the kept original's, apart from the two Q5 keys
  [ "$RC" = "$O_RC" ] || fail "$1: rc=$RC, the original's $O_RC: $ERR"
  [ "$(fails "$ERR")" = "$(fails "$O_ERR")" ] || fail "$1: FAIL lines differ: $ERR /// $O_ERR"
  [ "$(strip "$JS")" = "$(strip "$O_JS")" ] || fail "$1: JSON differs: $JS /// $O_JS"
  jtrue 'd["scope_roots"]["reads"] != []' "$1: no read recorded under the map"
}
# ---- sweep: the bounded re-review (drfc_ac05_consumers.sh's)
bounded() {
  mkdir -p "$H/notes/snapshots/bounded" "$H/notes/reviews/bounded"
  printf '%s  PRD-a.md\n%s  PRD-b.md\n' "$(digest built-prds/PRD-a.md)" "$1" > "$H/notes/snapshots/bounded/bounded.sha256"
  local bid; bid=$("$LINT" --scope-id "$H/notes/snapshots/bounded/bounded.sha256")
  printf 'b APPROVE %s\n' "$S_FB" > "$H/notes/reviews/bounded/verdict.txt"
  python3 - "$DEC" "$S_FB" "$bid" "$LOG" <<'PY2'
import sys, json
p, s, sid, log = sys.argv[1:]
R = [json.loads(l) for l in open(p).read().splitlines()]
R.append(dict(R[-1], ts="2026-11-18T12:30:00-08:00", session=s, scope="notes/snapshots/bounded/bounded.sha256", scope_id=sid))
open(p, "w").write("".join(json.dumps(r) + "\n" for r in R))
L = open(log).read().split("\n"); i = max(i for i, l in enumerate(L) if l.startswith("Review:"))
L.insert(i + 1, f"Review: notes/reviews/bounded/verdict.txt reviewer-session={s}")
L = [l.replace("b=reviewed:APPROVE b=eligible", "b=reviewed:APPROVE b=reviewed:APPROVE b=eligible") if l.startswith("State:") and k > i else l
     for k, l in enumerate(L)]
open(log, "w").write("\n".join(L))
PY2
}
setb() { use base; mansign "$AFT" "L[:] = [l for l in L if not l.endswith('  PRD-b.md')]"; bounded "$(digest built-prds/PRD-b.md)"; }
BSNAP=notes/snapshots/bounded/bounded.sha256
setb; run_fc; no_id affected-consumer-unreviewed; keep      # r2's own review-scope-mismatch (b left its manifest) is the original's too
setb; [ "$(python3 "$ABS" "$DEC" "$XR" "$S_FB")" = 1 ] || fail "sweep: absscope rewrote other than one row"
run_fc; has_fail review-scope-mismatch "$XR/$BSNAP" unreadable; has_fail affected-consumer-unreviewed "PRD-a.md" "PRD-b.md" "E1"
mapped; same sweep
jtrue 'd["scope_roots"]["reads"] == [{"scope": "'"$XR/$BSNAP"'", "read": "'"$(cd "$H" && pwd -P)/$BSNAP"'", "root": "'"$XR"'", "session": "'"$S_FB"'"}]' "sweep: the read"
OTHER=$(printf 'an unlisted manifest\n' | sha256sum | cut -d' ' -f1)
moveid() { decedit "dict(r,scope_id='$OTHER') if r.get('session')=='$S_FB' and r.get('decision')=='launch' else r"; }
setb; moveid; run_fc
has_fail review-scope-mismatch "$BSNAP" "$OTHER"; no_id affected-consumer-unreviewed
setb; moveid; python3 "$ABS" "$DEC" "$XR" "$S_FB" > /dev/null; mapped
has_fail review-scope-mismatch "the row's scope $XR/$BSNAP" "$OTHER"; has_fail affected-consumer-unreviewed "PRD-a.md" "PRD-b.md" "E1"
# ---- pins: the drmr superseded variant (drmr_ac05_snapshot.sh's), with drmr's own fixture copy
use_mr() {
  rm -rf "${W:?}"; mkdir -p "$W"; cp -r "$MRFIX/home" "$W/home"; cp "$MRFIX/decisions.jsonl" "$DEC"
  if [ -d "$MRFIX/variants/$1/home" ]; then cp -r "$MRFIX/variants/$1/home/." "$W/home/" || fail "variant $1: copy failed"; fi
  cp "$MRFIX/variants/$1/decisions.jsonl" "$DEC" || fail "variant $1: decisions.jsonl copy failed"
}
use_mr superseded; run_mr; [ "$RC" = 0 ] || fail "pins: original rc=$RC $ERR"
jtrue '[x.get("superseded") for x in d["reviews"]][0] == [{"slug": "a", "by": "'"$S_M2"'"}]' "pins: the original names a superseded"
keep
use_mr superseded; n=$(python3 "$ABS" "$DEC" "$XR"); [ "$n" -ge 2 ] || fail "pins: absscope rewrote $n rows"
run_mr; has_fail review-scope-mismatch "$XR/" unreadable
jtrue 'not any(x.get("superseded") for x in d["reviews"])' "pins: unmapped, no pin is read"
mapped; same pins
# ---- trigger: the datr snapshot case, uncovered
D="$T/datr"
python3 "$here/fixtures/datr/dfx.py" ac02-snapshot-free-text "$D" || fail "trigger: the datr fixture did not build"
foo=$(for d in build-queue built-prds parked; do [ -f "$D/home/$d/PRD-foo.md" ] && echo "$D/home/$d/PRD-foo.md"; done | head -1)
[ -n "$foo" ] || fail "trigger: no PRD-foo.md in the datr home"
printf '%s  PRD-foo.md\n' "$(sha256sum < "$foo" | cut -d' ' -f1)" > "$D/home/notes/snapshots/s0/s0.sha256"
sid=$("$LINT" --scope-id "$D/home/notes/snapshots/s0/s0.sha256")
python3 - "$D/decisions.jsonl" "$sid" <<'PY' || fail "trigger: scope_id rewrite"
import sys, json
p, sid = sys.argv[1:]
R = [json.loads(l) for l in open(p).read().splitlines()]
n = 0
for r in R:
    if r.get("scope") == "notes/snapshots/s0/s0.sha256":
        r["scope_id"], n = sid, n + 1
open(p, "w").write("".join(json.dumps(r) + "\n" for r in R))
sys.exit(0 if n == 1 else 1)
PY
dl() { JS=$(env -u SKILL_ROUTING_DECISIONS -u ANALYSIS_WIKI_DIR HOME="$T/fakehome" SKILL_ROUTING_POLICY="$D/policy.json" GIT_CONFIG_NOSYSTEM=1 \
  "$LINT" "$D/home/notes/dream-log.md" --last --prd-dir "$D/home" --json --decisions "$D/decisions.jsonl" "$@" 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_tb; }
dl; [ "$RC" = 0 ] || fail "trigger: the uncovered original rc=$RC $ERR"
jtrue 'd["analysis"].get("covered") == "none"' "trigger: the original is uncovered"
keep
n=$(python3 "$ABS" "$D/decisions.jsonl" "$XR"); [ "$n" -ge 1 ] || fail "trigger: absscope rewrote no row"
dl; [ "$RC" = 1 ] || fail "trigger: unmapped rc=$RC $ERR"
jtrue 'd["findings"] == ["analysis-skip-refused"] and d["analysis"].get("covered") == "new-material"' "trigger: unmapped, new material"
dl --scope-root "$XR=$D/home"
H="$D/home" same trigger
pass "Q5 readers: sweep (mapped as the original; content-bound when the scope_id moves), pins (superseded as the original), trigger (uncovered as the original); each refuses without the map"
