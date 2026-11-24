#!/usr/bin/env bash
# Regression test for review 4323f3ad finding F1 (the reviewer's counterexample, a1296-lint-verdict-correction-review-01
# work/mytests/cm_counterexample.sh, output out/f3-cm-counterexample.txt; adapted here to the repo's paths, logic unchanged):
# a NON-correction review session X (a real re-review of a reverted freeze m3, m0's bytes and so m0's scope_id, launched after m2's
# review, its REJECT verdicts never listed) must not escape the control-mutant newest-freeze rule when the note's author writes an
# identity verdict "correction" of cm0.txt naming X as corrected_by. No decisions row is written or changed for the escape.
#   CX0  no correction file:            base and head refuse, control-mutants-missing, unread [m0]
#   CX1  identity correction naming X:  base and head refuse, control-mutants-missing, unread [m0]; head also refuses the
#                                       correction as review-correction-noop and does not read it
# Known-bad control: the 9325ded lint (D5) reads CX1 clean (rc 0, unread []), the escape the reviewer showed.
set -uo pipefail
# shellcheck source=tests/drrec_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/fh" "$T/cwd"
DFX="$here/fixtures/datr/dfx.py"
X=dddddddd-0000-4000-8000-0000000000x1
build() {  # build <dir> <with-correction 0|1>
  python3 -I "$DFX" cm-freezes-in-launch-order-none-unread "$1" >/dev/null || fail "dfx build failed"
  local h=$1/home
  cp -r "$h/notes/snapshots/m0" "$h/notes/snapshots/m3"                 # the author reverts to m0's bytes: a NEWER freeze, same scope_id
  python3 - "$1/decisions.jsonl" "$X" <<'PY'
import sys, json
p, x = sys.argv[1:]
rows = [json.loads(l) for l in open(p) if l.strip()]
m0 = [r for r in rows if r.get("decision") == "launch" and r.get("role") == "review" and str(r.get("scope","")).endswith("m0/m.sha256")][0]
open(p, "a").write(json.dumps(dict(m0, session=x, ts="2026-11-15T03:00:00-08:00", resume=False, scope="notes/snapshots/m3/m.sha256")) + "\n")
PY
  printf 'foo REJECT fable\nbar REJECT fable\n' > "$h/notes/reviews/x-rereview.txt"     # X's real re-review, never listed
  if [ "$2" = 1 ]; then
    python3 - "$h" "$X" <<'PY'
import sys, json, hashlib, os
h, x = sys.argv[1:]
vf = "notes/reviews/cm0.txt"; raw = open(os.path.join(h, vf), "rb").read()
orig = [l for l in open(os.path.join(h, "notes/dream-log.md")) if l.startswith("Review: notes/reviews/cm0.txt")][0].split("reviewer-session=")[1].split()[0]
rows = [{"corrects": vf, "sha256": hashlib.sha256(raw).hexdigest(), "session": orig, "corrected_by": x}]
for ln in raw.decode().split("\n"):
    p = ln.split()
    if len(p) >= 3 and p[1] in ("APPROVE", "FIX", "REJECT"):
        rows.append({"line": " ".join(p), "slug": p[0], "verdict": p[1]})     # identity: corrects nothing
open(os.path.join(h, vf + ".verdicts.corrected-1.jsonl"), "w").write("".join(json.dumps(r) + "\n" for r in rows))
PY
  fi
}
run() {  # run <dir> <lint>: JSON in JS, exit in RC, stderr in ERRT
  JS=$(cd "$T/cwd" && env -u SKILL_ROUTING_DECISIONS -u ANALYSIS_WIKI_DIR HOME="$T/fh" SKILL_ROUTING_POLICY="$1/policy.json" GIT_CONFIG_NOSYSTEM=1 \
       bash "$2" "$1/home/notes/dream-log.md" --last --prd-dir "$1/home" --json --decisions "$1/decisions.jsonl" 2>"$T/err"); RC=$?
  ERRT=$(cat "$T/err"); case "$ERRT" in *Traceback*) fail "traceback: $ERRT";; esac
}
cm() { printf '%s' "$JS" | jget "$1"; }
git -C "$REPO" show 6ba4b87:skills/dream/scripts/dream-run-note-lint.sh > "$T/base.sh" 2>/dev/null || fail "git show 6ba4b87 failed"
git -C "$REPO" show 9325ded:skills/dream/scripts/dream-run-note-lint.sh > "$T/d5.sh" 2>/dev/null || fail "git show 9325ded failed"
build "$T/c0" 0; build "$T/c1" 1
[ "$(bash "$LINT" --scope-id "$T/c0/home/notes/snapshots/m0/m.sha256")" = "$(bash "$LINT" --scope-id "$T/c0/home/notes/snapshots/m3/m.sha256")" ] \
  || fail "m3 does not share m0's scope_id: the counterexample's premise does not hold"
UNREAD_M0='["notes/snapshots/m0/m.sha256"]'
for side in base head; do
  l=$T/base.sh; [ $side = head ] && l=$LINT
  run "$T/c0" "$l"
  [ "$RC" = 1 ] && [ "$(cm 'd["findings"]')" = '["control-mutants-missing"]' ] && [ "$(cm 'd["mission"]["control_mutants"]["unread"]')" = "$UNREAD_M0" ] \
    || fail "CX0 $side: rc=$RC findings=$(cm 'd["findings"]'): $ERRT"
  run "$T/c1" "$l"
  [ "$RC" = 1 ] || fail "CX1 $side: rc=$RC (the escape): $ERRT"
  [ "$(cm '"control-mutants-missing" in d["findings"]')" = true ] || fail "CX1 $side: no control-mutants-missing: $(cm 'd["findings"]')"
  [ "$(cm 'd["mission"]["control_mutants"]["unread"]')" = "$UNREAD_M0" ] || fail "CX1 $side: unread: $(cm 'd["mission"]["control_mutants"]')"
  [ "$(cm '[r.get("verdict_correction") for r in d["reviews"]]')" = '[null, null, null]' ] || fail "CX1 $side: a correction was read"
  printf '%s\n' "$ERRT" | grep >/dev/null -F "its review session $X launched 2026-11-15T03:00:00-08:00, after every review of the last listed manifest" \
    || fail "CX1 $side: the FAIL line does not name X: $ERRT"
done
[ "$(cm 'sorted(d["findings"])')" = '["control-mutants-missing", "review-correction-noop"]' ] || fail "CX1 head: findings $(cm 'd["findings"]')"
run "$T/c1" "$T/d5.sh"
[ "$RC" = 0 ] && [ "$(cm 'd["mission"]["control_mutants"]["unread"]')" = '[]' ] \
  || fail "known-bad control: the 9325ded lint no longer reads CX1 clean (rc=$RC): the test does not discriminate"
pass "review 4323f3ad F1 counterexample: a re-review X of reverted m0 bytes stays a review launch that makes m0 the newer freeze at base and head, with or without an identity 'correction' naming X (head refuses it as review-correction-noop); the 9325ded lint (D5) let X escape"
