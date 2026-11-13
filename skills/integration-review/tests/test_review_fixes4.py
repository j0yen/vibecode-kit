"""Repairs for the fourth independent exact-head review of 61398b26 (DEFECTS D1-D9, closed as classes).
Fixtures are synthetic and source-only; they exercise the rules, not production behavior. Credential-shaped
canaries are FAKE, assembled at run time from fragments and never printed: a failure reports a fixed message.
No test depends on the real clock or the host time zone: the reference clock is injected (NOW)."""
import copy
import itertools
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

from test_register import SK, base
from test_review_fixes2 import NOW, check, errs, mut, row, run, wj, H40, H64
import register_validate as rv

sys.path.insert(0, str(SK / "scripts"))
import extract_register as xr  # noqa: E402
import ir_norm  # noqa: E402
import lost_message_check as lm  # noqa: E402

FIX = SK / "tests" / "fixtures" / "review"
NOWS = "2026-11-13T12:00:00Z"
OBS = "2026-11-12T11:00:00Z"
COMB = "́"          # combining acute
ZW = "​"

TOK = "gh" + "p_" + "A1b2C3d4" + "E5f6G7h8I9j0" + "K1l2M3n4"      # FAKE
K40 = "wJalrXUtnFEMI" + "K7MDENGbPxRfiCY" + "EXAMPLE1234"          # FAKE, 38+ chars, mixed case + digit
K32 = "aB3dE5gH7jK9mN1pQ3" + "sT5vW7yZ9bC1dEf"                    # FAKE, 33 chars
FAKES = {
    "ghp": TOK,
    "sk-live": "sk" + "_live_" + "Ab12CdEf34GhIj56",
    "glpat": "glpat" + "-" + "Ab12Cd34Ef56Gh78Ij90",
    "npm": "npm" + "_" + "Ab12Cd34Ef56" + "Gh78Ij90Kl12Mn34",
    "hf": "hf" + "_" + "AbCdEfGhIjKlMnOp",
    "akia": "AK" + "IA" + "Q7W8E9R0T1Y2U3I4",
    "xox": "xox" + "b-" + "123456789012-abcdefABCDEF",
}


def leaked(text, secret=TOK):
    """The last 10 characters of a canary (ignoring marks) present in text; never prints either."""
    core = re.sub(r"[^A-Za-z0-9]", "", secret)[-10:]
    flat = re.sub(r"[^A-Za-z0-9]", "", text)
    return core in flat


def loaded(refs, declared="all-interfaces-complete"):
    reg = base(declared)
    reg["records"][0].update(installed_state="loaded", adoption_evidence=refs)
    return reg


# ---- D1 ----------------------------------------------------------------------------------------------
class TestD1UnstampedAdoption(unittest.TestCase):
    def fixture(self):
        return json.loads((FIX / "adopt_unstamped_complete.json").read_text())

    def test_complete_with_unstamped_adoption_is_refused_naming_the_record(self):
        res = check(self.fixture())
        self.assertFalse(res["ok"])
        bad = [f for f in res["findings"] if f["severity"] == "error" and f["record"] == "R1"]
        self.assertIn("missing-timestamp", {f["code"] for f in bad})
        self.assertTrue(any("adoption_evidence[0]" in f["message"] for f in bad))

    def test_cli_complete_refused_rc1_naming_record(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("register_validate.py", FIX / "adopt_unstamped_complete.json", "--now", NOWS)
        self.assertEqual(rc, 1)
        self.assertIn("REFUSED", out)
        self.assertIn("R1:missing-timestamp", out)
        self.assertNotIn("OK (declared", out)

    def test_partial_still_warns_and_passes(self):
        reg = self.fixture()
        reg["coverage"]["declared"] = "partial"
        res = check(reg)
        self.assertTrue(res["ok"])
        self.assertIn("missing-timestamp", {f["code"] for f in res["findings"] if f["severity"] == "warn"})

    def test_stamped_form_is_accepted(self):
        reg = self.fixture()
        reg["records"][0]["adoption_evidence"][0]["observed_at"] = OBS
        self.assertTrue(check(reg)["ok"])

    def test_any_unstamped_ref_refuses_even_beside_a_stamped_good_one(self):
        for refs in ([{"ref": "pid 4242 exe", "observed_at": OBS}, {"ref": "/proc/9/exe -> /bin/x"}],
                     [{"ref": "/proc/9/exe -> /bin/x"}, {"ref": "pid 4242 exe", "observed_at": OBS}],
                     [{"ref": "pid 4242 exe", "observed_at": OBS}, {"ref": "ps shows process ctl"}]):
            res = check(loaded(refs))
            self.assertFalse(res["ok"], "an unstamped adoption ref was passed beside a stamped one")
            self.assertIn("missing-timestamp", errs(res))

    def test_unparseable_or_non_string_stamp_is_refused_too(self):
        for v in (None, "", 5, True, "garbage", "2026-11-12T11:00:00", "2026-11-12"):
            res = check(loaded([{"ref": "pid 4242 exe", "observed_at": v}]))
            self.assertFalse(res["ok"], f"observed_at {v!r} accepted")

    def test_plain_evidence_omission_is_still_refused_and_class_is_symmetric(self):
        reg = mut(lambda r: r.update(evidence=[{"ref": "file:x#1"}]))
        self.assertIn("missing-timestamp", errs(check(reg)))
        reg = loaded([{"ref": "pid 4242 exe"}])
        self.assertIn("missing-timestamp", errs(check(reg)))

    def test_unevidenced_loaded_is_still_refused_independently(self):
        res = check(loaded([{"ref": "pid=", "observed_at": OBS}]))
        self.assertIn("unevidenced-state", errs(res))


# ---- D2 ----------------------------------------------------------------------------------------------
class TestD2PidSign(unittest.TestCase):
    def accepted(self, ref):
        return check(loaded([{"ref": ref, "observed_at": OBS}]))["ok"]

    def test_non_positive_or_malformed_pid_is_not_an_observation(self):
        for v in ("pid=-1 exe /bin/x", "pid -5 cmdline /bin/x", "pid:-7 comm ctl", "pid=0 exe /bin/x", "pid=+3 exe /bin/x",
                  "pid=1e3 exe /bin/x", "pid = - 1 exe /bin/x", "pid=1.5 exe /bin/x", "pid=4242.0 exe /bin/x",
                  "pid=−1 exe /bin/x", "pid=0x1f exe /bin/x", "pid=00 exe /bin/x", "pid # -3 exe /bin/x",
                  "pid=-0 exe /bin/x", "pid_-9 exe /bin/x", "PID=-1 EXE /bin/x", "pid=－1 exe /bin/x", "pid +8 cmdline x"):
            self.assertFalse(self.accepted(v), "a non-positive/malformed pid was accepted as a process observation")

    def test_positive_pids_still_accepted(self):
        for v in ("pid=4242 exe /bin/x", "pid 4242 cmdline /bin/x", "pid: 77 comm ctl", "pid-1 exe link", "pid=4242. exe /bin/x",
                  "pid #9 exe /bin/x", "pid_12 command ctl", "PID=5 EXE /bin/x"):
            self.assertTrue(self.accepted(v), "a positive pid observation was refused")


# ---- D3 ----------------------------------------------------------------------------------------------
SLASHES = ("∕", "⁄", "⧸", "／", "\\", "╱", "⟋", "∖", "⧵", "⧹", "﹨", "＼")


class TestD3SlashPlaceholders(unittest.TestCase):
    def test_every_slash_lookalike_in_every_placeholder_is_unknown(self):
        for s in SLASHES:
            for w in ("n%sa", "N%sA", "n%sa.", "n.%s.a", "n %s a", "none%s", "%snone", "nil%s", "n%s%sa", "n.a%s", "%sn%sa%s"):
                v = w % ((s,) * w.count("%s"))
                self.assertTrue(ir_norm.is_unknown(v), "a slash look-alike placeholder was read as a stated value")

    def test_combinations_with_dotting_and_marks(self):
        for v in ("N∕A", "n⁄a", "n\\a", "none∕", "n∕á", "n⧸/a", "N\\/A", "n/\\a", "NONE\\", "ni∕l",
                  "un∕known", "n​∕a"):
            if v in ("ni∕l", "un∕known"):
                self.assertTrue(ir_norm.is_unknown(v))      # separators inside a placeholder word are removed (existing rule)
            else:
                self.assertTrue(ir_norm.is_unknown(v))

    def test_real_values_with_slash_lookalikes_stay_stated(self):
        for v in ("a∕b", "svc∕api", "1∕2", "nonexistent∕host", "r1\\a.py", "none-of∕the-above", "unknown∕host7"):
            self.assertFalse(ir_norm.is_unknown(v), "a real value with a slash look-alike was read as UNKNOWN")

    def test_a_slash_lookalike_inside_a_path_is_not_folded_into_the_path(self):
        for ref in ("/proc/4242\u2215exe -> /bin/x", "/proc\u22154242/exe", "pid 4242 exe n\u2215a"):
            res = check(loaded([{"ref": ref, "observed_at": OBS}]))
            self.assertFalse(res["ok"], "a look-alike slash was read as a real path or a stated value")

    def test_validator_refuses_in_every_field(self):
        for fld in ("host", "component", "role", "installed_state", "label"):
            for v in ("N∕A", "n\\a", "none∕"):
                res = check(mut(lambda r: r.update({fld: v})))
                self.assertFalse(res["ok"], f"{fld} {v!r} accepted as stated")
        for fld in ("version", "repo"):
            reg = mut(lambda r: r["source_identity"].update({fld: "N∕A"}))
            self.assertFalse(check(reg)["ok"], f"source {fld} N/A look-alike accepted")
        reg = mut(lambda r: r.update(evidence=[{"ref": "n∕a", "observed_at": OBS}]))
        self.assertFalse(check(reg)["ok"])

    def test_equal_unknown_repos_never_fuse(self):
        for v in ("N∕A", "n\\a", "none∕", "n⁄a"):
            rows = [row(path_or_command="a/x.py", source_repo=v), row(path_or_command="./a/x.py", source_repo=v)]
            out = xr.convert(rows)
            self.assertEqual(len(out["register"]["records"]), 2, "two UNKNOWN repos were fused as the same repo")
            self.assertEqual(out["stats"].get("fused_multi_source_components", 0), 0)


# ---- D4 / D5 / D6 ------------------------------------------------------------------------------------
def with_marks(s, every=1):
    return "".join(c + (COMB if i % every == 0 and c.isalpha() else "") for i, c in enumerate(s))


class TestD4NormalizationOrder(unittest.TestCase):
    def test_combining_mark_cannot_hide_any_token_class(self):
        for name, v in FAKES.items():
            for variant in (with_marks(v), v[:3] + COMB + v[3:], with_marks(v[:6]) + v[6:], v[:4] + COMB * 3 + v[4:],
                            v[:2] + COMB + ZW + v[2:]):
                out = ir_norm.redact(variant)
                self.assertNotEqual(out, variant, f"{name}: a marked canary was not masked")
                self.assertFalse(leaked(out, v), f"{name}: tail echoed")

    def test_marks_inside_a_long_run_and_inside_validator_output(self):
        v = K40[:7] + COMB + K40[7:]
        self.assertNotEqual(ir_norm.redact(v), v)
        r1, r2 = (dict(copy.deepcopy(r), record_id=with_marks(TOK[:6]) + TOK[6:]) for r in base()["records"][:2])
        reg = {"schema_version": 1, "coverage": {"declared": "partial"}, "families": [{"id": "IF001"}], "records": [r1, r2]}
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("register_validate.py", wj(d, "r.json", reg), "--now", NOWS)
        self.assertFalse(leaked(out), "marked canary leaked through the validator CLI")

    def test_legitimate_accented_text_is_not_masked(self):
        for t in ("café résumé", "svc-á", "réseau-1", "Renée"):
            self.assertEqual(ir_norm.redact(t), t)


class TestD5LongRunAnywhere(unittest.TestCase):
    PREFIXES = ("/", "/srv/", "s3://bucket/", "x-", "https://api.example.test/v1/", "//", "x_", "./", "../", "/x-", "s3://b/x-",
                "gs://bkt/obj/", "x-api-", "/srv/x-")

    def test_40_and_32_char_mixed_case_runs_are_masked_after_any_prefix(self):
        for k in (K40, K32):
            for p in self.PREFIXES:
                for v in (p + k, k + p.strip("/"), "see " + p + k + " end"):
                    out = ir_norm.redact(v)
                    self.assertNotEqual(out, v, "a long mixed-case run was echoed")
                    self.assertFalse(leaked(out, k))

    def test_through_the_validator(self):
        for p in ("/srv/", "s3://bucket/", "x-"):
            v = p + K40
            r1 = dict(copy.deepcopy(base()["records"][0]), record_id=v)
            r2 = dict(copy.deepcopy(r1), role="consumer")
            reg = {"schema_version": 1, "coverage": {"declared": "partial"}, "families": [{"id": "IF001"}], "records": [r1, r2]}
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("register_validate.py", wj(d, "r.json", reg), "--now", NOWS)
            self.assertFalse(leaked(out, K40), f"prefix {p!r} leaked")

    def test_ordinary_values_are_not_masked(self):
        for t in ("a" * 64, "c" * 40, "0123456789abcdef" * 4, "x-0123456789abcdef", "123e4567-e89b-12d3-a456-426614174000",
                  "/mnt/ssd/cargo-target/r7-irvr4-20261113/src/skills/integration-review/scripts", "svc-a", "IF001",
                  "https://example.test/a/b/c", "s3://bucket/some/lower/case/path-without-upper-case-0"):
            self.assertEqual(ir_norm.redact(t), t)

    def test_rule_is_stated(self):
        txt = (SK / "SKILL.md").read_text()
        self.assertIn("whatever precedes it", txt)


class TestD6SplitTokens(unittest.TestCase):
    SPLITS = ("\n", "\t", "\r\n", "\\n", "\\t", "\\r", "\n\t", " \n ")

    def test_redact_masks_a_token_split_by_any_whitespace_or_its_json_escape(self):
        for s in self.SPLITS:
            for name, v in FAKES.items():
                t = v[:4] + s + v[4:]
                out = ir_norm.redact(t)
                self.assertNotEqual(out, t, f"{name} split by {s!r} not masked")
                self.assertFalse(leaked(out, v))
            t = K40[:15] + s + K40[15:]
            self.assertNotEqual(ir_norm.redact(t), t, f"long run split by {s!r} not masked")

    def test_every_output_path_of_the_validator_including_counts(self):
        for s in ("\n", "\t", "\\n"):
            for fld in ("role", "label", "installed_state"):
                reg = base("partial")
                reg["records"][0][fld] = TOK[:4] + s + TOK[4:]
                with tempfile.TemporaryDirectory() as d:
                    rc, out = run("register_validate.py", wj(d, "r.json", reg), "--now", NOWS)
                self.assertFalse(leaked(out), f"{fld} split by {s!r} leaked through the validator CLI")
                self.assertFalse(leaked(json.dumps(check(reg))), f"{fld} split by {s!r} leaked through the library result")

    def test_ordinary_multiline_text_is_not_masked(self):
        for t in ("line one\nline two", "a\tb", "pid 4242\nexe /bin/x", "svc-a\\nsvc-b"):
            self.assertEqual(ir_norm.redact(t), t)


# ---- D7 ----------------------------------------------------------------------------------------------
class TestD7SharedUnknownIsUnproven(unittest.TestCase):
    def load(self, name):
        return json.loads((FIX / name).read_text())

    def test_unknown_actors_on_both_ends_are_unproven(self):
        res = lm.classify(self.load("lost_unknown_actors.json"))
        self.assertEqual(res["consistency"], "unproven")
        self.assertTrue(any("actor" in w for w in res["unproven"]))

    def test_unknown_family_interface_message_on_both_links_are_unproven(self):
        res = lm.classify(self.load("lost_unknown_fields.json"))
        self.assertEqual(res["consistency"], "unproven")

    def test_cli_states_it_and_never_prints_proven(self):
        for n in ("lost_unknown_actors.json", "lost_unknown_fields.json"):
            rc, out = run("lost_message_check.py", FIX / n)
            self.assertIn("UNPROVEN", out)
            self.assertNotIn('"consistency": "proven"', out)

    def test_every_unknown_spelling_and_every_field_is_unproven(self):
        for v in ("UNKNOWN", "N/A", "?", "tbd", "none", "N∕A", " unknown ", "n.a.", None):
            for fld in ("family", "interface", "message", "actor"):
                f = self.load("lost_consistent.json")
                f["trace"]["producer"][fld] = v
                f["trace"]["waiter"][fld] = v
                if fld == "actor":
                    f["trace"]["adapters"] = []
                    f["trace"]["adapters_none_evidence"] = "direct, no adapter at p.sh:3"
                res = lm.classify(f)
                self.assertNotEqual(res["consistency"], "proven", f"{fld}={v!r} on two links proved consistency")

    def test_adapter_chain_with_unknown_actors_is_unproven(self):
        f = self.load("lost_consistent.json")
        f["trace"]["producer"]["actor"] = "UNKNOWN"
        f["trace"]["adapters"][0]["maps_from"] = "UNKNOWN"
        res = lm.classify(f)
        self.assertNotEqual(res["consistency"], "proven")

    def test_stated_values_still_prove_and_real_mismatches_still_refuse(self):
        res = lm.classify(self.load("lost_consistent.json"))
        self.assertEqual(res["consistency"], "proven")
        f = self.load("lost_consistent.json")
        f["trace"]["waiter"]["family"] = "IF002"
        self.assertEqual(lm.classify(f)["consistency"], "inconsistent")
        f = self.load("lost_consistent.json")
        f["trace"]["producer"]["actor"] = "UNKNOWN"
        f["trace"]["waiter"]["actor"] = "ops"
        self.assertNotEqual(lm.classify(f)["consistency"], "proven")
        f = self.load("lost_consistent.json")
        for link in (f["trace"]["producer"], f["trace"]["adapters"][0], f["trace"]["waiter"]):
            link["family"] = 5
        self.assertEqual(lm.classify(f)["consistency"], "proven")     # a numeric id is a stated value


# ---- D8 / D9 -----------------------------------------------------------------------------------------
def rows_of(name):
    return [json.loads(x) for x in (FIX / name).read_text().splitlines() if x.strip()]


def validate_extract(out, declared="partial"):
    reg = dict(out["register"], coverage={"declared": declared})
    return rv.validate(reg, rv.load_schema(), now=NOW)


class TestD8DistinctCommitsNeverFuse(unittest.TestCase):
    def recs(self, rows, **kw):
        out = xr.convert(rows, **kw)
        return out["register"]["records"], out["stats"]

    def test_fixture_same_repo_same_path_distinct_commits_stay_separate(self):
        recs, st = self.recs(rows_of("extract_distinct_commits.jsonl"))
        self.assertEqual(len(recs), 2)
        self.assertFalse([r for r in recs if "fusion_basis" in r])
        self.assertEqual(st.get("fused_multi_source_components", 0), 0)

    def test_every_spelling_of_one_repo_and_path_keeps_distinct_commits_separate(self):
        c1, c2 = "commit " + "1" * 40, "commit " + "2" * 40
        cases = (("a/x.py", "r1", "a/./x.py", "r1"), ("a/x.py", "https://github.com/o/r.git", "a//x.py", "git@github.com:o/r"),
                 ("a/x.py", "R1", "a/x.py/", "r1/"), ("a/b/../x.py", "r1", "a/x.py", "r1.git"))
        for p1, r1, p2, r2 in cases:
            recs, _ = self.recs([row(path_or_command=p1, source_repo=r1, source_identity=c1),
                                 row(path_or_command=p2, source_repo=r2, source_identity=c2)])
            self.assertEqual(len(recs), 2, (p1, r1, p2, r2))

    def test_same_commit_same_repo_and_path_still_fuses(self):
        c = "commit " + "1" * 40
        recs, _ = self.recs([row(path_or_command="a/./x.py", source_identity=c), row(path_or_command="a/x.py", source_identity=c)])
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["fusion_basis"], "same-repo-identity-and-path")

    def test_same_sha_basis_also_never_fuses_distinct_commits(self):
        # two members that each state a commit AND share a content sha256: the distinct commits keep them apart
        a = row(path_or_command="r1/a.py", source_identity="commit " + "1" * 40)
        b = row(path_or_command="r2/b.py", source_repo="r2", source_identity="commit " + "2" * 40)
        a2 = row(path_or_command="r1/a.py", source_identity="path+sha256:r1/a.py " + H64)
        b2 = row(path_or_command="r2/b.py", source_repo="r2", source_identity="path+sha256:r2/b.py " + H64)
        recs, _ = self.recs([a, a2, b, b2])
        self.assertEqual(len(recs), 2, "distinct commits fused through a shared content sha256")
        self.assertFalse([r for r in recs if "fusion_basis" in r])

    def test_transitive_chain_cannot_join_distinct_commits(self):
        c1, c2 = "commit " + "1" * 40, "commit " + "2" * 40
        rows = [row(path_or_command="r1/a.py", source_identity=c1),
                row(path_or_command="r1/a.py", source_identity=c1)]
        recs, _ = self.recs(rows + [row(path_or_command="a/./y.py", source_identity=c1),
                                    row(path_or_command="a/y.py", source_identity=c2)])
        self.assertEqual(len([r for r in recs if r.get("path_or_command") in ("a/./y.py", "a/y.py")]), 2)

    def test_heuristic_is_the_stated_opt_in_exception_and_still_needs_distinct_identities(self):
        # the opt-in heuristic guesses ONE component from distinct identities by definition (labelled a guess);
        # it still never fuses the same identity twice, and the default never reaches it.
        two = [row(path_or_command="r1/a.py", source_repo="r1", source_identity="commit " + "1" * 40),
               row(path_or_command="r2/a.py", source_repo="r2", source_identity="commit " + "2" * 40)]
        self.assertEqual(len(self.recs(two)[0]), 2)
        recs, _ = self.recs(two, heuristic_fusion=True)
        self.assertEqual([r["fusion_basis"] for r in recs], ["same-name-and-repo-rooted-paths-heuristic"])
        same = [dict(r, source_identity="commit " + "1" * 40) for r in two]
        self.assertEqual(len(self.recs(same, heuristic_fusion=True)[0]), 2)
        self.assertIn("exception", (SK / "SKILL.md").read_text().lower())

    def test_skill_md_and_docstring_agree(self):
        txt = (SK / "SKILL.md").read_text()
        self.assertIn("whatever the basis", txt)
        self.assertIn("distinct commits", (SK / "scripts" / "extract_register.py").read_text())


class TestD9UniqueRecordIds(unittest.TestCase):
    def convert(self, rows, **kw):
        return xr.convert(rows, **kw)

    def check_unique(self, out):
        recs = out["register"]["records"]
        ids = [r["record_id"] for r in recs]
        self.assertEqual(len(ids), len(set(ids)), "duplicate record_id in extractor output")
        keys = [(r["family"], r["role"], r["host"], r["component"], r.get("path_or_command"), r["interface_kind"]) for r in recs]
        self.assertEqual(len(keys), len(set(keys)), "duplicate record key in extractor output")
        for declared in ("partial", "all-interfaces-complete"):
            res = validate_extract(out, declared)
            self.assertNotIn("duplicate-record", {f["code"] for f in res["findings"]},
                             f"extractor output refused as a duplicate under {declared}")
        self.assertTrue(validate_extract(out, "partial")["ok"])

    def test_pathless_member_beside_a_fused_cluster(self):
        out = self.convert(rows_of("extract_pathless_beside_fused.jsonl"))
        self.assertEqual(len(out["register"]["records"]), 2)
        self.check_unique(out)

    def test_cli_output_passes_the_validator_under_partial(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("extract_register.py", FIX / "extract_pathless_beside_fused.jsonl", Path(d) / "o")
            rc2, out2 = run("register_validate.py", Path(d) / "o" / "register-partial.json")
        self.assertEqual(rc2, 0, "the validator refused the extractor's own partial output")
        self.assertNotIn("duplicate-record", out2)

    def test_second_cluster_and_pathless_member(self):
        s = lambda p, h: "path+sha256:%s %s" % (p, h)
        rows = [row(path_or_command="a/x.py", source_identity=s("/p/a.py", "d" * 64)),
                row(path_or_command="b/x.py", source_repo="r2", source_identity=s("/q/a.py", "d" * 64)),
                row(path_or_command="c/x.py", source_repo="r3", source_identity=s("/p/c.py", "e" * 64)),
                row(path_or_command="d/x.py", source_repo="r4", source_identity=s("/q/c.py", "e" * 64)),
                row()]
        self.check_unique(self.convert(rows))

    def test_a_pathless_member_inside_a_cluster_beside_another_pathless_one(self):
        s = lambda p, h: "path+sha256:%s %s" % (p, h)
        rows = [row(source_identity=s("/p/a.py", "d" * 64)),
                row(path_or_command="b/x.py", source_repo="r2", source_identity=s("/q/a.py", "d" * 64)),
                row(host="h", source_repo="r9", source_identity="commit " + "9" * 40)]
        self.check_unique(self.convert(rows))

    def test_exhaustive_small_row_sets_never_collide(self):
        s = lambda h: "path+sha256:/p/a.py " + h * 64
        pool = []
        for path in (None, "a/x.py", "b/x.py", "a/./x.py"):
            for ident in (s("d"), s("e"), "commit " + "1" * 40, "commit " + "2" * 40):
                for repo in ("r1", "r2"):
                    r = row(source_repo=repo, source_identity=ident)
                    if path:
                        r["path_or_command"] = path
                    pool.append(r)
        n = 0
        for combo in itertools.combinations(pool, 3):
            for heur in (False, True):
                out = self.convert([dict(r) for r in combo], heuristic_fusion=heur)
                recs = out["register"]["records"]
                ids = [r["record_id"] for r in recs]
                self.assertEqual(len(ids), len(set(ids)), "duplicate record_id")
                res = validate_extract(out)
                self.assertNotIn("duplicate-record", {f["code"] for f in res["findings"]}, "validator refused extractor output")
                n += 1
        self.assertGreater(n, 1000)


if __name__ == "__main__":
    unittest.main()
