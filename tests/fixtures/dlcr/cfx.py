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
- Repair 4 (r4-*, addendum 2): r1's finding F1 names the consumer external:newx, which m1's frozen header does not declare;
  m2's frozen header declares it and the F1 row (m1 -> m2, the author's) names the edges file (A1723 review 13's sidecar
  rows 1-3, the 093500Z header and repairs row 136).
- Repair 5 (r5-*, addendum 3): rounds(3)'s entry split into a pre-review entry (13:00, Review: lines of r1 and r2) and the
  post-review entry (14:00) adding r3's line, both naming the 11:00 matrix (A1723's review-14 entries).

Usage: cfx.py <case> <outdir> | --list
"""
import copy
import hashlib
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True       # no __pycache__ beside mfx.py: datr_h1_redate compares tests/fixtures/drmx byte for byte
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


# ---------------------------------------------------------------- Repair 4
def with_newx(M, k):
    """Manifest k's frozen edges header (and the live one, for the last manifest) declares the external newx."""
    ed = M.edges(matrix=M.mxb[k], mutate=lambda h, es: h["external"].append("newx"))
    m = M.mans_decl[k]
    m["members"][M.eb] = m["copies"][M.eb] = ed
    if k == len(M.mans_decl) - 1:
        M.files[M.edges_rel] = ed
    return M


def r4_base(declare_at=1, n=2, live_only=False, row_eb=True, reviewer_row=False, two_names=False, row_author=None,
            pair=None):
    """rounds(n) whose r1 finding F1 names consumers PRD-bar.md and external:newx; declare_at: the manifest index whose
    frozen header declares newx (1 = m2, the next; 2 = m3, two later; None = none); live_only: only the live header;
    two_names: F1 also names external:other, which no header declares; row_author: the edges row is written by this
    session instead of the mission author (a session with no author launch row); pair: (before, after) manifest indexes
    of the author's edges row instead of (0, 1)."""
    M = rounds(n)
    cons = ["PRD-bar.md", "external:newx"] + (["external:other"] if two_names else [])
    rv1 = M.review("notes/reviews/r1", S["R1"], [("foo", "FIX"), ("bar", "APPROVE")], "FIX", findings=[
        {"id": "F1", "class": "missing-producer-runner", "prds": ["PRD-foo.md"], "consumers": cons}])
    lines = entry_lines(M)
    for i, ln in enumerate(lines):
        if ln.startswith("Review: notes/reviews/r1/"):
            lines[i] = rv1
    if declare_at is not None:
        with_newx(M, declare_at)
    if live_only:
        M.files[M.edges_rel] = M.edges(matrix=M.mxb[-1], mutate=lambda h, es: h["external"].append("newx"))
    r = M.rep_rows[0]
    if not row_eb or reviewer_row:
        r["changed"] = [x for x in r["changed"] if x != M.eb]
    if pair is not None:
        r["before"], r["after"] = M.mans_decl[pair[0]]["rel"], M.mans_decl[pair[1]]["rel"]
    if row_author is not None:           # the only (m1, m2) row naming the edges file is another session's
        r["changed"] = [x for x in r["changed"] if x != M.eb]
        M.rep_rows.append({"finding": None, "class": None, "author_session": row_author, "before": M.mans_decl[0]["rel"],
                           "after": M.mans_decl[1]["rel"], "changed": [M.eb], "sweep": [], "disposition": "amended",
                           "reason": "another session's edges row"})
    if reviewer_row:                     # the only (m1, m2) row naming the edges file is the reviewer's, an admitted
        ar = M.row(at(9, 50), S["R1"], role="author")   # author too: an author launch row placed before its
        M.rows.remove(ar)                                # review launch row, so the review binding still holds
        M.rows.insert(next(i for i, x in enumerate(M.rows) if x.get("session") == S["R1"]), ar)
        M.rep_rows.append({"finding": None, "class": None, "author_session": S["R1"], "before": M.mans_decl[0]["rel"],
                           "after": M.mans_decl[1]["rel"], "changed": [M.eb], "sweep": [], "disposition": "amended",
                           "reason": "the reviewer's edges row"})
    return rewrite_repairs(M)


# ---------------------------------------------------------------- Repair 5
def r5_base(prev_all=False, scope_extra=False, other_scope_id=False, prev_uncovered=None, older_matrix=False,
            drop_old_line=False, new_author_role=False, prev_task=None, prev_scope_drop=False):
    """rounds(3)'s entry (14:00) split: a pre-review entry at 13:00 with the same lines but r3's Review: line (or all of
    them, prev_all), then the post-review entry. scope_extra: the post entry's scope= gains a manifest; other_scope_id:
    r3's launch row names m1; prev_uncovered: the pre entry's uncovered= value; older_matrix: the post entry names round
    1's matrix; drop_old_line: the post entry drops r1's Review: line; new_author_role: r3's latest launch row is an
    author row carrying m3's scope_id; prev_task: the pre-review entry's Task: names this task instead, after a
    same-task copy of it at 12:30 (so the mission record's earlier scope is unchanged); prev_scope_drop: the pre entry's
    scope= lacks m1 (the post entry adds a manifest that is not the last)."""
    M = rounds(3)
    post = M.entries[-1]
    pre = [ln for ln in post["lines"] if prev_all or not ln.startswith("Review: notes/reviews/r3/")]
    if prev_uncovered is not None:
        pre = [ln.replace(" uncovered=1", f" uncovered={prev_uncovered}") if ln.startswith("Analysis:") else ln for ln in pre]
    if prev_scope_drop:
        pre = [ln.replace("notes/snapshots/m1/m1.sha256,", "") if ln.startswith("Mission:") else ln for ln in pre]
    if prev_task is not None:
        M.entries.insert(len(M.entries) - 1, {"ts": at(12, 30), "lines": list(pre)})
        pre = [re.sub(r"^Task: \S+", f"Task: {prev_task}", ln) for ln in pre]
    M.entries.insert(len(M.entries) - 1, {"ts": at(13), "lines": pre})
    if scope_extra:
        post["lines"] = [ln.replace("m3/m3.sha256", "m3/m3.sha256,notes/snapshots/m4/m4.sha256") if ln.startswith("Mission:")
                         else ln for ln in post["lines"]]
    if other_scope_id:
        r3 = [r for r in M.rows if r.get("session") == S["R3"]][-1]
        r3["scope"], r3["scope_id"] = M.mans_decl[0]["rel"], M.sid(M.mans_decl[0])
    if older_matrix:
        post["lines"] = [ln.replace(mfx.mx_rel(11), mfx.mx_rel(9)) if ln.startswith("Analysis:") else ln for ln in post["lines"]]
    if drop_old_line:
        post["lines"] = [ln for ln in post["lines"] if not ln.startswith("Review: notes/reviews/r1/")]
    if new_author_role:
        m3 = M.mans_decl[-1]
        M.row(at(10, 30), S["R3"], role="author", scope=m3["rel"], sid=M.sid(m3))
    M.no_resign = other_scope_id
    return M


# ---------------------------------------------------------------- review r23 (L1, L2, L4)
def r2_dup_in_original():
    """r2-positive whose original sidecar row 1 repeats the key class (the findings= binding re-signed over it)."""
    M = r2_base()
    orig = M.files[SC_REL].decode().rstrip("\n").split("\n")
    orig[0] = '{"class": "authority-bypass", ' + orig[0][1:]
    sb = ("\n".join(orig) + "\n").encode()
    rv1 = M.review("notes/reviews/r1", S["R1"], [("foo", "FIX"), ("bar", "APPROVE")], "FIX", findings=[{}], sidecar_bytes=sb)
    lines = entry_lines(M)
    for i, ln in enumerate(lines):
        if ln.startswith("Review: notes/reviews/r1/"):
            lines[i] = rv1
    return corrected(rewrite_repairs(M))


def r4_other_task_author():
    """r4 whose only edges row is by a session whose author launch row is of another task."""
    x = "cccccccc-0000-4000-8000-0000000000ee"
    M = r4_base(row_author=x)
    M.row(at(9, 10), x, role="author", task_id="OTHER-TASK")
    return M


def r5_later_row(**kw):
    """r5-positive plus a later launch row of r3's session that is not of this task's dream (another task or skill)."""
    M = r5_base()
    M.row(at(10, 55), S["R3"], role="author", **kw)
    return M


def r5_first_round(keep_none=False):
    """rounds(1): a pre-review entry at 13:00 with `Review: none`, then the post-review entry with r1's review of m1 (the
    last manifest), both naming the same matrix; keep_none: the post entry keeps `Review: none` too."""
    M = mfx.rounds(1)
    post = M.entries[-1]
    pre = [ln for ln in post["lines"] if not ln.startswith("Review:")]
    i = next(k for k, ln in enumerate(pre) if ln.startswith("State:"))
    pre.insert(i, "Review: none")
    M.entries.insert(len(M.entries) - 1, {"ts": at(13), "lines": pre})
    if keep_none:
        j = next(k for k, ln in enumerate(post["lines"]) if ln.startswith("Review:"))
        post["lines"].insert(j, "Review: none")
    return M


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
    "r2-dup-in-original": r2_dup_in_original,
    "r3-original": lambda: r3_base(consolidate=False),
    "r3-positive": lambda: r3_base(),
    "r3-other-pair": r3_other_pair,
    "r3-omits-changed": lambda: r3_base(changed=["PRD-foo.md"]),
    "r3-other-session": r3_other_session,
    "r3-twice": r3_twice,
    "r4-original": lambda: r4_base(declare_at=None),
    "r4-positive": lambda: r4_base(),
    "r4-later-only": lambda: r4_base(declare_at=2, n=3),
    "r4-live-only": lambda: r4_base(declare_at=None, live_only=True),
    "r4-no-row": lambda: r4_base(row_eb=False),
    "r4-reviewer-row": lambda: r4_base(reviewer_row=True),
    "r4-two-names": lambda: r4_base(two_names=True),
    "r4-foreign-row": lambda: r4_base(row_author="cccccccc-0000-4000-8000-0000000000ff"),
    "r4-other-reviewer-row": lambda: r4_base(row_author=S["R2"]),
    "r4-wrong-before": lambda: r4_base(pair=(1, 1)),
    "r4-wrong-after": lambda: r4_base(pair=(0, 0)),
    "r4-other-task-author": r4_other_task_author,
    "r5-positive": lambda: r5_base(),
    "r5-scope-added": lambda: r5_base(scope_extra=True),
    "r5-no-new-review": lambda: r5_base(prev_all=True),
    "r5-other-scope-id": lambda: r5_base(other_scope_id=True),
    "r5-uncovered-changed": lambda: r5_base(prev_uncovered=2),
    "r5-older-matrix": lambda: r5_base(older_matrix=True),
    "r5-old-line-dropped": lambda: r5_base(drop_old_line=True),
    "r5-new-line-author-role": lambda: r5_base(new_author_role=True),
    "r5-prev-other-task": lambda: r5_base(prev_task="MX-2"),
    "r5-scope-dropped": lambda: r5_base(prev_scope_drop=True),
    "r5-later-other-task-row": lambda: r5_later_row(task_id="OTHER-TASK"),
    "r5-later-non-dream-row": lambda: r5_later_row(skill="other"),
    "r5-first-round-review-none": lambda: r5_first_round(),
    "r5-first-round-keeps-none": lambda: r5_first_round(keep_none=True),
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
    if not getattr(M, "no_resign", False):
        resign(M)
    M.write(argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
