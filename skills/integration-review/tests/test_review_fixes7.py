"""Repairs for the seventh independent exact-head review of 2f5a98ab (DEFECTS D1-D8, closed as classes).
Fixtures are synthetic and source-only; they exercise the rules, not production behavior. Credential-shaped
canaries are FAKE, assembled at run time from fragments and never printed: a failure reports a fixed message.
No test depends on the real clock or the host time zone: the reference clock is injected (NOW).
D1 (major): a record missing its commit or repo on one side never escapes the validator's duplicate check, so a
complete claim is refused naming the records. D2: path-less rows of different repos or commits never fuse; any
fusion carries fusion_basis and is counted. D3-D5: every named output path redacts credential-shaped file names
(a prefixed AWS key id, URL credentials with any scheme separator, percent-encoded) and e-mail text. D6/D8:
negated evidence is never positive evidence (side marks, adoption proof, evidence presence). D7: same-key joins
use keyed lookup, not a rescan of every endpoint of the key."""
import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

from test_register import SK, base, rec
from test_review_fixes2 import NOW, check, errs, row, run, wj, H40, H64   # noqa: F401  (NOW: injected clock)

sys.path.insert(0, str(SK / "scripts"))
import extract_register as xr  # noqa: E402
import ir_norm  # noqa: E402
import register_validate as rv  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "review"
REAL = Path(__file__).resolve().parent / "fixtures" / "endpoints.jsonl"


def join(*p):
    return "".join(p)


# FAKE canaries, assembled at run time, never printed
AWS = join("AK", "IA", "Zq9Xw3Lm5Nb7Vc1K4JF")
PW = join("Zq9Xw3Lm5", "Nb7")
NEEDLES = ("Zq9Xw3Lm5", "AKIAZq9", "alice.smith")
MAIL = join("alice", ".smith", "@", "example", ".com")


def leaked(out):
    flat = out.replace("\n", "")
    return any(n in flat for n in NEEDLES)


def cm(c):
    return "commit " + c * 40


def srcid(repo=None, commit=None, **kw):
    d = {"version": commit or "v1", "available": True, "captured_at": "2026-11-12T09:00:00Z"}
    if repo:
        d["repo"] = repo
    if commit:
        d["commit"] = commit
        d["raw"] = "commit " + commit
    d.update(kw)
    return d


def hand(rid, path="a.py", **kw):
    r = rec(rid, comp="svc-a", installed_state="source-only")
    r.pop("source_identity", None)
    if path:
        r["path_or_command"] = path
    r.update(kw)
    return r


def regs(pair, declared="all-interfaces-complete"):
    """Two competing records for one endpoint plus a consumer and a caller, so the family is otherwise whole."""
    reg = base(declared)
    reg["records"] = list(pair) + reg["records"][1:]
    return reg


A, B = "a" * 40, "b" * 40


# ---------------------------------------------------------------------------------------------------------
class TestD1ValidatorNeverLosesADuplicateToAMissingCommitOrRepo(unittest.TestCase):
    """The extractor reads an unstated commit or repo as 'not different'; the validator agrees."""

    def refused(self, a, b, declared="all-interfaces-complete"):
        res = check(regs((a, b), declared))
        return "duplicate-record" in errs(res), res

    def test_commit_stated_on_one_record_only_is_a_duplicate_and_complete_is_refused(self):
        a = hand("r1", source_identity=srcid("o/r", A))
        b = hand("r2", source_identity=srcid("o/r"))
        a["installed_state"], b["installed_state"] = "source-only", "installed"
        hit, res = self.refused(a, b)
        self.assertTrue(hit)
        self.assertFalse(res["ok"])

    def test_cli_complete_is_refused_and_names_both_records(self):
        a = hand("r1", source_identity=srcid("o/r", A))
        b = hand("r2", source_identity=srcid("o/r"))
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("register_validate.py", wj(d, "r.json", regs((a, b))), "--now", "2026-11-13T12:00:00Z")
        self.assertEqual(rc, 1)
        self.assertIn("REFUSED", out)
        self.assertIn("r1", out)
        self.assertIn("r2", out)
        self.assertIn("duplicate-record", out)
        self.assertNotIn("OK (declared", out)

    def test_same_pair_is_also_an_error_under_partial(self):
        a = hand("r1", source_identity=srcid("o/r", A))
        b = hand("r2", source_identity=srcid("o/r"))
        hit, res = self.refused(a, b, "partial")
        self.assertTrue(hit)
        self.assertFalse(res["ok"])

    def test_repo_stated_on_one_record_only_is_a_duplicate(self):
        a = hand("r1", source_identity=srcid("o/r", A))
        b = hand("r2", source_identity=srcid(None, A))
        hit, _ = self.refused(a, b, "partial")
        self.assertTrue(hit)

    def test_neither_commit_nor_repo_stated_on_the_second_is_a_duplicate(self):
        a = hand("r1", source_identity=srcid("o/r", A))
        b = hand("r2", source_identity=srcid())
        hit, _ = self.refused(a, b, "partial")
        self.assertTrue(hit)

    def test_multi_source_record_repeating_a_single_source_endpoint_is_a_duplicate(self):
        a = hand("r1", sources=[srcid("o/r", A), srcid("p/r", A)])
        a.pop("source_identity", None)
        b = hand("r2", source_identity=srcid("o/r", A))
        hit, _ = self.refused(a, b)
        self.assertTrue(hit)
        a2 = hand("r1", sources=[srcid("o/r", A), srcid("p/r", A)])
        b2 = hand("r2", source_identity=srcid("o/r"))
        hit, _ = self.refused(a2, b2)
        self.assertTrue(hit)

    def test_third_record_without_identity_collides_with_both_proved_different_ones(self):
        a = hand("r1", source_identity=srcid("o1/r", A))
        b = hand("r2", source_identity=srcid("o2/r", B))
        c = hand("r3", source_identity=srcid())
        reg = regs((a, b))
        reg["records"].insert(2, c)
        res = check(reg)
        self.assertIn("duplicate-record", errs(res))
        named = json.dumps([f for f in res["findings"] if f["code"] == "duplicate-record"])
        self.assertIn("r3", named)

    def test_spelling_variants_of_one_repo_with_the_same_commit_stay_a_duplicate(self):
        a = hand("r1", source_identity=srcid("https://github.com/o/r", A))
        b = hand("r2", source_identity=srcid("git@github.com:o/r.git", A))
        hit, _ = self.refused(a, b)
        self.assertTrue(hit)

    def test_equal_commits_stay_a_duplicate(self):
        a = hand("r1", source_identity=srcid("o/r", A))
        b = hand("r2", source_identity=srcid("o/r", A))
        hit, _ = self.refused(a, b)
        self.assertTrue(hit)

    # negatives of the same class: provably different endpoints are NOT duplicates
    def test_distinct_repos_stated_on_both_are_two_endpoints(self):
        hit, _ = self.refused(hand("r1", source_identity=srcid("o/r", A)), hand("r2", source_identity=srcid("p/r", A)))
        self.assertFalse(hit)

    def test_distinct_commits_stated_on_both_are_two_endpoints(self):
        hit, _ = self.refused(hand("r1", source_identity=srcid("o/r", A)), hand("r2", source_identity=srcid("o/r", B)))
        self.assertFalse(hit)

    def test_pathless_records_of_provably_different_repos_are_two_endpoints(self):
        a = hand("r1", path=None, source_identity=srcid("o/r", A))
        b = hand("r2", path=None, source_identity=srcid("p/r", B))
        hit, _ = self.refused(a, b, "partial")
        self.assertFalse(hit)

    def test_pathless_records_with_one_side_unstated_are_a_duplicate(self):
        a = hand("r1", path=None, source_identity=srcid("o/r", A))
        b = hand("r2", path=None, source_identity=srcid("o/r"))
        hit, _ = self.refused(a, b, "partial")
        self.assertTrue(hit)

    def test_fixture_register_one_sided_commit_refuses_complete(self):
        reg = json.loads((FIX / "dup_one_sided_commit_register.json").read_text(encoding="utf-8"))
        res = check(reg)
        self.assertIn("duplicate-record", errs(res))
        self.assertFalse(res["ok"])
        reg["coverage"]["declared"] = "partial"
        self.assertIn("duplicate-record", errs(check(reg)))

    def test_many_distinct_endpoints_of_one_key_validate_quickly(self):
        n = 1500
        recs_ = [hand("r%d" % i, source_identity=srcid("o%d/r" % i, "%040x" % i)) for i in range(n)]
        t = time.perf_counter()
        res = check(regs(recs_, "partial"))
        self.assertLess(time.perf_counter() - t, 8.0)
        self.assertNotIn("duplicate-record", errs(res))


# ---------------------------------------------------------------------------------------------------------
def recs_of(rows, **kw):
    o = xr.convert(rows, "partial", **kw)
    return o["register"]["records"], o["stats"]


def pl(repo, ident, **k):
    r = row(component="c", source_repo=repo, source_identity=ident, **k)
    return r


class TestD2PathlessRowsOfDifferentReposOrCommitsNeverFuse(unittest.TestCase):
    def test_pathless_different_repos_distinct_commits_are_two_records(self):
        rs, st = recs_of([pl("o1/r", cm("1")), pl("o2/r", cm("2"))])
        self.assertEqual(len(rs), 2)
        self.assertEqual(st.get("fused_multi_source_components", 0), 0)
        self.assertEqual(len({r["record_id"] for r in rs}), 2)
        self.assertTrue(all("fusion_basis" not in r for r in rs))

    def test_pathless_different_repos_same_commit_are_two_records(self):
        rs, _ = recs_of([pl("o1/r", cm("1")), pl("o2/r", cm("1"))])
        self.assertEqual(len(rs), 2)

    def test_pathless_same_repo_distinct_commits_are_two_records(self):
        rs, _ = recs_of([pl("o/r", cm("1")), pl("o/r", cm("2"))])
        self.assertEqual(len(rs), 2)

    def test_pathless_same_repo_same_commit_merge_and_keep_both_evidence(self):
        rs, _ = recs_of([pl("o/r", cm("1")), pl("o/r", cm("1"), evidence="side=producer again")])
        self.assertEqual(len(rs), 1)
        self.assertEqual(len(rs[0]["evidence"]), 2)

    def test_pathless_unstated_repo_row_is_not_a_difference(self):
        a = pl("o/r", cm("1"))
        b = pl("o/r", cm("1"))
        b.pop("source_repo")
        rs, _ = recs_of([a, b])
        self.assertEqual(len(rs), 1)

    def test_pathless_records_with_unstated_identities_still_merge(self):
        a, b = pl("o/r", None), pl("o/r", None)
        a.pop("source_identity", None)
        b.pop("source_identity", None)
        rs, _ = recs_of([a, b])
        self.assertEqual(len(rs), 1)

    def test_pathless_split_records_pass_the_validator_with_no_duplicate(self):
        o = xr.convert([pl("o1/r", cm("1")), pl("o2/r", cm("2"))], "partial")
        res = check(o["register"])
        self.assertNotIn("duplicate-record", {f["code"] for f in res["findings"]})

    def test_fixture_rows_split_by_cli_and_complete_is_still_refused(self):
        src = FIX / "extract_pathless_two_repos.jsonl"
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("extract_register.py", src, d)
            self.assertEqual(rc, 0)
            self.assertIn("records: 2", out)
            self.assertNotIn("fused_multi_source_components", out)
            rc, out = run("register_validate.py", Path(d) / "register-declared-complete.json", "--now", "2026-11-13T12:00:00Z")
            self.assertEqual(rc, 1)
            self.assertIn("REFUSED", out)

    def test_any_multi_source_record_in_a_mixed_batch_is_counted_and_labelled(self):
        sh = "path+sha256:/p/x.py " + "a" * 64
        rows = [pl("o1/r", sh, path_or_command="a.py"), pl("o2/r", sh, path_or_command="b.py"),
                pl("o3/r", cm("1")), pl("o4/r", cm("2"))]
        rs, st = recs_of(rows)
        fused = [r for r in rs if "sources" in r and len(r["sources"]) > 1]
        self.assertEqual(st["fused_multi_source_components"], len(fused))
        self.assertTrue(all(r.get("fusion_basis") for r in fused))
        self.assertEqual(len(rs), 3)

    def test_same_repo_and_path_with_distinct_paths_text_never_fuses_distinct_commits(self):
        rs, st = recs_of([pl("o/r", cm("1"), path_or_command="a.py"), pl("o/r", cm("2"), path_or_command="b.py")])
        self.assertEqual(len(rs), 2)
        self.assertEqual(st.get("fused_multi_source_components", 0), 0)


# ---------------------------------------------------------------------------------------------------------
class TestD3D4D5CredentialAndEmailShapesRedactInEveryEchoedName(unittest.TestCase):
    def sc(self, name, body="[1]"):
        with tempfile.TemporaryDirectory() as d:
            a = wj(d, "old.json", "{\"type\": \"object\"}")
            b = Path(d) / name
            b.write_text(body, encoding="utf-8")
            return run("schema_compat.py", a, b)

    def test_aws_key_id_inside_a_file_name_redacts_whatever_surrounds_it(self):
        for nm in (AWS, "backup_" + AWS, "prod-" + AWS, "x" + AWS + "y", "k" + AWS, AWS + "_old", "my.key." + AWS):
            rc, out = self.sc(nm + ".json")
            self.assertEqual(rc, 2)
            self.assertFalse(leaked(out), "AWS key id echoed in a file name")

    def test_aws_shape_redacts_in_the_shared_net_everywhere(self):
        for t in ("backup_" + AWS, "x" + AWS + "y", AWS, "[" + AWS + "]", AWS.replace("AK", "AS", 1)):
            self.assertEqual(ir_norm.redact(t), ir_norm.REDACTED)

    def test_ordinary_words_that_start_like_a_key_id_are_not_masked(self):
        for t in ("AsiaPacific.json", "akiak.json", "ASIA.txt", "Akia-notes.md", "src/asia_east/a.py"):
            self.assertEqual(ir_norm.redact(t), t)

    def test_url_credentials_with_any_separator_in_a_file_name_redact(self):
        cu = join("us", "er:", PW, "x@host.example")
        for sep in ("∕∕", "\\\\", "__", "_", "--", "..", "⧸⧸", "／／", "%2F%2F", "::", "+", "⁄⁄", ""):
            nm = join("https:", sep, cu)
            rc, out = self.sc(nm + ".json")
            self.assertEqual(rc, 2)
            self.assertFalse(leaked(out), "URL credential file name echoed (separator %r)" % sep)

    def test_percent_encoded_scheme_separator_redacts(self):
        self.assertEqual(ir_norm.redact(join("https%3A%2F%2F", "us", "er:", PW, "x@h.example")), ir_norm.REDACTED)
        self.assertEqual(ir_norm.redact(join("https%3a%2f%2f", "u:", PW, "x@h.example")), ir_norm.REDACTED)

    def test_urls_and_names_without_a_credential_pass_unchanged(self):
        for t in ("https://example.org/x", "a_b_c.json", "https:__example.org_x", "release:v1.2@latest", "note: a@b is not an address",
                  "dir\\file.json", "https:\\\\example.org\\x"):
            self.assertEqual(ir_norm.redact(t), t, t)

    def test_email_text_in_a_schema_property_name_is_not_printed(self):
        with tempfile.TemporaryDirectory() as d:
            a = wj(d, "o.json", {"type": "object", "properties": {MAIL: {"type": "string"}}})
            b = wj(d, "n.json", {"type": "object", "properties": {}})
            rc, out = run("schema_compat.py", a, b)
        self.assertFalse(leaked(out), "e-mail text printed from a property name")

    def test_email_text_in_required_enum_and_file_names_is_not_printed(self):
        with tempfile.TemporaryDirectory() as d:
            a = wj(d, "o.json", {"type": "object", "properties": {"k": {"type": "string", "enum": [MAIL, "x"]}}, "required": [MAIL]})
            b = wj(d, "n.json", {"type": "object", "properties": {"k": {"type": "string", "enum": ["x"]}}})
            rc, out = run("schema_compat.py", a, b)
            self.assertFalse(leaked(out))
            rc, out = self.sc(MAIL + ".json")
            self.assertFalse(leaked(out))

    def test_email_text_in_register_messages_and_ids_is_not_printed(self):
        reg = base()
        reg["records"][0]["record_id"] = MAIL
        reg["records"][0]["component"] = "UNKNOWN"
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("register_validate.py", wj(d, "r.json", reg), "--now", "2026-11-13T12:00:00Z")
        self.assertEqual(rc, 1)
        self.assertFalse(leaked(out))

    def test_email_text_in_lost_message_and_discriminator_paths_is_not_printed(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("lost_message_check.py", Path(d) / (MAIL + ".json"))
            self.assertFalse(leaked(out))
            rc, out = run("discriminator_check.py", Path(d) / (MAIL + ".sh"), "--line", "1", "--names", "a")
            self.assertFalse(leaked(out))
            rc, out = run("extract_register.py", Path(d) / (MAIL + ".jsonl"), Path(d) / "o")
            self.assertFalse(leaked(out))

    def test_extract_unwritable_output_path_with_aws_and_url_names_redacts(self):
        for c in (join("b_", AWS), join("https:", "∕∕", "us", "er:", PW, "x@h.example")):
            with tempfile.TemporaryDirectory() as d:
                src = Path(d) / "in.jsonl"
                src.write_text(json.dumps(row()) + "\n", encoding="utf-8")
                blocker = Path(d) / c
                blocker.write_text("x", encoding="utf-8")
                rc, out = run("extract_register.py", src, blocker / "sub")
                self.assertEqual(rc, 2)
                self.assertFalse(leaked(out))

    def test_discriminator_argparse_and_hash_paths_redact_aws_and_url_values(self):
        for c in (join("b_", AWS), join("https:", "\\\\", "us", "er:", PW, "x@h.example")):
            with tempfile.TemporaryDirectory() as d:
                src = Path(d) / "s.sh"
                src.write_text("X='^a$'\n", encoding="utf-8")
                rc, out = run("discriminator_check.py", src, "--line", c, "--names", "a")
                self.assertFalse(leaked(out))
                rc, out = run("discriminator_check.py", src, "--line", "1", "--names", "a", "--sha256", c)
                self.assertFalse(leaked(out))


# ---------------------------------------------------------------------------------------------------------
class TestD6D8NegatedEvidenceIsNeverPositiveEvidence(unittest.TestCase):
    def role(self, ev, claimed="producer"):
        return xr.norm_role({"role": claimed}, xr.evidence_text({"evidence": ev}))

    def test_negated_side_marks_are_not_marks(self):
        for ev in ("not side=producer", "no side=producer here", "side=producer failed", "never side=producer",
                   "side=producer is not verified", "without side=producer", "side=producer: no test",
                   "side=producer cannot be confirmed", "side=producer unverified", "isn't side=producer"):
            self.assertEqual(self.role(ev)[0], "UNKNOWN", ev)
            self.assertEqual(self.role(ev)[1], "producer", ev)

    def test_positive_side_marks_still_count(self):
        for ev in ("side=producer", "side=producer observed in handler", "reads the topic; side=producer",
                   "no tests exist for x; side=producer"):
            self.assertEqual(self.role(ev)[0], "producer", ev)

    def test_a_negated_mark_beside_a_positive_one_keeps_only_the_positive(self):
        self.assertEqual(self.role(["not side=consumer", "side=producer"])[0], "producer")
        self.assertEqual(self.role(["side=consumer failed", "side=producer; not side=consumer"])[0], "producer")

    def test_a_negated_mark_never_contradicts_into_a_second_side(self):
        # "side=producer" plus a negated consumer mark is one positive side, not a contradiction
        self.assertEqual(self.role("side=producer, not side=consumer")[0], "producer")

    def adopt(self, ref):
        reg = base()
        reg["records"][0].update(installed_state="loaded",
                                 adoption_evidence=[{"ref": ref, "observed_at": "2026-11-12T10:00:00Z"}])
        return check(reg)["ok"]

    def test_non_running_process_states_are_not_adoption_proof(self):
        for ref in ("pid 4242 exe /x <defunct>", "pid 4242 comm qd (zombie)", "pid 4242 exe /x ESRCH", "pid 4242 exe /x died",
                    "pid 4242 exe /x crashed", "pid 4242 exe /x aborted", "pid 4242 comm qd has died", "pid 4242 exe /x isn't running",
                    "pid 4242 exe /x wasn't found", "pid 4242 exe /x didn't start", "pid 4242 exe /x failure", "pid 4242 exe /x fails",
                    "pid 4242 exe /x reaped", "pid 4242 exe /x Zombie", "pid 4242 exe /x DEFUNCT",
                    "pid 4242 exe /x unreachable", "pid 4242 exe /x timed out", "pid 4242 exe /x refused", "pid 4242 exe /x can\u2019t"):
            self.assertFalse(self.adopt(ref), ref)

    def test_positive_process_observations_still_adopt(self):
        for ref in ("pid 4242 exe /x", "/proc/4242/exe -> /usr/bin/qd", "pid 4242 comm qd", "ps shows process qd",
                    "pid-1 exe /bin/x", "pid 4242 cmdline qd --serve", "/proc/4242/exe -> /x (deleted)"):
            self.assertTrue(self.adopt(ref), ref)

    def test_a_word_that_merely_contains_a_negation_does_not_refuse(self):
        for ref in ("pid 4242 exe /usr/bin/notifyd", "pid 4242 cmdline qd --node-name x", "pid 4242 comm diesel"):
            self.assertTrue(self.adopt(ref), ref)

    def test_negated_evidence_alone_is_missing_evidence_under_complete(self):
        for ref in ("not verified", "no test found", "check failed", "never observed", "unverified claim"):
            reg = base()
            reg["records"][1]["evidence"] = [{"ref": ref, "observed_at": "2026-11-12T11:00:00Z"}]
            res = check(reg)
            self.assertFalse(res["ok"], ref)
            self.assertIn("missing-evidence", errs(res), ref)
            self.assertIn("R2", json.dumps([f for f in res["findings"] if f["code"] == "missing-evidence"]))

    def test_one_positive_ref_beside_a_negated_one_is_enough(self):
        reg = base()
        reg["records"][1]["evidence"] = [{"ref": "not verified", "observed_at": "2026-11-12T11:00:00Z"},
                                         {"ref": "file:x#1", "observed_at": "2026-11-12T11:00:00Z"}]
        self.assertTrue(check(reg)["ok"])

    def test_path_like_refs_are_not_judged_as_prose(self):
        reg = base()
        reg["records"][1]["evidence"] = [{"ref": "docs/no-op-notes.md#failed-cases", "observed_at": "2026-11-12T11:00:00Z"}]
        self.assertTrue(check(reg)["ok"])

    def test_partial_register_with_negated_evidence_only_warns(self):
        reg = base("partial")
        reg["records"][1]["evidence"] = [{"ref": "not verified", "observed_at": "2026-11-12T11:00:00Z"}]
        res = check(reg)
        self.assertTrue(res["ok"])
        self.assertIn("missing-evidence", {f["code"] for f in res["findings"]})


# ---------------------------------------------------------------------------------------------------------
class TestD7SameKeyJoinsAreKeyedNotRescanned(unittest.TestCase):
    def test_same_path_rows_from_distinct_repos_do_not_rescan_every_endpoint(self):
        calls = {"n": 0}
        real = ir_norm.repo_id

        def counting(r):
            calls["n"] += 1
            return real(r)
        xr._N.repo_id = counting
        try:
            n = 600
            rows = [pl("o%d/r" % i, cm("%x" % (i % 15 + 1)), path_or_command="a.py") for i in range(n)]
            rs, _ = recs_of(rows)
        finally:
            xr._N.repo_id = real
        self.assertEqual(len(rs), n)
        self.assertLess(calls["n"], 30 * n, "repo_id is called per endpoint per row: the join rescans the key")

    def test_large_same_key_shapes_finish_in_linearish_time(self):
        n = 3000
        shapes = {
            "same-path-distinct-repo": [pl("o%d/r" % i, cm("%x" % (i % 15 + 1)), path_or_command="a.py") for i in range(n)],
            "pathless-distinct-repo": [pl("o%d/r" % i, cm("%x" % (i % 15 + 1))) for i in range(n)],
            "same-repo-distinct-commit": [pl("o/r", "commit %040x" % i, path_or_command="a.py") for i in range(n)],
            "one-repo-many-sources": [pl("o/r", "path+sha256:/p/x.py %064x" % i, path_or_command="a.py") for i in range(n)],
        }
        for name, rows in shapes.items():
            t = time.perf_counter()
            rs, _ = recs_of(rows)
            self.assertLess(time.perf_counter() - t, 6.0, name)
            self.assertGreaterEqual(len(rs), 1, name)

    def test_shared_sha_across_many_members_clusters_quickly(self):
        n = 1500
        sh = "path+sha256:/p/x.py " + "c" * 64
        rows = [pl("o%d/r" % i, sh, path_or_command="p%d.py" % i) for i in range(n)]
        t = time.perf_counter()
        rs, st = recs_of(rows)
        self.assertLess(time.perf_counter() - t, 6.0)
        self.assertEqual(len(rs), 1)
        self.assertEqual(rs[0]["fusion_basis"], "same-content-sha256")
        self.assertEqual(st["fused_multi_source_components"], 1)

    def test_distinct_commits_with_the_same_sha_do_not_fuse_in_any_order(self):
        sh_a = "commit " + "1" * 40
        rows = [pl("o/r", sh_a, path_or_command="a.py"), pl("o/r", "commit " + "2" * 40, path_or_command="b.py"),
                pl("o/r", "commit " + "1" * 40, path_or_command="a.py")]
        for perm in ((0, 1, 2), (2, 1, 0), (1, 0, 2)):
            rs, st = recs_of([rows[i] for i in perm])
            self.assertEqual(len(rs), 2)
            self.assertEqual(st.get("fused_multi_source_components", 0), 0)

    def test_evidence_and_sources_dedupe_stay_correct_with_many_rows(self):
        rows = [pl("o/r", cm("1"), path_or_command="a.py", evidence="side=producer e%d" % (i % 50)) for i in range(2000)]
        rs, _ = recs_of(rows)
        self.assertEqual(len(rs), 1)
        self.assertEqual(len(rs[0]["evidence"]), 50)
        self.assertEqual(len(rs[0]["source_rows"]), 2000)


class TestExtractorOutputAlwaysPassesTheValidatorDuplicateCheck(unittest.TestCase):
    """The extractor reads an unstated repo or commit as 'not different' and so does the validator; an unstated-repo
    row that the extractor attached to a record beside a stated repo must not make that record a wildcard."""

    def test_unstated_repo_row_attached_beside_two_repos_is_not_a_wildcard(self):
        a = pl("https://github.com/o1/r.git", cm("1"), path_or_command="a.py")
        b = pl("o1/r", cm("1"), path_or_command="a.py")           # a different canonical identity: stays separate
        u = pl("o1/r", cm("1"), path_or_command="a.py")
        u.pop("source_repo")
        for rows in ([a, u, b], [u, a, b], [a, b, u]):
            o = xr.convert(rows, "partial")
            self.assertEqual(len(o["register"]["records"]), 2)
            self.assertNotIn("duplicate-record", {f["code"] for f in check(o["register"])["findings"]})

    def test_random_groups_validate_without_a_duplicate_and_without_an_id_collision(self):
        import random
        rnd = random.Random(7)
        repos = ["o1/r", "o2/r", "https://github.com/o1/r.git", "git@github.com:o1/r", None, "UNKNOWN"]
        idents = [cm("1"), cm("2"), None, "path+sha256:/p/x.py " + "a" * 64, "path+sha256:/p/x.py " + "b" * 64]
        for _ in range(500):
            rows = []
            for _i in range(rnd.randint(2, 7)):
                r = pl(rnd.choice(repos), rnd.choice(idents), path_or_command=rnd.choice(["a.py", "./a.py", "b.py", None]))
                for k in ("source_repo", "source_identity", "path_or_command"):
                    if r.get(k) is None:
                        r.pop(k, None)
                rows.append(r)
            o = xr.convert(rows, "partial")
            ids = [r["record_id"] for r in o["register"]["records"]]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertNotIn("duplicate-record", {f["code"] for f in check(o["register"])["findings"]})


class TestRealInputUnchanged(unittest.TestCase):
    def test_real_input_extracts_and_complete_is_refused_naming_records(self):
        src = REAL
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("extract_register.py", src, d)
            self.assertEqual(rc, 0)
            self.assertIn("records: 507", out)
            rc, out = run("register_validate.py", Path(d) / "register-partial.json", "--now", "2026-11-13T12:00:00Z")
            self.assertEqual(rc, 0, out[-300:])
            rc, out = run("register_validate.py", Path(d) / "register-declared-complete.json", "--now", "2026-11-13T12:00:00Z")
            self.assertEqual(rc, 1)
            self.assertIn("REFUSED: declared all-interfaces-complete but gaps remain in:", out)


if __name__ == "__main__":
    unittest.main()
