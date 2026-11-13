"""Repairs for the sixth independent exact-head review of cff40cb0 (DEFECTS D1-D2, closed as classes).
Fixtures are synthetic and source-only; they exercise the rules, not production behavior. Credential-shaped
canaries are FAKE, assembled at run time from fragments and never printed: a failure reports a fixed message.
No test depends on the real clock or the host time zone: the reference clock is injected (NOW).
D1: every script path that echoes a file name, path, key or value redacts it (non-object schema, unwritable
output, unreadable source, argparse errors). D2: rows with one endpoint key but different repos, or distinct
commits, stay separate records; any fusion carries fusion_basis and is counted."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from test_register import SK
from test_review_fixes2 import NOW, check, errs, row, run, wj, H40, H64   # noqa: F401  (NOW: injected clock)

sys.path.insert(0, str(SK / "scripts"))
import extract_register as xr  # noqa: E402
import ir_norm  # noqa: E402,F401


def join(*p):
    return "".join(p)


CANARIES = {
    "ghp": join("gh", "p_", "Zq9Xw3Lm5Nb7Vc1Kd4Jf6Hg8Sa2Pe0Ro3Ti5U"),         # FAKE
    "sk": join("sk", "_live_", "Zq9Xw3Lm5Nb7Vc1Kd4Jf"),                        # FAKE
    "glpat": join("glpat", "-", "Zq9Xw3Lm5Nb7Vc1Kd4Jf"),                       # FAKE
    "aws": join("AK", "IA", "Zq9Xw3Lm5Nb7Vc1K4JF"),                            # FAKE
    "jwt": join("eyJ", "hbGciOiJIUzI1NiJ9.", "eyJzdWIiOiIxMjM0NTY3ODkwIn0.", "Zq9Xw3Lm5Nb7Vc1Kd4Jf"),   # FAKE
}
NEEDLES = ("Zq9Xw3Lm5", "hbGciOiJ")


def cm(c):
    return "commit " + c * 40


def leaked(out):
    flat = out.replace("\n", "")
    return any(n in flat for n in NEEDLES)


class TestD1EveryNamedOutputPathRedacts(unittest.TestCase):
    def schema_run(self, name, content, other="{\"type\": \"object\"}"):
        with tempfile.TemporaryDirectory() as d:
            a = wj(d, "old.json", other)
            b = Path(d) / name
            b.write_text(content, encoding="utf-8")
            return run("schema_compat.py", a, b)

    def test_non_object_top_level_schema_redacts_file_name(self):
        for k, c in CANARIES.items():
            for body in ("[1]", "3", "\"s\"", "null"):
                rc, out = self.schema_run(c + ".json", body)
                self.assertEqual(rc, 2, k)
                self.assertIn("top level is", out)
                self.assertFalse(leaked(out), "credential-shaped file name echoed on the non-object path (%s)" % k)

    def test_non_object_in_old_position_also_redacts(self):
        for k, c in CANARIES.items():
            with tempfile.TemporaryDirectory() as d:
                a = Path(d) / (c + ".json")
                a.write_text("[]", encoding="utf-8")
                b = wj(d, "new.json", {"type": "object"})
                rc, out = run("schema_compat.py", a, b)
                self.assertEqual(rc, 2)
                self.assertFalse(leaked(out), "old-position non-object file name echoed (%s)" % k)

    def test_unreadable_and_bad_json_schema_file_names_still_redact(self):
        for k, c in CANARIES.items():
            rc, out = self.schema_run(c + ".json", "{\"a\": ")
            self.assertEqual(rc, 2)
            self.assertFalse(leaked(out), k)
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("schema_compat.py", wj(d, "o.json", {}), Path(d) / (c + "_missing.json"))
                self.assertEqual(rc, 2)
                self.assertFalse(leaked(out), k)

    def test_extract_output_unwritable_error_redacts_the_path(self):
        for k, c in CANARIES.items():
            with tempfile.TemporaryDirectory() as d:
                src = Path(d) / "in.jsonl"
                src.write_text(json.dumps(row()) + "\n", encoding="utf-8")
                blocker = Path(d) / c
                blocker.write_text("x", encoding="utf-8")          # a file where the output directory must go
                rc, out = run("extract_register.py", src, blocker / "sub")
                self.assertEqual(rc, 2, k)
                self.assertIn("output unwritable", out)
                self.assertFalse(leaked(out), "credential-shaped output path echoed (%s)" % k)

    def test_extract_input_unreadable_error_redacts_the_path(self):
        for k, c in CANARIES.items():
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("extract_register.py", Path(d) / (c + ".jsonl"), Path(d) / "o")
                self.assertEqual(rc, 2)
                self.assertFalse(leaked(out), k)

    def test_discriminator_unreadable_source_and_argparse_errors_redact(self):
        for k, c in CANARIES.items():
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("discriminator_check.py", Path(d) / (c + ".sh"), "--line", "1", "--names", "a")
                self.assertNotEqual(rc, 0)
                self.assertFalse(leaked(out), "source path echoed (%s)" % k)
                rc, out = run("discriminator_check.py", "x.sh", "--line", c, "--names", "a")
                self.assertNotEqual(rc, 0)
                self.assertFalse(leaked(out), "argparse value echoed (%s)" % k)
                rc, out = run("discriminator_check.py", "x.sh", "--line", "1", "--names", "a", "--" + c)
                self.assertNotEqual(rc, 0)
                self.assertFalse(leaked(out), "argparse option echoed (%s)" % k)

    def test_register_validate_and_lost_message_unreadable_paths_redact(self):
        for k, c in CANARIES.items():
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("register_validate.py", Path(d) / (c + ".json"))
                self.assertNotEqual(rc, 0)
                self.assertFalse(leaked(out), k)
                rc, out = run("register_validate.py", wj(d, "r.json", "[]"), "--now", c)
                self.assertFalse(leaked(out), k)
                rc, out = run("lost_message_check.py", Path(d) / (c + ".json"))
                self.assertNotEqual(rc, 0)
                self.assertFalse(leaked(out), k)

    def test_url_credential_in_a_file_name_whose_slashes_became_underscores_redacts(self):
        c = join("https:", "__", "us", "er:Zq9Xw3Lm5Nb7", "@host.example_x")          # FAKE
        rc, out = self.schema_run(c + ".json", "[1]")
        self.assertEqual(rc, 2)
        self.assertFalse(leaked(out), "slash-mangled URL credential in a file name echoed")
        from ir_norm import redact
        self.assertEqual(redact("a_b_c.json"), "a_b_c.json")
        self.assertEqual(redact("https://example.org/x"), "https://example.org/x")

    def test_success_path_still_prints_a_clean_name(self):
        rc, out = self.schema_run("new.json", json.dumps({"type": "object"}))
        self.assertEqual(rc, 0)
        self.assertIn("compatible", out)


def recs(rows, **kw):
    o = xr.convert(rows, "partial", **kw)
    return o["register"]["records"], o["stats"]


def r6(i, repo, ident, path="src/a.py", **k):
    return row(component="c", source_repo=repo, source_identity=ident, path_or_command=path, **k)


class TestD2SameKeyDifferentRepoOrCommitStaysSeparate(unittest.TestCase):
    def test_different_repos_distinct_commits_are_two_records(self):
        rs, st = recs([r6(0, "o1/r", cm("1")), r6(1, "o2/r", cm("2"))])
        self.assertEqual(len(rs), 2)
        self.assertEqual(st.get("fused_multi_source_components", 0), 0)
        self.assertEqual(len({r["record_id"] for r in rs}), 2)
        self.assertEqual({r["source_identity"]["repo"] for r in rs}, {"o1/r", "o2/r"})

    def test_different_repos_same_commit_are_two_records(self):
        rs, _ = recs([r6(0, "o1/r", cm("1")), r6(1, "o2/r", cm("1"))])
        self.assertEqual(len(rs), 2)

    def test_different_repos_no_identity_are_two_records(self):
        rows = [row(component="c", source_repo="o1/r", path_or_command="a.py"),
                row(component="c", source_repo="o2/r", path_or_command="a.py")]
        for r in rows:
            r.pop("source_identity")
        rs, _ = recs(rows)
        self.assertEqual(len(rs), 2)

    def test_different_hosts_of_same_owner_name_are_two_records(self):
        rs, _ = recs([r6(0, "github.com/o/r", cm("1"), "a.py"), r6(1, "gitlab.com/o/r", cm("1"), "a.py")])
        self.assertEqual(len(rs), 2)

    def test_same_repo_distinct_commits_same_path_are_two_records(self):
        rs, st = recs([r6(0, "o/r", cm("1")), r6(1, "o/r", cm("2"))])
        self.assertEqual(len(rs), 2)
        self.assertEqual(st.get("fused_multi_source_components", 0), 0)

    def test_same_repo_spelling_variants_same_commit_still_merge_as_one_endpoint(self):
        rs, _ = recs([r6(0, "o/r", cm("1")), r6(1, "https://github.com/o/r.git", cm("1"))], )
        # the first is a bare owner/name, the second a URL: not the same canonical identity, so two records
        self.assertEqual(len(rs), 2)
        rs, _ = recs([r6(0, "https://github.com/o/r.git", cm("1")), r6(1, "git@github.com:o/r", cm("1"))])
        self.assertEqual(len(rs), 1)

    def test_same_repo_same_commit_duplicate_rows_merge_evidence(self):
        rs, _ = recs([r6(0, "o/r", cm("1")),
                      r6(1, "o/r", cm("1"), evidence="side=producer two")])
        self.assertEqual(len(rs), 1)
        self.assertEqual(len(rs[0]["evidence"]), 2)
        self.assertEqual(rs[0]["source_rows"], [1, 2])

    def test_unknown_repo_row_beside_a_known_repo_row_keeps_the_old_merge(self):
        rows = [row(component="c", path_or_command="a.py", source_identity=cm("1")),
                row(component="c", source_repo="o/r", path_or_command="a.py", source_identity=cm("1"))]
        rows[0].pop("source_repo")
        rs, _ = recs(rows)
        self.assertEqual(len(rs), 1)

    def test_record_ids_are_deterministic_and_input_order_independent_in_count(self):
        a = [r6(0, "o1/r", cm("1")), r6(1, "o2/r", cm("2")), r6(2, "o3/r", cm("3"))]
        ids1 = [r["record_id"] for r in recs(a)[0]]
        ids2 = [r["record_id"] for r in recs(a)[0]]
        self.assertEqual(ids1, ids2)
        self.assertEqual(len(set(ids1)), 3)
        self.assertEqual(len(recs(list(reversed(a)))[0]), 3)

    def test_split_records_validate_with_no_identity_collision_and_partial_ok(self):
        o = xr.convert([r6(0, "o1/r", cm("1")), r6(1, "o2/r", cm("2"))], "partial")
        res = check(o["register"])
        self.assertNotIn("identity-collision", {f["code"] for f in res["findings"]})
        self.assertFalse(errs(res) & {"duplicate-record-id", "identity-collision", "duplicate-key"})

    def test_same_sha_across_repos_still_fuses_and_is_labelled_and_counted(self):
        sha = "path+sha256:/p/a.py " + "d" * 64
        rs, st = recs([r6(0, "o1/r", sha), r6(1, "o2/r", sha)])
        fused = [r for r in rs if "fusion_basis" in r]
        self.assertEqual(len(rs), len(fused))
        self.assertEqual(st["fused_multi_source_components"], len(fused))
        for r in fused:
            self.assertEqual(r["fusion_basis"], "same-content-sha256")

    def test_every_multi_repo_record_in_a_mixed_batch_carries_a_basis_or_is_single_repo(self):
        rows = []
        for i in range(12):
            rows.append(r6(i, "o%d/r" % (i % 3), cm("%x" % (i % 4 + 1)), "src/a.py" if i % 2 else "src/./a.py"))
        rs, st = recs(rows)
        for r in rs:
            srcs = r.get("sources") or [r["source_identity"]]
            repos = {xr._repo_id(s["repo"]) for s in srcs}
            if len(repos) > 1:
                self.assertIn("fusion_basis", r)
        self.assertEqual(st.get("fused_multi_source_components", 0), sum(1 for r in rs if "fusion_basis" in r))

    def test_cli_two_repos_two_records_and_complete_claim_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.jsonl"
            src.write_text("\n".join(json.dumps(r6(i, "o%d/r" % (i + 1), cm(str(i + 1)))) for i in range(2)) + "\n",
                           encoding="utf-8")
            rc, out = run("extract_register.py", src, Path(d) / "o")
            self.assertEqual(rc, 0)
            reg = json.loads((Path(d) / "o" / "register-partial.json").read_text(encoding="utf-8"))
            self.assertEqual(len(reg["records"]), 2)


class TestD2ValidatorKeepsCollisionDetectionForTrueDuplicates(unittest.TestCase):
    def two(self, a, b):
        o = xr.convert([r6(0, *a), r6(1, *b)], "partial")
        reg = o["register"]
        return reg, check(reg)

    def test_same_endpoint_same_repo_same_commit_hand_duplicate_is_still_refused(self):
        reg, _ = self.two(("o/r", cm("1")), ("o/r", cm("1")))
        reg["records"].append(dict(reg["records"][0], record_id="x-other"))
        self.assertIn("duplicate-record", {f["code"] for f in check(reg)["findings"]})

    def test_same_record_id_is_still_refused_across_repos(self):
        reg, _ = self.two(("o1/r", cm("1")), ("o2/r", cm("2")))
        reg["records"][1]["record_id"] = reg["records"][0]["record_id"]
        self.assertIn("duplicate-record", {f["code"] for f in check(reg)["findings"]})

    def test_two_repos_same_path_pass_the_validator_with_no_duplicate(self):
        _, res = self.two(("o1/r", cm("1")), ("o2/r", cm("2")))
        self.assertNotIn("duplicate-record", {f["code"] for f in res["findings"]})


if __name__ == "__main__":
    unittest.main()
