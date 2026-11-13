"""Repairs for the thirteenth independent exact-head review of a818a6dd (DEFECTS Y1-Y3, closed as classes).
Fixtures are synthetic and source-only (tests/fixtures/review/fixes13.json); they exercise the rules, not production
behavior. The reference clock is injected (NOW via the shared helpers); no test reads the wall clock or the host time zone.

THE IDENTITY RULE FOR RELATION WORDS (ir_norm._relates), stated once:
  * a relation word just before the hex (_RELATION) makes the text a name of its own, ANOTHER commit than the sha, when the
    word points AWAY from the sha: bare ("parent <hex>", "fix <hex>"), or with of / for / from / to / onto / on / with;
  * the same word followed by in / by / at / as points AT the sha: "fixed in <hex>", "merged at <hex>", "reverted by <hex>",
    "superseded by <hex>" name the fixing / merging / reverting commit, which IS the sha, so the text stays the sha;
  * the bare forms "fix <hex>", "merge <hex>", "since <hex>", "base <hex>" are ambiguous and stay a different commit (author
    judgement stated in SKILL.md).
Y2 a hedge mark (modal, hedge word stem, "?", an alternative side) in the clause leaves a role UNKNOWN. Y3 a state word beside only a
number or a count (a result, a count, a non-pinned location) is not evidence."""
import json
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path

from test_review_fixes11 import erow, pair_dup, verdict
from test_register import SK
from test_review_fixes2 import run

sys.path.insert(0, str(SK / "scripts"))
import ir_norm  # noqa: E402

FX = json.loads((Path(__file__).resolve().parent / "fixtures" / "review" / "fixes13.json").read_text())
H, O = FX["hex"], FX["other_hex"]


def fill(templates, h=H):
    return [t % h if "%s" in t else t for t in templates]


def roles(evidence):
    """The roles the extractor gives one row whose evidence is `evidence` (claimed role producer)."""
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "in.jsonl"
        src.write_text(json.dumps(erow("1" * 40, evidence=evidence)) + "\n")
        out = Path(d) / "out"
        rc, text = run("extract_register.py", str(src), str(out))
        assert rc == 0, text
        return [r["role"] for r in json.loads((out / "register-partial.json").read_text())["records"]]


class TestY1RelationDirection(unittest.TestCase):
    def test_a_relation_that_points_at_the_sha_is_the_sha(self):
        for c in fill(FX["rel13_same"] + FX["own_relation_same"]):
            self.assertEqual(ir_norm.commit_id(c), H, c)
            hit, res = pair_dup(H, c)
            self.assertTrue(hit and not res["ok"], f"read as a distinct commit: {c!r}")

    def test_a_relation_that_points_away_is_another_commit(self):
        for c in fill(FX["rel13_distinct"] + FX["own_relation_distinct"] + FX["author_pinned_distinct"]):
            self.assertNotEqual(ir_norm.commit_id(c), H, c)
            self.assertIsNotNone(ir_norm.commit_id(c), c)
            self.assertFalse(pair_dup(H, c)[0], c)

    def test_the_direction_does_not_fuse_different_shas(self):
        for c in FX["rel13_same"] + FX["own_relation_same"]:
            self.assertFalse(pair_dup(H, c % O)[0], c)
            self.assertTrue(pair_dup(c % H, c % H)[0], c)

    def test_two_pointing_at_phrases_of_one_sha_are_a_duplicate_and_a_distinct_one_is_not(self):
        self.assertTrue(pair_dup("fixed in " + H, "reverted by " + H[:9])[0])
        self.assertFalse(pair_dup("fixed in " + H, "parent " + H)[0])

    def test_skill_states_the_direction_and_the_author_judgement(self):
        text = (SK / "SKILL.md").read_text()
        for w in ("points at", "fixed in", "fix <hex>", "since <hex>"):
            self.assertIn(w, text, w)


class TestY2HedgeMarksLeaveTheRoleUnknown(unittest.TestCase):
    def test_reviewer_hedge_forms_are_unknown(self):
        for e in FX["hedge_forms"]:
            self.assertEqual(roles(e), ["UNKNOWN"], e)

    def test_own_hedge_forms_not_spelled_in_the_code_are_unknown(self):
        for e in FX["hedge_own"]:
            self.assertEqual(roles(e), ["UNKNOWN"], e)

    def test_a_plain_statement_keeps_the_role(self):
        for e in FX["hedge_plain_producer"]:
            self.assertEqual(roles(e), ["producer"], e)

    def test_hedge_is_one_rule_in_ir_norm(self):
        self.assertTrue(ir_norm.hedged("maybe "))
        self.assertTrue(ir_norm.hedged(" or consumer"))
        self.assertFalse(ir_norm.hedged(" confirmed by src/a.py:3"))

    def test_skill_states_the_vocabulary_limit(self):
        text = (SK / "SKILL.md").read_text()
        for w in ("hedge", "alternative"):
            self.assertIn(w, text, w)


class TestY3StateWordBesideOnlyANumber(unittest.TestCase):
    def test_reviewer_decorated_placeholders_are_non_evidence(self):
        for r in FX["ev_state_number_non_evidence"]:
            self.assertTrue(ir_norm.non_evidence(r), r)
            self.assertTrue(verdict(r)[1], r)

    def test_own_decorated_placeholders_not_spelled_in_the_code_are_non_evidence(self):
        for r in FX["own_state_number_non_evidence"]:
            self.assertTrue(ir_norm.non_evidence(r), r)

    def test_a_zero_count_of_a_state_word_is_a_positive_statement(self):
        """"0 pending", "zero missing" are not state words (regression found by the earlier neg9 probe set, row e30)."""
        for r in FX["zero_count_of_a_state_word_is_evidence"]:
            self.assertFalse(ir_norm.non_evidence(r), r)

    def test_the_pinned_location_tolerance_stays(self):
        for r in FX["ev_state_pinned_location_evidence"]:
            self.assertFalse(ir_norm.non_evidence(r), r)

    def test_a_number_without_a_state_word_is_evidence(self):
        for r in FX["own_number_evidence"] + FX["ev_genuine"]:
            if r == "pending PR 12 merged":
                continue                      # R4, the stated refusal-side residual
            self.assertFalse(ir_norm.non_evidence(r), r)

    def test_a_long_run_of_state_word_and_counts_is_read_in_linear_time(self):
        """A quadratic re-scan of the text per number ("unknown 3 passed 3 passed ...": found by the strict ReDoS probe) costs 64x for 8x
        the length; a linear pass costs 8x. The bound (below 24x for 8x the length, best of three) is coarse on purpose."""
        def best(n):
            text = "unknown " + "3 passed " * n
            out = []
            for _ in range(3):
                s = time.process_time()
                ir_norm.non_evidence(text)
                out.append(time.process_time() - s)
            return min(out)
        small, large = best(2000), best(16000)
        self.assertLess(large, 24 * max(small, 0.002), (small, large))

    def test_skill_states_the_rule(self):
        text = (SK / "SKILL.md").read_text()
        self.assertIn("result count", text)
        self.assertIn("state word", text)


if __name__ == "__main__":
    unittest.main()
