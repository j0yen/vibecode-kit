"""Repairs for the fifth independent exact-head review of a2ca5eb8 (DEFECTS D1-D4, closed as classes).
Fixtures are synthetic and source-only; they exercise the rules, not production behavior. Credential-shaped
canaries are FAKE, assembled at run time from fragments and never printed: a failure reports a fixed message.
No test depends on the real clock or the host time zone: the reference clock is injected (NOW).
D1 is a performance class: the bounds below are generous wall-clock ceilings (the fixed code needs well under a second)."""
import copy
import json
import random
import sys
import tempfile
import time
import unittest

from test_register import SK, base
from test_review_fixes2 import NOW, check, errs, row, run, wj, H40, H64

FIX = SK / "tests" / "fixtures" / "review"

sys.path.insert(0, str(SK / "scripts"))
import extract_register as xr  # noqa: E402

HEUR = "same-name-and-repo-rooted-paths-heuristic"
WALL_S = 10.0          # ceiling for n=400 (reviewer: 0.04 s at 61398b26, 20.9 s at n=100 at a2ca5eb8)


def join(*p):
    return "".join(p)


FAKE_A = join("gh", "p_", "Zq9Xw3Lm5Nb7Vc1Kd4Jf6Hg8Sa2Pe0Ro3Ti5U")       # FAKE
FAKE_B = join("sk", "_live_", "Zq9Xw3Lm5Nb7Vc1Kd4Jf")                      # FAKE
FAKE_C = join("glpat", "-", "Zq9Xw3Lm5Nb7Vc1Kd4Jf")                        # FAKE
NEEDLES = ("Zq9Xw3Lm5N", "Zq9 Xw3", "Zq9Xw3Lm5Nb7Vc1Kd4")


def _slow_positive_clusters(members):
    """The a2ca5eb8 cluster rule, kept as the reference implementation (quartic, only used for small n)."""
    parent = list(range(len(members)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    basis = {}
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            a, b = members[i], members[j]
            how = None
            sa = {s["sha256"] for s in a["sources"] if "sha256" in s}
            sb = {s["sha256"] for s in b["sources"] if "sha256" in s}
            if sa & sb:
                how = "same-content-sha256"
            else:
                ra = {xr._repo_id(s["repo"]) for s in a["sources"] if s["repo"] != "UNKNOWN"}
                rb = {xr._repo_id(s["repo"]) for s in b["sources"] if s["repo"] != "UNKNOWN"}
                pa, pb = xr._path_id(a["key"][5]), xr._path_id(b["key"][5])
                if ra & rb and pa and pa == pb:
                    how = "same-repo-identity-and-path"
            if how and not any(xr._distinct_commits(members[x], members[y])
                               for x in range(len(members)) if find(x) == find(i)
                               for y in range(len(members)) if find(y) == find(j)):
                parent[find(i)] = find(j)
                basis[find(i)] = how
    out = {}
    for i in range(len(members)):
        out.setdefault(find(i), []).append(i)
    res = []
    for root, idx in out.items():
        if len(idx) > 1:
            hows = {basis.get(k) for k in (find(i) for i in idx)} - {None}
            res.append((idx, "same-content-sha256" if "same-content-sha256" in hows else "same-repo-identity-and-path"))
    return res


def member(i, path, repo, sha=None, commit=None):
    src = {"repo": repo}
    if sha:
        src["sha256"] = sha
    if commit:
        src["commit"] = commit
    return {"key": ("IF001", "producer", "h", "c", "http", path), "sources": [src]}


def perf_rows(n, mode):
    rows = []
    for i in range(n):
        if mode == "sha":            # one content hash, n distinct repos and paths: one cluster of n
            rows.append(row(component="c", source_repo="o/r%d" % i, path_or_command="d%d/x.py" % i,
                            source_identity="path+sha256:/p/a.py " + "d" * 64))
        elif mode == "repo-path":    # one repo, n spellings of one path, one commit: one cluster of n
            rows.append(row(component="c", source_repo="o/r", path_or_command="a/%d/../x.py" % i,
                            source_identity="commit " + "1" * 40))
        elif mode == "distinct-commits":   # same repo and path, every row a different commit: n records
            rows.append(row(component="c", source_repo="o/r", path_or_command="a/%d/../x.py" % i,
                            source_identity="commit " + ("%040x" % (i + 1))))
        else:                        # a hundred separate small clusters
            rows.append(row(component="c", source_repo="o/r%d" % (i % 100), path_or_command="p%d/x.py" % (i % 100),
                            source_identity="commit " + ("%040x" % (i % 100 + 1))))
    return rows


class TestD1ExtractionIsNearLinear(unittest.TestCase):
    def timed(self, n, mode, **kw):
        t = time.monotonic()
        out = xr.convert(perf_rows(n, mode), **kw)
        return out, time.monotonic() - t

    def test_n400_same_sha_fuses_into_one_record_within_wall_bound(self):
        out, dt = self.timed(400, "sha")
        self.assertLess(dt, WALL_S, "n=400 same-sha extraction exceeded the wall bound")
        self.assertEqual(len(out["register"]["records"]), 1)
        self.assertEqual(len(out["register"]["records"][0]["sources"]), 400)

    def test_n400_same_repo_and_path_within_wall_bound(self):
        out, dt = self.timed(400, "repo-path")
        self.assertLess(dt, WALL_S, "n=400 repo-and-path extraction exceeded the wall bound")
        self.assertEqual(len(out["register"]["records"]), 1)

    def test_n400_distinct_commits_stay_separate_within_wall_bound(self):
        out, dt = self.timed(400, "distinct-commits")
        self.assertLess(dt, WALL_S, "n=400 distinct-commit extraction exceeded the wall bound")
        self.assertEqual(len(out["register"]["records"]), 400)

    def test_n400_many_small_clusters_within_wall_bound(self):
        out, dt = self.timed(400, "clusters")
        self.assertLess(dt, WALL_S, "n=400 clustered extraction exceeded the wall bound")
        self.assertEqual(len(out["register"]["records"]), 100)

    def test_n400_heuristic_path_within_wall_bound(self):
        _, dt = self.timed(400, "sha", heuristic_fusion=True)
        self.assertLess(dt, WALL_S)

    def test_cluster_rule_equals_the_slow_reference_on_small_random_groups(self):
        rng = random.Random(5)
        shas = [None, "a" * 64, "b" * 64]
        commits = [None, "1" * 40, "2" * 40, "3" * 40]
        repos = ["o/r1", "https://github.com/o/r1.git", "o/r2", "o/r3"]
        paths = ["a/x.py", "a/./x.py", "b/y.py", None]
        for trial in range(300):
            n = rng.randint(2, 9)
            ms = [member(i, rng.choice(paths), rng.choice(repos), rng.choice(shas), rng.choice(commits)) for i in range(n)]
            self.assertEqual(xr._positive_clusters(copy.deepcopy(ms)), _slow_positive_clusters(copy.deepcopy(ms)), trial)

    def test_converted_register_equals_the_slow_path_on_small_n(self):
        orig = xr._positive_clusters
        for mode in ("sha", "repo-path", "distinct-commits", "clusters"):
            rows = perf_rows(12, mode)
            fast = xr.convert(copy.deepcopy(rows))
            xr._positive_clusters = _slow_positive_clusters
            try:
                slow = xr.convert(copy.deepcopy(rows))
            finally:
                xr._positive_clusters = orig
            self.assertEqual(fast, slow, mode)

    def test_chain_through_a_commitless_member_still_blocked(self):
        ms = [member(0, "a/x.py", "o/r", commit="1" * 40), member(1, "a/x.py", "o/r"), member(2, "a/x.py", "o/r", commit="2" * 40)]
        self.assertEqual(xr._positive_clusters(copy.deepcopy(ms)), _slow_positive_clusters(copy.deepcopy(ms)))
        self.assertTrue(all(len(idx) < 3 for idx, _ in xr._positive_clusters(ms)))


class TestD2SchemaCompatRedacts(unittest.TestCase):
    def go(self, old, new, *extra):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("schema_compat.py", wj(d, "o.json", old), wj(d, "n.json", new), "--direction", "both", *extra)
        return rc, out

    def clean(self, out, msg):
        self.assertFalse(any(n in out for n in NEEDLES), msg)

    def test_credential_shaped_property_name_is_not_echoed(self):
        for canary in (FAKE_A, FAKE_B, FAKE_C):
            rc, out = self.go({"type": "object"}, {"type": "object", "properties": {canary: {"type": "string"}}})
            self.assertIn(rc, (0, 1))
            self.clean(out, "canary property name echoed")

    def test_credential_shaped_required_name_is_not_echoed(self):
        rc, out = self.go({"type": "object"}, {"type": "object", "required": [FAKE_A]})
        self.clean(out, "canary required name echoed")

    def test_credential_shaped_enum_values_are_not_echoed(self):
        rc, out = self.go({"type": "string", "enum": ["a"]}, {"type": "string", "enum": ["a", FAKE_A]})
        self.clean(out, "added enum canary echoed")
        rc, out = self.go({"type": "string", "enum": ["a", FAKE_B]}, {"type": "string", "enum": ["a"]})
        self.clean(out, "removed enum canary echoed")

    def test_removed_and_nested_property_names_are_not_echoed(self):
        rc, out = self.go({"type": "object", "properties": {FAKE_A: {"type": "string"}}}, {"type": "object"})
        self.clean(out, "removed property canary echoed")
        rc, out = self.go({"type": "object", "properties": {"a": {"type": "object"}}},
                          {"type": "object", "properties": {"a": {"type": "object", "properties": {FAKE_C: {"type": "integer"}}}}})
        self.clean(out, "nested property canary echoed")
        rc, out = self.go({"type": "array", "items": {"type": "string", "enum": ["a"]}},
                          {"type": "array", "items": {"type": "string", "enum": ["a", FAKE_A]}})
        self.clean(out, "items enum canary echoed")

    def test_split_and_combining_spellings_are_masked_by_the_same_rule(self):
        spaced = FAKE_A[:8] + "\n" + FAKE_A[8:]            # newline inside the token: normalized, then masked
        combined = FAKE_A[:4] + "́" + FAKE_A[4:]       # combining mark inside the token
        for canary in (spaced, combined):
            rc, out = self.go({"type": "object"}, {"type": "object", "properties": {canary: {"type": "string"}}})
            self.assertFalse("Zq9Xw3Lm5Nb7Vc1Kd4" in out.replace("\n", "").replace("\\n", "").replace("́", "").replace("\\u0301", ""),
                             "split canary echoed")

    def test_ordinary_names_and_verdicts_are_unchanged(self):
        rc, out = self.go({"type": "object"}, {"type": "object", "properties": {"plain_name": {"type": "string"}}, "required": ["plain_name"]})
        data = json.loads(out)
        self.assertIn("plain_name", out)
        self.assertEqual(data["compatible"], rc == 0)


class TestD3RepoIdentityNegatives(unittest.TestCase):
    """Two rows share name, path and commit and differ ONLY in repo owner (or host): never fused."""
    # The two paths are spellings of one normalized path ("src/a.py" and "src/./a.py"), so they are different endpoint
    # keys that only the repo identity can separate (identical path text would merge as one key, a different rule).
    def recs(self, r1, r2, **kw):
        same = "commit " + H40
        rows = [row(component="recall", source_repo=r1, path_or_command="src/a.py", source_identity=same),
                row(component="recall", source_repo=r2, path_or_command="src/./a.py", source_identity=same)]
        return xr.convert(rows, **kw)["register"]["records"]

    def test_differing_only_in_owner_stay_separate(self):
        for r1, r2 in (("github.com/o1/r", "github.com/o2/r"), ("https://github.com/o1/r.git", "https://github.com/o2/r"),
                       ("git@github.com:o1/r.git", "git@github.com:o2/r.git")):
            self.assertEqual(len(self.recs(r1, r2)), 2, (r1, r2))

    def test_differing_only_in_host_stay_separate(self):
        for r1, r2 in (("github.com/o/r", "gitlab.com/o/r"), ("https://github.com/o/r.git", "https://git.example.org/o/r.git"),
                       ("git@github.com:o/r.git", "git@bitbucket.org:o/r.git")):
            self.assertEqual(len(self.recs(r1, r2)), 2, (r1, r2))

    def test_differing_only_in_repo_name_stays_separate(self):
        self.assertEqual(len(self.recs("github.com/o/r1", "github.com/o/r2")), 2)

    def test_same_identity_in_other_spellings_still_fuses_on_the_same_inputs(self):
        for r1, r2 in (("github.com/o/r", "https://github.com/O/r.git/"), ("github.com/o/r", "git@github.com:o/r.git")):
            out = self.recs(r1, r2)
            self.assertEqual(len(out), 1, (r1, r2))
            self.assertEqual(out[0]["fusion_basis"], "same-repo-identity-and-path")

    def test_owner_and_host_negatives_are_not_decided_by_commits_alone(self):
        """The same pairs with no commit stated at all must also stay separate (the guard that did the work before)."""
        for r1, r2 in (("github.com/o1/r", "github.com/o2/r"), ("github.com/o/r", "gitlab.com/o/r")):
            rows = [row(component="recall", source_repo=r1, path_or_command="src/a.py", source_identity="UNKNOWN"),
                    row(component="recall", source_repo=r2, path_or_command="src/./a.py", source_identity="UNKNOWN")]
            self.assertEqual(len(xr.convert(rows)["register"]["records"]), 2, (r1, r2))


class TestD4HeuristicFusionIsWarned(unittest.TestCase):
    def heur(self, declared="all-interfaces-complete", basis=HEUR):
        reg = base(declared)
        r = reg["records"][0]
        s = r.pop("source_identity")
        r["sources"] = [s, dict(s, repo="j0yen/y", commit="c" * 40)]
        r["fusion_basis"] = basis
        return reg

    def validate_file(self, reg, *extra):
        with tempfile.TemporaryDirectory() as d:
            return run("register_validate.py", wj(d, "r.json", reg), "--now", "2026-11-13T12:00:00Z", *extra)

    def warns(self, out):
        return [l for l in out.splitlines() if l.startswith("WARN") and "heuristic" in l.lower()]

    def test_complete_register_warns_naming_record_and_basis(self):
        rc, out = self.validate_file(self.heur())
        self.assertEqual(rc, 0, out)
        w = self.warns(out)
        self.assertEqual(len(w), 1, out)
        self.assertIn("R1", w[0])
        self.assertIn(HEUR, w[0])
        self.assertIn("OK", out)

    def test_partial_register_warns_and_stays_rc0(self):
        rc, out = self.validate_file(self.heur("partial"))
        self.assertEqual(rc, 0, out)
        w = self.warns(out)
        self.assertEqual(len(w), 1, out)
        self.assertIn("R1", w[0])

    def test_finding_is_a_warning_not_an_error_and_keeps_ok(self):
        res = check(self.heur())
        self.assertTrue(res["ok"], res["findings"])
        f = [x for x in res["findings"] if x["code"] == "heuristic-fusion"]
        self.assertEqual([x["severity"] for x in f], ["warn"])
        self.assertEqual(f[0]["record"], "R1")

    def test_proven_fusion_bases_are_not_warned(self):
        for basis in ("same-content-sha256", "same-repo-identity-and-path"):
            rc, out = self.validate_file(self.heur(basis=basis))
            self.assertEqual(rc, 0, out)
            self.assertEqual(self.warns(out), [], basis)

    def test_basis_spelling_and_case_variants_still_warn(self):
        for basis in (HEUR.upper(), " " + HEUR + " ", "heuristic"):
            rc, out = self.validate_file(self.heur(basis=basis))
            self.assertEqual(rc, 0, out)
            self.assertEqual(len(self.warns(out)), 1, basis)

    def test_two_heuristic_records_each_named(self):
        reg = self.heur()
        r = reg["records"][1]
        s = r.pop("source_identity")
        r["sources"] = [s, dict(s, repo="j0yen/z", commit="d" * 40)]
        r["fusion_basis"] = HEUR
        rc, out = self.validate_file(reg)
        self.assertEqual(len(self.warns(out)), 2, out)

    def test_extractor_output_with_heuristic_fusion_is_warned_by_the_validator(self):
        rows = [row(component="recall", source_repo="r1", path_or_command="r1/a.py", source_identity="commit " + H40),
                row(component="recall", source_repo="r2", path_or_command="r2/b.py", source_identity="commit " + "c" * 40)]
        out = xr.convert(rows, declared="partial", heuristic_fusion=True)
        self.assertEqual(out["register"]["records"][0]["fusion_basis"], HEUR)
        res = check(out["register"])
        self.assertIn("heuristic-fusion", {f["code"] for f in res["findings"]})

    def test_fixture_register_warns_under_complete(self):
        rc, out = run("register_validate.py", FIX / "heuristic_fused_complete.json", "--now", "2026-11-13T12:00:00Z")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.warns(out)), 1, out)

    def test_skill_md_states_complete_warns(self):
        text = (SK / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("heuristic-fusion", text)


if __name__ == "__main__":
    unittest.main()
