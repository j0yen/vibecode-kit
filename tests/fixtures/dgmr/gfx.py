#!/usr/bin/env python3
"""Fixture builder for the dgmr tests (PRD-dream-generation-aware-mission-records R1 and R4).

Builds on tests/fixtures/drmx/mfx.py (Mission, rounds, the lint's own matrix and edge-map helpers),
imported by path. A case is one PRD home and a private decisions log under <outdir>, written the way
mfx.py writes them; every review row records its manifest's scope_id.

R1 cases (legacy matrix) take the A1724 GEN1 shape: entry 1 carries no scope= and names matrix x1;
the manifest m1 frozen with x1 and a header without `matrix` is first listed by entry 2, whose
adversarial= names x2. The `-before` cases move every fixture date to 2026-11-17, before
LEGACY_MATRIX_SINCE; the others stay on the drmx fixture day (mfx.DAY), after it.

R4 cases (path keys) take rounds(2) (F1 on foo, repaired m1 -> m2) with m2 one directory deeper
(notes/snapshots/deep/m2/m2.sha256) and five data files data/g1..g5/graph.json listed by path in
both manifests; g2 and g4 move between m1 and m2.

Usage: gfx.py <case> <outdir> | --list
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("dgmr_mfx", os.path.join(HERE, "..", "drmx", "mfx.py"))
mfx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mfx)
Mission, rounds, resign, repairs_text, json_edges = mfx.Mission, mfx.rounds, mfx.resign, mfx.repairs_text, mfx.json_edges
S, at, mx_rel, prd, sha = mfx.S, mfx.at, mfx.mx_rel, mfx.prd, mfx.sha

OLD_DAY = "2026-11-17"          # before LEGACY_MATRIX_SINCE
DEEP = "notes/snapshots/deep/m2/m2.sha256"
M2 = "notes/snapshots/m2/m2.sha256"
DATA = [f"data/g{i}/graph.json" for i in range(1, 6)]
M1DIR, M2DIR = "notes/snapshots/m1", os.path.dirname(DEEP)


def rel_from(manifest_rel, target_rel):
    return os.path.relpath(target_rel, os.path.dirname(manifest_rel))


def _swap(x, old, new):
    if isinstance(x, bytes):
        return x.replace(old.encode(), new.encode())
    if isinstance(x, str):
        return x.replace(old, new)
    if isinstance(x, list):
        return [_swap(v, old, new) for v in x]
    if isinstance(x, dict):
        return {_swap(k, old, new): _swap(v, old, new) for k, v in x.items()}
    return x


def swap_all(M, old, new):
    """Replace a string everywhere a fixture keeps it (file names and bytes, manifests, rows, entries)."""
    M.files = _swap(M.files, old, new)
    for m in M.manifests:
        for k in ("rel", "members", "copies", "extra"):
            m[k] = _swap(m[k], old, new)
    M.rows[:] = _swap(M.rows, old, new)
    for e in M.entries:
        e["ts"], e["lines"] = _swap(e["ts"], old, new), _swap(e["lines"], old, new)
    return M


# ---------------------------------------------------------------- R1: the A1724 GEN1 shape
def gen1_shape(m1_matrices, before=True, named=True, m1_copies=None):
    """m1 lists the matrices m1_matrices ({basename: bytes}; m1_copies overrides a frozen copy's
    bytes); entry 1 (no scope=) names x1 in adversarial= unless named is False (then entry 1 skips
    its matrix); entry 2 lists m1 and m2."""
    M = Mission(header_matrix=False)
    x1, x2 = mx_rel(11), mx_rel(13)
    M.files[x1] = M.matrix(tag=" run 1")
    M.files[x2] = M.matrix(tag=" run 2")
    ed = M.edges()
    M.files[M.edges_rel] = ed
    m1 = M.manifest("notes/snapshots/m1/m1.sha256", dict({f"PRD-{s}.md": prd(s, 1) for s in M.slugs},
                                                        **m1_matrices, **{M.eb: ed}), copies=m1_copies)
    aff = ["PRD-foo.md", "PRD-bar.md"]
    row = {"finding": "F1", "class": "missing-producer-runner", "author_session": S["A"], "before": m1["rel"],
           "after": M2, "changed": ["PRD-foo.md"] + list(m1_matrices) + [os.path.basename(x2)],
           "sweep": [e["id"] for e in json_edges(ed) if e["producer"] in aff or e["consumer"] in aff],
           "disposition": "repaired"}
    M.files[M.rep_rel] = repairs_text([row])
    M.files["built-prds/PRD-foo.md"] = prd("foo", 2).encode()
    m2 = M.manifest(M2, {"PRD-foo.md": prd("foo", 2), "PRD-bar.md": prd("bar", 1),
                         os.path.basename(x2): M.files[x2], M.eb: ed, M.rb: M.files[M.rep_rel]})
    M.row(at(8), S["A"], role="author")
    M.row(at(11, 30), S["R1"], role="review", scope=m1["rel"], sid=M.sid(m1))
    M.row(at(12, 30), S["A2"], role="author")
    M.row(at(13, 30), S["R2"], role="review", scope=m2["rel"], sid=M.sid(m2))
    r1 = M.review("notes/reviews/r1", S["R1"], [("foo", "FIX"), ("bar", "APPROVE")], "FIX",
                  findings=[{"id": "F1", "class": "missing-producer-runner", "prds": ["PRD-foo.md"], "consumers": ["PRD-bar.md"]}])
    r2 = M.review("notes/reviews/r2", S["R2"], [("foo", "APPROVE"), ("bar", "APPROVE")], "APPROVE")
    M.entry(at(12), None, "foo=linted bar=linted", f"Mission: {M.name} edges={M.edges_rel}",
            x1 if named else "skipped: entry 1 wrote no matrix")
    M.entry(at(15), [r1, r2], "foo=reviewed:FIX foo=reviewed:APPROVE foo=eligible bar=reviewed:APPROVE bar=reviewed:APPROVE bar=eligible",
            f"Mission: {M.name} scope={m1['rel']},{m2['rel']} repairs={M.rep_rel}", x2, route=(S["A2"], at(12, 30)))
    M.x1, M.x2 = x1, x2
    return swap_all(M, mfx.DAY, OLD_DAY) if before else M


def _mx(M_like_tag, slugs=None):
    return Mission(header_matrix=False).matrix(slugs=slugs, tag=M_like_tag)


def c_legacy(kind, before=True):
    """m1's matrices: one (x1, named by entry 1, valid), none, two (x1 and x0), stale (x0, unnamed,
    sections for another slug), named-stale (x1, named, sections for another slug), unnamed-valid
    (x0, unnamed, valid at its listed digest), unnamed-moved (x0, unnamed, valid at its listed digest,
    but its frozen copy edited after the freeze)."""
    def f():
        x1, x0 = os.path.basename(mx_rel(11)), os.path.basename(mx_rel(10))
        run1, stale = _mx(" run 1"), _mx(" stale", slugs=["baz"])
        mats = {"one": {x1: run1}, "none": {}, "two": {x1: run1, x0: _mx(" run 0")}, "stale": {x0: stale},
                "named-stale": {x1: stale}, "unnamed-valid": {x0: _mx(" run 0")},
                "unnamed-moved": {x0: _mx(" run 0")}}[kind]
        copies = {x0: _mx(" run 0 moved")} if kind == "unnamed-moved" else None
        return gen1_shape(mats, before=before, named=not kind.startswith("unnamed"), m1_copies=copies)
    return f



def c_legacy_route():
    """legacy-one-before with the linted entry's header ts moved to the drmx day (after the
    constant) while its Route decision= stays on the old day: the first-listing entry is dated by
    its Route decision=, so R1 still applies."""
    M = c_legacy("one")()
    M.entries[-1]["ts"] = M.entries[-1]["ts"].replace(OLD_DAY, mfx.DAY)
    return M


def c_legacy_later():
    """legacy-one-before continued by a round on the drmx day (after the constant): m3 freezes m2's
    members with a new matrix x3, r3 (APPROVE) binds m3, and entry 3, linted last, lists m1, m2 and
    m3 with adversarial= x3. m1 is still first listed by entry 2 (before the constant), so R1 keeps
    its one matrix x1; dated by the linted entry instead, m1 would fall to drmx R2 and lack x2."""
    M = c_legacy("one")()
    x2b = os.path.basename(M.x2).replace(mfx.DAY, OLD_DAY)
    x3 = mx_rel(16)
    M.files[x3] = M.matrix(tag=" run 3")
    m2 = next(m for m in M.manifests if m["rel"] == M2)
    members3 = {k: v for k, v in m2["members"].items() if k != x2b}
    members3[os.path.basename(x3)] = M.files[x3]
    m3 = M.manifest("notes/snapshots/m3/m3.sha256", members3)
    M.row(at(9), S["A2"], role="author")
    M.row(at(16, 30), S["R3"], role="review", scope=m3["rel"], sid=M.sid(m3))
    r3 = M.review("notes/reviews/r3", S["R3"], [("foo", "APPROVE"), ("bar", "APPROVE")], "APPROVE")
    e2 = M.entries[-1]["lines"]
    reviews = [ln for ln in e2 if ln.startswith("Review:")] + [r3]
    state = ("foo=reviewed:FIX foo=reviewed:APPROVE foo=reviewed:APPROVE foo=eligible "
             "bar=reviewed:APPROVE bar=reviewed:APPROVE bar=reviewed:APPROVE bar=eligible")
    m1rel = "notes/snapshots/m1/m1.sha256"
    M.entry(at(17), reviews, state, f"Mission: {M.name} scope={m1rel},{M2},{m3['rel']} repairs={M.rep_rel}", x3,
            route=(S["A2"], at(9)))
    return M


# ---------------------------------------------------------------- R4: path keys
def paths_base(last_verdict="APPROVE", bar_by_path=False):
    """rounds(2) with m2 at DEEP and five graph.json listed by path in both manifests (g2, g4 move)."""
    M = rounds(2, last_verdict=last_verdict)
    m1, m2 = M.mans_decl
    v1 = {d: f'{{"graph": "{d}", "v": 1}}\n'.encode() for d in DATA}
    v2 = {d: (f'{{"graph": "{d}", "v": 2}}\n'.encode() if d in (DATA[1], DATA[3]) else v1[d]) for d in DATA}
    m2["rel"] = DEEP
    for r in M.rows:
        if r.get("scope") == M2:
            r["scope"] = DEEP
    for e in M.entries:
        e["lines"] = [ln.replace(M2, DEEP) for ln in e["lines"]]
    for r in M.rep_rows:
        if r["after"] == M2:
            r["after"] = DEEP
    m1["extra"] += [f"{sha(v1[d])}  {rel_from(m1['rel'], d)}" for d in DATA]
    m2["extra"] += [f"{sha(v2[d])}  {rel_from(DEEP, d)}" for d in DATA]
    for d in DATA:
        M.files[d] = v2[d]
    M.v1, M.v2, M.m1, M.m2 = v1, v2, m1, m2
    if bar_by_path:                     # PRD-bar.md listed by path (the live file), and moved m1 -> m2
        b1, b2 = prd("bar", 1).encode(), prd("bar", 2).encode()
        for m, v in ((m1, b1), (m2, b2)):
            del m["members"]["PRD-bar.md"]
            m["copies"].pop("PRD-bar.md", None)
            m["extra"].append(f"{sha(v)}  {rel_from(m['rel'], 'built-prds/PRD-bar.md')}")
        M.files["built-prds/PRD-bar.md"] = b2
        M.bar = (b1, b2)
    return M


def refreeze(M):
    """The repairs rows changed: the live file and m2's frozen member follow them; review rows re-signed."""
    M.files[M.rep_rel] = repairs_text(M.rep_rows)
    M.m2["members"][M.rb] = M.files[M.rep_rel]
    M.m2["copies"][M.rb] = M.files[M.rep_rel]
    resign(M)
    return M


def declare(M, rows=None, moved=(1, 3)):
    """Row F1 names g2 and g4 by path (relative to m2's directory) with their delta records."""
    r = M.rep_rows[0]
    paths = [rel_from(DEEP, DATA[i]) for i in moved]
    r["changed"] = r["changed"] + paths
    r["delta"] = {"changed": [{"path": p, "before": sha(M.v1[DATA[i]]), "after": sha(M.v2[DATA[i]])}
                              for p, i in zip(paths, moved)]}
    return r


def _pick(pred):
    """aux.json bytes (Y at m1, Y moved, X) whose digests stand in the order pred(Y, Y moved, X) asks."""
    for i in range(10000):
        y1, y2, x1 = (f'{{"y": 1, "n": {i}}}\n'.encode(), f'{{"y": 2, "n": {i}}}\n'.encode(),
                      f'{{"x": 1, "n": {i}}}\n'.encode())
        if pred(sha(y1), sha(y2), sha(x1)):
            return y1, y2, x1
    raise SystemExit("gfx.py: no aux.json bytes in the asked digest order")


def c_paths(variant):
    def f():
        M = paths_base(last_verdict="FIX" if variant in ("amended-held", "amended-unswept-held") else "APPROVE",
                       bar_by_path=variant.startswith("amended"))
        r = M.rep_rows[0]
        if variant in ("ok", "wrong-pair", "no-record", "delta-bare", "added-removed", "added-wrong", "changed-added",
                       "member-twice", "repairs-twice", "a1724-rows", "a1724-rows-wrong", "cross-dir-declared",
                       "record-spelling", "member-path-unmoved", "twin-hide", "twin-show", "twin-apart", "member-asym-hide",
                       "member-asym-show", "member-far-hide", "member-asym-once") \
                or variant.startswith("amended"):
            declare(M)
        if variant == "wrong-pair":
            r["delta"]["changed"][1]["after"] = sha(b"not the after bytes\n")
        elif variant == "no-record":
            del r["delta"]["changed"][1]
        elif variant == "legacy-bare":
            r["changed"] = r["changed"] + ["graph.json"]
        elif variant == "delta-bare":
            r["changed"] = r["changed"] + ["graph.json"]
        elif variant == "legacy-path":                # a row without delta naming g2 and g4 by path
            r["changed"] = r["changed"] + [rel_from(DEEP, DATA[i]) for i in (1, 3)]
        elif variant in ("added-removed", "added-wrong", "changed-added"):
            g6, g0 = "data/g6/graph.json", "data/g0/graph.json"
            n6, o0 = b'{"graph": "g6", "v": 1}\n', b'{"graph": "g0", "v": 1}\n'
            M.files[g6] = n6
            M.files[g0] = o0
            M.m1["extra"].append(f"{sha(o0)}  {rel_from(M.m1['rel'], g0)}")
            M.m2["extra"].append(f"{sha(n6)}  {rel_from(DEEP, g6)}")
            p6, p0 = rel_from(DEEP, g6), rel_from(M.m1["rel"], g0)
            want6 = sha(n6) if variant != "added-wrong" else sha(b"other bytes\n")
            r["delta"]["added"] = [{"path": p6, "sha256": want6}]
            r["delta"]["removed"] = [{"path": p0, "sha256": sha(o0)}]
            if variant == "changed-added":
                r["changed"] = r["changed"] + [p6]
            else:
                r["added"] = [p6]
            r["removed"] = [p0]
        elif variant in ("a1724-rows", "a1724-rows-wrong"):   # A1724 rows 16 and 41: paths outside the PRD home,
            e1, e2, ct = b"edit log v1\n", b"edit log v2\n", b"class table\n"     # changed and added, with records
            p1 = "../../../../contract/EDIT-LOG.md"            # from notes/snapshots/m1: <out>/contract/EDIT-LOG.md
            p2 = "../../../../../contract/EDIT-LOG.md"         # from notes/snapshots/deep/m2: the same file
            pc = "../../../../../repair-3/out/CLASS-TABLE.md"  # from deep/m2: <out>/repair-3/out/CLASS-TABLE.md
            M.m1["extra"].append(f"{sha(e1)}  {p1}")
            M.m2["extra"] += [f"{sha(e2)}  {p2}", f"{sha(ct)}  {pc}"]
            r["changed"] = r["changed"] + [p2]
            r["delta"]["changed"].append({"path": p2, "before": sha(e1 if variant == "a1724-rows" else e2), "after": sha(e2)})
            r["added"] = [pc]
            r["delta"]["added"] = [{"path": pc, "sha256": sha(ct)}]
        elif variant in ("cross-dir-undeclared", "cross-dir-declared"):   # a file beside m1: m1 lists it bare,
            a1, a2 = b'{"aux": 1}\n', b'{"aux": 2}\n'                     # m2 by path; it moves
            M.m1["members"]["aux.json"] = M.m1["copies"]["aux.json"] = a1
            pa = rel_from(DEEP, "notes/snapshots/m1/aux.json")
            M.m2["extra"].append(f"{sha(a2)}  {pa}")
            if variant == "cross-dir-declared":
                r["changed"] = r["changed"] + [pa]
                r["delta"]["changed"].append({"path": pa, "before": sha(a1), "after": sha(a2)})
        elif variant in ("twin-hide", "twin-show"):     # Q1 (request 4): aux.json twice, Y beside m1 and X beside m2;
            y1, y2, x1 = _pick((lambda a, b, c: c < a and c < b) if variant == "twin-hide"     # m1 lists Y bare and
                               else (lambda a, b, c: c > a and c > b))     # X by path, m2 X bare and Y by path; Y moves,
            M.m1["extra"] += [f"{sha(y1)}  aux.json", f"{sha(x1)}  {rel_from(M.m1['rel'], M2DIR + '/aux.json')}"]
            M.m2["extra"] += [f"{sha(x1)}  aux.json", f"{sha(y2)}  {rel_from(DEEP, M1DIR + '/aux.json')}"]
            M.files[M1DIR + "/aux.json"], M.files[M2DIR + "/aux.json"] = y2, x1     # undeclared (hide: X smallest)
        elif variant == "twin-apart":   # over-strict control: Y beside m1, X beside m2, one basename, each manifest
            y1 = _pick(lambda a, b, c: True)[0]      # lists only its own file (the frozen-copy shape), same bytes
            M.m1["extra"].append(f"{sha(y1)}  aux.json")
            M.m2["extra"].append(f"{sha(y1)}  aux.json")
            M.files[M1DIR + "/aux.json"] = M.files[M2DIR + "/aux.json"] = y1
        elif variant.startswith(("member-asym", "member-far")):   # review r20 F1: notes.md is a packet member of m2's header
            ed = M.edges(matrix=M.mxb[1], mutate=lambda h, es: h.update(packet=["notes.md"]))      # only; m1 lists it for two
            M.m2["members"][M.eb] = M.m2["copies"][M.eb] = ed       # files: X beside m2 by path at x1 and Y beside m1 bare
            M.files[M.edges_rel] = ed                               # (far: Y in drafts/) at x2, x2 the smaller (hide) or the
            for i in range(10000):                                  # larger (show); X moves x1 -> x2 undeclared. once (the
                x1, x2 = f"notes v1 {i}\n".encode(), f"notes v2 {i}\n".encode()     # over-strict control): m1 lists X once,
                if variant == "member-asym-once" or (sha(x2) < sha(x1)) == (variant != "member-asym-show"):      # unmoved
                    break
            px = rel_from(M.m1["rel"], M2DIR + "/notes.md")
            if variant == "member-asym-once":
                M.m1["extra"].append(f"{sha(x2)}  {px}")
            else:
                far = variant == "member-far-hide"
                M.m1["extra"] += [f"{sha(x2)}  {'../../../drafts/notes.md' if far else 'notes.md'}", f"{sha(x1)}  {px}"]
                M.files["drafts/notes.md" if far else M1DIR + "/notes.md"] = x2
            M.m2["members"]["notes.md"] = M.m2["copies"]["notes.md"] = x2
        elif variant in ("dupkey-hide", "dupkey-show"):  # Q1: m2 lists g2 twice, at its bytes and (spelled with ./)
            p = rel_from(DEEP, DATA[1]).replace("/g2/", "/./g2/")    # at m1's digest, the smaller (hide), or at a
            dg = sha(M.v1[DATA[1]]) if variant == "dupkey-hide" else sha(b"g2 listed again\n")   # larger one (show);
            assert (dg < sha(M.v2[DATA[1]])) == (variant == "dupkey-hide")                   # g2 and g4 move undeclared
            M.m2["extra"].append(f"{dg}  {p}")
        elif variant == "record-spelling":      # g4's record names the same path spelled with ./
            r["delta"]["changed"][1]["path"] = r["delta"]["changed"][1]["path"].replace("/g4/", "/./g4/")
        elif variant == "member-path-unmoved":  # a row without delta names PRD-bar.md (unmoved) by path
            ed = M.m1["members"][M.eb]
            M.rep_rows.append({"finding": None, "class": None, "author_session": S["A"], "before": M.m1["rel"],
                               "after": DEEP, "changed": [rel_from(DEEP, "built-prds/PRD-bar.md")],
                               "sweep": [e["id"] for e in json_edges(ed) if "PRD-bar.md" in (e["producer"], e["consumer"])],
                               "disposition": "amended", "reason": "bar named by path, unchanged"})
        elif variant == "member-twice":
            M.m2["extra"].append(f"{sha(M.m2['members'][M.eb])}  {rel_from(DEEP, M.edges_rel)}")
        elif variant.startswith("amended"):
            b1, b2 = M.bar
            p = rel_from(DEEP, "built-prds/PRD-bar.md")
            ed = M.m1["members"][M.eb]
            sweep = [e["id"] for e in json_edges(ed) if "PRD-bar.md" in (e["producer"], e["consumer"])]
            row2 = {"finding": None, "class": None, "author_session": S["A"], "before": M.m1["rel"],
                    "after": DEEP, "changed": [p],
                    "delta": {"changed": [{"path": p, "before": sha(b1), "after": sha(b2)}]},
                    "sweep": sweep if variant in ("amended-swept", "amended-held", "amended-legacy-path") else [],
                    "disposition": "amended", "reason": "PRD bar re-worded between the reviews"}
            if variant == "amended-legacy-path":    # a row without delta names the header member by path
                del row2["delta"]
            M.rep_rows.append(row2)
        M = refreeze(M)
        if variant == "repairs-twice":       # the repairs file listed by its frozen copy and by its live path
            M.m2["extra"].append(f"{sha(M.files[M.rep_rel])}  {rel_from(DEEP, M.rep_rel)}")
        return M
    return f


CASES = {
    "legacy-one-before": c_legacy("one"),
    "legacy-one-after": c_legacy("one", before=False),
    "legacy-none-before": c_legacy("none"),
    "legacy-two-before": c_legacy("two"),
    "legacy-stale-before": c_legacy("stale"),
    "legacy-unnamed-valid-before": c_legacy("unnamed-valid"),
    "legacy-named-stale-before": c_legacy("named-stale"),
    "legacy-unnamed-moved-before": c_legacy("unnamed-moved"),
    "legacy-route-before": c_legacy_route,
    "legacy-later-entry": c_legacy_later,
    "header-matrix": lambda: rounds(3),
}
for _v in ("plain", "ok", "wrong-pair", "no-record", "legacy-bare", "legacy-path", "delta-bare", "added-removed", "added-wrong",
           "changed-added", "member-twice", "repairs-twice", "a1724-rows", "a1724-rows-wrong", "amended-unswept",
           "amended-unswept-held", "amended-swept", "amended-held", "amended-legacy-path", "member-path-unmoved",
           "cross-dir-undeclared", "cross-dir-declared", "record-spelling", "twin-hide", "twin-show", "twin-apart",
           "dupkey-hide", "dupkey-show", "member-asym-hide", "member-asym-show", "member-far-hide", "member-asym-once"):
    CASES["paths-" + _v] = c_paths(_v)


def main(argv):
    if argv[:1] == ["--list"]:
        print("\n".join(CASES))
        return 0
    if len(argv) != 2 or argv[0] not in CASES:
        print(f"usage: gfx.py <case> <outdir> | --list (cases: {' '.join(CASES)})", file=sys.stderr)
        return 2
    M = CASES[argv[0]]()
    resign(M)
    M.write(argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
