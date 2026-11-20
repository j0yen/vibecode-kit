#!/usr/bin/env python3
"""Fixture builder for the dlcr tests: the Dream lint's producer-contract repairs of A1723 decision 3 (the PRD author's
requests followon7/dream/requests/source-03415-lint-contract-repairs.md and its addendum 1).

Builds on tests/fixtures/drmx/mfx.py (Mission, rounds, the lint's own helpers), imported by path, the way
tests/fixtures/dgmr/gfx.py does. A case is one PRD home and a private decisions log under <outdir>.

- Repair 1 (r1-*): rounds(3) with review r1 (manifest m1) issuing F1 on foo and F2 on bar. F1's row is m1 -> m2 and F2's
  row m2 -> m3; m2 has no chain review (A1723 round 11b: a partial repair frozen, no review of it); r3 on m3 APPROVEs.
- Repair 2 (r2-*): rounds(2) whose r1 sidecar row F1 names no PRD and an undeclared external (A1723 review 12's R12-F3);
  the corrected sidecar r1/verdict.txt.findings.corrected-1.jsonl is written by r1's session, resumed.
- Repair 3 (r3-*): rounds(3) plus amended rows 3-5 of the pair (m1, m2) that overlap (A1723 rows 129-131) and a
  consolidation row 6 naming their union.

Usage: cfx.py <case> <outdir> | --list
"""
import copy
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("dlcr_mfx", os.path.join(HERE, "..", "drmx", "mfx.py"))
mfx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mfx)
rounds, resign, repairs_text, json_edges, S, at, sha = mfx.rounds, mfx.resign, mfx.repairs_text, mfx.json_edges, mfx.S, mfx.at, mfx.sha
FINDING = mfx.FINDING


def rewrite_repairs(M):
    """The repairs rows changed: the live file and the last manifest's frozen copy follow them; review rows re-signed."""
    M.files[M.rep_rel] = repairs_text(M.rep_rows)
    last = M.mans_decl[-1]
    last["members"][M.rb] = last["copies"][M.rb] = M.files[M.rep_rel]
    resign(M)
    return M


def entry_lines(M):
    return M.entries[-1]["lines"]


# ---------------------------------------------------------------- Repair 1
def r1_base(intermediate_reviewed=False, f1_row=True):
    """r1 issues F1 (foo) and F2 (bar) on m1; F1 m1 -> m2; F2 m2 -> m3; no chain review on m2 (or an APPROVE one)."""
    M = rounds(3)
    m1 = M.mans_decl[0]
    r2_rows = [r for r in M.rows if r.get("session") == S["R2"]]
    for r in r2_rows:
        M.rows.remove(r)
    for k in [k for k in M.files if k.startswith("notes/reviews/r2/")]:
        del M.files[k]
    lines = entry_lines(M)
    lines[:] = [ln for ln in lines if "notes/reviews/r2/" not in ln]
    rv1 = M.review("notes/reviews/r1", S["R1"], [("foo", "FIX"), ("bar", "FIX")], "FIX", findings=[
        {"id": "F1", "class": "missing-producer-runner", "prds": ["PRD-foo.md"], "consumers": ["PRD-bar.md"]},
        {"id": "F2", "class": "missing-producer-runner", "prds": ["PRD-bar.md"], "consumers": ["PRD-foo.md"]}])
    if intermediate_reviewed:          # negative 1: m2 carries an APPROVE chain review after all
        M.row(at(10, 1), S["R2"], role="review", scope=M.mans_decl[1]["rel"], sid=M.sid(M.mans_decl[1]))
        rv2 = M.review("notes/reviews/r2", S["R2"], [("foo", "APPROVE"), ("bar", "APPROVE")], "APPROVE")
    for i, ln in enumerate(lines):
        if ln.startswith("Review: notes/reviews/r1/"):
            lines[i] = rv1
            if intermediate_reviewed:
                lines.insert(i + 1, rv2)
            break
    mid = " foo=reviewed:APPROVE" if intermediate_reviewed else ""
    mid_b = " bar=reviewed:APPROVE" if intermediate_reviewed else ""
    for i, ln in enumerate(lines):
        if ln.startswith("State:"):
            lines[i] = (f"State: foo=linted foo=reviewed:FIX{mid} foo=reviewed:APPROVE bar=linted bar=reviewed:FIX{mid_b} "
                        "bar=reviewed:APPROVE foo=eligible bar=eligible")
    if not f1_row:                     # negative 2: F1 has no row, so no repairs row has m2 as its after
        M.rep_rows[:] = [r for r in M.rep_rows if r["finding"] != "F1"]
        rv1 = M.review("notes/reviews/r1", S["R1"], [("foo", "APPROVE"), ("bar", "FIX")], "FIX", findings=[
            {"id": "F2", "class": "missing-producer-runner", "prds": ["PRD-bar.md"], "consumers": ["PRD-foo.md"]}])
        for i, ln in enumerate(lines):
            if ln.startswith("Review: notes/reviews/r1/"):
                lines[i] = rv1
            if ln.startswith("State:"):
                lines[i] = ("State: foo=linted foo=reviewed:APPROVE foo=reviewed:APPROVE bar=linted bar=reviewed:FIX "
                            "bar=reviewed:APPROVE foo=eligible bar=eligible")
    M.m1 = m1
    return rewrite_repairs(M)


def r1_before_earlier():
    """negative 3: rounds(3) as built (F2 issued by r2 on m2) with F2's row moved back to m1 -> m2."""
    M = rounds(3)
    r = next(x for x in M.rep_rows if x["finding"] == "F2")
    r["before"], r["after"] = M.mans_decl[0]["rel"], M.mans_decl[1]["rel"]
    return rewrite_repairs(M)


# ---------------------------------------------------------------- Repair 2
SC_REL = "notes/reviews/r1/verdict.txt.findings.jsonl"
CORR_REL = "notes/reviews/r1/verdict.txt.findings.corrected-1.jsonl"


def r2_base():
    """rounds(2) with r1's F1 naming no PRD and an undeclared external (the R12-F3 shape)."""
    M = rounds(2)
    lines = entry_lines(M)
    rv1 = M.review("notes/reviews/r1", S["R1"], [("foo", "FIX"), ("bar", "APPROVE")], "FIX", findings=[
        {"id": "F1", "class": "missing-producer-runner", "prds": [], "consumers": ["external:l1-binding-check"]}])
    for i, ln in enumerate(lines):
        if ln.startswith("Review: notes/reviews/r1/"):
            lines[i] = rv1
    return rewrite_repairs(M)


def corrected(M, session=None, corrects=None, change=None, resume_row=True):
    """The corrected sidecar (prds and consumers given), and the resumed launch row of r1's session."""
    orig = M.files[SC_REL]
    rows = [json.loads(x) for x in orig.decode().split("\n") if x.strip()]
    body = []
    for r in rows:
        c = dict(r, prds=["PRD-foo.md"], consumers=["PRD-bar.md"])
        if change:
            c.update(change)
        body.append(c)
    head = {"corrects": corrects or sha(orig), "session": session or S["R1"]}
    M.files[CORR_REL] = "".join(json.dumps(x) + "\n" for x in [head] + body).encode()
    if resume_row:
        m1 = M.mans_decl[0]
        M.row(at(12), S["R1"], role="review", scope=m1["rel"], sid=M.sid(m1), resume=True)
    return M


def r2_resume_only_row():
    """review r21 L1: r1's only review launch row is itself the resume row; nothing shows a resumption after it."""
    M = corrected(r2_base(), resume_row=False)
    r = [x for x in M.rows if x.get("session") == S["R1"] and x.get("role") == "review"]
    assert len(r) == 1
    r[0]["resume"] = True
    return M


def r2_resume_before():
    """review r21 L1: the only resume row of r1's session is stamped before r1's review launch."""
    M = corrected(r2_base(), resume_row=False)
    m1 = M.mans_decl[0]
    M.row(at(9, 30), S["R1"], role="review", scope=m1["rel"], sid=M.sid(m1), resume=True)
    return M


def r2_dupkey():
    """review r21 L2: the corrected row repeats "class"; a parsed row keeps the last (the original's) value."""
    M = corrected(r2_base())
    lines = M.files[CORR_REL].decode().split("\n")
    assert lines[1].startswith("{")
    lines[1] = '{"class": "authority-bypass", ' + lines[1][1:]
    M.files[CORR_REL] = "\n".join(lines).encode()
    return M


# ---------------------------------------------------------------- Repair 3
def r3_base(consolidate=True, **kw):
    """rounds(3) plus amended rows 3-5 of (m1, m2): 3 names foo and the edge map, 4 foo, 5 the edge map (rows 3/4 and
    3/5 are repair-duplicate); row 6, when consolidate, consolidates 3-5 naming their union."""
    M = rounds(3)
    m1, m2 = M.mans_decl[0], M.mans_decl[1]
    ed = m1["members"][M.eb]
    sw_foo = [e["id"] for e in json_edges(ed) if "PRD-foo.md" in (e["producer"], e["consumer"])]

    def am(changed, sweep, **extra):
        r = {"finding": None, "class": None, "author_session": S["A"], "before": m1["rel"], "after": m2["rel"],
             "changed": changed, "sweep": sweep, "disposition": "amended", "reason": "fixture amendment"}
        r.update(extra)
        return r
    M.rep_rows += [am(["PRD-foo.md", M.eb], sw_foo), am(["PRD-foo.md"], sw_foo), am([M.eb], [])]
    if consolidate:
        row = am(["PRD-foo.md", M.eb], sw_foo, consolidates=[3, 4, 5], reason="consolidates rows 3-5")
        row.update(kw)
        M.rep_rows.append(row)
    return rewrite_repairs(M)


def r3_other_pair():
    """negative 1: row 6 also lists row 7, an amended row of (m2, m3)."""
    M = r3_base(consolidate=False)
    m1, m2, m3 = M.mans_decl
    ed = m1["members"][M.eb]
    sw_foo = [e["id"] for e in json_edges(ed) if "PRD-foo.md" in (e["producer"], e["consumer"])]
    M.rep_rows.append({"finding": None, "class": None, "author_session": S["A"], "before": m2["rel"], "after": m3["rel"],
                       "changed": [M.eb], "sweep": [], "disposition": "amended", "reason": "fixture amendment (m2, m3)"})
    M.rep_rows.append({"finding": None, "class": None, "author_session": S["A"], "before": m1["rel"], "after": m2["rel"],
                       "changed": ["PRD-foo.md", M.eb], "sweep": sw_foo, "disposition": "amended",
                       "reason": "consolidates rows 3-5 and 6", "consolidates": [3, 4, 5, 6]})
    return rewrite_repairs(M)


def r3_twice():
    """rule (d): row 7 consolidates row 3 again."""
    M = r3_base()
    r = copy.deepcopy(M.rep_rows[-1])
    r["consolidates"], r["changed"], r["reason"] = [3], ["PRD-foo.md", M.eb], "consolidates row 3 again"
    M.rep_rows.append(r)
    return rewrite_repairs(M)


def r3_other_session():
    """negative 3: the consolidation row's author is another author session (with its own launch row)."""
    M = r3_base(author_session=S["A2"])
    M.row(at(8, 5), S["A2"], role="author")
    return rewrite_repairs(M)


CASES = {
    "r1-positive": lambda: r1_base(),
    "r1-intermediate-reviewed": lambda: r1_base(intermediate_reviewed=True),
    "r1-intermediate-undeclared": lambda: r1_base(f1_row=False),
    "r1-before-earlier": r1_before_earlier,
    "r2-original": r2_base,
    "r2-positive": lambda: corrected(r2_base()),
    "r2-author-session": lambda: corrected(r2_base(), session=S["A"], resume_row=False),
    "r2-other-reviewer": lambda: corrected(r2_base(), session=S["R2"], resume_row=False),
    "r2-no-resume-row": lambda: corrected(r2_base(), resume_row=False),
    "r2-wrong-digest": lambda: corrected(r2_base(), corrects=hashlib.sha256(b"other sidecar bytes\n").hexdigest()),
    "r2-resume-only-row": r2_resume_only_row,
    "r2-resume-before": r2_resume_before,
    "r2-dupkey": r2_dupkey,
    "r3-original": lambda: r3_base(consolidate=False),
    "r3-positive": lambda: r3_base(),
    "r3-other-pair": r3_other_pair,
    "r3-omits-changed": lambda: r3_base(changed=["PRD-foo.md"]),
    "r3-other-session": r3_other_session,
    "r3-twice": r3_twice,
}
for _k, _v in (("id", "F9"), ("class", "authority-bypass"), ("counterexample", "another counterexample"),
               ("correction", "another correction"), ("control", "another control")):
    CASES[f"r2-changes-{_k}"] = (lambda k, v: lambda: corrected(r2_base(), change={k: v}))(_k, _v)


def main(argv):
    if argv[:1] == ["--list"]:
        print("\n".join(CASES))
        return 0
    if len(argv) != 2 or argv[0] not in CASES:
        print(f"usage: cfx.py <case> <outdir> | --list (cases: {' '.join(CASES)})", file=sys.stderr)
        return 2
    M = CASES[argv[0]]()
    resign(M)
    M.write(argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
