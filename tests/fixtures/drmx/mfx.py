#!/usr/bin/env python3
"""Mission fixture builder for the drmx tests (PRD-dream-matrix-per-manifest) and the tests that
build on it (drpe, drle).

The fixture matrices and edge maps come from the lint's own selftest helpers (`mx_file`,
`mission_edges`), loaded from skills/dream/scripts/dream-run-note-lint.sh (its Python body, every
definition but the final `sys.exit(main(...))`), so they follow the selftest's grammar. A fixture
is one PRD home and a private decisions log under <outdir>: <outdir>/home and
<outdir>/decisions.jsonl. Every manifest sits in its own directory beside a copy of each file it
lists, and every review row records the manifest's scope_id computed by this module's `scope_id`
(the canonical text the lint's --scope-id hashes).

Usage: mfx.py <case> <outdir>        build one case (see CASES at the end of the file)
       mfx.py --list                 print the case names
Cases of other prefixes import this file by path (importlib) and call `Mission`.
"""
import copy
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
LINT = os.path.join(REPO, "skills", "dream", "scripts", "dream-run-note-lint.sh")


def lint_helpers(path=LINT):
    src = open(path, encoding="utf-8").read()
    code = src.split("\n#__PYTHON__\n", 1)[1].split("\n#__PYTHON_END__", 1)[0]
    code = code.rsplit("\nsys.exit(main(sys.argv[1:]))", 1)[0]
    ns = {"__name__": "dream_lint_helpers"}
    exec(compile(code, path + ":python", "exec"), ns)
    return ns


H = lint_helpers()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def as_bytes(x):
    return x if isinstance(x, bytes) else x.encode("utf-8")


def scope_id(text):
    """The canonical scope id of a manifest text (the lint's R4 canon for well-formed lines)."""
    lines = [ln for ln in text.split("\n") if ln]
    canon = sorted({ln[:64] + "  " + ln[66:].rsplit("/", 1)[-1] + "\n" for ln in lines})
    return sha("".join(canon).encode())


S = {k: f"cccccccc-0000-4000-8000-0000000000{n:02d}" for n, k in enumerate(
    ["A", "A2", "R1", "R2", "R3", "R4", "R5", "R6", "X1", "X2", "X3", "N", "N0", "U", "F", "C"], 1)}
DAY = "2027-03-01"


def at(hh, mm=0):
    return f"{DAY}T{hh:02d}:{mm:02d}:00-08:00"


def mx_rel(hh):
    return f"notes/reviews/{at(hh)}-adversarial.md"


def prd(slug, v):
    return f"# PRD-{slug} (fixture v{v})\n"


FINDING = {"counterexample": "a run that satisfies every local AC and fails the mission",
           "correction": "the minimal correction", "control": "a discriminating control"}


class Mission:
    """A mission note under construction. Live files and manifests are declared, then written."""

    def __init__(self, name="drmx-mission", task="MX-1", slugs=("foo", "bar"), header_matrix=True):
        self.name, self.task, self.slugs = name, task, list(slugs)
        self.header_matrix = header_matrix
        self.files = {}          # home-relative path -> bytes (live files)
        self.manifests = []      # [{rel, members: {basename: bytes}, copies: {basename: bytes}, extra: [lines]}]
        self.rows = []           # decisions rows
        self.entries = []        # [{ts, lines}]
        self.eb = f"{name}.edges.jsonl"
        self.rb = f"{name}.repairs.jsonl"
        self.edges_rel = f"notes/missions/{self.eb}"
        self.rep_rel = f"notes/missions/{self.rb}"
        for s in self.slugs:
            self.files[f"built-prds/PRD-{s}.md"] = prd(s, 1).encode()

    # ---- live content builders
    def edges(self, matrix=None, prds=None, mutate=None):
        """Edge map text: the selftest's mission_edges over prds (known edges only), the header named
        for this mission and, when given, carrying `matrix`."""
        prds = list(prds or self.slugs)

        def mut(h, es):
            h["mission"] = self.name
            if matrix is not None:
                h["matrix"] = matrix
            if len(prds) == 1:   # one PRD: its edge goes to the external only
                es[:] = [dict(es[1], id="E0", producer=f"PRD-{prds[0]}.md")]
            if mutate:
                mutate(h, es)
        return H["mission_edges"](prds, mutate=mut, known_only=True).encode()

    def matrix(self, slugs=None, tag="", drop_family=None, sections=None):
        slugs = list(self.slugs if slugs is None else slugs)
        if sections is not None:
            body = sections
        else:
            body = "".join(H["mx_section"](s, drop=drop_family) for s in slugs)
        return H["mx_file"](slugs, sections=body, pre=f"# Adversarial matrix (fixture{tag})\n\n").encode()

    # ---- manifests
    def manifest(self, rel, members, copies=None, extra=()):
        """Declare a manifest at rel listing members {basename: bytes}; a copy of each member is
        written beside it (copies overrides a copy's bytes, None leaves it out)."""
        m = {"rel": rel, "members": dict(members), "copies": dict(members), "extra": list(extra)}
        for b, v in (copies or {}).items():
            m["copies"][b] = v
        self.manifests.append(m)
        return m

    def man_text(self, m):
        return "".join(f"{sha(as_bytes(v))}  {b}\n" for b, v in m["members"].items()) + "".join(x + "\n" for x in m["extra"])

    def sid(self, m):
        return scope_id(self.man_text(m))

    # ---- reviews and rows
    def row(self, ts, session, decision="launch", role=None, scope=None, sid=None, **kw):
        r = {"ts": ts, "decision": decision, "task_id": self.task, "skill": "dream", "route": "opus-high",
             "model": "claude-opus-5-5", "effort": "high", "account": "lane-x", "session": session,
             "resume": False, "reasons": "fixture"}
        if role is not None:
            r["role"] = role
            r["scope"] = scope if scope is not None else ""
            r["scope_id"] = sid if sid is not None else ""
        r.update(kw)
        self.rows.append(r)
        return r

    def review(self, d, session, verdicts, mission, findings=None, result=True, sidecar_bytes=None):
        """Verdict file d/verdict.txt (+ d/verdict.txt.findings.jsonl when findings), and its result=
        capture d/result.json carrying the same lines and the findings= digest."""
        lines = [f"{s} {v} fixture-reviewer" for s, v in verdicts]
        if mission:
            lines.append(f"mission={mission} {session}")
        self.files[f"{d}/verdict.txt"] = ("".join(x + "\n" for x in lines)).encode()
        sc = None
        if findings:
            sc = sidecar_bytes if sidecar_bytes is not None else "".join(json.dumps(dict(FINDING, **f)) + "\n" for f in findings).encode()
            self.files[f"{d}/verdict.txt.findings.jsonl"] = sc
        if result:
            text = "Done.\n" + f"findings={'none' if sc is None else sha(sc)}\n" + "\n".join(lines)
            self.files[f"{d}/result.json"] = json.dumps({"type": "result", "is_error": False, "session_id": session,
                                                         "result": text}).encode() + b"\n"
        return f"Review: {d}/verdict.txt reviewer-session={session}" + (f" result={d}/result.json" if result else "")

    def entry(self, ts, reviews, state, mission, adversarial, route=None, task=None, extra=()):
        route = route or (S["A"], at(8))
        adv = adversarial if adversarial.startswith("skipped:") else f"{adversarial} uncovered=1"
        lines = ["Contract: /fixture/build-contract.md   Hooks: dream.lint", "Seeds: fixture", "Lineage: greenfield",
                 "Drafted: " + ", ".join(f"PRD-{s}.md" for s in self.slugs) + "   Build order: " + " → ".join(self.slugs),
                 "Lint: clean   Eligibility: pending scan",
                 f"Task: {task or self.task}   Consumer: hermes",
                 f"Route: opus-high claude-opus-5-5 high session={route[0]} decision={route[1]}",
                 f"Analysis: wwhtbt=skipped: fixture 5whys=skipped: fixture adversarial={adv}"]
        lines += list(reviews) if reviews else ["Review: none"]
        lines += [f"State: {state}", mission] + list(extra) + ["Open questions: none"]
        self.entries.append({"ts": ts, "lines": lines})
        return self.entries[-1]

    # ---- output
    def write(self, out):
        home = os.path.join(out, "home")
        for rel, data in self.files.items():
            p = os.path.join(home, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as fh:
                fh.write(as_bytes(data))
        for m in self.manifests:
            p = os.path.join(home, m["rel"])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(self.man_text(m))
            for b, v in m["copies"].items():
                if v is None:
                    continue
                with open(os.path.join(os.path.dirname(p), b), "wb") as fh:
                    fh.write(as_bytes(v))
        with open(os.path.join(out, "decisions.jsonl"), "w", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(r) + "\n" for r in self.rows))
        os.makedirs(os.path.join(home, "notes"), exist_ok=True)
        text = "# dream log (fixture)\n\n" + "\n".join(
            f"## {e['ts']}  /dream  vision-{self.name}\n" + "\n".join(e["lines"]) + "\n" for e in self.entries)
        with open(os.path.join(home, "notes", "dream-log.md"), "w", encoding="utf-8") as fh:
            fh.write(text)
        return out


def repairs_text(rows):
    return "".join(json.dumps(r) + "\n" for r in rows).encode()


def rounds(n=3, header_matrix=True, changed_matrix="both", one_name=False, prds_by_round=None,
           matrix_tweak=None, man_tweak=None, live_edges=None, adversarial=None, entry_ts=None,
           last_verdict="APPROVE", state_extra=" foo=eligible bar=eligible"):
    """The run3 shape reduced: n manifests m1..mn, one run entry. Round k freezes PRD versions, the
    round's matrix (renamed each round unless one_name), the edge map (whose header names the round's
    matrix when header_matrix) and, from round 2 on, the repairs file. Review rk binds mk; r1..r(n-1)
    return FIX with one finding each (F1 on foo, F2 on bar, ...), answered by a repaired row (k -> k+1)
    whose `changed` names the moved PRD and the edge map, plus the old matrix, the new one, both
    (run3's rows) or neither (changed_matrix). The last review returns `last_verdict`."""
    M = Mission(header_matrix=header_matrix)
    sl = M.slugs
    prds_by_round = prds_by_round or [sl] * n
    vers = {s: 1 for s in sl}
    mats = [mx_rel(9 if one_name else 9 + k) for k in range(n)]
    mxb = [os.path.basename(x) for x in mats]
    rows, reviews, states = [], [], {s: [] for s in sl}
    M.row(at(8), S["A"], role="author")
    mans = []
    for k in range(n):
        pr = prds_by_round[k]
        mtx = M.matrix(slugs=pr, tag=f" round {k + 1}" if not one_name else "")
        if matrix_tweak:
            mtx = matrix_tweak(k, mtx) or mtx
        M.files[mats[k]] = mtx
        ed = M.edges(matrix=mxb[k] if header_matrix else None, prds=pr)
        members = {f"PRD-{s}.md": prd(s, vers[s]) for s in pr}
        members[mxb[k]] = mtx
        members[M.eb] = ed
        if rows:
            members[M.rb] = repairs_text(rows)
        rel = f"notes/snapshots/m{k + 1}/m{k + 1}.sha256"
        m = M.manifest(rel, members)
        if man_tweak:
            man_tweak(k, m, M)
        mans.append(m)
        sess = S[f"R{k + 1}"]
        rd = f"notes/reviews/r{k + 1}"
        M.row(at(10, k), sess, role="review", scope=rel, sid=M.sid(m))
        if k < n - 1:
            moved = sl[k % len(sl)]
            other = [s for s in pr if s != moved]
            cons = [f"PRD-{other[0]}.md"] if other else ["external:hermes"]
            fid = f"F{k + 1}"
            verdicts = [(s, "FIX" if s == moved else "APPROVE") for s in pr]
            reviews.append(M.review(rd, sess, verdicts, "FIX", findings=[
                {"id": fid, "class": "missing-producer-runner", "prds": [f"PRD-{moved}.md"], "consumers": cons}]))
            vers[moved] += 1
            M.files[f"built-prds/PRD-{moved}.md"] = prd(moved, vers[moved]).encode()
            ch = [f"PRD-{moved}.md"]
            nxt = mxb[k + 1]
            if not one_name:
                ch += {"both": [mxb[k], nxt], "old": [mxb[k]], "new": [nxt], "neither": []}[changed_matrix]
            if (header_matrix and not one_name) or prds_by_round[k + 1] != pr:
                ch.append(M.eb)
            aff = [f"PRD-{moved}.md"] + cons
            sweep = [e["id"] for e in json_edges(members[M.eb]) if e["producer"] in aff or e["consumer"] in aff]
            rows.append({"finding": fid, "class": "missing-producer-runner", "author_session": S["A"],
                         "before": rel, "after": f"notes/snapshots/m{k + 2}/m{k + 2}.sha256", "changed": ch,
                         "sweep": sweep, "disposition": "repaired"})
        else:
            verdicts = [(s, last_verdict) for s in pr]
            reviews.append(M.review(rd, sess, verdicts, last_verdict))
        for s, v in verdicts:
            states[s].append(f"reviewed:{v}")
    M.files[M.edges_rel] = live_edges if live_edges is not None else mans[-1]["members"][M.eb]
    if rows:
        M.files[M.rep_rel] = repairs_text(rows)
    st = " ".join(f"{s}=linted " + " ".join(f"{s}={v}" for v in states[s]) for s in sl) + state_extra
    mission = (f"Mission: {M.name} edges={M.edges_rel} scope=" + ",".join(m["rel"] for m in mans)
               + (f" repairs={M.rep_rel}" if rows else ""))
    M.entry(entry_ts or at(14), reviews, st.strip(), mission, adversarial or mats[-1])
    M.mats, M.mxb, M.mans_decl, M.rep_rows = mats, mxb, mans, rows
    return M


def json_edges(b):
    out = []
    for ln in b.decode().split("\n")[1:]:
        if ln.strip():
            out.append(json.loads(ln))
    return out


def resign(M):
    """Re-record every review row's scope_id from its manifest's current declared text."""
    by = {m["rel"]: m for m in M.manifests}
    for r in M.rows:
        if r.get("role") == "review" and r.get("scope") in by:
            r["scope_id"] = M.sid(by[r["scope"]])


# ---------------------------------------------------------------- drmx cases
def c_run3(**kw):
    return rounds(3, **kw)


def c_missing_header(**kw):
    """m2's frozen header names x2, m2 lists no x2."""
    def tw(k, m, M):
        if k == 1:
            del m["members"][M_mxb(m)]
    return rounds(3, man_tweak=tw)


def M_mxb(m):
    return next(b for b in m["members"] if b.endswith("-adversarial.md"))


def c_missing_legacy(**kw):
    """Legacy headers (no matrix key), one matrix name: m1 lists no matrix."""
    def tw(k, m, M):
        if k == 0:
            del m["members"][M_mxb(m)]
    return rounds(2, header_matrix=False, one_name=True, man_tweak=tw)


def c_last_differs(**kw):
    """The last manifest's frozen header (and the live one) names x2 while adversarial= names x3."""
    def tw(k, m, M):
        if k == 2:
            old = os.path.basename(mx_rel(10))
            m["members"] = {b: v for b, v in m["members"].items() if not b.endswith("-adversarial.md")}
            m["members"][old] = M.files[mx_rel(10)]
            m["copies"] = dict(m["members"])
            m["members"][M.eb] = m["copies"][M.eb] = M.edges(matrix=old)
    M = rounds(3, man_tweak=tw)
    M.files[M.edges_rel] = M.manifests[2]["members"][M.eb]
    for r in M.rep_rows:
        if r["after"].endswith("m3.sha256"):
            r["changed"] = [x for x in r["changed"] if not x.endswith("-adversarial.md") and x != M.eb]
    _rebuild_repairs(M)
    return M


def _rebuild_repairs(M):
    """After editing M.rep_rows: every manifest listing the repairs file lists the rows written before
    its freeze (rows whose `after` is that manifest or earlier); the live file holds all rows."""
    order = [m["rel"] for m in M.manifests]
    for m in M.manifests:
        if M.rb in m["members"]:
            k = order.index(m["rel"])
            rs = [r for r in M.rep_rows if r["after"] in order[:k + 1]]
            m["members"][M.rb] = m["copies"][M.rb] = repairs_text(rs)
    M.files[M.rep_rel] = repairs_text(M.rep_rows)
    resign(M)


def c_live_differs(**kw):
    """The live edges header names another matrix than adversarial= after the last freeze."""
    M = rounds(3)
    M.files[M.edges_rel] = M.edges(matrix="2027-03-01T23:00:00-08:00-adversarial.md")
    return M


def c_bad_matrix(value):
    def f(**kw):
        M = rounds(3)
        M.files[M.edges_rel] = M.edges(matrix=None, mutate=lambda h, es: h.__setitem__("matrix", value))
        return M
    return f


def c_bad_vision(**kw):
    M = rounds(3)
    M.files["visions/drmx-vision.md"] = b"# vision\n"
    M.files[M.edges_rel] = M.edges(matrix=None, mutate=lambda h, es: h.update(packet=["drmx-vision.md"], matrix="drmx-vision.md"))
    return M


def c_two(changed_matrix="both"):
    def f(**kw):
        return rounds(2, changed_matrix=changed_matrix)
    return f


def c_added_prd(**kw):
    """m1 freezes prds [foo] with x1 (section foo); m2 adds bar with x2 (sections foo, bar)."""
    return rounds(2, prds_by_round=[["foo"], ["foo", "bar"]])


def c_m1_tweak(fn, legacy=False):
    def f(**kw):
        def tw(k, m, M):
            if k == 0:
                fn(m, M)
        return rounds(2, man_tweak=tw, header_matrix=not legacy, one_name=legacy)
    return f


def _m1_no_matrix(m, M):
    del m["members"][M_mxb(m)]
    m["copies"] = dict(m["members"])


def _m1_copy(content_fn):
    def g(m, M):
        b = M_mxb(m)
        new = content_fn(M)
        m["members"][b] = new        # the listed digest follows the copy (a frozen bad matrix)
        m["copies"][b] = new
    return g


def _m1_wrong_digest(m, M):
    b = M_mxb(m)
    m["copies"][b] = m["members"][b] + b"tampered after the freeze\n"


def two_entries(M, e1, e2):
    """Helper for the cross-entry cases: e1 and e2 are (ts, reviews, state, mission, adversarial, route)."""
    for e in (e1, e2):
        M.entry(e[0], e[1], e[2], e[3], e[4], route=e[5])


def c_prefix(listed=True):
    """The drmr/variants/prefix shape: entry 1 (adversarial=skipped:, Review: none) first lists m1;
    entry 2 names matrix x and binds review r1 to m1 (legacy header, no matrix key)."""
    def f(**kw):
        M = Mission(header_matrix=False)
        x = mx_rel(13)
        M.files[x] = M.matrix()
        ed = M.edges()
        M.files[M.edges_rel] = ed
        members = {f"PRD-{s}.md": prd(s, 1) for s in M.slugs}
        if listed:
            members[os.path.basename(x)] = M.files[x]
        members[M.eb] = ed
        m1 = M.manifest("notes/snapshots/m1/m1.sha256", members)
        M.row(at(8), S["A"], role="author")
        M.row(at(12, 30), S["R1"], role="review", scope=m1["rel"], sid=M.sid(m1))
        r1 = M.review("notes/reviews/r1", S["R1"], [(s, "APPROVE") for s in M.slugs], "APPROVE")
        ml = f"Mission: {M.name} edges={M.edges_rel} scope={m1['rel']}"
        M.entry(at(12), None, " ".join(f"{s}=linted" for s in M.slugs), ml, "skipped: entry 1 of the prefix shape")
        M.entry(at(14), [r1], " ".join(f"{s}=linted {s}=reviewed:APPROVE" for s in M.slugs), ml, x)
        return M
    return f


def c_legacy_pair(**kw):
    """A legacy-headed mission continued in a later run entry: entry 1 (x1) binds r1 (FIX, F1) to m1;
    entry 2 (x2, later than entry 1) freezes m2 with x2 and the repairs file, binds r2 (APPROVE),
    and row 1 (m1 -> m2) names the old and the new matrix in `changed` as run3's rows did."""
    M = Mission(header_matrix=False)
    x1, x2 = mx_rel(11), mx_rel(13)
    M.files[x1] = M.matrix(tag=" run 1")
    M.files[x2] = M.matrix(tag=" run 2")
    ed = M.edges()
    M.files[M.edges_rel] = ed
    m1 = M.manifest("notes/snapshots/m1/m1.sha256", dict({f"PRD-{s}.md": prd(s, 1) for s in M.slugs},
                                                        **{os.path.basename(x1): M.files[x1], M.eb: ed}))
    aff = ["PRD-foo.md", "PRD-bar.md"]
    row = {"finding": "F1", "class": "missing-producer-runner", "author_session": S["A"], "before": m1["rel"],
           "after": "notes/snapshots/m2/m2.sha256",
           "changed": ["PRD-foo.md", os.path.basename(x1), os.path.basename(x2)],
           "sweep": [e["id"] for e in json_edges(ed) if e["producer"] in aff or e["consumer"] in aff],
           "disposition": "repaired"}
    M.files[M.rep_rel] = repairs_text([row])
    M.files["built-prds/PRD-foo.md"] = prd("foo", 2).encode()
    m2 = M.manifest("notes/snapshots/m2/m2.sha256", {"PRD-foo.md": prd("foo", 2), "PRD-bar.md": prd("bar", 1),
                                                    os.path.basename(x2): M.files[x2], M.eb: ed,
                                                    M.rb: M.files[M.rep_rel]})
    M.row(at(8), S["A"], role="author")
    M.row(at(11, 30), S["R1"], role="review", scope=m1["rel"], sid=M.sid(m1))
    M.row(at(12, 30), S["A2"], role="author")
    M.row(at(13, 30), S["R2"], role="review", scope=m2["rel"], sid=M.sid(m2))
    r1 = M.review("notes/reviews/r1", S["R1"], [("foo", "FIX"), ("bar", "APPROVE")], "FIX",
                  findings=[{"id": "F1", "class": "missing-producer-runner", "prds": ["PRD-foo.md"], "consumers": ["PRD-bar.md"]}])
    r2 = M.review("notes/reviews/r2", S["R2"], [("foo", "APPROVE"), ("bar", "APPROVE")], "APPROVE")
    M.entry(at(12), [r1], "foo=linted foo=reviewed:FIX bar=linted bar=reviewed:APPROVE",
            f"Mission: {M.name} edges={M.edges_rel} scope={m1['rel']}", x1)
    M.entry(at(15), [r1, r2], "foo=reviewed:FIX foo=reviewed:APPROVE foo=eligible bar=reviewed:APPROVE bar=reviewed:APPROVE bar=eligible",
            f"Mission: {M.name} scope={m1['rel']},{m2['rel']} repairs={M.rep_rel}", x2, route=(S["A2"], at(12, 30)))
    return M


CASES = {
    "run3": c_run3,
    "run3-old": lambda **kw: rounds(3, changed_matrix="old"),
    "run3-onename-legacy": lambda **kw: rounds(3, header_matrix=False, one_name=True),
    "missing-header": c_missing_header,
    "missing-legacy": c_missing_legacy,
    "last-differs": c_last_differs,
    "live-differs": c_live_differs,
    "matrix-empty": c_bad_matrix(""),
    "matrix-int": c_bad_matrix(5),
    "matrix-path": c_bad_matrix("notes/reviews/2027-03-01T11:00:00-08:00-adversarial.md"),
    "matrix-prd": c_bad_matrix("PRD-foo.md"),
    "matrix-not-md": c_bad_matrix("2027-03-01T11:00:00-08:00-adversarial.txt"),
    "matrix-vision": c_bad_vision,
    "two-both": c_two("both"),
    "two-old": c_two("old"),
    "two-new": c_two("new"),
    "two-neither": c_two("neither"),
    "added-prd": c_added_prd,
    "m1-no-matrix": c_m1_tweak(_m1_no_matrix),
    "m1-no-sections": c_m1_tweak(_m1_copy(lambda M: M.matrix(slugs=[], sections=""))),
    "m1-missing-slug": c_m1_tweak(_m1_copy(lambda M: M.matrix(slugs=["foo"]))),
    "m1-bad-grammar": c_m1_tweak(_m1_copy(lambda M: M.matrix(drop_family="Falsifier quality"))),
    "m1-wrong-digest": c_m1_tweak(_m1_wrong_digest),
    "rename-no-header": lambda **kw: rounds(2, header_matrix=False),
    "prefix-listed": c_prefix(True),
    "prefix-unlisted": c_prefix(False),
    "legacy-pair": c_legacy_pair,
}


def main(argv):
    if argv[:1] == ["--list"]:
        print("\n".join(CASES))
        return 0
    if len(argv) != 2 or argv[0] not in CASES:
        print(f"usage: mfx.py <case> <outdir> | --list (cases: {' '.join(CASES)})", file=sys.stderr)
        return 2
    M = CASES[argv[0]]()
    resign(M)
    M.write(argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
