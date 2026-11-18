#!/usr/bin/env python3
"""Pre-launch fixture builder for the drpe tests (PRD-dream-packet-errors-while-repairable).

Each case writes <outdir>/home (a PRD home), <outdir>/decisions.jsonl (governed cases) and
<outdir>/pending.md: the pending entry (a `## <ts>  /dream  vision-...` header and its Task:,
Route:, Analysis:, Review:, State: and Mission: lines), never appended to the note. The note
home/notes/dream-log.md holds the recorded entries; for the first-run shapes it is absent, empty
or a title line only. Matrices and edge maps come from the lint's own selftest helpers through
tests/fixtures/drmx/mfx.py.

Shapes (the PRD's AC 1 and AC 7 notes):
  continued  entry E1 (run 1) recorded: m1 (x1) bound by r1 (FIX, finding F1 on foo); run 2 pending:
             row 1 (F1, m1 -> m2), m2 frozen with foo v2, the run's matrix x2 and the repairs file
  inrun      no recorded entry of the mission: m1 bound by r1 (FIX, F1); row 1; m2 pending (one run)
  first      no recorded entry: m1 frozen, nothing reviewed (Review: none)
  three      continued, and run 2 already bound m2 (r2 launched and returned FIX, finding F2 on bar),
             m2 holds a byte copy of the repairs file (row 1); row 2 (F2, m2 -> m3); m3 pending

Usage: pfx.py <case> <outdir> | --list.  A case name ending in `@nolog` builds the same case for a
host with no decisions log (every Route: line `ungoverned`, no decisions.jsonl).
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mfx", os.path.join(HERE, "..", "drmx", "mfx.py"))
mfx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mfx)
H, S, at, mx_rel, prd, sha, scope_id, json_edges, FINDING = (mfx.H, mfx.S, mfx.at, mfx.mx_rel, mfx.prd, mfx.sha,
                                                             mfx.scope_id, mfx.json_edges, mfx.FINDING)
NAME = "drpe-mission"
EB, RB = f"{NAME}.edges.jsonl", f"{NAME}.repairs.jsonl"
EDGES, REP = f"notes/missions/{EB}", f"notes/missions/{RB}"
SLUGS = ["foo", "bar"]


def b(x):
    return x if isinstance(x, bytes) else x.encode("utf-8")


def edges(matrix=None, prds=None, mutate=None):
    prds = list(prds or SLUGS)

    def mut(h, es):
        h["mission"] = NAME
        if matrix is not None:
            h["matrix"] = matrix
        if mutate:
            mutate(h, es)
    return H["mission_edges"](prds, mutate=mut, known_only=True).encode()


def matrix(slugs=None, tag="", drop_family=None):
    slugs = list(SLUGS if slugs is None else slugs)
    body = "".join(H["mx_section"](s, drop=drop_family) for s in slugs)
    return H["mx_file"](slugs, sections=body, pre=f"# Adversarial matrix (drpe fixture{tag})\n\n").encode()


class Man:
    def __init__(self, name, members, d=None):
        self.name = name
        self.dir = d or f"notes/snapshots/{name}"
        self.rel = f"{self.dir}/{name}.sha256"
        self.members = dict(members)         # basename -> bytes ("@repairs" filled at write time)
        self.copies = {}                     # basename -> bytes | None (None: no copy beside)
        self.lines_override = None           # exact manifest text
        self.extra = []

    def text(self):
        if self.lines_override is not None:
            return self.lines_override
        return "".join(f"{sha(b(v))}  {k}\n" for k, v in self.members.items()) + "".join(x + "\n" for x in self.extra)


class Scen:
    def __init__(self, shape, header_matrix=False, nolog=False):
        self.shape, self.hm, self.nolog = shape, header_matrix, nolog
        self.files = {f"built-prds/PRD-{s}.md": prd(s, 1).encode() for s in SLUGS}
        self.mans = {}          # name -> Man (in freeze order)
        self.rows = []          # repairs rows (dicts) in file order
        self.raw_rep = None     # exact live repairs bytes (overrides rows)
        self.frozen_rows = {}   # manifest name -> number of leading rows its repairs copy holds
        self.dec = []           # decisions rows
        self.entries = []       # recorded entries: {ts, lines: {kind: line or [lines]}}
        self.pending = None     # {ts, lines}
        self.note = "present"   # present | absent | empty | title
        self.live_override = {} # rel -> bytes written after everything else

    def route(self, sess, ts):
        if self.nolog:
            return f"Route: ungoverned session={sess} host=fixture-host"
        return f"Route: opus-high claude-opus-5-5 high session={sess} decision={ts}"

    def drow(self, ts, sess, role=None, man=None, decision="launch", **kw):
        r = {"ts": ts, "decision": decision, "task_id": "PE-1", "skill": "dream", "route": "opus-high",
             "model": "claude-opus-5-5", "effort": "high", "account": "lane-x", "session": sess, "resume": False,
             "reasons": "fixture"}
        if role:
            r.update(role=role, scope=man.rel if man else "", scope_id="@" + man.name if man else "")
        r.update(kw)
        self.dec.append(r)
        return r

    def review(self, d, sess, verdicts, mission, findings=None):
        lines = [f"{s} {v} fixture-reviewer" for s, v in verdicts] + ([f"mission={mission} {sess}"] if mission else [])
        self.files[f"{d}/verdict.txt"] = ("".join(x + "\n" for x in lines)).encode()
        sc = None
        if findings:
            sc = "".join(json.dumps(dict(FINDING, **f)) + "\n" for f in findings).encode()
            self.files[f"{d}/verdict.txt.findings.jsonl"] = sc
        text = "Done.\n" + f"findings={'none' if sc is None else sha(sc)}\n" + "\n".join(lines)
        self.files[f"{d}/result.json"] = json.dumps({"type": "result", "is_error": False, "session_id": sess,
                                                     "result": text}).encode() + b"\n"
        return f"Review: {d}/verdict.txt reviewer-session={sess} result={d}/result.json"

    def entry_lines(self, route, adv, reviews, state, mission):
        a = adv if adv.startswith("skipped:") else f"{adv} uncovered=1"
        return {"Task": "Task: PE-1   Consumer: hermes", "Route": route,
                "Analysis": f"Analysis: wwhtbt=skipped: fixture 5whys=skipped: fixture adversarial={a}",
                "Review": list(reviews) if reviews else ["Review: none"], "State": f"State: {state}",
                "Mission": mission}

    def rep_bytes(self, n=None):
        if self.raw_rep is not None and n is None:
            return self.raw_rep
        rs = self.rows if n is None else self.rows[:n]
        return "".join(json.dumps(r) + "\n" for r in rs).encode()

    # ---- output
    def write(self, out):
        home = os.path.join(out, "home")
        live = dict(self.files)
        if self.rows or self.raw_rep is not None:
            live[REP] = self.rep_bytes()
        live.update(self.live_override)
        for rel, data in live.items():
            if data is None:
                continue
            p = os.path.join(home, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as fh:
                fh.write(b(data))
        ids = {}
        for m in self.mans.values():
            if RB in m.members and m.members[RB] == "@repairs":
                m.members[RB] = self.rep_bytes(self.frozen_rows.get(m.name, len(self.rows)))
            p = os.path.join(home, m.rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            txt = m.text()
            if txt is not None:
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                ids[m.name] = scope_id(txt)
            for k, v in m.members.items():
                c = m.copies.get(k, v)
                if c is None:
                    continue
                with open(os.path.join(os.path.dirname(p), k), "wb") as fh:
                    fh.write(b(c))
        for r in self.dec:
            if isinstance(r.get("scope_id"), str) and r["scope_id"].startswith("@"):
                r["scope_id"] = ids.get(r["scope_id"][1:], r.get("scope_id_fixed", "0" * 64))
        if not self.nolog:
            with open(os.path.join(out, "decisions.jsonl"), "w", encoding="utf-8") as fh:
                fh.write("".join(json.dumps(r) + "\n" for r in self.dec))
        notes = os.path.join(home, "notes")
        os.makedirs(notes, exist_ok=True)
        log = os.path.join(notes, "dream-log.md")
        if self.note == "present":
            body = "# dream log (drpe fixture)\n\n" + "\n".join(render(e) for e in self.entries)
            with open(log, "w", encoding="utf-8") as fh:
                fh.write(body)
        elif self.note == "empty":
            open(log, "w").close()
        elif self.note == "title":
            with open(log, "w", encoding="utf-8") as fh:
                fh.write("# dream log (drpe fixture)\n")
        with open(os.path.join(out, "pending.md"), "w", encoding="utf-8") as fh:
            fh.write(render(self.pending))
        for rel, data in self.live_override.items():     # removals after the manifests (a deleted manifest)
            if data is None and os.path.exists(os.path.join(home, rel)):
                os.remove(os.path.join(home, rel))
        return out


ORDER = ["Task", "Route", "Analysis", "Review", "State", "Mission"]


def render(e):
    out = [f"## {e['ts']}  /dream  vision-{NAME}", "Contract: /fixture/build-contract.md   Hooks: dream.lint",
           "Seeds: fixture", "Lineage: greenfield", "Drafted: PRD-foo.md, PRD-bar.md   Build order: foo → bar",
           "Lint: clean   Eligibility: pending scan"]
    for k in ORDER + [k for k in e["lines"] if k not in ORDER]:
        v = e["lines"].get(k)
        if v is None:
            continue
        out += v if isinstance(v, list) else [v]
    return "\n".join(out + ["Open questions: none"]) + "\n"


def members(vers, mx_rel_, mx_bytes, ed, rep=False):
    m = {f"PRD-{s}.md": prd(s, vers[s]) for s in vers}
    if mx_rel_:
        m[os.path.basename(mx_rel_)] = mx_bytes
    m[EB] = ed
    if rep:
        m[RB] = "@repairs"
    return m


def sweep_for(ed, aff):
    return [e["id"] for e in json_edges(ed) if e["producer"] in aff or e["consumer"] in aff]


F1 = {"id": "F1", "class": "missing-producer-runner", "prds": ["PRD-foo.md"], "consumers": ["PRD-bar.md"]}
F2 = {"id": "F2", "class": "missing-producer-runner", "prds": ["PRD-bar.md"], "consumers": ["PRD-foo.md"]}


def build(shape, hm=False, nolog=False):
    """The correct (exit 0) pending state of a shape; cases mutate it."""
    s = Scen(shape, hm, nolog)
    s.x1, s.x2, s.x3 = mx_rel(11), mx_rel(13), mx_rel(14)
    inrun = shape in ("inrun", "first")
    if inrun:
        s.note = "absent"
        s.x2 = s.x1 if not hm else mx_rel(12)       # one run entry: a legacy header keeps the name
    s.files[s.x1] = matrix(tag=" x1")
    s.files[s.x2] = matrix(tag=" x2") if s.x2 != s.x1 else s.files[s.x1]
    e1 = edges(os.path.basename(s.x1) if hm else None)
    s.mans["m1"] = Man("m1", members({"foo": 1, "bar": 1}, s.x1, s.files[s.x1], e1))
    s.drow(at(8), S["A"], role="author")
    s.files[EDGES] = e1
    s.mission_line = f"Mission: {NAME} edges={EDGES} scope=notes/snapshots/m1/m1.sha256"
    if shape == "first":
        s.pending = {"ts": at(15), "lines": s.entry_lines(s.route(S["A"], at(8)), s.x1, None,
                                                         "foo=linted bar=linted", s.mission_line)}
        return s
    r1 = s.review("notes/reviews/r1", S["R1"], [("foo", "FIX"), ("bar", "APPROVE")], "FIX", findings=[F1])
    s.drow(at(11, 30), S["R1"], role="review", man=s.mans["m1"])
    s.r1 = r1
    route2 = (S["A"], at(8))
    if not inrun:
        s.entries.append({"ts": at(12), "lines": s.entry_lines(s.route(S["A"], at(8)), s.x1, [r1],
                                                               "foo=linted foo=reviewed:FIX bar=linted bar=reviewed:APPROVE",
                                                               s.mission_line)})
        s.drow(at(12, 30), S["A2"], role="author")
        route2 = (S["A2"], at(12, 30))
    s.route2 = route2
    e2 = edges(os.path.basename(s.x2) if hm else None)
    s.files["built-prds/PRD-foo.md"] = prd("foo", 2).encode()
    s.rows.append({"finding": "F1", "class": "missing-producer-runner", "author_session": route2[0],
                   "before": "notes/snapshots/m1/m1.sha256", "after": "notes/snapshots/m2/m2.sha256",
                   "changed": ["PRD-foo.md"] + ([EB] if hm else []), "sweep": sweep_for(e1, ["PRD-foo.md", "PRD-bar.md"]),
                   "disposition": "repaired"})
    if hm and s.x1 != s.x2:
        s.rows[0]["changed"] += [os.path.basename(s.x1), os.path.basename(s.x2)]
    s.mans["m2"] = Man("m2", members({"foo": 2, "bar": 1}, s.x2, s.files[s.x2], e2, rep=True))
    s.files[EDGES] = e2
    reviews = [r1]
    state = "foo=linted foo=reviewed:FIX bar=reviewed:APPROVE"
    scope = "notes/snapshots/m1/m1.sha256,notes/snapshots/m2/m2.sha256"
    adv = s.x2
    if shape == "three":
        r2 = s.review("notes/reviews/r2", S["R2"], [("foo", "APPROVE"), ("bar", "FIX")], "FIX", findings=[F2])
        s.drow(at(13, 30), S["R2"], role="review", man=s.mans["m2"])
        s.r2 = r2
        reviews.append(r2)
        state = "foo=linted foo=reviewed:FIX foo=reviewed:APPROVE bar=reviewed:APPROVE bar=reviewed:FIX"
        e3 = edges(os.path.basename(s.x3) if hm else None)
        s.files["built-prds/PRD-bar.md"] = prd("bar", 2).encode()
        s.rows.append({"finding": "F2", "class": "missing-producer-runner", "author_session": route2[0],
                       "before": "notes/snapshots/m2/m2.sha256", "after": "notes/snapshots/m3/m3.sha256",
                       "changed": ["PRD-bar.md"] + ([EB, os.path.basename(s.x2), os.path.basename(s.x3)] if hm else []),
                       "sweep": sweep_for(e2, ["PRD-foo.md", "PRD-bar.md"]), "disposition": "repaired"})
        s.frozen_rows["m2"] = 1
        if not hm:
            s.x3 = s.x2                 # legacy header: run 2 keeps its matrix name for m3
        else:
            s.files[s.x3] = matrix(tag=" x3")
        s.mans["m3"] = Man("m3", members({"foo": 2, "bar": 2}, s.x3, s.files[s.x3], e3, rep=True))
        s.files[EDGES] = e3
        scope += ",notes/snapshots/m3/m3.sha256"
        adv = s.x3
    s.scope = scope
    s.pending = {"ts": at(15), "lines": s.entry_lines(s.route(*route2), adv, reviews, state,
                                                     f"Mission: {NAME} " + (f"edges={EDGES} " if inrun else "")
                                                     + f"scope={scope} repairs={REP}")}
    return s


def setp(s, kind, line):
    """Replace (None: drop) the pending entry's <kind> line."""
    if line is None:
        s.pending["lines"].pop(kind, None)
    else:
        s.pending["lines"][kind] = line


def mission(s, extra=""):
    return s.pending["lines"]["Mission"] + extra


# ---------------------------------------------------------------- cases
CASES = {}


def case(name):
    def deco(fn):
        CASES[name] = fn
        return fn
    return deco


# AC 7: correct pending states (exit 0)
for _shape in ("continued", "inrun", "first", "three"):
    for _hm in (False, True):
        def _c(shape=_shape, hm=_hm, **kw):
            return build(shape, hm, kw.get("nolog", False))
        CASES[f"ok-{_shape}{'-hm' if _hm else ''}"] = _c
for _note in ("empty", "title"):
    def _c(note=_note, **kw):
        s = build("first", False, kw.get("nolog", False))
        s.note = note
        return s
    CASES[f"ok-first-{_note}"] = _c
    def _c2(note=_note, **kw):
        s = build("inrun", False, kw.get("nolog", False))
        s.note = note
        return s
    CASES[f"ok-inrun-{_note}"] = _c2


# AC 1 defects
@case("d-same-id")
def _(nolog=False):
    """withdrawn=m2 with a replacement whose lines differ from m2's only in path spelling."""
    s = build("continued", nolog=nolog)
    m2 = s.mans["m2"]
    r = Man("m2b", dict(m2.members), d="notes/snapshots/m2b")
    s.mans["m2b"] = r
    s.write_hook = lambda home: None
    r.spell = True
    setp(s, "Mission", f"Mission: {NAME} scope={s.scope},notes/snapshots/m2b/m2b.sha256 repairs={REP} "
                       "withdrawn=notes/snapshots/m2/m2.sha256")
    s.rows[0]["after"] = "notes/snapshots/m2b/m2b.sha256"
    return s


for _note in ("absent", "empty", "title"):
    def _c(note=_note, nolog=False):
        """First repair round of a first run (no note, an empty one, a title line only): m2 omits the repairs file."""
        s = build("inrun", nolog=nolog)
        s.note = note
        del s.mans["m2"].members[RB]
        return s
    CASES[f"d-norepairs-{_note}"] = _c


@case("d-duplicate")
def _(nolog=False):
    """three: row 1 frozen in bound m2's copy; a new row 3 answers F1 again."""
    s = build("three", nolog=nolog)
    s.rows.append(dict(s.rows[0]))
    return s


@case("d-live-repairs-line")
def _(nolog=False):
    """three: bound m2's repairs line names the live file (no copy beside m2); frozen row 1 has a short sweep."""
    s = build("three", nolog=nolog)
    s.rows[0]["sweep"] = s.rows[0]["sweep"][:1]
    m2 = s.mans["m2"]
    m2.copies[RB] = None
    m2.extra_live = True
    return s


@case("held-row-copy")
def _(nolog=False):
    """AC 5: the same short-sweep row 1, frozen in bound m2's byte copy: held."""
    s = build("three", nolog=nolog)
    s.rows[0]["sweep"] = s.rows[0]["sweep"][:1]
    return s


@case("held-matrix")
def _(nolog=False):
    """AC 5: header matrices; bound m2's frozen matrix x2 (its listed digest) holds no bar section: held."""
    s = build("three", True, nolog)
    one = matrix(slugs=["foo"], tag=" x2")
    s.files[s.x2] = one
    s.mans["m2"].members[os.path.basename(s.x2)] = one
    return s


@case("d-changed-absent")
def _(nolog=False):
    """continued: the new row names in `changed` a basename its bound `before` (m1) lacks."""
    s = build("continued", nolog=nolog)
    s.rows[0]["changed"].append("PRD-qux.md")
    return s


@case("d-first-missing-prd")
def _(nolog=False):
    s = build("first", nolog=nolog)
    del s.mans["m1"].members["PRD-bar.md"]
    return s


@case("d-rename-legacy")
def _(nolog=False):
    """inrun, legacy header: round 2 writes x2 and the pending adversarial= names it (bound m1 lists x1)."""
    s = build("inrun", nolog=nolog)
    x2 = mx_rel(12)
    s.files[x2] = matrix(tag=" x2")
    m2 = s.mans["m2"]
    m2.members = {k: v for k, v in m2.members.items() if not k.endswith("-adversarial.md")}
    m2.members[os.path.basename(x2)] = s.files[x2]
    setp(s, "Analysis", f"Analysis: wwhtbt=skipped: fixture 5whys=skipped: fixture adversarial={x2} uncovered=1")
    return s


@case("d-repairs-omitted")
def _(nolog=False):
    s = build("continued", nolog=nolog)
    del s.mans["m2"].members[RB]
    return s


@case("d-amended-nosweep")
def _(nolog=False):
    s = build("continued", nolog=nolog)
    s.files["built-prds/PRD-bar.md"] = prd("bar", 2).encode()
    s.mans["m2"].members["PRD-bar.md"] = prd("bar", 2)
    s.rows.append({"finding": None, "class": None, "author_session": s.route2[0], "before": "notes/snapshots/m1/m1.sha256",
                   "after": "notes/snapshots/m2/m2.sha256", "changed": ["PRD-bar.md"], "sweep": [],
                   "disposition": "amended", "reason": "bar re-worded"})
    return s


@case("d-matrix-grammar")
def _(nolog=False):
    s = build("continued", nolog=nolog)
    bad = matrix(tag=" x2", drop_family="Falsifier quality")
    s.files[s.x2] = bad
    m2 = s.mans["m2"]
    m2.members[os.path.basename(s.x2)] = bad
    return s


@case("d-forgot-row")
def _(nolog=False):
    """continued: run 2 answers r1's FIX finding F1 (foo v2) but writes no row and no repairs= token."""
    s = build("continued", nolog=nolog)
    s.rows = []
    del s.mans["m2"].members[RB]
    setp(s, "Mission", f"Mission: {NAME} scope={s.scope}")
    return s


@case("d-analysis-malformed")
def _(nolog=False):
    s = build("continued", nolog=nolog)
    _drop_matrix(s, "m2")
    setp(s, "Analysis", f"Analysis: adversarial={s.x2} uncovered=1")
    return s


@case("d-analysis-absent")
def _(nolog=False):
    s = build("continued", nolog=nolog)
    _drop_matrix(s, "m2")
    setp(s, "Analysis", None)
    return s


@case("d-state-absent")
def _(nolog=False):
    s = build("continued", nolog=nolog)
    _drop_matrix(s, "m2")
    setp(s, "State", None)
    return s


@case("d-task-absent")
def _(nolog=False):
    s = build("continued", nolog=nolog)
    setp(s, "Task", None)
    return s


@case("d-mission-absent")
def _(nolog=False):
    s = build("continued", nolog=nolog)
    setp(s, "Mission", None)
    return s


@case("d-task-malformed")
def _(nolog=False):
    """The Task: line names the task but no Consumer:."""
    s = build("continued", nolog=nolog)
    setp(s, "Task", "Task: PE-1")
    return s


@case("d-first-skipped")
def _(nolog=False):
    s = build("first", nolog=nolog)
    _drop_matrix(s, "m1")
    setp(s, "Analysis", "Analysis: wwhtbt=skipped: fixture 5whys=skipped: fixture adversarial=skipped: first freeze")
    return s


def _drop_matrix(s, name):
    m = s.mans[name]
    m.members = {k: v for k, v in m.members.items() if not k.endswith("-adversarial.md")}


@case("d-state-short")
def _(nolog=False):
    """continued: the pending State names this run's foo only; the re-listed r1 names bar; x2 has no bar section."""
    s = build("continued", nolog=nolog)
    one = matrix(slugs=["foo"], tag=" x2")
    s.files[s.x2] = one
    s.mans["m2"].members[os.path.basename(s.x2)] = one
    setp(s, "State", "State: foo=linted foo=reviewed:FIX")
    return s


@case("d-row-edited")
def _(nolog=False):
    """three: frozen row 1 edited in place in the live file (its sweep shortened) after bound m2 froze it."""
    s = build("three", nolog=nolog)
    s.edit_row1 = True
    return s


@case("d-recency-same")
def _(nolog=False):
    """continued: the pending adversarial= keeps E1's matrix x1 (not later than E1), the native run-2 shape."""
    s = build("continued", nolog=nolog)
    m2 = s.mans["m2"]
    m2.members = {k: v for k, v in m2.members.items() if not k.endswith("-adversarial.md")}
    m2.members[os.path.basename(s.x1)] = s.files[s.x1]
    setp(s, "Analysis", f"Analysis: wwhtbt=skipped: fixture 5whys=skipped: fixture adversarial={s.x1} uncovered=1")
    return s


@case("d-recency-new-name")
def _(nolog=False):
    """continued: a new matrix name whose timestamp is not later than E1 (11:30 against 12:00)."""
    s = build("continued", nolog=nolog)
    xo = "notes/reviews/2027-03-01T11:30:00-08:00-adversarial.md"
    s.files[xo] = matrix(tag=" x-old")
    m2 = s.mans["m2"]
    m2.members = {k: v for k, v in m2.members.items() if not k.endswith("-adversarial.md")}
    m2.members[os.path.basename(xo)] = s.files[xo]
    setp(s, "Analysis", f"Analysis: wwhtbt=skipped: fixture 5whys=skipped: fixture adversarial={xo} uncovered=1")
    return s


for _hm in (False, True):
    def _c(hm=_hm, nolog=False):
        """first freeze: the header lists foo and bar, this run drafts foo only (State, matrix)."""
        s = build("first", hm, nolog)
        one = matrix(slugs=["foo"], tag=" x1")
        s.files[s.x1] = one
        s.mans["m1"].members[os.path.basename(s.x1)] = one
        if hm:
            ed = edges(os.path.basename(s.x1))
            s.files[EDGES] = ed
            s.mans["m1"].members[EB] = ed
        setp(s, "State", "State: foo=linted")
        return s
    CASES[f"d-header-member{'-hm' if _hm else ''}"] = _c


@case("d-live-row-fixed")
def _(nolog=False):
    """continued: m2 froze row 1 with a short sweep; the live repairs file holds the fixed row."""
    s = build("continued", nolog=nolog)
    good = list(s.rows[0]["sweep"])
    s.rows[0]["sweep"] = good[:1]
    s.fix_live_rows = good
    return s


@case("d-live-matrix-fixed")
def _(nolog=False):
    """continued (legacy): m2's x2 lacks the bar section; a section was added to the live x2 only."""
    s = build("continued", nolog=nolog)
    s.mans["m2"].members[os.path.basename(s.x2)] = matrix(slugs=["foo"], tag=" x2")
    return s


@case("d-live-edges-fixed")
def _(nolog=False):
    """continued: m2's edges copy has an edge with an empty trigger; the live edges file was fixed."""
    s = build("continued", nolog=nolog)
    bad = edges(None, mutate=lambda h, es: es[0].update(trigger=""))
    s.mans["m2"].members[EB] = bad
    return s


# AC 2 withdrawals and AC 8: a defective unbound m2 (a row's `after`), withdrawn and replaced by m2r
def defective(kind, nolog=False):
    s = build("continued", nolog=nolog)
    m2 = s.mans["m2"]
    if kind == "header":
        bad = edges(None, mutate=lambda h, es: h.update(prds=h["prds"] + ["PRD-baz.md"]))
        s.files["built-prds/PRD-baz.md"] = b"# PRD-baz (fixture v1)\n"
        m2.members[EB] = bad
    elif kind == "edges-unlisted":
        del m2.members[EB]
    elif kind == "repairs":
        del m2.members[RB]
    elif kind == "row":
        s.rows[0]["sweep"] = []
    elif kind == "amended":         # a row defect a host with no decisions log also checks (no finding needed)
        s.rows.append({"finding": None, "class": None, "author_session": s.route2[0], "before": "notes/snapshots/m1/m1.sha256",
                       "after": "notes/snapshots/m2/m2.sha256", "changed": ["PRD-foo.md"], "sweep": [],
                       "disposition": "amended", "reason": "foo re-worded"})
    return s


def withdrawn_case(kind, nolog=False):
    s = defective(kind, nolog)
    good = Man("m2r", members({"foo": 2, "bar": 1}, s.x2, s.files[s.x2], s.files[EDGES], rep=True))
    s.mans["m2r"] = good
    row = dict(s.rows[0], after="notes/snapshots/m2r/m2r.sha256", sweep=sweep_for(s.files[EDGES], ["PRD-foo.md", "PRD-bar.md"]))
    s.frozen_rows["m2"] = len(s.rows)
    if kind == "amended":
        s.rows.append(row)
        s.rows.append(dict(s.rows[1], after="notes/snapshots/m2r/m2r.sha256", sweep=sweep_for(s.files[EDGES], ["PRD-foo.md"])))
    else:
        s.rows.append(row)
    s.scope += ",notes/snapshots/m2r/m2r.sha256"
    setp(s, "Mission", f"Mission: {NAME} scope={s.scope} repairs={REP} withdrawn=notes/snapshots/m2/m2.sha256")
    return s


for _k in ("header", "edges-unlisted", "repairs", "row", "amended"):
    CASES[f"wd0-{_k}"] = (lambda k=_k, nolog=False: defective(k, nolog))
    CASES[f"wd1-{_k}"] = (lambda k=_k, nolog=False: withdrawn_case(k, nolog))


# AC 3 refusals: m2 bound, then withdrawn
def bound_case(how, nolog=False):
    s = withdrawn_case("repairs", nolog)
    m2 = s.mans["m2"]
    if how in ("review", "launch", "edited", "deleted"):
        s.drow(at(14, 0), S["R2"], role="review", man=m2)
        if how == "review":
            r2 = s.review("notes/reviews/r2", S["R2"], [("foo", "APPROVE"), ("bar", "APPROVE")], "APPROVE")
            s.pending["lines"]["Review"] = s.pending["lines"]["Review"] + [r2]
            s.pending["lines"]["State"] += " foo=reviewed:APPROVE bar=reviewed:APPROVE"
        if how == "edited":
            s.edit_m2_after_launch = True
        if how == "deleted":
            s.live_override["notes/snapshots/m2/m2.sha256"] = None
    elif how == "twice":
        setp(s, "Mission", f"Mission: {NAME} scope={s.scope},notes/snapshots/m2/m2.sha256 repairs={REP} "
                           "withdrawn=notes/snapshots/m2/m2.sha256")
    elif how == "dropped":
        # E1 withdrew m0 (an unbound manifest it listed); the pending withdrawn= omits m0
        m0 = Man("m0", members({"foo": 1, "bar": 1}, s.x1, s.files[s.x1], s.mans["m1"].members[EB]), d="notes/snapshots/m0")
        m0.extra = ["0" * 64 + "  m0-note.md"]
        s.mans = {"m0": m0, **s.mans}
        e1 = s.entries[0]
        e1["lines"]["Mission"] = (f"Mission: {NAME} edges={EDGES} scope=notes/snapshots/m0/m0.sha256,notes/snapshots/m1/m1.sha256 "
                                  "withdrawn=notes/snapshots/m0/m0.sha256")
        setp(s, "Mission", f"Mission: {NAME} scope=notes/snapshots/m0/m0.sha256,{s.scope} repairs={REP} "
                           "withdrawn=notes/snapshots/m2/m2.sha256")
    return s


for _h in ("review", "launch", "edited", "deleted", "twice", "dropped"):
    CASES[f"bound-{_h}"] = (lambda h=_h, nolog=False: bound_case(h, nolog))


# AC 5 held rule, live arm: m2 bound (r2 launched on it and listed APPROVE) and still the last manifest (no
# new manifest); after the launch the live edges header gains a packet member, a prds member or an external
# contract that m2 (and its frozen edges copy) lacks. No frozen copy carries the error, so it is exit-setting.
def live_bound(kind, nolog=False):
    s = build("continued", nolog=nolog)
    m2 = s.mans["m2"]
    r2 = s.review("notes/reviews/r2", S["R2"], [("foo", "APPROVE"), ("bar", "APPROVE")], "APPROVE")
    s.drow(at(14, 0), S["R2"], role="review", man=m2)
    s.pending["lines"]["Review"] = s.pending["lines"]["Review"] + [r2]
    s.pending["lines"]["State"] += " foo=reviewed:APPROVE bar=reviewed:APPROVE"
    if kind == "packet":
        s.files["visions/drpe-glossary.md"] = b"# drpe glossary (fixture)\n"
        s.files[EDGES] = edges(None, mutate=lambda h, es: h.update(packet=list(h.get("packet") or []) + ["drpe-glossary.md"]))
    elif kind == "prds":
        s.files["built-prds/PRD-baz.md"] = b"# PRD-baz (fixture v1)\n"
        s.files[EDGES] = edges(None, mutate=lambda h, es: h.update(prds=h["prds"] + ["PRD-baz.md"]))
    elif kind == "contract":
        s.files["contracts/hermes-contract.md"] = b"# hermes contract (fixture)\n"
        s.files[EDGES] = edges(None, mutate=lambda h, es: h.update(
            external=[{"name": "hermes", "contract": "contracts/hermes-contract.md"}]))
    elif kind == "clash":           # a contract path whose basename is a prds member's (m2 lists that member)
        s.files["contracts/PRD-foo.md"] = b"# hermes contract named like a PRD (fixture)\n"
        s.files[EDGES] = edges(None, mutate=lambda h, es: h.update(
            external=[{"name": "hermes", "contract": "contracts/PRD-foo.md"}]))
    elif kind == "dupbase":         # two contract paths sharing one basename
        s.files["contracts/a/hermes.md"] = b"# hermes contract a (fixture)\n"
        s.files["contracts/b/hermes.md"] = b"# hermes contract b (fixture)\n"
        s.files[EDGES] = edges(None, mutate=lambda h, es: h.update(
            external=[{"name": "hermes", "contract": ["contracts/a/hermes.md", "contracts/b/hermes.md"]}]))
    return s


for _k in ("none", "packet", "prds", "contract", "clash", "dupbase"):
    CASES[f"live-bound-{_k}"] = (lambda k=_k, nolog=False: live_bound(k, nolog))


# AC 5 held rule, the whole class (R1: held only "when it is also present in the bound manifest's own
# frozen copies ... which record the state when its review launched"). On the same bound m2: a defect
# m2's frozen edges header raises too (the same member, contract basename or collision), or one no header
# supplies (the edges file, the matrix), is held under both labels; a live collision on another basename,
# or a live member with no readable frozen header, is not.
def frozen_live(s, mutate, live_mutate=None):
    """m2's frozen edges copy carries `mutate`, the live header `live_mutate` (default the same)."""
    fe = edges(None, mutate=mutate)
    s.mans["m2"].members[EB] = fe
    s.files[EDGES] = edges(None, mutate=live_mutate) if live_mutate else fe
    s.rows[0]["changed"] = s.rows[0]["changed"] + [EB]


def held_class(kind, nolog=False):
    s = live_bound("none", nolog)
    m2 = s.mans["m2"]
    ext = lambda *cs: (lambda h, es: h.update(external=[{"name": "hermes", "contract": list(cs) if len(cs) > 1 else cs[0]}]))
    if kind == "frozen-prds":           # both headers list PRD-bar.md, m2 does not
        del m2.members["PRD-bar.md"]
    elif kind == "frozen-packet":       # run9g's shape: a packet member both headers name
        s.files["visions/drpe-glossary.md"] = b"# drpe glossary (fixture)\n"
        frozen_live(s, lambda h, es: h.update(packet=list(h.get("packet") or []) + ["drpe-glossary.md"]))
    elif kind == "frozen-contract":
        s.files["contracts/hermes-contract.md"] = b"# hermes contract (fixture)\n"
        frozen_live(s, ext("contracts/hermes-contract.md"))
    elif kind == "frozen-dupbase":      # m2 lists hermes.md: the collision is the only defect
        s.files["contracts/a/hermes.md"] = b"# hermes contract a (fixture)\n"
        s.files["contracts/b/hermes.md"] = b"# hermes contract b (fixture)\n"
        frozen_live(s, ext("contracts/a/hermes.md", "contracts/b/hermes.md"))
        m2.members["hermes.md"] = s.files["contracts/a/hermes.md"]
    elif kind == "frozen-clash":
        s.files["contracts/PRD-foo.md"] = b"# hermes contract named like a PRD (fixture)\n"
        frozen_live(s, ext("contracts/PRD-foo.md"))
    elif kind == "dupbase-other":       # the frozen header collides on x.md, the live one on hermes.md
        for p in ("contracts/a/x.md", "contracts/b/x.md", "contracts/a/hermes.md", "contracts/b/hermes.md"):
            s.files[p] = f"# {p} (fixture)\n".encode()
        frozen_live(s, ext("contracts/a/x.md", "contracts/b/x.md"), ext("contracts/a/hermes.md", "contracts/b/hermes.md"))
        m2.members["x.md"] = s.files["contracts/a/x.md"]
        m2.members["hermes.md"] = s.files["contracts/a/hermes.md"]
    elif kind == "clash-other":         # the frozen header clashes on PRD-foo.md, the live one on PRD-bar.md
        s.files["contracts/PRD-foo.md"] = b"# contract named like PRD-foo (fixture)\n"
        s.files["contracts/PRD-bar.md"] = b"# contract named like PRD-bar (fixture)\n"
        frozen_live(s, ext("contracts/PRD-foo.md"), ext("contracts/PRD-bar.md"))
    elif kind == "edges":               # run9h's shape: m2 lists no edges file (no readable frozen header)
        del m2.members[EB]
    elif kind == "edges-member":        # ... and the live header names the edges file as a packet member
        del m2.members[EB]
        s.files[EDGES] = edges(None, mutate=lambda h, es: h.update(packet=list(h.get("packet") or []) + [EB]))
    elif kind == "noheader-dupbase":    # no readable frozen header; the live header collides on hermes.md
        del m2.members[EB]
        s.files["contracts/a/hermes.md"] = b"# hermes contract a (fixture)\n"
        s.files["contracts/b/hermes.md"] = b"# hermes contract b (fixture)\n"
        s.files[EDGES] = edges(None, mutate=ext("contracts/a/hermes.md", "contracts/b/hermes.md"))
    elif kind in ("matrix-noheader", "matrix-member"):  # no readable frozen header, no copy of the note's matrix x2
        del m2.members[EB]
        del m2.members[os.path.basename(s.x2)]
        if kind == "matrix-member":     # ... and the live header names x2 as a packet member
            s.files[EDGES] = edges(None, mutate=lambda h, es: h.update(
                packet=list(h.get("packet") or []) + [os.path.basename(s.x2)]))
    elif kind == "clash-need":          # both headers list PRD-baz.md (m2 lacks it); the live one adds contracts/PRD-baz.md
        s.files["built-prds/PRD-baz.md"] = b"# PRD-baz (fixture v1)\n"
        s.files["contracts/PRD-baz.md"] = b"# contract named like PRD-baz (fixture)\n"
        s.files[s.x2] = matrix(slugs=["foo", "bar", "baz"], tag=" x2")     # no slug error for baz
        m2.members[os.path.basename(s.x2)] = s.files[s.x2]
        frozen_live(s, lambda h, es: h.update(prds=h["prds"] + ["PRD-baz.md"]),
                    lambda h, es: h.update(prds=h["prds"] + ["PRD-baz.md"],
                                           external=[{"name": "hermes", "contract": "contracts/PRD-baz.md"}]))
    elif kind == "mx-member-frozen":    # m2 keeps its frozen header, lists no x2; the live header names x2
        del m2.members[os.path.basename(s.x2)]
        s.files[EDGES] = edges(None, mutate=lambda h, es: h.update(
            packet=list(h.get("packet") or []) + [os.path.basename(s.x2)]))
    return s


for _k in ("frozen-prds", "frozen-packet", "frozen-contract", "frozen-dupbase", "frozen-clash", "dupbase-other",
           "clash-other", "edges", "edges-member", "noheader-dupbase", "matrix-noheader", "matrix-member",
           "mx-member-frozen", "clash-need"):
    CASES[f"live-bound-{_k}"] = (lambda k=_k, nolog=False: held_class(k, nolog))


# AC 5 held rule, launch state: m2 bound by the path of r2's launch row, then edited after the launch (a
# line appended, so m2's scope id is no longer the row's) or deleted. Its copies no longer record the state
# when r2 launched (R3: "edited or deleted after a launch"), so no error on m2 is held and its repairs copy
# holds no row. A launch row with no scope_id records no id to compare: noid-held (m2 unedited, both headers
# list PRD-bar.md, m2 does not) is held; noid-deleted (m2 deleted) is not.
def late(kind, nolog=False):
    s = held_class("frozen-prds", nolog) if kind in ("edited", "noid-held") else live_bound("none", nolog)
    if kind == "edited-row":            # frozen row 1 (in m2's copy) has a short sweep
        s.rows[0]["sweep"] = s.rows[0]["sweep"][:1]
    if kind.startswith("noid"):
        del s.dec[-1]["scope_id"]
    if kind in ("edited", "edited-row"):
        s.post_edit = ("notes/snapshots/m2/m2.sha256", "0" * 64 + "  late-addition.md\n")
    elif kind in ("deleted", "noid-deleted"):
        s.live_override["notes/snapshots/m2/m2.sha256"] = None
    return s


for _k in ("edited", "edited-row", "deleted", "noid-held", "noid-deleted"):
    CASES[f"late-{_k}"] = (lambda k=_k, nolog=False: late(k, nolog))


# AC 5 held rule, missing rows: three (m2 bound by r2, m3 pending), the live repairs file drops row 1
# (F1, m1 -> m2). m2's copy holds row 1 (the reviewer of m2 read it: repair-missing and the undeclared
# PRD-foo.md change are new), is listed but differs from its digest (no hold), holds no row or is not
# listed (m2 froze no row: both are carried). row-dropped-pair: m3 bound too (a launch row on m3), the
# live file drops row 2 (F2, m2 -> m3), which m3's copy holds.
def row_dropped(kind, nolog=False):
    s = build("three", nolog=nolog)
    r1, r2 = (json.dumps(r) + "\n" for r in s.rows)
    m2, m3 = s.mans["m2"], s.mans["m3"]
    if kind == "pair":
        s.drow(at(14, 30), S["R3"], role="review", man=m3)
        s.raw_rep = r1.encode()
        m2.members[RB] = r1.encode()
        m3.members[RB] = (r1 + r2).encode()
        return s
    s.raw_rep = r2.encode()
    m3.members[RB] = r2.encode()
    if kind == "copy":
        m2.members[RB] = r1.encode()
    elif kind == "badcopy":
        m2.members[RB] = r1.encode()
        m2.copies[RB] = (r1 + r1).encode()
    elif kind == "empty":
        m2.members[RB] = b""
    elif kind == "unlisted":
        del m2.members[RB]
    return s


for _k in ("copy", "badcopy", "empty", "unlisted", "pair"):
    CASES["row-dropped" + ("" if _k == "copy" else f"-{_k}")] = (lambda k=_k, nolog=False: row_dropped(k, nolog))


# AC 5 held rule, the repairs copy evaluated at the latest bound manifest's launch (round 3): the frozen
# evaluation reads the copy beside that manifest with the withdrawals recorded before its latest launch, over
# the findings that existed then.
# - notoken-pair: no Mission: line ever carries repairs=; PRD-foo.md moved between bound m1 and m2 (r1 APPROVE,
#   no findings): no row existed at either launch, so the undeclared change is carried (held).
# - void-row: ac8 without row 2 (F1, m1 -> m2r): F1's only row names m2, whose withdrawal E2 recorded before
#   r3's launch on m3; void at that launch too (held). void-row-s3: the same, but only the pending entry
#   withdraws m2 (S3): at the launch the row answered F1 and (m1, m2r) was no pair (both exit).
# - live-absent: three, the live repairs file deleted; m2's copy holds row 1 (exit).
# - own-finding: live-bound-none, but r2 (launched on m2, still the last manifest) returned FIX with F2: F2 did
#   not exist at r2's launch (exit); own-finding-notoken: the same with no repairs= token, where F1 of r1 is held.
def frozen_eval(kind, nolog=False):
    if kind == "notoken-pair":
        s = live_bound("none", nolog)
        s.files.pop("notes/reviews/r1/verdict.txt.findings.jsonl", None)
        s.review("notes/reviews/r1", S["R1"], [("foo", "APPROVE"), ("bar", "APPROVE")], "APPROVE")
        s.entries[0]["lines"]["State"] = "State: foo=linted foo=reviewed:APPROVE bar=linted bar=reviewed:APPROVE"
        s.rows = []
        del s.mans["m2"].members[RB]
        s.pending["lines"]["State"] = ("State: foo=linted foo=reviewed:APPROVE bar=reviewed:APPROVE "
                                       "foo=reviewed:APPROVE bar=reviewed:APPROVE")
        setp(s, "Mission", f"Mission: {NAME} scope={s.scope}")
    elif kind in ("void-row", "void-row-s3"):
        s = CASES["ac8"](nolog=nolog)
        del s.rows[1]
        s.frozen_rows["m2r"] = 1
        if kind == "void-row-s3":
            e2 = s.entries[-1]
            e2["lines"]["Mission"] = e2["lines"]["Mission"].replace(" withdrawn=notes/snapshots/m2/m2.sha256", "")
            s.pending["lines"]["Mission"] += " withdrawn=notes/snapshots/m2/m2.sha256"
    elif kind == "live-absent":
        s = build("three", nolog=nolog)
        s.live_override[REP] = None
    else:
        s = live_bound("none", nolog)
        s.review("notes/reviews/r2", S["R2"], [("foo", "APPROVE"), ("bar", "FIX")], "FIX", findings=[F2])
        st = s.pending["lines"]["State"]
        s.pending["lines"]["State"] = st[:st.rindex(" bar=reviewed:APPROVE")] + " bar=reviewed:FIX"
        if kind == "own-finding-notoken":
            s.rows = []
            del s.mans["m2"].members[RB]
            setp(s, "Mission", f"Mission: {NAME} scope={s.scope}")
    return s


for _k in ("notoken-pair", "void-row", "void-row-s3", "live-absent", "own-finding", "own-finding-notoken"):
    CASES[_k] = (lambda k=_k, nolog=False: frozen_eval(k, nolog))


# AC 8: E2 records the withdrawal of m2 (edges copy unlisted) with r2 on m2r returning APPROVE; E3 (pending
# here, appended by the test) extends scope= with m3 (an amended bar), omits withdrawn= and binds r3 APPROVE
@case("ac8")
def _(nolog=False):
    s = withdrawn_case("edges-unlisted", nolog)
    m2r = s.mans["m2r"]
    r2 = s.review("notes/reviews/r2", S["R2"], [("foo", "APPROVE"), ("bar", "APPROVE")], "APPROVE")
    s.drow(at(14, 0), S["R2"], role="review", man=m2r)
    e2 = dict(s.pending)
    e2["lines"] = dict(e2["lines"])
    e2["lines"]["Review"] = e2["lines"]["Review"] + [r2]
    e2["lines"]["State"] = "foo=linted foo=reviewed:FIX foo=reviewed:APPROVE bar=reviewed:APPROVE bar=reviewed:APPROVE"
    e2["lines"]["State"] = "State: " + e2["lines"]["State"]
    s.entries.append(e2)
    s.drow(at(15, 30), S["A3"] if "A3" in S else S["X1"], role="author")
    a3 = S["X1"]
    s.files["built-prds/PRD-bar.md"] = prd("bar", 2).encode()
    m3 = Man("m3", members({"foo": 2, "bar": 2}, s.x2, s.files[s.x2], s.files[EDGES], rep=True))
    s.mans["m3"] = m3
    s.rows.append({"finding": None, "class": None, "author_session": a3, "before": "notes/snapshots/m2r/m2r.sha256",
                   "after": "notes/snapshots/m3/m3.sha256", "changed": ["PRD-bar.md"],
                   "sweep": sweep_for(s.files[EDGES], ["PRD-bar.md"]), "disposition": "amended", "reason": "bar re-worded"})
    s.frozen_rows["m2r"] = 2
    x3 = mx_rel(16)
    s.files[x3] = matrix(tag=" x3")
    m3.members = {k: v for k, v in m3.members.items() if not k.endswith("-adversarial.md")}
    m3.members[os.path.basename(x3)] = s.files[x3]
    r3 = s.review("notes/reviews/r3", S["R3"], [("foo", "APPROVE"), ("bar", "APPROVE")], "APPROVE")
    s.drow(at(16, 30), S["R3"], role="review", man=m3)
    s.pending = {"ts": at(17), "lines": s.entry_lines(s.route(a3, at(15, 30)), x3, e2["lines"]["Review"] + [r3],
                                                     "foo=reviewed:FIX foo=reviewed:APPROVE foo=reviewed:APPROVE foo=eligible "
                                                     "bar=reviewed:APPROVE bar=reviewed:APPROVE bar=reviewed:APPROVE bar=eligible",
                                                     f"Mission: {NAME} scope={s.scope},notes/snapshots/m3/m3.sha256")}
    return s


def finish(s):
    """Apply the cases' post-build flags that need the final bytes."""
    m2 = s.mans.get("m2")
    if getattr(s, "fix_live_rows", None) is not None:
        live_rows = [dict(r) for r in s.rows]
        live_rows[0]["sweep"] = s.fix_live_rows
        frozen = s.rep_bytes()
        for m in s.mans.values():
            if m.members.get(RB) == "@repairs":
                m.members[RB] = frozen
        s.raw_rep = "".join(json.dumps(r) + "\n" for r in live_rows).encode()
    if getattr(s, "edit_row1", False):
        for m in s.mans.values():
            if m.members.get(RB) == "@repairs":
                m.members[RB] = s.rep_bytes(s.frozen_rows.get(m.name, len(s.rows)))
        rows = [dict(r) for r in s.rows]
        rows[0]["sweep"] = rows[0]["sweep"][:1]
        s.raw_rep = "".join(json.dumps(r) + "\n" for r in rows).encode()
    if m2 is not None and getattr(m2, "extra_live", False):
        m2.members[RB] = s.rep_bytes(s.frozen_rows.get("m2", len(s.rows)))
        txt = "".join(f"{sha(b(v))}  {('../../missions/' + k) if k == RB else k}\n" for k, v in m2.members.items())
        m2.lines_override = txt
    if m2 is not None and getattr(m2, "spell", False):
        pass
    sb = s.mans.get("m2b")
    if sb is not None and getattr(sb, "spell", False):
        for k, v in list(sb.members.items()):
            if v == "@repairs":
                sb.members[k] = s.rep_bytes()
        sb.lines_override = "".join(f"{sha(b(v))}  ./{k}\n" for k, v in sb.members.items())
        m2.members[RB] = s.rep_bytes() if m2.members.get(RB) == "@repairs" else m2.members.get(RB)
        if RB in m2.members:
            m2.members[RB] = sb.members[RB]
    if m2 is not None and getattr(s, "edit_m2_after_launch", False):
        s.post_edit = ("notes/snapshots/m2/m2.sha256", "0" * 64 + "  late-addition.md\n")
    return s


# ---- reviewer round 3 (db9e3389): cells of the held/fail class the author's table does not exercise
def rv3_notoken(nolog=False):
    """Bound m1 (r1 APPROVE, no findings) and bound m2 (r2 APPROVE); PRD-foo.md moved between them; the
    mission never carried a repairs= token and no repairs file exists. The undeclared change is in both
    manifests' frozen state (no row declared it when r2 launched): R1 holds it."""
    s = live_bound("none", nolog)
    s.files.pop("notes/reviews/r1/verdict.txt.findings.jsonl", None)
    s.review("notes/reviews/r1", S["R1"], [("foo", "APPROVE"), ("bar", "APPROVE")], "APPROVE")
    s.entries[0]["lines"]["State"] = "State: foo=linted foo=reviewed:APPROVE bar=linted bar=reviewed:APPROVE"
    s.rows = []
    del s.mans["m2"].members[RB]
    s.pending["lines"]["State"] = ("State: foo=linted foo=reviewed:APPROVE bar=reviewed:APPROVE "
                                   "foo=reviewed:APPROVE bar=reviewed:APPROVE")
    setp(s, "Mission", f"Mission: {NAME} scope={s.scope}")
    return s


def rv3_void_row(nolog=False):
    """ac8 without row 2 (F1, m1 -> m2r): F1's only row names the withdrawn m2 (void, packet-errors R2) in
    the live file and in the copies beside m2r and m3 alike (live file == m3's copy, byte for byte)."""
    s = CASES["ac8"](nolog=nolog)
    del s.rows[1]
    s.frozen_rows["m2r"] = 1
    return s


def rv3_mx_member_frozen(nolog=False):
    """live-bound-none with m2's frozen (legacy) header kept: m2 lists no x2 (the matrix the pending
    adversarial= names) and the live header names x2 as a packet member the frozen header lacks."""
    s = live_bound("none", nolog)
    x2 = os.path.basename(s.x2)
    del s.mans["m2"].members[x2]
    s.files[EDGES] = edges(None, mutate=lambda h, es: h.update(packet=list(h.get("packet") or []) + [x2]))
    return s


def rv3_clash_need(nolog=False):
    """m2's frozen header names PRD-baz.md (a prds member m2 lacks); the live header names it too and adds
    the contract contracts/PRD-baz.md: a live contract/member clash the frozen header lacks (exit), on the
    basename of a need the frozen header carries (held)."""
    s = live_bound("none", nolog)
    s.files["built-prds/PRD-baz.md"] = b"# PRD-baz (fixture v1)\n"
    s.files["contracts/PRD-baz.md"] = b"# contract named like PRD-baz (fixture)\n"
    x2 = os.path.basename(s.x2)         # the note's matrix and m2's copy carry a baz section (no slug error)
    s.files[s.x2] = matrix(slugs=["foo", "bar", "baz"], tag=" x2")
    s.mans["m2"].members[x2] = s.files[s.x2]
    frozen_live(s, lambda h, es: h.update(prds=h["prds"] + ["PRD-baz.md"]),
                lambda h, es: h.update(prds=h["prds"] + ["PRD-baz.md"],
                                       external=[{"name": "hermes", "contract": "contracts/PRD-baz.md"}]))
    return s


CASES["rv3-notoken-pair"] = (lambda nolog=False: rv3_notoken(nolog))
CASES["rv3-clash-need"] = (lambda nolog=False: rv3_clash_need(nolog))
CASES["rv3-void-row"] = (lambda nolog=False: rv3_void_row(nolog))
CASES["rv3-mx-member-frozen"] = (lambda nolog=False: rv3_mx_member_frozen(nolog))


# ---- reviewer round 4 (db9e3389): the repairs-copy arm against the frozen evaluation
REP2 = "notes/missions/drpe-mission.repairs-v2.jsonl"
RB2 = os.path.basename(REP2)


def rv4_void_row_s3(nolog=False):
    """ac8 without row 2 (F1, m1 -> m2r), but E2 lists m2 without withdrawing it; only the pending entry
    withdraws m2 (S3). At r3's launch on m3 the row (F1, m1 -> m2) answered F1 and m2 stood between m1 and
    m2r, so repair-missing F1 and the PRD-foo.md change between m1 and m2r are new: both exit."""
    s = CASES["ac8"](nolog=nolog)
    del s.rows[1]
    s.frozen_rows["m2r"] = 1
    e2 = s.entries[-1]
    e2["lines"]["Mission"] = e2["lines"]["Mission"].replace(" withdrawn=notes/snapshots/m2/m2.sha256", "")
    s.pending["lines"]["Mission"] += " withdrawn=notes/snapshots/m2/m2.sha256"
    return s


def rv4_rename(nolog=False):
    """three, but the pending entry starts a new repairs file: repairs= names REP2 (holding only row 2,
    F2 m2 -> m3), which pending m3 lists instead of the old file. At r2's launch on m2 the token named the
    old file, whose copy beside m2 holds row 1 (F1, m1 -> m2, changed PRD-foo.md): F1 was answered and the
    PRD-foo.md change between m1 and m2 declared. Both errors are new (the frozen evaluation lacks them)."""
    s = build("three", nolog=nolog)
    r1b, r2b = (json.dumps(r) + "\n" for r in s.rows)
    m3 = s.mans["m3"]
    del m3.members[RB]
    m3.members[RB2] = r2b.encode()
    s.files[REP2] = r2b.encode()
    s.raw_rep = (r1b + r2b).encode()            # the old file stays as it was
    s.pending["lines"]["Mission"] = s.pending["lines"]["Mission"].replace(f"repairs={REP}", f"repairs={REP2}")
    return s


def rv4_relaunch_issuer(nolog=False):
    """live-bound-none (r2 APPROVE on bound m2), the live repairs file and m2's copy hold one amended row
    (no row answers F1), and r1's session has a second launch row on m1 after r2's launch (a resume). F1
    existed when r2 launched (r1 returned before it): the frozen evaluation carries repair-missing F1."""
    s = live_bound("none", nolog)
    s.rows = [{"finding": None, "class": None, "author_session": s.route2[0], "before": "notes/snapshots/m1/m1.sha256",
               "after": "notes/snapshots/m2/m2.sha256", "changed": ["PRD-foo.md"],
               "sweep": sweep_for(s.files[EDGES], ["PRD-foo.md"]), "disposition": "amended", "reason": "foo re-worded"}]
    s.drow(at(14, 30), S["R1"], role="review", man=s.mans["m1"])
    return s


def rv4_tier3(nolog=False):
    """The same repairs state, no resume; r2's launch row on m2 carries m2's scope id with role "reviewer"
    (not "review"): m2 is bound through r2's Review: line (R3), r2 is no chain review, so F1 of r1 is checked
    against the review about to launch on m2. F1 existed when r2 launched: carried."""
    s = rv4_relaunch_issuer(nolog)
    s.dec = [r for r in s.dec if not (r.get("session") == S["R1"] and r.get("ts") == at(14, 30))]
    for r in s.dec:
        if r.get("session") == S["R2"] and r.get("role") == "review":
            r["role"] = "reviewer"
    return s


CASES["rv4-void-row-s3"] = (lambda nolog=False: rv4_void_row_s3(nolog))
CASES["rv4-rename"] = (lambda nolog=False: rv4_rename(nolog))
CASES["rv4-relaunch-issuer"] = (lambda nolog=False: rv4_relaunch_issuer(nolog))
CASES["rv4-tier3"] = (lambda nolog=False: rv4_tier3(nolog))


# ---- reviewer round 4 (db9e3389), second batch: controls for the branches no cell discriminates
def rv4_rename_rec(nolog=False):
    """ac8 (E2 recorded with repairs= the old file, r3 on m3 launched after it), but the pending entry names a
    new repairs file holding only row 1 (F1, m1 -> m2: void). At r3's launch the token named the old file,
    whose copy beside m3 answers F1 (row 2) and declares PRD-foo.md (m1 -> m2r) and PRD-bar.md (m2r -> m3)."""
    s = CASES["ac8"](nolog=nolog)
    s.files[REP2] = (json.dumps(s.rows[0]) + "\n").encode()
    s.pending["lines"]["Mission"] += f" repairs={REP2}"
    return s


def rv4_rereview_own(nolog=False):
    """live-bound-none, r2 on m2 returned FIX with F2, then r2b re-reviewed m2 unchanged (launched after r2,
    APPROVE). F2 existed at m2's latest launch (r2b's) and had no row there or now: repair-missing F2 HELD."""
    s = live_bound("none", nolog)
    s.review("notes/reviews/r2", S["R2"], [("foo", "APPROVE"), ("bar", "FIX")], "FIX", findings=[F2])
    r2b = s.review("notes/reviews/r2b", S["R3"], [("foo", "APPROVE"), ("bar", "APPROVE")], "APPROVE")
    s.drow(at(14, 30), S["R3"], role="review", man=s.mans["m2"])
    s.pending["lines"]["Review"] = s.pending["lines"]["Review"] + [r2b]
    st = s.pending["lines"]["State"]
    s.pending["lines"]["State"] = (st[:st.rindex(" bar=reviewed:APPROVE")] + " bar=reviewed:FIX"
                                   + " foo=reviewed:APPROVE bar=reviewed:APPROVE")
    return s


def rv4_pending_early(nolog=False):
    """rv4-void-row-s3 with the pending entry's own header written before r3's launch (16:00; r3 launched
    16:30): the withdrawal only the pending entry carries is still not in force at that launch (S3)."""
    s = rv4_void_row_s3(nolog)
    s.pending["ts"] = at(16)
    return s


CASES["rv4-rename-rec"] = (lambda nolog=False: rv4_rename_rec(nolog))
CASES["rv4-rereview-own"] = (lambda nolog=False: rv4_rereview_own(nolog))
CASES["rv4-pending-early"] = (lambda nolog=False: rv4_pending_early(nolog))


def main(argv):
    if argv[:1] == ["--list"]:
        print("\n".join(CASES))
        return 0
    if len(argv) != 2:
        print("usage: pfx.py <case>[@nolog] <outdir> | --list", file=sys.stderr)
        return 2
    name, nolog = (argv[0][:-6], True) if argv[0].endswith("@nolog") else (argv[0], False)
    if name not in CASES:
        print(f"unknown case {name}", file=sys.stderr)
        return 2
    s = finish(CASES[name](nolog=nolog))
    s.write(argv[1])
    pe = getattr(s, "post_edit", None)
    if pe:
        with open(os.path.join(argv[1], "home", pe[0]), "a", encoding="utf-8") as fh:
            fh.write(pe[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
