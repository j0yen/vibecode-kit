#!/usr/bin/env bash
# Manual: request 01 (A1296 Increment-2, e9d18227) positive on the real case, on a COPY. Needs a read-only copy of the ryzen7 inputs
# and a host where an unprivileged user and mount namespace can be created (unshare -rm), because the decisions rows and the
# consumption record name absolute ryzen7 paths: the copy is shown at its original path inside a private namespace; nothing outside it
# is written.
#   DRVC_REAL_FIXTURE=<dir holding work/dream-PRDs/, dream-run-4/dream-log-with-draft.md and decisions.jsonl (ryzen7
#                     ~/.local/state/skill-routing/decisions.jsonl)>  bash tests/manual/drvc_real_case.sh [<out dir for the logs>]
# Checks the request's input digests, then lints the draft entry (--last --json --prd-dir <home> --decisions <copy>):
#   A  base lint (6ba4b87), inputs as delivered: the nine FAILs of the request (8 historical + mission-approval-blocked on E4)
#   B  this lint, inputs as delivered (no correction): the same nine FAIL lines, byte for byte
#   C  this lint, a correction of r1 by a fresh session (a STAND-IN launch row, marked synthetic, launched after r4's review; the
#      real one comes from the governed launcher) and the draft's State: line unchanged: the 8 historical FAILs are gone; the four
#      full slugs now carry r1's FIX in their files sequence and the draft's State: tokens (written around the r1 defect) omit it
#   D  as C with the draft's State: line carrying r1's corrected verdicts (reviewed:FIX first for each of the four slugs): exactly
#      one FAIL, mission-approval-blocked on E4, E4 still unknown in the edges file
#   E  as D with the correction changing one verdict word: refused (review-correction-verdict-changed), the 8 historical FAILs back
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$here/.." && pwd)"
LINT="${DRREC_LINT:-$REPO/skills/dream/scripts/dream-run-note-lint.sh}"
FX="${DRVC_REAL_FIXTURE:?set DRVC_REAL_FIXTURE}"
OUTD="${1:-$(mktemp -d)}"; mkdir -p "$OUTD"
fail() { echo "FAIL $(basename "$0"): $*"; exit 1; }
ORIG=/home/jsy/wintermute-operations/wintermute-parallel-20261123/backlog-bindings
R1=notes/reviews/dream-increment2-backlog-bindings-verdicts-r1-20261123.md
S_R1=0d599323-1a54-4d23-babb-7c5694a9197a
S_STANDIN=5717d1e0-0000-4000-8000-0000000000c1          # synthetic stand-in for the fresh correction session
command -v unshare >/dev/null || fail "unshare is required"
( cd "$FX" && sha256sum -c --quiet ) <<EOF || fail "the fixture is not the request's inputs"
521a8e1dab970c5bde01b1901f5a6fc3578ddf660d7e2c1d0021ea3d65226438  dream-run-4/dream-log-with-draft.md
fac815ad386a70fefb7891f43d2919cc5f65f7aadea13245c337fb7f4c14094a  work/dream-PRDs/$R1
50882ee0db5b3d30d73d10996084f0286a1a6ad1cdd7dcf2aa996b6fe4d34d19  work/dream-PRDs/notes/snapshots/20261123-increment2-backlog-bindings-r1/manifest.sha256
EOF
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
git -C "$REPO" show 6ba4b87:skills/dream/scripts/dream-run-note-lint.sh > "$T/base.sh" || fail "git show 6ba4b87 failed"
cp "$LINT" "$T/head.sh"
# variant <name>: a fresh copy of the inputs in $T/<name>/ (work/, dream-run-4/, decisions.jsonl)
variant() { rm -rf "${T:?}/$1"; mkdir -p "$T/$1"; cp -a "$FX/work" "$FX/dream-run-4" "$T/$1/"; cp "$FX/decisions.jsonl" "$T/$1/"; }
# standin_row <name>: append the stand-in fresh session's launch row: r1's review row (role review, r1's scope and scope_id) with the
# stand-in session, resume false and a ts one minute after the latest launch row of the Task, reasons marked synthetic
standin_row() { python3 -I - "$T/$1/decisions.jsonl" "$S_R1" "$S_STANDIN" <<'PY'
import sys, json, datetime
p, orig, sess = sys.argv[1:]
rows = [json.loads(l) for l in open(p).read().splitlines() if l.strip()]
base = [r for r in rows if r.get("session") == orig and r.get("decision") == "launch" and r.get("role") == "review"][-1]
ts = max(datetime.datetime.fromisoformat(r["ts"]) for r in rows if r.get("task_id") == base["task_id"] and r.get("ts"))
r = dict(base, session=sess, resume=False, ts=(ts + datetime.timedelta(minutes=1)).isoformat(),
         reasons="SYNTHETIC stand-in for a governed fresh review launch (tests/manual/drvc_real_case.sh); not a launcher row")
open(p, "a").write(json.dumps(r) + "\n")
PY
}
# correction <name> [<python expr on rows>]: write r1's verdict correction (header, then one row per r1 verdict line in order)
correction() { python3 -I - "$T/$1/work/dream-PRDs" "$R1" "$S_R1" "$S_STANDIN" "${2:-rows}" <<'PY'
import sys, json, hashlib, os
home, vf, orig, fresh, expr = sys.argv[1:]
raw = open(os.path.join(home, vf), "rb").read()
rows = [{"corrects": vf, "sha256": hashlib.sha256(raw).hexdigest(), "session": orig, "corrected_by": fresh}]
for ln in raw.decode().split("\n"):
    p = ln.split()
    if len(p) >= 3 and p[1] in ("APPROVE", "FIX", "REJECT") and p[2] == orig:
        rows.append({"line": " ".join(p), "slug": "swarm-decide-wintermute-" + p[0], "verdict": p[1]})
assert len(rows) == 5, rows
rows = eval(expr, {"rows": rows, "dict": dict})
open(os.path.join(home, vf + ".verdicts.corrected-1.jsonl"), "w").write("".join(json.dumps(x) + "\n" for x in rows))
PY
}
# state_with_r1 <name>: the draft entry's State: line with reviewed:FIX (r1) placed first among each of the four slugs' reviewed tokens
state_with_r1() { python3 -I - "$T/$1/dream-run-4/dream-log-with-draft.md" <<'PY'
import sys
p = sys.argv[1]
lines = open(p).read().split("\n")
i = max(k for k, l in enumerate(lines) if l.startswith("State: "))
out = []
for tok in lines[i][len("State: "):].split():
    out.append(tok)
    s, v = tok.split("=", 1)
    if v == "linted" and s.startswith("swarm-decide-wintermute-"):
        out.append(s + "=reviewed:FIX")
lines[i] = "State: " + " ".join(out)
open(p, "w").write("\n".join(lines))
PY
}
# lintns <name> <lint>: the request's command inside a private namespace showing $T/<name> at $ORIG
lintns() {
  unshare --user --map-root-user --mount bash -s "$T/$1" "$2" "$ORIG" "$OUTD/$1.$(basename "$2" .sh)" <<'SH'
set -euo pipefail
V=$1; L=$2; ORIG=$3; O=$4
A=$ORIG; while [ ! -e "$A" ]; do A=$(dirname "$A"); done
if [ "$A" != "$ORIG" ]; then        # re-expose the deepest existing ancestor's entries over a tmpfs, then add the missing path
  S=$(mktemp -d -p /tmp); case "$S/" in "$A"/*) echo "staging $S lies under $A" >&2; exit 3;; esac
  mount --bind "$A" "$S"; mount -t tmpfs tmpfs "$A"
  for e in "$S"/* "$S"/.[!.]*; do [ -e "$e" ] || [ -L "$e" ] || continue; b=$(basename "$e")
    if [ -L "$e" ]; then ln -s "$(readlink "$e")" "$A/$b"; elif [ -d "$e" ]; then mkdir "$A/$b"; mount --bind "$e" "$A/$b"
    else touch "$A/$b"; mount --bind "$e" "$A/$b"; fi
  done
  mkdir -p "$ORIG"
fi
mkdir -p "$ORIG/work" "$ORIG/dream-run-4"
mount --bind "$V/work" "$ORIG/work"; mount --bind "$V/dream-run-4" "$ORIG/dream-run-4"
cd "$ORIG/work/dream-PRDs"
set +e
bash "$L" --last --json --prd-dir "$PWD" --decisions "$V/decisions.jsonl" "$ORIG/dream-run-4/dream-log-with-draft.md" > "$O.json" 2> "$O.err"
echo $? > "$O.rc"
SH
  RC=$(cat "$OUTD/$1.$(basename "$2" .sh).rc"); ERRT=$(cat "$OUTD/$1.$(basename "$2" .sh).err")
}
NINE="$T/nine.txt"
cat > "$NINE" <<EOF
FAIL review-scope-mismatch: $R1: reviewer-session $S_R1: slug backlog-coverage-view: PRD-backlog-coverage-view.md is not among the basenames of scope $ORIG/work/dream-PRDs/notes/snapshots/20261123-increment2-backlog-bindings-r1/manifest.sha256
FAIL review-scope-mismatch: $R1: reviewer-session $S_R1: slug binding-adoption: PRD-binding-adoption.md is not among the basenames of scope $ORIG/work/dream-PRDs/notes/snapshots/20261123-increment2-backlog-bindings-r1/manifest.sha256
FAIL review-scope-mismatch: $R1: reviewer-session $S_R1: slug dependency-milestones: PRD-dependency-milestones.md is not among the basenames of scope $ORIG/work/dream-PRDs/notes/snapshots/20261123-increment2-backlog-bindings-r1/manifest.sha256
FAIL review-scope-mismatch: $R1: reviewer-session $S_R1: slug grade-correction-adapter: PRD-grade-correction-adapter.md is not among the basenames of scope $ORIG/work/dream-PRDs/notes/snapshots/20261123-increment2-backlog-bindings-r1/manifest.sha256
FAIL review-verdict-mismatch: slug=backlog-coverage-view files=FIX state=absent
FAIL review-verdict-mismatch: slug=binding-adoption files=FIX state=absent
FAIL review-verdict-mismatch: slug=dependency-milestones files=FIX state=absent
FAIL review-verdict-mismatch: slug=grade-correction-adapter files=FIX state=absent
FAIL mission-approval-blocked: mission=APPROVE beside unknown edge(s) E4 of notes/missions/wintermute-increment2-backlog-bindings.edges.jsonl
EOF
E4='FAIL mission-approval-blocked: mission=APPROVE beside unknown edge(s) E4 of notes/missions/wintermute-increment2-backlog-bindings.edges.jsonl'
variant A; lintns A "$T/base.sh"
[ "$RC" = 1 ] && [ "$ERRT" = "$(cat "$NINE")" ] || fail "A (base, as delivered): rc=$RC, not the nine FAIL lines: $ERRT"
echo "A base as delivered: rc=$RC, the request's nine FAIL lines"
variant B; lintns B "$T/head.sh"
[ "$RC" = 1 ] && [ "$ERRT" = "$(cat "$NINE")" ] || fail "B (head, as delivered): rc=$RC, not the nine FAIL lines: $ERRT"
echo "B head as delivered: rc=$RC, the same nine FAIL lines"
variant C; standin_row C; correction C; lintns C "$T/head.sh"
[ "$RC" = 1 ] || fail "C: rc=$RC: $ERRT"
grep -F -x -f <(head -8 "$NINE") <<<"$ERRT" >/dev/null && fail "C: a historical FAIL line stands: $ERRT"
[ "$(grep -c '^FAIL ' <<<"$ERRT")" = 5 ] || fail "C: want five FAIL lines: $ERRT"
grep -x -F "$E4" <<<"$ERRT" >/dev/null || fail "C: E4 line changed: $ERRT"
for s in backlog-coverage-view binding-adoption dependency-milestones grade-correction-adapter; do
  grep -F "FAIL review-verdict-mismatch: slug=swarm-decide-wintermute-$s files=FIX " <<<"$ERRT" >/dev/null || fail "C: $s: $ERRT"
done
echo "C head, correction, State as delivered: rc=$RC; the 8 historical FAILs gone; r1's FIX now in the four full slugs' files sequence, which the draft's State omits (4 review-verdict-mismatch); E4 unchanged"
variant D; standin_row D; correction D; state_with_r1 D
mkdir -p "$OUTD/D.inputs"            # what D adds to the delivered inputs, kept for an independent verifier
cp "$T/D/work/dream-PRDs/$R1.verdicts.corrected-1.jsonl" "$OUTD/D.inputs/"
tail -1 "$T/D/decisions.jsonl" > "$OUTD/D.inputs/standin-launch-row.jsonl"
diff "$FX/dream-run-4/dream-log-with-draft.md" "$T/D/dream-run-4/dream-log-with-draft.md" > "$OUTD/D.inputs/dream-log-with-draft.state.diff"
lintns D "$T/head.sh"
[ "$RC" = 1 ] && [ "$ERRT" = "$E4" ] || fail "D: rc=$RC, not exactly the E4 FAIL: $ERRT"
python3 -I - "$T/D/work/dream-PRDs/notes/missions/wintermute-increment2-backlog-bindings.edges.jsonl" <<'PY' || fail "D: E4 is not unknown"
import sys, json
rows = [json.loads(l) for l in open(sys.argv[1]).read().splitlines()[1:] if l.strip()]
assert [r["status"] for r in rows if r.get("id") == "E4"] == ["unknown"]
PY
python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); vc=d["reviews"][0]["verdict_correction"]; assert d["findings"]==["mission-approval-blocked"], d["findings"]; assert vc["corrected_by"]==sys.argv[2] and [l["line"].split()[0] for l in vc["lines"]]==["backlog-coverage-view","binding-adoption","dependency-milestones","grade-correction-adapter"], vc' \
  "$OUTD/D.head.json" "$S_STANDIN" || fail "D: JSON"
echo "D head, correction, State with r1's FIX: rc=$RC, exactly one FAIL: mission-approval-blocked (E4 unknown); JSON keeps r1's original text"
variant E; standin_row E; correction E '[rows[0], dict(rows[1], verdict="APPROVE")] + rows[2:]'; state_with_r1 E; lintns E "$T/head.sh"
[ "$RC" = 1 ] || fail "E: rc=$RC: $ERRT"
grep '^FAIL review-correction-verdict-changed: ' <<<"$ERRT" >/dev/null || fail "E: not refused: $ERRT"
[ "$(grep -c -x -F -f <(head -4 "$NINE") <<<"$ERRT")" = 4 ] || fail "E: the historical scope FAILs are not back: $ERRT"
echo "E head, a refused correction: rc=$RC, review-correction-verdict-changed; the historical review-scope-mismatch lines back"
echo "PASS $(basename "$0"): logs in $OUTD"
