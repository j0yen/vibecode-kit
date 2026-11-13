"""Repairs for the tenth independent exact-head review of 55a4af8b (DEFECTS D1, D2, closed as classes).
Fixtures are synthetic and source-only (tests/fixtures/review/fixes10.json); they exercise the rules, not production
behavior. The reference clock is injected (NOW); no test reads the wall clock or depends on the host time zone.
D1: a prose evidence ref built from the contract's own placeholder words stays non-evidence whatever punctuation, quote,
    "=", backtick, number or date decorates it. A weak mark (quote, "=", backtick, "#", a bare number or version attached
    to a placeholder word) is never a concrete anchor; a path, dotted name, "::", call or "@" token with a word that is
    not a placeholder/filler word, or a number following a content word ("line 12"), is.
D2: a commit that only says it is not known (any placeholder wording, an all-zero sha) is UNSTATED; one commit written
    around its hex (0x, g, a (HEAD) mark, HEAD@{..}, a URL, a trailing ref name) is the same commit; a label followed by
    "-" is not stripped from a non-hex ref (git-2.40 is not 2.40)."""
import json
import sys
import unittest
from pathlib import Path

from test_register import SK, base
from test_review_fixes2 import NOW, check, errs   # noqa: F401  (NOW: injected clock)
from test_review_fixes8 import hand, regs, srcid, vcli

sys.path.insert(0, str(SK / "scripts"))
import ir_norm  # noqa: E402
import register_validate as rv  # noqa: E402

FX = json.loads((Path(__file__).resolve().parent / "fixtures" / "review" / "fixes10.json").read_text())
H, H2 = FX["hex"], FX["other_hex"]


def pair_dup(ca, cb):
    a = hand("r1", source_identity=srcid("o/r", ca))
    b = hand("r2", source_identity=srcid("o/r", cb))
    res = check(regs((a, b), "all-interfaces-complete"))
    return "duplicate-record" in errs(res), res


class TestD2UnstatedAndAlternateCommits(unittest.TestCase):
    def test_every_unstated_wording_is_a_duplicate_of_the_real_commit(self):
        for c in FX["unstated_commits"]:
            hit, res = pair_dup(H, c)
            self.assertTrue(hit and not res["ok"], f"read as a stated commit: {c!r}")
            self.assertIsNone(ir_norm.commit_id(c), c)

    def test_two_unstated_wordings_are_a_duplicate_of_each_other(self):
        for ca, cb in (("tbc", "not recorded"), ("pending", "unknown commit"), ("no commit", "UNKNOWN")):
            hit, _ = pair_dup(ca, cb)
            self.assertTrue(hit, (ca, cb))

    def test_hex_with_a_decoration_is_the_same_commit(self):
        for c in FX["spelled_same"]:
            hit, res = pair_dup(H, c)
            self.assertTrue(hit and not res["ok"], f"read as a different commit: {c!r}")

    def test_distinct_commits_stay_two_endpoints(self):
        for ca, cb in FX["distinct_commits"]:
            hit, _ = pair_dup(ca, cb)
            self.assertFalse(hit, (ca, cb))
        hit, _ = pair_dup(H, H2)
        self.assertFalse(hit)

    def test_a_label_before_a_dash_is_not_stripped_from_a_name(self):
        self.assertEqual(ir_norm.commit_id("git-2.40"), "git-2.40")
        self.assertEqual(ir_norm.commit_id("rev-1"), "rev-1")
        self.assertEqual(ir_norm.commit_id("sha256-" + H), H)
        self.assertEqual(ir_norm.commit_id("sha-1:" + H), H)

    def test_branch_names_are_stated_commits_of_their_own(self):
        for c in ("HEAD", "main", "master", "latest"):
            self.assertEqual(ir_norm.commit_id(c), c.lower())

    def test_cli_refuses_complete_naming_both_records(self):
        for c in ("unknown (pending)", "tbc", "not recorded", "HEAD@{" + H + "}"):
            a = hand("r1", source_identity=srcid("o/r", H))
            b = hand("r2", source_identity=srcid("o/r", c))
            rc, out = vcli(regs((a, b)))
            self.assertEqual(rc, 1, c)
            self.assertIn("duplicate-record", out)
            self.assertIn("r1", out)
            self.assertIn("r2", out)

    def test_identity_keeps_an_unstated_commit_out_of_the_stated_set(self):
        for c in FX["unstated_commits"]:
            self.assertEqual(rv._ident(hand("r1", source_identity=srcid("o/r", c)))[1], frozenset(), c)

    def test_pairwise_definition_and_keyed_grouping_agree_on_the_new_spellings(self):
        for c in FX["unstated_commits"] + FX["spelled_same"] + [x for p in FX["distinct_commits"] for x in p]:
            a = hand("r1", source_identity=srcid("o/r", H))
            b = hand("r2", source_identity=srcid("o/r", c))
            self.assertEqual(bool(rv._duplicate_groups([a, b])), rv._conflict(rv._ident(a), rv._ident(b)), c)

    def test_commit_rule_is_one_function_a_mutant_of_it_breaks_the_validator(self):
        real = rv._N.commit_id
        rv._N.commit_id = lambda c: c.lower().strip() if isinstance(c, str) else None
        try:
            self.assertFalse(pair_dup(H, "tbc")[0])
        finally:
            rv._N.commit_id = real
        self.assertTrue(pair_dup(H, "tbc")[0])


class TestD1PlaceholderWordsWithPunctuationAreNeverEvidence(unittest.TestCase):
    def verdict(self, ref, declared="all-interfaces-complete"):
        reg = base(declared)
        reg["records"][1]["evidence"] = [{"ref": ref, "observed_at": "2026-11-12T11:00:00Z"}]
        res = check(reg)
        return res["ok"], "missing-evidence" in {f["code"] for f in res["findings"]}

    def test_every_decorated_placeholder_is_missing_evidence_on_complete(self):
        for ref in FX["non_evidence"]:
            ok, missing = self.verdict(ref)
            self.assertTrue(missing and not ok, f"counts as evidence: {ref!r}")
            self.assertTrue(ir_norm.non_evidence(ref), ref)

    def test_genuine_refs_stay_evidence(self):
        for ref in FX["evidence"]:
            ok, missing = self.verdict(ref)
            self.assertTrue(ok and not missing, f"refused: {ref!r}")
            self.assertFalse(ir_norm.non_evidence(ref), ref)

    def test_weak_marks_next_to_a_placeholder_word_are_not_anchors(self):
        for ref in ("unknown 2026", "unknown v1", "null #3", "nil 'x'", "status: unknown (2026-11-12)", "pending `a`"):
            self.assertTrue(ir_norm.non_evidence(ref), ref)

    def test_a_location_or_a_number_after_a_content_word_is_an_anchor(self):
        for ref in ("mock server config line 12", "unknown.log line 3", "stub gen/stub.py:7", "pending parse.rs:9",
                    "see unknown::parse", "todo fix() at x.py:2"):
            self.assertFalse(ir_norm.non_evidence(ref), ref)

    def test_placeholder_judged_the_same_with_or_without_prose_shape(self):
        # one rule: a ref of one token ("status=unknown", "<evidence>") is judged as a ref with spaces
        for ref in ("status=unknown", "status:unknown", "<evidence>", "FIXME", "tbc"):
            self.assertTrue(ir_norm.non_evidence(ref), ref)
            self.assertTrue(self.verdict(ref)[1], ref)

    def test_cli_refuses_complete_naming_the_record(self):
        for ref in ("status=unknown", "evidence: n.a.", "status: unknown v1"):
            reg = base()
            reg["records"][1]["evidence"] = [{"ref": ref, "observed_at": "2026-11-12T11:00:00Z"}]
            rc, out = vcli(reg)
            self.assertEqual(rc, 1, ref)
            self.assertIn("missing-evidence", out)

    def test_partial_register_only_warns(self):
        ok, missing = self.verdict("status=unknown", "partial")
        self.assertTrue(ok and missing)

    def test_skill_states_the_anchor_rule_as_code_does(self):
        text = (SK / "SKILL.md").read_text()
        self.assertIn("weak mark", text)
        self.assertIn("unstated commit", text)


if __name__ == "__main__":
    unittest.main()
