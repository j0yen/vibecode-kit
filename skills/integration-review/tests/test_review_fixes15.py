"""Repairs for the fifteenth independent exact-head review of 5de4632b (D1-D5), closed by ONE name-vs-hedge rule.
Fixtures are synthetic and source-only (tests/fixtures/review/fixes15*.json); they exercise the rules, not production behavior.
The reference clock is injected (NOW via the shared helpers); no test reads the wall clock or the host time zone.

THE NAME-VS-HEDGE RULE (ir_norm._is_name, ir_norm._is_hedge_word), stated once: a hedge word or a side word of an evidence span is
part of a NAME only on evidence that it is not prose: (1) its blank-delimited token is code by the shared code-token rule (call, ::,
URL, name@version, file, path, module or dotted name); (2) its word run is an identifier (an underscore or an inner capital, not all
capitals), a key ("maybe=1") or a handle ("@maybe"); (3) it is a QUOTED NAME: an opening quote glued to it, every word Capitalised, the
quote after a word of the same span ("in 'Might' handler"); (4) for "may" only, the MONTH: a number after it, or a time word just before
it and no verb-able word after it. Anything else is prose: a capital alone (D1), a preposition alone (D2), a compound with no code
mark are not evidence. An alternative connective (or nor either vs versus / |) beside any token holding a side word is an alternative; a
conjunction (and plus & +) adds a second side only beside a side word that is prose (D3). Ambiguous forms resolve to UNKNOWN.
THE SCAN (extract_register._marks, ir_norm.doubted_suffixes): the after-text of a side mark is the rest of its clause with the other
marks blanked, judged as ONE text, as the pre-repair scan did (D5); the single pass is linear in the clause."""
import json
import random
import sys
import time
import unittest
from pathlib import Path

from test_register import SK
from test_review_fixes13 import roles
from test_review_fixes14 import reference_marks

sys.path.insert(0, str(SK / "scripts"))
import extract_register as E  # noqa: E402
import ir_norm  # noqa: E402

FXD = Path(__file__).resolve().parent / "fixtures" / "review"
RV = json.loads((FXD / "fixes15_reviewer.json").read_text(encoding="utf-8"))
OWN = json.loads((FXD / "fixes15.json").read_text(encoding="utf-8"))
P, U = "producer", "UNKNOWN"


def role(evidence):
    """The extractor's role for one row claiming producer whose evidence is `evidence` (norm_role, the CLI's own decision)."""
    return E.norm_role({"role": "producer"}, [evidence])[0]


def mismatches(cases, got):
    return [(c, want, got(c)) for c, want in cases if got(c) != want]


class TestCls15ShapesAndProse(unittest.TestCase):
    def test_840_path_and_identifier_shapes(self):
        refused = OWN["cls15_refused_shapes"]
        cases = []
        for w in RV["cls15_words"]:
            for s in RV["cls15_shapes"]:
                cases.append(("side=producer at " + s.format(w=w, W=w.capitalize()), s in refused))
        self.assertEqual(len(cases), 840)
        bad = mismatches(cases, ir_norm.hedged)
        self.assertEqual(bad, [], "%d of 840: %r" % (len(bad), bad[:12]))

    def test_368_prose_hedges_stay_hedged(self):
        cases = [(t.format(w=w, W=w.capitalize()), True) for w in RV["cls15_prose_words"] for t in RV["cls15_prose_templates"]]
        self.assertEqual(len(cases), 368)
        bad = mismatches(cases, ir_norm.hedged)
        self.assertEqual(bad, [], "%d of 368: %r" % (len(bad), bad[:12]))


class TestFin15AndSem15(unittest.TestCase):
    def test_fin15_28_hedged_forms_are_unknown(self):
        bad = mismatches([(e, U) for e in RV["fin15_hedged"]], role)
        self.assertEqual(bad, [], "under-refusal %d/28: %r" % (len(bad), bad))

    def test_fin15_genuine_forms_keep_the_role(self):
        neg = OWN["fin15_good_negation_layer"]
        bad = mismatches([(e, U if e in neg else P) for e in RV["fin15_good"]], role)
        self.assertEqual(bad, [], "over-refusal: %r" % bad)
        for e in neg:
            self.assertFalse(ir_norm.hedged(e.split("side=producer", 1)[1]), e)   # refused by the negation layer only
            self.assertTrue(ir_norm.negated(e, doubt=True), e)

    def test_sem15_rows(self):
        disputed, info = OWN["sem15_disputed"], OWN["sem15_info_expected"]
        cases = []
        for _cls, e, want in RV["sem15"]:
            if e in disputed:
                want = disputed[e][0]
            elif e in info:
                want = info[e]
            cases.append((e, want))
        bad = mismatches(cases, role)
        self.assertEqual(bad, [], bad)


class TestD1ACapitalIsNoName(unittest.TestCase):
    def test_reviewer_i_think_and_title_case_rows_are_unknown(self):
        rows = RV["hole15b"] + RV["hole15c"][1:] + RV["hole15_hedged"]
        kept = OWN["hole15b_kept"]
        bad = mismatches([(e, P if e in kept else U) for e in rows], role)
        self.assertEqual(bad, [], bad)

    def test_hole15_genuine_rows_keep_the_role(self):
        neg = OWN["hole15_good_negation_layer"]
        bad = mismatches([(e, U if e in neg else P) for e in RV["hole15_good"]], role)
        self.assertEqual(bad, [], bad)

    def test_own_capitalised_prose_is_a_hedge(self):
        for e in OWN["own_capital_prose"]:
            self.assertEqual(role(e), U, e)

    def test_own_quoted_names_keep_the_role(self):
        for e in OWN["own_quoted_name"]:
            self.assertEqual(role(e), P, e)

    def test_own_quoted_forms_without_name_evidence_are_hedges(self):
        for e in OWN["own_quoted_prose"]:
            self.assertEqual(role(e), U, e)

    def test_through_the_cli(self):
        self.assertEqual(roles("side=producer, which I think is right"), [U])
        self.assertEqual(roles("side=producer in 'Might' handler a.py:3"), [P])


class TestD2TheMonthNeedsDateEvidence(unittest.TestCase):
    def test_own_month_forms_keep_the_role(self):
        for e in OWN["own_month"]:
            self.assertEqual(role(e), P, e)

    def test_own_modal_forms_are_hedges(self):
        for e in OWN["own_modal"]:
            self.assertEqual(role(e), U, e)

    def test_reviewer_modal_rows(self):
        for e in ("the end may change side=producer", "side=producer from may differ", "side=producer by may be consumer",
                  "side=producer mid may change", "side=producer by may be"):
            self.assertEqual(role(e), U, e)
        self.assertEqual(roles("the end may change side=producer"), [U])


class TestD3AlternativeAndSecondSide(unittest.TestCase):
    def test_conn15_alternatives_leave_no_mark(self):
        kept = OWN["conn15_kept"]
        bad = [(a, E._marks(a)) for a in RV["conn15"] if (E._marks(a) == {"producer"}) != (a in kept)]
        self.assertEqual(bad, [], bad)

    def test_own_alternatives_are_unknown(self):
        for e in OWN["own_alternative"]:
            self.assertEqual(role(e), U, e)

    def test_own_conjunction_with_a_prose_side_word_is_a_second_side(self):
        for e in OWN["own_conjunction_second_side"]:
            self.assertEqual(role(e), U, e)

    def test_own_conjunction_with_a_named_location_keeps_the_role(self):
        for e in OWN["own_conjunction_location"]:
            self.assertEqual(role(e), P, e)

    def test_a_name_that_holds_a_slash_or_a_connective_word_is_no_connective(self):
        """Regression guards for this repair (they pass on 5de4632b too): an absolute path's leading "/" and a connective word inside a
        path are part of a name, not a connective."""
        for e in OWN["own_name_beside_connective"]:
            self.assertEqual(role(e), P, e)

    def test_through_the_cli(self):
        self.assertEqual(roles("side=producer or consumer.py"), [U])
        self.assertEqual(roles("side=producer at emit.py:4 and consumer.py:9"), [P])


class TestD4CodeTokensAreNames(unittest.TestCase):
    def test_reviewer_rows(self):
        for e in ("side=producer in possible-values.md:3", "side=producer calls maybe() at a.py:3",
                  "side=producer via should() helper a.py:3", "side=producer in assumed-roles.yaml:1"):
            self.assertEqual(role(e), P, e)
        # disputed: the hedge layer reads a name, the negation layer reads "fail" inside it (OWN fin15_good_negation_layer)
        self.assertFalse(ir_norm.hedged(" in should-fail-cases.md:3"))
        self.assertTrue(ir_norm.negated(" in should-fail-cases.md:3", doubt=True))

    def test_own_code_names_keep_the_role(self):
        for e in OWN["own_name_code"]:
            self.assertEqual(role(e), P, e)

    def test_own_prose_shapes_are_hedges(self):
        for e in OWN["own_prose_shape"]:
            self.assertEqual(role(e), U, e)

    def test_through_the_cli(self):
        self.assertEqual(roles("side=producer calls maybe() at a.py:3"), [P])


class TestD5TheAfterTextIsOneText(unittest.TestCase):
    def test_reviewer_example(self):
        self.assertEqual(E._marks(RV["d5_example"]), {"consumer"})

    def test_own_scan_rows(self):
        for t, want in OWN["own_scan"]:
            self.assertEqual(E._marks(t), set(want), t)
            self.assertEqual(E._marks(t), reference_marks(t), t)

    def _equal_on(self, vocab, seeds, n):
        bad = []
        for seed in seeds:
            rng = random.Random(seed)
            for _ in range(n):
                t = " ".join(rng.choice(vocab) for _ in range(rng.randint(1, 14)))
                if E._marks(t) != reference_marks(t):
                    bad.append(t)
        return bad

    def test_equal_to_the_joined_reference_on_the_reviewer_vocabularies(self):
        v = RV["eq15_vocab"]
        v2 = [x for x in v if x not in RV["eq15b_dropped"]] + RV["eq15b_extra"]
        bad = self._equal_on(v, (15, 16), 1500) + self._equal_on(v2, (17, 18), 1500)
        self.assertEqual(bad, [], "%d mismatches: %r" % (len(bad), bad[:5]))

    def test_equal_to_the_joined_reference_on_own_vocabulary(self):
        bad = self._equal_on(OWN["own_scan_vocab"], (19, 20, 21), 1500)
        self.assertEqual(bad, [], "%d mismatches: %r" % (len(bad), bad[:5]))

    def test_doubted_suffixes_is_each_suffix_judged_whole(self):
        f = getattr(ir_norm, "doubted_suffixes", None)
        self.assertIsNotNone(f, "ir_norm.doubted_suffixes is the one suffix rule")
        rng = random.Random(22)
        vocab = OWN["own_scan_vocab"] + RV["eq15_vocab"]
        for _ in range(1500):
            pieces = [" ".join(rng.choice(vocab) for _ in range(rng.randint(0, 5))) for _ in range(rng.randint(1, 5))]
            want = [ir_norm.negated(" ".join(pieces[i:]), doubt=True) or ir_norm.hedged(" ".join(pieces[i:])) for i in range(len(pieces))]
            self.assertEqual(f(pieces), want, pieces)

    def test_marks_of_a_long_clause_stay_linear_on_adversarial_shapes(self):
        """Quadratic re-judging costs 64x for 8x the marks; one pass costs 8x. The bound (below 20x for 8x, best of three) is coarse."""
        for unit in ("side=producer or producer ", "side=producer Maybe ", "side=producer may ", "side=producer 'Might' ",
                     "side=producer maybe.", "side=producer a/maybe ", "side=producer zero ", "side=producer kind "):
            def timed(n, unit=unit):
                text = unit * n + " fails"
                s = time.process_time()
                E._marks(text)
                return time.process_time() - s
            small = min(timed(250) for _ in range(3))
            large = min(timed(2000) for _ in range(3))
            self.assertLess(large, 20 * max(small, 0.002), (unit, small, large))


class TestOneRule(unittest.TestCase):
    def test_both_consumers_route_through_is_name(self):
        self.assertTrue(hasattr(ir_norm, "_is_name"), "ir_norm._is_name is the one name-vs-prose rule")
        saved = ir_norm._is_name
        try:
            ir_norm._is_name = lambda *a, **k: False
            self.assertTrue(ir_norm.hedged(" in possible-values.md:3"))
            self.assertTrue(ir_norm.hedged(" at emit.py:4 and consumer.py:9"))
        finally:
            ir_norm._is_name = saved
        self.assertFalse(ir_norm.hedged(" in possible-values.md:3"))
        self.assertFalse(ir_norm.hedged(" at emit.py:4 and consumer.py:9"))

    def test_skill_states_the_rule(self):
        text = (SK / "SKILL.md").read_text()
        for w in ("not prose", "capital alone", "quoted name", "time word", "alternative connective", "conjunction", "judged as one text"):
            self.assertIn(w, text, w)


if __name__ == "__main__":
    unittest.main()
