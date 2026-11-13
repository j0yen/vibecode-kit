"""Repairs for the eleventh independent exact-head review of 5d8534e3 (DEFECTS D1-D5, closed as classes).
Fixtures are synthetic and source-only (tests/fixtures/review/fixes11.json); they exercise the rules, not production
behavior. The reference clock is injected (NOW); no test reads the wall clock or depends on the host time zone.
THE ONE IDENTITY RULE (ir_norm.commit_id): a commit text IDENTIFIES a commit when it is a sha (7+ hex, not all zero), a
sha written inside decoration (the hex is a token of its own: 0x, g, a (HEAD) mark, HEAD@{..}, a URL ending in @, label-<hex>),
or a name specific to one commit (a tag, a release, a branch such as feature/login). It is UNSTATED (non-identifying, differs
from nothing, so a same-endpoint pair is a duplicate) when it names no particular commit: UNKNOWN wordings, the null object
(all zeros) and the generic moving pointers HEAD / main / master / latest ... A name never fuses with another name or with a
sha because it contains a hex-like or placeholder word: a hex glued to a name by - / _ . is part of the name.
D1 null sha and floating refs are unstated. D2 an all-digit hex is a hex; text naming two hexes is its own identity.
D3 a lone call / dotted / :: token is a location whatever its words (status(), a.status). D4 names stay distinct (feature/abc1234-login).
D5 a placeholder beside an incidental token (e.g. b/c @bob foo.bar) is non-evidence; a located token (file with line, file with
extension, call, ::, URL, name@version) beside a placeholder is evidence."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from test_register import SK, base
from test_review_fixes2 import NOW, check, errs, run   # noqa: F401  (NOW: injected clock)
from test_review_fixes8 import hand, regs, srcid, vcli

sys.path.insert(0, str(SK / "scripts"))
import ir_norm  # noqa: E402
import register_validate as rv  # noqa: E402

FX = json.loads((Path(__file__).resolve().parent / "fixtures" / "review" / "fixes11.json").read_text())
H, H2, DG = FX["hex"], FX["other_hex"], FX["digit_hex"]


def pair_dup(ca, cb):
    a = hand("r1", source_identity=srcid("o/r", ca))
    b = hand("r2", source_identity=srcid("o/r", cb))
    res = check(regs((a, b), "all-interfaces-complete"))
    return "duplicate-record" in errs(res), res


def verdict(ref, declared="all-interfaces-complete"):
    reg = base(declared)
    reg["records"][1]["evidence"] = [{"ref": ref, "observed_at": "2026-11-12T11:00:00Z"}]
    res = check(reg)
    return res["ok"], "missing-evidence" in {f["code"] for f in res["findings"]}


class TestD1NonIdentifyingCommitsAreUnstated(unittest.TestCase):
    def test_null_sha_and_floating_refs_are_a_duplicate_of_a_real_commit(self):
        for c in FX["non_identifying_commits"]:
            hit, res = pair_dup(H, c)
            self.assertTrue(hit and not res["ok"], f"read as a distinct commit: {c!r}")
            self.assertIsNone(ir_norm.commit_id(c), c)

    def test_two_non_identifying_commits_are_a_duplicate_of_each_other(self):
        for ca, cb in (("HEAD", "main"), ("main", "master"), ("latest", "HEAD"), ("0" * 40, "0000000"), ("0" * 40, "origin/main"),
                       ("trunk", "FETCH_HEAD")):
            self.assertTrue(pair_dup(ca, cb)[0], (ca, cb))

    def test_a_specific_name_is_a_commit_of_its_own(self):
        for c in FX["specific_names_distinct_from_sha"]:
            self.assertFalse(pair_dup(H, c)[0], c)
            self.assertIsNotNone(ir_norm.commit_id(c), c)
        for ca, cb in FX["specific_name_pairs"]:
            self.assertFalse(pair_dup(ca, cb)[0], (ca, cb))

    def test_a_pointer_word_inside_a_longer_name_does_not_make_it_a_pointer(self):
        for c in ("main-fix-12", "mainline", "headless-v2", "latest-release-notes", "tip-of-the-day-2"):
            self.assertIsNotNone(ir_norm.commit_id(c), c)

    def test_zero_sha_in_a_different_repo_or_host_still_does_not_fuse(self):
        a = hand("r1", source_identity=srcid("o/a", "0" * 40))
        b = hand("r2", source_identity=srcid("o/b", "0" * 40))
        self.assertFalse("duplicate-record" in errs(check(regs((a, b)))))
        c = hand("r3", source_identity=srcid("o/a", "0" * 40), host="h2")
        self.assertFalse("duplicate-record" in errs(check(regs((a, c)))))

    def test_cli_refuses_complete_naming_both_records(self):
        for c in ("0" * 40, "0000000", "HEAD", "main", "origin/main", "FETCH_HEAD", "HEAD~1"):
            a = hand("r1", source_identity=srcid("o/r", H))
            b = hand("r2", source_identity=srcid("o/r", c))
            rc, out = vcli(regs((a, b)))
            self.assertEqual(rc, 1, c)
            self.assertIn("duplicate-record", out)
            self.assertIn("r1", out)
            self.assertIn("r2", out)

    def test_skill_lists_every_pointer_word_the_code_reads(self):
        text = (SK / "SKILL.md").read_text()
        for w in ir_norm.FLOATING_WORDS:
            self.assertIn(w, text, w)
        for phrase in ("non-identifying commit", "all-zero"):
            self.assertIn(phrase, text)


class TestD2AllDigitHexAndTwoHexTexts(unittest.TestCase):
    def test_all_digit_hex_in_any_decoration_is_the_same_commit(self):
        for c in FX["digit_spelled_same"]:
            hit, res = pair_dup(DG, c)
            self.assertTrue(hit and not res["ok"], f"read as a different commit: {c!r}")
            self.assertEqual(ir_norm.commit_id(c), DG, c)

    def test_long_all_digit_hex_in_decoration(self):
        for c in FX["digit_long_spelled_same"]:
            self.assertEqual(ir_norm.commit_id(c), "12345678", c)
            self.assertTrue(pair_dup("12345678", c)[0], c)

    def test_all_digit_abbreviation_matches_the_long_sha_it_prefixes(self):
        self.assertTrue(pair_dup(DG, "1234567" + "8901234567890123456789012345678" + "90")[0])
        self.assertTrue(pair_dup("g" + DG, "1234567890123456789012345678901234567890")[0])

    def test_a_web_url_ending_in_the_sha_is_the_same_commit(self):
        for c in FX["url_spelled_same"]:
            self.assertEqual(ir_norm.commit_id(c), H, c)
            self.assertTrue(pair_dup(H, c)[0], c)
        for c in FX["url_digit_spelled_same"]:
            self.assertEqual(ir_norm.commit_id(c), DG, c)

    def test_text_naming_two_hexes_is_its_own_identity(self):
        for t in FX["two_hex_texts"]:
            c = ir_norm.commit_id(t)
            self.assertIsNotNone(c, t)
            for h in ("a1b2c3d4", "1" * 40, DG, "7654321", "abc1234", "abc1235"):
                self.assertNotEqual(c, h, (t, h))
                self.assertFalse(pair_dup(h, t)[0], (h, t))

    def test_one_hex_repeated_is_still_one_commit(self):
        self.assertEqual(ir_norm.commit_id("1234567 (1234567)"), DG)
        self.assertEqual(ir_norm.commit_id("abc1234 / abc1234"), "abc1234")

    def test_all_letter_words_are_never_read_as_a_hex(self):
        for t in ("see defaced code", "commit defaced main"):
            self.assertNotEqual(ir_norm.commit_id(t), "defaced", t)

    def test_cli_refuses_complete_for_all_digit_spellings(self):
        for c in ("g1234567", "1234567 (HEAD)", "v1.0-3-g1234567"):
            a = hand("r1", source_identity=srcid("o/r", DG))
            b = hand("r2", source_identity=srcid("o/r", c))
            rc, out = vcli(regs((a, b)))
            self.assertEqual(rc, 1, c)
            self.assertIn("duplicate-record", out)


def erow(commit, **kw):
    r = {"family": "IF001", "role": "producer", "host": "h", "component": "c", "interface_kind": "http",
         "installed_state": "source-only", "evidence": "side=producer", "source_repo": "o/r",
         "source_identity": "commit " + commit, "path_or_command": "a.py"}
    r.update(kw)
    return r


class TestExtractorReadsTheNullShaAsTheValidatorDoes(unittest.TestCase):
    """The extractor's output must pass the validator's duplicate-record check: a row whose commit is the null object
    states no commit, as UNKNOWN does, so it joins the row of the same endpoint instead of staying a second record."""

    def extract(self, rows):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.jsonl"
            src.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            out = Path(d) / "out"
            rc, text = run("extract_register.py", str(src), str(out))
            self.assertEqual(rc, 0, text)
            return json.loads((out / "register-partial.json").read_text())

    def test_null_sha_row_joins_the_row_of_the_same_endpoint(self):
        for z in ("0" * 40,):
            reg = self.extract([erow("1" * 40), erow(z)])
            self.assertEqual(len(reg["records"]), 1, z)
            self.assertEqual(rv._duplicate_groups(reg["records"]), [])

    def test_two_real_commits_stay_two_records_and_never_a_duplicate_pair(self):
        reg = self.extract([erow("1" * 40), erow("2" * 40)])
        self.assertEqual(len(reg["records"]), 2)
        self.assertEqual(rv._duplicate_groups(reg["records"]), [])

    def test_null_sha_row_is_not_a_stated_source_commit(self):
        reg = self.extract([erow("0" * 40)])
        for r in reg["records"]:
            for si in rv._sources(r):
                self.assertNotIn("commit", si[1])


class TestD3CallAndDottedRefsOfFillerWordsAreEvidence(unittest.TestCase):
    def test_a_lone_call_dotted_or_scope_token_is_a_location(self):
        for ref in FX["call_dotted_evidence"]:
            ok, missing = verdict(ref)
            self.assertTrue(ok and not missing, f"refused: {ref!r}")
            self.assertFalse(ir_norm.non_evidence(ref), ref)

    def test_a_token_of_placeholder_words_only_is_still_non_evidence(self):
        for ref in FX["call_dotted_non_evidence"]:
            ok, missing = verdict(ref)
            self.assertTrue(missing and not ok, f"counts as evidence: {ref!r}")
            self.assertTrue(ir_norm.non_evidence(ref), ref)

    def test_cli_accepts_complete_with_a_call_ref(self):
        for ref in ("status()", "a.status", "Status::Unknown"):
            reg = base()
            reg["records"][1]["evidence"] = [{"ref": ref, "observed_at": "2026-11-12T11:00:00Z"}]
            rc, out = vcli(reg)
            self.assertNotIn("missing-evidence", out, ref)


class TestD4DistinctNamesStayDistinct(unittest.TestCase):
    def test_branch_and_tag_names_never_fuse(self):
        for ca, cb in FX["branch_name_pairs"]:
            hit, _ = pair_dup(ca, cb)
            self.assertFalse(hit, (ca, cb))

    def test_a_name_keeps_its_own_spelling_as_identity(self):
        for c in ("feature/abc1234-login", "bugfix/abc1234-logout", "null-handling-fix", "pending-release", "pr/abc1234"):
            self.assertEqual(ir_norm.commit_id(c), c.lower(), c)

    def test_a_phrase_with_blanks_that_holds_a_placeholder_word_is_still_unstated(self):
        for c in ("unknown commit", "pending approval from bob", "not recorded", "unknown until release"):
            self.assertIsNone(ir_norm.commit_id(c), c)

    def test_names_are_a_separate_endpoint_on_the_cli(self):
        a = hand("r1", source_identity=srcid("o/r", "feature/abc1234-login"))
        b = hand("r2", source_identity=srcid("o/r", "bugfix/abc1234-logout"))
        rc, out = vcli(regs((a, b)))
        self.assertEqual(rc, 0, out)


class TestD5PlaceholderWithIncidentalTokenIsNonEvidence(unittest.TestCase):
    def test_abbreviation_mention_or_alternative_beside_a_placeholder(self):
        for ref in FX["incidental_token_non_evidence"]:
            ok, missing = verdict(ref)
            self.assertTrue(missing and not ok, f"counts as evidence: {ref!r}")
            self.assertTrue(ir_norm.non_evidence(ref), ref)

    def test_a_located_token_beside_a_placeholder_is_evidence(self):
        for ref in FX["located_prose_evidence"]:
            ok, missing = verdict(ref)
            self.assertTrue(ok and not missing, f"refused: {ref!r}")
            self.assertFalse(ir_norm.non_evidence(ref), ref)

    def test_cli_refuses_complete_naming_the_record(self):
        for ref in ("unknown e.g. later", "status: unknown (owner @bob)", "status: unknown, see foo.bar"):
            reg = base()
            reg["records"][1]["evidence"] = [{"ref": ref, "observed_at": "2026-11-12T11:00:00Z"}]
            rc, out = vcli(reg)
            self.assertEqual(rc, 1, ref)
            self.assertIn("missing-evidence", out)

    def test_partial_register_only_warns(self):
        ok, missing = verdict("unknown e.g. later", "partial")
        self.assertTrue(ok and missing)


class TestOneRuleEachConceptHoldsBothDirections(unittest.TestCase):
    def test_pairwise_definition_and_keyed_grouping_agree_on_every_new_spelling(self):
        cs = (FX["non_identifying_commits"] + FX["specific_names_distinct_from_sha"] + FX["digit_spelled_same"]
              + FX["digit_long_spelled_same"] + FX["two_hex_texts"] + [x for p in FX["branch_name_pairs"] for x in p])
        for base_c in (H, DG, "main", "feature/abc1234-login"):
            for c in cs:
                a = hand("r1", source_identity=srcid("o/r", base_c))
                b = hand("r2", source_identity=srcid("o/r", c))
                self.assertEqual(bool(rv._duplicate_groups([a, b])), rv._conflict(rv._ident(a), rv._ident(b)), (base_c, c))

    def test_commit_rule_is_one_function_a_mutant_of_it_breaks_the_validator(self):
        real = rv._N.commit_id
        rv._N.commit_id = lambda c: c.lower().strip() if isinstance(c, str) else None
        try:
            self.assertFalse(pair_dup(H, "0" * 40)[0])
            self.assertFalse(pair_dup(H, "HEAD")[0])
        finally:
            rv._N.commit_id = real
        self.assertTrue(pair_dup(H, "0" * 40)[0])
        self.assertTrue(pair_dup(H, "HEAD")[0])

    def test_evidence_rule_is_one_function_a_mutant_of_it_breaks_the_validator(self):
        real = rv._N.non_evidence
        rv._N.non_evidence = lambda ref: False
        try:
            self.assertFalse(verdict("unknown e.g. later")[1])
        finally:
            rv._N.non_evidence = real
        self.assertTrue(verdict("unknown e.g. later")[1])

    def test_every_new_spelling_gives_the_same_answer_as_before_when_repeated(self):
        for c in FX["non_identifying_commits"] + FX["digit_spelled_same"]:
            self.assertEqual(ir_norm.commit_id(c), ir_norm.commit_id(c))

    def test_skill_states_the_identity_rule_and_the_anchor_rule(self):
        text = (SK / "SKILL.md").read_text()
        for phrase in ("non-identifying commit", "all-zero", "a hex glued to a name", "lone call"):
            self.assertIn(phrase, text, phrase)


if __name__ == "__main__":
    unittest.main()
