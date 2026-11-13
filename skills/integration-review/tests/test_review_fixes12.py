"""Repairs for the twelfth independent exact-head review of d00cb14a (DEFECTS X1-X5, closed as classes).
Fixtures are synthetic and source-only (tests/fixtures/review/fixes12.json); they exercise the rules, not production
behavior. The reference clock is injected (NOW); no test reads the wall clock or depends on the host time zone.

THE ONE IDENTITY RULE (ir_norm.commit_id): a commit text names the commit it IS.
  * a sha (7+ hex, not all zero), or a sha that is the subject of its text (a token of its own, or glued to 0x / g / a label
    by - _ / : = # @, followed by a file suffix such as .patch or a trailing slash, inside a URL path), is that commit;
  * a RELATION to a sha (parent, revert, cherry-picked from, hotfix for, ~N, ^N) is another commit: a name of its own;
  * a name that merely contains a hex ("feature/<hex>-login", "fix-<hex>", "build-<hex>") is a name of its own;
  * a text naming no particular commit (UNKNOWN wordings, the null object, a moving pointer, a reflog / upstream expression
    X@{..}, a pointer with ~N / ^N) is UNSTATED and differs from nothing.
X1 reflog and upstream suffixes; X2 label-glued spellings; X3 linear time in a token's length; X4 a number anchors a placeholder
only after a location noun (line, row, column, page, step ...); X5 relation phrases are not the commit they relate to."""
import gc
import json
import re
import sys
import time
import unittest
from pathlib import Path

from test_review_fixes11 import pair_dup, verdict
from test_register import SK

sys.path.insert(0, str(SK / "scripts"))
import ir_norm  # noqa: E402

FX = json.loads((Path(__file__).resolve().parent / "fixtures" / "review" / "fixes12.json").read_text())
H, O = FX["hex"], FX["other_hex"]


def fill(templates, h=H):
    return [t % h if "%s" in t else t for t in templates]


class TestX1ReflogAndPointerSuffixes(unittest.TestCase):
    def test_reflog_and_upstream_suffixes_are_unstated_and_a_duplicate(self):
        for c in FX["reflog_unstated"]:
            self.assertIsNone(ir_norm.commit_id(c), c)
            hit, res = pair_dup(H, c)
            self.assertTrue(hit and not res["ok"], f"read as a distinct commit: {c!r}")

    def test_revision_suffix_on_a_pointer_is_unstated(self):
        for c in FX["revision_suffix_pointer_unstated"]:
            self.assertIsNone(ir_norm.commit_id(c), c)
            self.assertTrue(pair_dup(H, c)[0], c)

    def test_pointer_vocabulary_is_unstated(self):
        for c in FX["pointer_vocabulary_unstated"]:
            self.assertIsNone(ir_norm.commit_id(c), c)
            self.assertTrue(pair_dup(H, c)[0], c)

    def test_a_name_that_holds_a_pointer_word_stays_a_name(self):
        for c in FX["names_not_pointers"]:
            self.assertIsNotNone(ir_norm.commit_id(c), c)
            self.assertFalse(pair_dup(H, c)[0], c)

    def test_reflog_entry_naming_a_sha_is_still_that_sha(self):
        self.assertEqual(ir_norm.commit_id("HEAD@{%s}" % H), H)
        self.assertEqual(ir_norm.commit_id("main@{%s}" % H[:9]), H[:9])

    def test_two_reflog_forms_are_a_duplicate_of_each_other(self):
        for ca, cb in (("HEAD@{1}", "main@{upstream}"), ("@{u}", "stash@{3}"), ("HEAD@{yesterday}", H[:9] + "@{1}")):
            self.assertTrue(pair_dup(ca, cb)[0], (ca, cb))

    def test_skill_states_the_reflog_rule(self):
        text = (SK / "SKILL.md").read_text()
        self.assertIn("@{..}", text)


class TestX2LabelGluedSpellingsAreTheSameCommit(unittest.TestCase):
    def test_label_and_file_suffix_spellings_equal_the_bare_sha(self):
        for c in fill(FX["glued_spellings_same"]):
            self.assertEqual(ir_norm.commit_id(c), H, c)
            hit, res = pair_dup(H, c)
            self.assertTrue(hit and not res["ok"], f"read as a distinct commit: {c!r}")

    def test_abbreviated_glued_spelling_matches_the_long_sha(self):
        for t in ("commit_%s", "sha_%s", "commit/%s", "%s.patch", "archive/%s.zip", "rev_%s"):
            self.assertTrue(pair_dup(H, t % H[:8])[0], t)

    def test_glued_spelling_of_a_different_sha_is_a_different_commit(self):
        for t in ("commit_%s", "sha_%s", "commit/%s", "%s.patch", "archive/%s.zip", "hash_%s"):
            self.assertFalse(pair_dup(H, t % O)[0], t)
            self.assertFalse(pair_dup(t % H, t % O)[0], t)

    def test_names_holding_a_hex_stay_names(self):
        for c in fill(FX["glued_names_distinct"]):
            self.assertNotEqual(ir_norm.commit_id(c), H, c)
            self.assertFalse(pair_dup(H, c)[0], c)
        for a, b in FX["glued_name_pairs"]:
            self.assertFalse(pair_dup(a % H, b % O)[0], (a, b))
            self.assertFalse(pair_dup(a % H, b % H)[0], (a, b))

    def test_same_glued_spelling_twice_is_a_duplicate(self):
        for c in ("commit_%s", "feature/%s-login", "fix-%s"):
            self.assertTrue(pair_dup(c % H, c % H)[0], c)


class TestX3LinearInTokenLength(unittest.TestCase):
    """The reviewer's adversarial shapes: one long unbroken word / dotted / call-like / hex token."""
    SHAPES = {
        "word": lambda n: "a" * n,
        "dotted": lambda n: "a." * (n // 2),
        "callish": lambda n: "unknown " + "a_b.c" * (n // 5),
        "hexdump": lambda n: "e3b0c44298fc1c14" * (n // 16),
        "dotrun-then-call": lambda n: "a." * (n // 2) + "(x)",
        "many-calls": lambda n: "a(x)" * (n // 4),
        "open-parens": lambda n: "unknown " + "(" * n,
    }

    def best(self, f, x):
        """CPU seconds of f(x): the minimum of up to seven runs with the collector off (one run when it already takes 0.2 s:
        a slow path is not noise)."""
        out = []
        gc.disable()
        try:
            for _ in range(7):
                s = time.process_time()
                f(x)
                out.append(time.process_time() - s)
                if out[-1] > 0.2:
                    break
        finally:
            gc.enable()
        return min(out)

    def test_time_doubles_with_the_length_not_quadruples(self):
        """n = 1000 / 2000 / 4000 units of 16 characters. A linear path doubles its time (measured 1.4x-2.6x per doubling on a loaded
        host: cache and allocator steps, and a 10-50 ms call is near the timer noise); a quadratic path costs 4x per doubling and
        16x over the range. The test therefore fails above 6x over n=1000 -> 4000 or above 3.4x at one doubling. Load only adds
        time, so the series keeps the minimum per size over up to five rounds. The strict figure (worst ratio per doubling <= 2.2
        on a quiet host) is measured in the report, not asserted here."""
        unit = 16
        for name, make in self.SHAPES.items():
            for fn in (ir_norm.non_evidence, ir_norm._commit_id.__wrapped__):
                xs = [make(n * unit) for n in (1000, 2000, 4000)]
                ts = [float("inf")] * 3
                for _ in range(5):
                    ts = [min(t, self.best(fn, x)) for t, x in zip(ts, xs)]
                    if ts[2] / max(ts[0], 0.01) <= 6.0 and all(b / max(a, 0.01) <= 3.4 for a, b in zip(ts, ts[1:])):
                        break
                else:
                    self.fail((name, fn.__name__, ts))

    def test_a_long_token_is_judged_in_well_under_a_second(self):
        for name, make in self.SHAPES.items():
            self.assertLess(self.best(ir_norm.non_evidence, make(64000)), 1.0, name)

    def test_call_detection_reads_the_same_tokens_as_before(self):
        for tok in ("a_b.c", "a.b.c", "aaaa", "a1", "a.", "(", "a(", "(a", "a(b", "a(b)(c", "ab.cd(", "1(2)"):
            self.assertEqual(ir_norm._has_call(tok), bool(re.search(r"[a-z_][\w.]*\([^()\s]*\)", tok)), tok)
        for tok in ("f()", "a.b()", "status(x)", "1.f(a)", "x(y)z", "(a)b(c)", "a b(c)", "emit.send()", "self.f(1)", ".(x)", "1(2)", "9.(x)",
                    "check_null()", "a(b c)"):
            self.assertEqual(ir_norm._has_call(tok), bool(re.search(r"[a-z_][\w.]*\([^()\s]*\)", tok)), tok)


class TestX4NumberAnchorsOnlyAfterALocationNoun(unittest.TestCase):
    def test_dated_and_counted_placeholders_are_non_evidence(self):
        for r in FX["number_after_word_non_evidence"]:
            self.assertTrue(ir_norm.non_evidence(r), r)
            self.assertTrue(verdict(r)[1], r)

    def test_a_number_after_a_location_noun_is_a_location(self):
        for r in FX["number_after_location_evidence"]:
            self.assertFalse(ir_norm.non_evidence(r), r)

    def test_located_placeholders_stay_evidence_in_the_register(self):
        for r in ("unknown line 3", "mock server config line 12", "stub at column 8", "unknown 2026-11-12 line 3"):
            ok, missing = verdict(r)
            self.assertFalse(missing, r)

    def test_a_number_with_a_real_anchor_is_evidence(self):
        for r in FX["number_with_anchor_evidence"]:
            self.assertFalse(ir_norm.non_evidence(r), r)

    def test_no_placeholder_no_change(self):
        for r in ("status 200", "ran 12 tests", "4 passed", "since 2026-11-12 the build is green", "after 3 retries it passed"):
            self.assertFalse(ir_norm.non_evidence(r), r)


class TestX5RelationsAreNotTheCommitTheyRelateTo(unittest.TestCase):
    def test_relation_phrases_are_distinct_from_the_sha(self):
        for c in fill(FX["relation_phrases_distinct"]):
            self.assertIsNotNone(ir_norm.commit_id(c), c)
            self.assertNotEqual(ir_norm.commit_id(c), H, c)
            self.assertFalse(pair_dup(H, c)[0], c)

    def test_relation_phrases_of_different_shas_and_relations_stay_distinct(self):
        for a, b in FX["relation_pairs_distinct"]:
            if a == b:
                self.assertFalse(pair_dup(a % H, b % O)[0], (a, b))
                self.assertTrue(pair_dup(a % H, b % H)[0], (a, b))
            else:
                self.assertFalse(pair_dup(a % H, b % H)[0], (a, b))

    def test_decorated_sha_is_still_the_sha(self):
        for c in fill(FX["decorated_same"]):
            self.assertEqual(ir_norm.commit_id(c), H, c)
            self.assertTrue(pair_dup(H, c)[0], c)

    def test_a_relation_word_in_a_url_path_is_not_a_relation(self):
        for c in ("https://example.org/fix/r/commit/%s", "https://example.org/parent/r/commit/%s"):
            self.assertEqual(ir_norm.commit_id(c % H), H, c)


class TestReviewer12ReproducersKeptAsRegressionTests(unittest.TestCase):
    """The spellings of re-review 12's probes (float12, glue12, fus12, num12), pinned as data with their dispositions."""
    H12 = "b7e1c9a" + "2" * 33

    def test_float12_forms_are_all_unstated(self):
        for c in FX["reviewer_float12"]:
            self.assertIsNone(ir_norm.commit_id(c), c)
            self.assertTrue(pair_dup(self.H12, c)[0], c)

    def test_glue12_spellings_of_one_commit_fuse_and_names_stay_names(self):
        for t in FX["reviewer_glue12_fused"]:
            self.assertEqual(ir_norm.commit_id(t % self.H12 if "%s" in t else t), self.H12 if "%s" in t else ir_norm.commit_id(t), t)
        for t in FX["reviewer_glue12_names"]:
            self.assertNotEqual(ir_norm.commit_id(t % self.H12), self.H12, t)
            self.assertFalse(pair_dup(self.H12, t % self.H12)[0], t)

    def test_fus12_relations_are_distinct_and_glued_labels_fuse(self):
        for t in FX["reviewer_fus12_distinct"]:
            self.assertFalse(pair_dup(self.H12, t % self.H12[:7])[0], t)
        for t in FX["reviewer_fus12_same"]:
            self.assertTrue(pair_dup(self.H12, t % self.H12[:7])[0], t)

    def test_num12_dates_and_counts_are_non_evidence_and_locations_stay_evidence(self):
        for r in FX["reviewer_num12_non_evidence"]:
            self.assertTrue(ir_norm.non_evidence(r), r)
        for r in FX["reviewer_num12_located_tolerated"]:
            self.assertFalse(ir_norm.non_evidence(r), r)


class TestSkillStatesTheRules(unittest.TestCase):
    def test_skill_names_the_rule_words(self):
        text = (SK / "SKILL.md").read_text()
        for w in ("relation", "location noun", "commit_", "reflog"):
            self.assertIn(w, text, w)


if __name__ == "__main__":
    unittest.main()
