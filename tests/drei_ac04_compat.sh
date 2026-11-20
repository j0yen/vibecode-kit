#!/usr/bin/env bash
# AC4 (R7) — a note without Mission: lints as the predecessor does. The predecessor is read
# at run time by `git show 373ff679:skills/dream/scripts/dream-run-note-lint.sh` (sha256
# acde611f…), never a checked-in expectation. Over every tests/fixtures/drrec/ note and the
# drei two-entry note stripped of its Mission: line (each entry by --entry, and --last):
# text stdout, stderr and exit are byte-identical; --json stderr and exit are identical and
# the JSON equals the predecessor's once `mission` and `provenance.mission` are deleted
# (findings, exit and every provenance label among it); --matrix and --scope-id outputs are
# byte-identical; --selftest holds every predecessor PASS line verbatim, no FAIL, exit 0,
# and every further PASS line is a new marked fixture (drei-/drmr-/drfc-/drsp-/datr-/dfcn-), at least
# one per new edge-map finding id, so the count is the predecessor's 70 plus the new ones.
set -uo pipefail
# shellcheck source=tests/drei_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drei_lib.sh"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/fakehome"; export HOME="$T/fakehome"; unset SKILL_ROUTING_DECISIONS
OLD="$T/pred-lint.sh"
git -C "$REPO" show "$PRED_SHA:skills/dream/scripts/dream-run-note-lint.sh" > "$OLD" 2>"$T/git.err" \
  || fail "predecessor lint not readable by git show $PRED_SHA: $(cat "$T/git.err")"
[ "$(sha256sum "$OLD" | cut -d' ' -f1)" = "$PRED_LINT_SHA" ] || fail "predecessor lint sha256 differs from $PRED_LINT_SHA"
chmod +x "$OLD"
ncase=0
# same <tag> <args...>: predecessor vs this lint, text and --json
same() {
  local tag=$1; shift
  bash "$OLD" "$@" >"$T/o.out" 2>"$T/o.err"; local ro=$?
  "$LINT" "$@" >"$T/n.out" 2>"$T/n.err"; local rn=$?
  case "$(cat "$T/n.err")" in *Traceback*) fail "$tag: traceback: $(cat "$T/n.err")";; esac
  [ "$ro" = "$rn" ] || fail "$tag: text exit old=$ro new=$rn"
  cmp -s "$T/o.out" "$T/n.out" || fail "$tag: text stdout differs: $(diff "$T/o.out" "$T/n.out" | head -5)"
  cmp -s "$T/o.err" "$T/n.err" || fail "$tag: text stderr differs: $(diff "$T/o.err" "$T/n.err" | head -5)"
  bash "$OLD" "$@" --json >"$T/o.out" 2>"$T/o.err"; ro=$?
  "$LINT" "$@" --json >"$T/n.out" 2>"$T/n.err"; rn=$?
  [ "$ro" = "$rn" ] || fail "$tag: json exit old=$ro new=$rn"
  cmp -s "$T/o.err" "$T/n.err" || fail "$tag: json stderr differs: $(diff "$T/o.err" "$T/n.err" | head -5)"
  if [ -s "$T/o.out" ] || [ -s "$T/n.out" ]; then
    python3 - "$T/o.out" "$T/n.out" <<'PY' || fail "$tag: JSON differs from the predecessor's: $(cat "$T/o.out") / $(cat "$T/n.out")"
import sys, json
o = json.load(open(sys.argv[1])); n = json.load(open(sys.argv[2]))
assert n.get("mission", "absent") is None, ("mission", n.get("mission", "absent"))
assert n["provenance"].get("mission") == "none", n["provenance"]
assert n["findings"] == o["findings"] and n["exit"] == o["exit"], (o["findings"], n["findings"])
for k, v in o["provenance"].items():
    assert n["provenance"][k] == v, (k, o["provenance"], n["provenance"])
del n["mission"]; del n["provenance"]["mission"]
assert n == o, (o, n)
PY
  fi
  ncase=$((ncase+1))
}
# every tests/fixtures/drrec/ note, copied (byte-unchanged in the repo)
cp -r "$FIX" "$T/drrec"; export ANALYSIS_WIKI_DIR="$T/drrec/wiki"
same drrec-home "$T/drrec/home/notes/dream-log.md" --last --prd-dir "$T/drrec/home" --decisions "$T/drrec/decisions.jsonl"
same drrec-home-ungoverned "$T/drrec/home/notes/dream-log.md" --last --prd-dir "$T/drrec/home"
same drrec-verified "$T/drrec/verified/home/notes/dream-log.md" --last --prd-dir "$T/drrec/verified/home" --decisions "$T/drrec/verified/decisions.jsonl"
# the drei two-entry note stripped of Mission: (every entry)
cp -r "$EIFIX" "$T/drei"
grep -v '^Mission:' "$T/drei/home/notes/dream-log-two.md" > "$T/drei/home/notes/dream-log.md"
grep -q '^Mission:' "$T/drei/home/notes/dream-log.md" && fail "strip left a Mission: line"
for e in "$EI_TS" "$EI_TS2"; do
  same "drei-two-stripped-$e" "$T/drei/home/notes/dream-log.md" --entry "$e" --prd-dir "$T/drei/home" --decisions "$T/drei/decisions.jsonl"
done
same drei-two-stripped-last "$T/drei/home/notes/dream-log.md" --last --prd-dir "$T/drei/home" --decisions "$T/drei/decisions.jsonl"
# --matrix and --scope-id: byte for byte
mxsame() { bash "$OLD" "$@" >"$T/o.out" 2>"$T/o.err"; local ro=$?; "$LINT" "$@" >"$T/n.out" 2>"$T/n.err"; local rn=$?
  if ! { [ "$ro" = "$rn" ] && cmp -s "$T/o.out" "$T/n.out" && cmp -s "$T/o.err" "$T/n.err"; }; then
    fail "$* differs: rc $ro/$rn $(diff "$T/o.out" "$T/n.out" | head -3)"
  fi
  ncase=$((ncase+1)); }
for j in "" --json; do
  mxsame --matrix "$T/drrec/home/notes/reviews/2026-11-15T01:00:00-08:00-adversarial.md" --states foo=linted ${j:+"$j"}
  mxsame --matrix "$T/drrec/home/notes/reviews/2026-11-15T01:00:00-08:00-adversarial.md" --states foo=linted bar=linted ${j:+"$j"}
  mxsame --matrix "$T/drrec/verified/home/notes/reviews/2026-11-16T04:05:40-08:00-adversarial.md" --states rs-alpha=linted rs-beta=linted ${j:+"$j"}
done
for m in "$T"/drrec/review-scope/*.sha256 "$T/drrec/verified/home/notes/snapshots/happy.sha256" "$T/drei/home/$EI_M1"; do
  mxsame --scope-id "$m"
done
# --selftest: predecessor PASS lines verbatim, plus marked new fixtures only
bash "$OLD" --selftest >"$T/st.old" 2>&1 || fail "predecessor selftest failed: $(tail -3 "$T/st.old")"
"$LINT" --selftest >"$T/st.new" 2>&1; rc=$?
[ "$rc" = 0 ] || fail "selftest rc=$rc: $(grep -v '^PASS' "$T/st.new" | head -10)"
grep -q '^FAIL' "$T/st.new" && fail "selftest FAIL lines: $(grep '^FAIL' "$T/st.new" | head -5)"
npred=$(grep -c '^PASS ' "$T/st.old")
[ "$npred" = 70 ] || fail "predecessor PASS count $npred, want 70"
while IFS= read -r l; do grep -qxF -- "$l" "$T/st.new" || fail "predecessor PASS line missing: $l"; done < <(grep '^PASS ' "$T/st.old")
nnew=0
while IFS= read -r l; do
  grep -qxF -- "$l" "$T/st.old" && continue
  case "$l" in *drei-*|*drmr-*|*drfc-*|*drsp-*|*datr-*|*dfcn-*) nnew=$((nnew+1));; *) fail "unmarked new PASS line: $l";; esac
done < <(grep '^PASS ' "$T/st.new")
nhead=$(grep -c '^PASS ' "$T/st.new")
[ "$nhead" = $((npred + nnew)) ] || fail "PASS count $nhead != $npred + $nnew"
for id in mission-grammar mission-edges-missing edge-grammar edge-unexplained edge-unknown-unowned edge-node-unlisted mission-prd-unlisted; do
  grep -q "^PASS refuse:$id:drei-" "$T/st.new" || fail "selftest has no drei refusal fixture for $id"
done
grep -q '^PASS pass:drei-' "$T/st.new" || fail "selftest has no passing drei mission fixture"
pass "$ncase base/head comparisons equal; selftest $npred predecessor PASS + $nnew new"
