#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the drsp_* tests (gate fix A1723 prerequisite: superseded
# chain-review APPROVE pins). Each test copies tests/fixtures/drsp (the P1 fixture: review
# K on manifest k APPROVEs a, a's bytes change, review J on manifest j re-APPROVEs a on the
# new bytes with result= and mission=APPROVE, J is the latest review launch, and the note
# carries `Mission: ... scope=k,j`) into a temporary directory with a private HOME and an
# explicit --decisions file, applies exactly one named mutation (`mut <name>`, the table
# in the Python below) and lints with the base lint (373ff679, read by `git show`) and the
# head lint, in text and --json mode, with identical arguments.
# Env: DRSP_LINT runs the head side against another copy (mutants); DRSP_CASES, when set,
# limits a test to the named cases (a mutant run of one control); unset runs every case.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$here/.." && pwd)"
LINT="${DRSP_LINT:-$REPO/skills/dream/scripts/dream-run-note-lint.sh}"
BASE_SHA=373ff679da9fbed12109fdb3da2a7a8fbd330748
FIX="$here/fixtures/drsp"
S_AUTH=cccccccc-0000-4000-8000-000000000001
S_K=cccccccc-0000-4000-8000-000000000002
S_J=cccccccc-0000-4000-8000-000000000003
S_X=cccccccc-0000-4000-8000-000000000004
S_U=cccccccc-0000-4000-8000-000000000005
S_Y=cccccccc-0000-4000-8000-000000000006
TS=2026-11-16T11:00:00-08:00
fail() { echo "FAIL $(basename "$0"): $*"; exit 1; }
pass() { echo "PASS $(basename "$0")${1:+: $1}"; exit 0; }
command -v python3 >/dev/null 2>&1 || fail "python3 is required (never a skip)"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required (never a skip)"
setup() {
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  mkdir -p "$T/fakehome" "$T/r"
  export HOME="$T/fakehome" ANALYSIS_WIKI_DIR="$T/wiki"
  unset SKILL_ROUTING_DECISIONS
  BASE_LINT="$T/base-lint.sh"
  git -C "$REPO" show "$BASE_SHA:skills/dream/scripts/dream-run-note-lint.sh" > "$BASE_LINT" 2>"$T/git.err" \
    || fail "cannot read the base lint at $BASE_SHA: $(cat "$T/git.err")"
  chmod +x "$BASE_LINT"
  W="$T/w"; reset
}
# reset: a fresh copy of the P1 fixture, made a bound mission under the three A1723 PRDs (the
# checked-in fixture stays byte-unchanged; the base lint ignores every addition):
# - edge-map R1 refuses a Mission: line without edges= (mission-grammar): the line gains
#   `edges=notes/missions/drsp-fixture.edges.jsonl`, an edge map over PRD-a/b/c written here;
# - chain-review R1 requires each scope= manifest to list its frozen edges copy and the
#   matrix: both are copied into k/ and j/ and listed, and K's and J's rows get the new
#   canonical scope_id; chain-review R3 requires one `mission=` line per chain review: K's
#   file and capture gain `mission=APPROVE <K>` (J's already carry theirs);
# - failure-class-sweep R1/R5 declare a's change between k and j: one `amended` row (author
#   S_AUTH, sweep [E1], the edges incident to a) in `repairs=notes/missions/drsp-fixture.repairs.jsonl`,
#   listed in j's manifest (R1: every manifest later than the row's `before`).
EDGES_REL=notes/missions/drsp-fixture.edges.jsonl
REPAIRS_REL=notes/missions/drsp-fixture.repairs.jsonl
reset() {
  rm -rf "$W"; mkdir -p "$W"; cp -r "$FIX/." "$W/"
  LOG="$W/home/notes/dream-log.md"; DEC="$W/decisions.jsonl"; H="$W/home"
  python3 - "$H" "$EDGES_REL" "$REPAIRS_REL" "$W/decisions.jsonl" <<'PY2' || fail "edge map for the drsp copy"
import sys, os, json, hashlib, shutil
H, rel, rrel, dec = sys.argv[1:]
f8 = lambda p, c, x: {"producer": p, "consumer": c, "command": x + " command", "trigger": x + " trigger",
                      "authority": x + " authority", "effect_id": x + " effect", "recovery_owner": x + " owner",
                      "postcondition": x + " postcondition"}
h = {"mission": "drsp-fixture", "outcome": "drsp outcome", "invariants": ["drsp invariant"],
     "prds": ["PRD-a.md", "PRD-b.md", "PRD-c.md"], "external": []}
es = [dict(id="E1", status="known", **f8("PRD-a.md", "PRD-b.md", "E1")), dict(id="E2", status="known", **f8("PRD-b.md", "PRD-c.md", "E2"))]
os.makedirs(os.path.join(H, os.path.dirname(rel)), exist_ok=True)
open(os.path.join(H, rel), "w").write("".join(json.dumps(x) + "\n" for x in [h] + es))
log = os.path.join(H, "notes", "dream-log.md")
L = open(log, encoding="utf-8").read().split("\n")
L = [l + " edges=" + rel + " repairs=" + rrel if l.startswith("Mission:") else l for l in L]
open(log, "w", encoding="utf-8").write("\n".join(L))
S_AUTH, S_K = "cccccccc-0000-4000-8000-000000000001", "cccccccc-0000-4000-8000-000000000002"
KM, JM = "notes/snapshots/k/snapshot.sha256", "notes/snapshots/j/snapshot.sha256"
row = {"finding": None, "class": None, "author_session": S_AUTH, "before": KM, "after": JM, "changed": ["PRD-a.md"],
       "sweep": ["E1"], "disposition": "amended", "reason": "PRD-a re-worded between review K and review J"}
open(os.path.join(H, rrel), "w").write(json.dumps(row) + "\n")
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
mx = os.path.join(H, "notes/reviews/2026-11-16T10:05:00-08:00-adversarial.md")
ids = {}
for m, extra in ((KM, []), (JM, [rrel])):
    d = os.path.dirname(os.path.join(H, m))
    with open(os.path.join(H, m), "a") as fh:
        for src in [os.path.join(H, rel), mx] + [os.path.join(H, x) for x in extra]:
            shutil.copyfile(src, os.path.join(d, os.path.basename(src)))
            fh.write(f"{sha(src)}  {os.path.basename(src)}\n")
    t = open(os.path.join(H, m), "rb").read()
    ids[m] = hashlib.sha256(b"".join(sorted(set(t.splitlines(True))))).hexdigest()
rows = [json.loads(l) for l in open(dec).read().splitlines()]
for r in rows:
    if r.get("scope") in ids:
        r["scope_id"] = ids[r["scope"]]
open(dec, "w").write("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows))
mk = "mission=APPROVE " + S_K
with open(os.path.join(H, "notes/reviews/k.txt"), "a") as fh:
    fh.write(mk + "\n")
kj = os.path.join(H, "notes/reviews/k.json"); r = json.load(open(kj)); r["result"] += "\n" + mk
open(kj, "w").write(json.dumps(r) + "\n")
PY2
}
# want <case>: run this case (DRSP_CASES unset, or the case is listed)
want() { [ -z "${DRSP_CASES:-}" ] && return 0; case " $DRSP_CASES " in *" $1 "*) return 0;; esac; return 1; }
# mut <name>: reset to P1, then apply exactly the one named mutation
mut() { reset; [ "$1" = P1 ] && return 0; python3 - "$W" "$1" <<'PY' || fail "mutation $1 failed"
import sys, os, json, hashlib
W, name = sys.argv[1], sys.argv[2]
H = os.path.join(W, "home"); LOG = os.path.join(H, "notes", "dream-log.md"); DEC = os.path.join(W, "decisions.jsonl")
S_AUTH, S_K, S_J, S_X, S_U, S_Y = ("cccccccc-0000-4000-8000-00000000000%d" % i for i in (1, 2, 3, 4, 5, 6))
KM, JM = "notes/snapshots/k/snapshot.sha256", "notes/snapshots/j/snapshot.sha256"
note = open(LOG, encoding="utf-8").read().split("\n")
rows = [json.loads(l) for l in open(DEC, encoding="utf-8").read().splitlines()]
def wr(rel, text):
    p = os.path.join(H, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text)
def rd(rel):
    return open(os.path.join(H, rel), encoding="utf-8").read()
def sha(rel):
    return hashlib.sha256(open(os.path.join(H, rel), "rb").read()).hexdigest()
def idx(prefix, n=0):
    return [i for i, l in enumerate(note) if l.startswith(prefix)][n]
def setline(prefix, new, n=0):
    note[idx(prefix, n)] = new
def state(*toks):
    setline("State:", "State: " + " ".join(toks))
def mission(scope):
    setline("Mission:", "Mission: drsp-fixture scope=" + scope + " edges=notes/missions/drsp-fixture.edges.jsonl"
            " repairs=notes/missions/drsp-fixture.repairs.jsonl")
def result(rel, session, text):
    wr(rel, json.dumps({"type": "result", "is_error": False, "session_id": session, "result": text}) + "\n")
def review(name, session, lines, res=True):
    wr(f"notes/reviews/{name}.txt", f"# review {name} (drsp mutation)\n" + "".join(l + "\n" for l in lines))
    if res:
        result(f"notes/reviews/{name}.json", session, f"Review {name} done.\n" + "\n".join(lines))
def rline(name, session, res=True):
    return f"Review: notes/reviews/{name}.txt reviewer-session={session}" + (f" result=notes/reviews/{name}.json" if res else "")
def J(**kw):
    for r in rows:
        if r["session"] == S_J:
            r.update(kw)
def row(ts, session, role="review", scope=JM, sid=None):
    return dict(rows[2], ts=ts, session=session, role=role, scope=scope,
                scope_id=rows[2]["scope_id"] if sid is None else sid)
def manifest(rel, extra, packet=()):
    # a reviewer manifest over the current a, b, c plus one extra file, so its id differs from k and j;
    # `packet` names further files frozen beside it (a listed manifest's edges copy, matrix, repairs)
    d = os.path.dirname(rel)
    wr(d + "/notes.md", extra)
    for f in packet:
        wr(d + "/" + os.path.basename(f), rd(f))
    wr(rel, "".join(f"{sha('built-prds/PRD-' + s + '.md')}  PRD-{s}.md\n" for s in "abc") + f"{sha(d + '/notes.md')}  notes.md\n"
       + "".join(f"{sha(f)}  {os.path.basename(f)}\n" for f in packet))
    lines = open(os.path.join(H, rel), "rb").read()[:-1].split(b"\n")
    return hashlib.sha256(b"".join(sorted({ln + b"\n" for ln in lines}))).hexdigest()   # basenames already
A_K, A_J = f"a APPROVE {S_K}", f"a APPROVE {S_J}"
MJ, MK = f"mission=APPROVE {S_J}", f"mission=APPROVE {S_K}"
SCOPE = f"{KM},{JM}"
m = name
if m == "P3":    # K also APPROVEs b, which is unchanged since K's manifest
    review("k", S_K, [A_K, f"b APPROVE {S_K}", MK]); state("a=linted", "a=reviewed:APPROVE", "a=linted", "a=reviewed:APPROVE", "b=reviewed:APPROVE")
elif m == "P4":  # K and J both APPROVE b on its unchanged bytes
    review("k", S_K, [A_K, f"b APPROVE {S_K}", MK]); review("j", S_J, [A_J, f"b APPROVE {S_J}", MJ])
    state("a=linted", "a=reviewed:APPROVE", "a=linted", "a=reviewed:APPROVE", "b=reviewed:APPROVE", "b=reviewed:APPROVE")
elif m == "P4-only-b":  # b is K's only APPROVE candidate (K names b, not a); K and J both APPROVE b
    review("k", S_K, [f"b APPROVE {S_K}", MK]); review("j", S_J, [A_J, f"b APPROVE {S_J}", MJ])
    state("a=linted", "a=reviewed:APPROVE", "b=reviewed:APPROVE", "b=reviewed:APPROVE")
elif m == "KB1":  # J's last verdict for a is FIX
    review("j", S_J, [f"a FIX {S_J}", MJ]); state("a=linted", "a=reviewed:APPROVE", "a=linted", "a=reviewed:FIX")
elif m == "KB1-eligible":  # KB1 with a reaching eligible (chain-review R6: a is held, per-PRD verdict FIX)
    review("j", S_J, [f"a FIX {S_J}", MJ]); state("a=linted", "a=reviewed:APPROVE", "a=linted", "a=reviewed:FIX", "a=eligible")
elif m == "KB2":  # a's bytes change again after J's freeze
    wr("built-prds/PRD-a.md", rd("built-prds/PRD-a.md") + "Edited again after review J.\n")
elif m == "KB3":  # J's file names b and c only
    review("j", S_J, [f"b APPROVE {S_J}", f"c APPROVE {S_J}", MJ])
    state("a=linted", "a=reviewed:APPROVE", "b=reviewed:APPROVE", "c=reviewed:APPROVE")
elif m == "KB4":  # J's row ts earlier than K's
    J(ts="2026-11-16T10:05:00-08:00")
elif m == "KB5-no-mission":
    del note[idx("Mission:")]
elif m == "KB5-no-scope":
    setline("Mission:", "Mission: drsp-fixture manifests=" + SCOPE)
elif m == "KB5-two-mission":
    note.insert(idx("Mission:") + 1, note[idx("Mission:")])
elif m == "KB5-empty-item":
    mission(f"{KM},,{JM}")
elif m == "KB6-author":  # J's latest row has role author
    J(role="author")
elif m == "KB6-absent":  # J's row has no role (legacy)
    for r in rows:
        if r["session"] == S_J:
            del r["role"]
elif m == "KB7":  # J's manifest omitted from scope=
    mission(KM)
elif m == "KB8":  # K's manifest omitted from scope=
    mission(JM)
elif m == "KB9":  # J's row scope_id is K's listed id, not what J's manifest canonicalizes to
    J(scope_id=rows[1]["scope_id"])
elif m == "KB10-unreadable":  # one listed item names no file
    mission(f"{SCOPE},notes/snapshots/missing/snapshot.sha256")
elif m == "KB10-malformed":  # one listed item is not a manifest
    wr("notes/snapshots/bad/snapshot.sha256", "not a manifest\n"); mission(f"{SCOPE},notes/snapshots/bad/snapshot.sha256")
elif m == "KB11":  # bound review X (unlisted manifest) launched after J, FIX on a
    sid = manifest("notes/snapshots/x/snapshot.sha256", "review X packet notes\n")
    rows.append(row("2026-11-16T10:50:00-08:00", S_X, scope="notes/snapshots/x/snapshot.sha256", sid=sid))
    review("x", S_X, [f"a FIX {S_X}"]); note.insert(idx("Review:", 1) + 1, rline("x", S_X))
    state("a=linted", "a=reviewed:APPROVE", "a=linted", "a=reviewed:APPROVE", "a=reviewed:FIX")
elif m == "KB12-review":  # an unlisted review launch row later than J, session named by no Review line
    rows.append(row("2026-11-16T10:50:00-08:00", S_U))
elif m == "KB12-eligible":  # KB12-review with a reaching eligible (chain-review R6: unlisted later review)
    rows.append(row("2026-11-16T10:50:00-08:00", S_U)); state("a=linted", "a=reviewed:APPROVE", "a=linted", "a=reviewed:APPROVE", "a=eligible")
elif m == "KB12-no-role":
    r = row("2026-11-16T10:50:00-08:00", S_U); del r["role"]; rows.append(r)
elif m == "KB13":  # J's Review line has no result=
    setline("Review:", rline("j", S_J, res=False), 1)
elif m == "KB14":  # J's result.json gives FIX for a, J's file APPROVE
    result("notes/reviews/j.json", S_J, f"Review j done.\na FIX {S_J}\n{MJ}")
elif m == "KB15-j-ts-absent":
    for r in rows:
        if r["session"] == S_J:
            del r["ts"]
elif m == "KB15-j-ts-bad":
    J(ts="not-a-timestamp")
elif m == "KB15-k-ts-bad":
    rows[1]["ts"] = "2026-11-16 ten past ten"
elif m == "KB15-other-ts-absent":
    r = row("x", S_U); del r["ts"]; rows.append(r)
elif m == "KB15-other-ts-numeric":
    rows.append(row(1789571400, S_U))
elif m == "KB15-j-scope-numeric":
    J(scope=5)
elif m == "KB16-route":  # J's Review line names the Route session
    setline("Review:", rline("j", S_AUTH), 1)
elif m == "KB16-none":
    setline("Review:", rline("j", "none"), 1)
elif m == "KB17":  # K and J one session on two Review lines
    setline("Review:", rline("j", S_K), 1)
elif m == "KB18":  # J's verdict file is missing
    os.remove(os.path.join(H, "notes/reviews/j.txt"))
elif m == "KB19-file-fix":  # J's file has mission=FIX J; its result keeps mission=APPROVE J
    wr("notes/reviews/j.txt", rd("notes/reviews/j.txt").replace(MJ, f"mission=FIX {S_J}"))
elif m == "KB19-file-none":  # J's file has no mission= line
    wr("notes/reviews/j.txt", rd("notes/reviews/j.txt").replace(MJ + "\n", ""))
elif m == "KB19-result-fix":  # J's file mission=APPROVE J, J's result.json mission=FIX J
    result("notes/reviews/j.json", S_J, f"Review j done.\n{A_J}\nmission=FIX {S_J}")
elif m == "KB20":  # an author launch row carries J's session (before J's review row: J stays bound)
    rows.insert(2, row("2026-11-16T10:20:00-08:00", S_J, role="author", scope="", sid=""))
elif m == "KB21":  # listed review Y before J in line order, launched after J, FIX on a
    sid = manifest("notes/snapshots/y/snapshot.sha256", "review Y packet notes\n",
                   ("notes/missions/drsp-fixture.edges.jsonl", "notes/reviews/2026-11-16T10:05:00-08:00-adversarial.md",
                    "notes/missions/drsp-fixture.repairs.jsonl"))
    rows.append(row("2026-11-16T10:50:00-08:00", S_Y, scope="notes/snapshots/y/snapshot.sha256", sid=sid))
    review("y", S_Y, [f"a FIX {S_Y}"]); note.insert(idx("Review:", 0) + 1, rline("y", S_Y))
    mission(f"{KM},notes/snapshots/y/snapshot.sha256,{JM}")
    state("a=linted", "a=reviewed:APPROVE", "a=reviewed:FIX", "a=linted", "a=reviewed:APPROVE")
else:
    sys.exit(f"unknown mutation {m}")
open(LOG, "w", encoding="utf-8").write("\n".join(note))
open(DEC, "w", encoding="utf-8").write("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows))
PY
}
# run1 <lint> <tag>: one lint run of the current fixture, text and --json, into $T/r/<tag>.*
run1() {
  "$1" "$LOG" --last --prd-dir "$H" --decisions "$DEC" >"$T/r/$2.txt.out" 2>"$T/r/$2.txt.err"; echo $? >"$T/r/$2.txt.rc"
  "$1" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --json >"$T/r/$2.json.out" 2>"$T/r/$2.json.err"; echo $? >"$T/r/$2.json.rc"
}
# pair <case>: base and head on the current fixture; sets OUT (head text stdout+stderr),
# JS (head --json stdout), RC (head rc), SAME (1 when every base/head byte matches, the head
# JSON read without the `mission` and `provenance.mission` keys edge-map R5 adds to every
# object, and without `FAIL mission-grammar` lines when $GRAMMAR is 1: a case whose own
# Mission: line breaks edge-map R1's grammar)
pair() {
  run1 "$BASE_LINT" "$1.base"; run1 "$LINT" "$1.head"
  python3 - "$T/r/$1.head" "${GRAMMAR:-0}" <<'PY2' || fail "$1: normalizing the head output"
import sys, json
p, g = sys.argv[1], sys.argv[2] == "1"
for k in ("txt.out", "txt.err", "json.err"):
    L = open(f"{p}.{k}").read().split("\n")
    open(f"{p}.{k}.n", "w").write("\n".join(l for l in L if not (g and l.startswith("FAIL mission-grammar: "))))
t = open(f"{p}.json.out").read()
if t.strip():
    d = json.loads(t); d.pop("mission", None); d["provenance"].pop("mission", None)
    if g:
        d["findings"] = [x for x in d["findings"] if x != "mission-grammar"]
    t = json.dumps(d, separators=(",", ":")) + "\n"
open(f"{p}.json.out.n", "w").write(t)
for k in ("txt.rc", "json.rc"):
    open(f"{p}.{k}.n", "w").write(open(f"{p}.{k}").read())
PY2
  SAME=1
  for k in txt.out txt.err txt.rc json.out json.err json.rc; do
    cmp -s "$T/r/$1.base.$k" "$T/r/$1.head.$k.n" || SAME=0
  done
  OUT=$(cat "$T/r/$1.head.txt.out" "$T/r/$1.head.txt.err"); JS=$(cat "$T/r/$1.head.json.out"); RC=$(cat "$T/r/$1.head.txt.rc")
  case "$OUT$(cat "$T/r/$1.head.json.err" "$T/r/$1.base.txt.err" "$T/r/$1.base.json.err")" in
    *Traceback*) fail "$1: traceback: $OUT";; esac
}
# jget '<python expr on d>' < json
jget() { python3 -c 'import sys,json; d=json.load(sys.stdin); print(json.dumps(eval(sys.argv[1],{"d":d})))' "$1"; }
# kb <case> [extra finding id ...]: the mutation already applied; head == base byte for byte,
# exit 1, `review-snapshot-stale` naming K's file, K's session and slug a, and each extra id
kb() {
  local c="$1"; shift
  pair "$c"
  [ "$SAME" = 1 ] || fail "$c: head differs from base ($(diff <(cat "$T/r/$c.base.txt.out" "$T/r/$c.base.txt.err") <(printf '%s\n' "$OUT") | head -5 | tr '\n' ' '); rc base=$(cat "$T/r/$c.base.txt.rc") head=$RC)"
  [ "$RC" = 1 ] || fail "$c: rc=$RC want 1: $OUT"
  printf '%s\n' "$OUT" | grep >/dev/null -F "FAIL review-snapshot-stale: notes/reviews/k.txt: reviewer-session $S_K: slug a: " \
    || fail "$c: no review-snapshot-stale naming K ($S_K) and slug a: $OUT"
  printf '%s' "$JS" | jget 'd["findings"]' | grep >/dev/null -F '"review-snapshot-stale"' || fail "$c: JSON findings lack review-snapshot-stale: $JS"
  for id in "$@"; do
    printf '%s\n' "$OUT" | grep >/dev/null "^FAIL $id: " || fail "$c: no $id finding: $OUT"
  done
  if [ "${GRAMMAR:-0}" = 1 ]; then
    printf '%s\n' "$OUT" | grep >/dev/null "^FAIL mission-grammar: " || fail "$c: no mission-grammar for its broken Mission: line: $OUT"
  else
    printf '%s\n' "$OUT" | grep >/dev/null "^FAIL mission-grammar: " && fail "$c: mission-grammar on a valid Mission: line: $OUT"
  fi
  case "$JS" in *'"superseded"'*) fail "$c: a superseded key on a refused note: $JS";; esac
  echo "ok $c: base==head bytes, rc=1, review-snapshot-stale K/a${*:+, $*}"
}
# ch <case> <rc> <findings, space-separated, sorted> [FAIL-line substring ...]: a case whose
# outcome the A1723 PRDs change (each caller names the PRD line); the head alone is asserted:
# exit, the exact finding-id set, and each substring in some FAIL line. An empty findings
# argument means [].
ch() {
  local c="$1" rc="$2" ids="$3"; shift 3
  pair "$c"
  [ "$RC" = "$rc" ] || fail "$c: rc=$RC want $rc: $OUT"
  local got; got=$(printf '%s' "$JS" | python3 -c 'import sys,json; print(" ".join(sorted(set(json.load(sys.stdin)["findings"]))))')
  [ "$got" = "$ids" ] || fail "$c: findings [$got] want [$ids]: $OUT"
  for s in "$@"; do
    printf '%s\n' "$OUT" | grep '^FAIL ' | grep >/dev/null -F -- "$s" || fail "$c: no FAIL line carries '$s': $OUT"
  done
  echo "ok $c: rc=$RC findings [$ids]"
}
# jq_ <case> '<python assertion on d (head --json)>' <label>: one JSON assertion on the last pair
jq_() {
  printf '%s' "$JS" | python3 -c "import sys,json
d=json.load(sys.stdin); K,J,U='$S_K','$S_J','$S_U'
r={x['session']:x for x in d['reviews']}
m=d.get('mission') or {}
dep={x['slug']:x['reason'] for x in m.get('dependent_slugs') or []}
assert $2" 2>"$T/jq.err" || fail "$1: $3: $(tail -1 "$T/jq.err") json=$JS"
}
# not_stale_k <case>: K's APPROVE on a is superseded (chain-review R5), never a stale finding
not_stale_k() {
  case "$OUT" in *"review-snapshot-stale: notes/reviews/k.txt"*) fail "$1: K's pin on a still checked: $OUT";; esac
  jq_ "$1" 'r[K].get("superseded")==[{"slug":"a","by":J}]' "K superseded [a by J]"
}
