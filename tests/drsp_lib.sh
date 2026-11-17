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
# reset: a fresh copy of the P1 fixture
reset() {
  rm -rf "$W"; mkdir -p "$W"; cp -r "$FIX/." "$W/"
  LOG="$W/home/notes/dream-log.md"; DEC="$W/decisions.jsonl"; H="$W/home"
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
    setline("Mission:", "Mission: drsp-fixture scope=" + scope)
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
def manifest(rel, extra):
    # a reviewer manifest over the current a, b, c plus one extra file, so its id differs from k and j
    d = os.path.dirname(rel)
    wr(d + "/notes.md", extra)
    wr(rel, "".join(f"{sha('built-prds/PRD-' + s + '.md')}  PRD-{s}.md\n" for s in "abc") + f"{sha(d + '/notes.md')}  notes.md\n")
    lines = open(os.path.join(H, rel), "rb").read()[:-1].split(b"\n")
    return hashlib.sha256(b"".join(sorted({ln + b"\n" for ln in lines}))).hexdigest()   # basenames already
A_K, A_J = f"a APPROVE {S_K}", f"a APPROVE {S_J}"
MJ = f"mission=APPROVE {S_J}"
SCOPE = f"{KM},{JM}"
m = name
if m == "P3":    # K also APPROVEs b, which is unchanged since K's manifest
    review("k", S_K, [A_K, f"b APPROVE {S_K}"]); state("a=linted", "a=reviewed:APPROVE", "a=linted", "a=reviewed:APPROVE", "b=reviewed:APPROVE")
elif m == "P4":  # K and J both APPROVE b on its unchanged bytes
    review("k", S_K, [A_K, f"b APPROVE {S_K}"]); review("j", S_J, [A_J, f"b APPROVE {S_J}", MJ])
    state("a=linted", "a=reviewed:APPROVE", "a=linted", "a=reviewed:APPROVE", "b=reviewed:APPROVE", "b=reviewed:APPROVE")
elif m == "P4-only-b":  # b is K's only APPROVE candidate (K names b, not a); K and J both APPROVE b
    review("k", S_K, [f"b APPROVE {S_K}"]); review("j", S_J, [A_J, f"b APPROVE {S_J}", MJ])
    state("a=linted", "a=reviewed:APPROVE", "b=reviewed:APPROVE", "b=reviewed:APPROVE")
elif m == "KB1":  # J's last verdict for a is FIX
    review("j", S_J, [f"a FIX {S_J}", MJ]); state("a=linted", "a=reviewed:APPROVE", "a=linted", "a=reviewed:FIX")
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
    sid = manifest("notes/snapshots/y/snapshot.sha256", "review Y packet notes\n")
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
# JS (head --json stdout), RC (head rc), SAME (1 when every base/head byte matches)
pair() {
  run1 "$BASE_LINT" "$1.base"; run1 "$LINT" "$1.head"
  SAME=1
  for k in txt.out txt.err txt.rc json.out json.err json.rc; do
    cmp -s "$T/r/$1.base.$k" "$T/r/$1.head.$k" || SAME=0
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
  printf '%s\n' "$OUT" | grep -qF "FAIL review-snapshot-stale: notes/reviews/k.txt: reviewer-session $S_K: slug a: " \
    || fail "$c: no review-snapshot-stale naming K ($S_K) and slug a: $OUT"
  printf '%s' "$JS" | jget 'd["findings"]' | grep -qF '"review-snapshot-stale"' || fail "$c: JSON findings lack review-snapshot-stale: $JS"
  for id in "$@"; do
    printf '%s\n' "$OUT" | grep -q "^FAIL $id: " || fail "$c: no $id finding: $OUT"
  done
  case "$JS" in *'"superseded"'*) fail "$c: a superseded key on a refused note: $JS";; esac
  echo "ok $c: base==head bytes, rc=1, review-snapshot-stale K/a${*:+, $*}"
}
