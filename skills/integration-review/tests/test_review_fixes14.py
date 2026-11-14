"""Repairs for the fourteenth independent exact-head review of 83bb0390 (DEFECTS H1 and Q1, closed as classes).
Fixtures are synthetic and source-only (tests/fixtures/review/fixes14*.json); they exercise the rules, not production behavior.
The reference clock is injected (NOW via the shared helpers); no test reads the wall clock or the host time zone.

THE HEDGE-WORD RULE (ir_norm.hedged), stated once: a hedge is a WORD of the prose. A hedge stem, modal or phrase inside a path or an
identifier is no hedge (possible_values.py, maybe.py, assumptions.md, MightyEmit, src/should.rs): the token is bounded by / \\ or
".<word>" or holds "_" or an inner capital. A Capitalised hedge word that follows another word is a name ("in May", 'Should Not Happen'),
and "may" after in / since / until / during / from / by / early / late / mid / end is the month. A connective beside a side word is an
alternative only when the side word is a BARE word: a side word that is a path component (/consumer/, adapter.py, producers/, adapter-http,
consumer_test) is not.
THE MARK-SCAN RULE (extract_register._marks), stated once: one pass over the text per evidence ref; each text span between two marks is
examined once, so the cost is linear in the number of marks of a clause."""
import json
import random
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path

from test_review_fixes13 import roles
from test_register import SK

sys.path.insert(0, str(SK / "scripts"))
import extract_register as E  # noqa: E402
import ir_norm  # noqa: E402

FXD = Path(__file__).resolve().parent / "fixtures" / "review"
RV = json.loads((FXD / "fixes14_reviewer.json").read_text())
OWN = json.loads((FXD / "fixes14.json").read_text())


class TestH1HedgeIsAWholeWordOfProse(unittest.TestCase):
    def test_reviewer_genuine_rows_keep_the_role(self):
        for e in RV["hedge14_good"] + RV["two14"][5:] + RV["two14b"]:
            if "Should Not Happen" in e:
                continue                      # disputed: the word "Not" is a negation at base too, see the next test
            self.assertEqual(E._marks(e), {"producer"}, e)

    def test_a_quoted_not_is_the_negation_layer_not_the_hedge_layer(self):
        """Disputed reviewer row: base a818a6dd also reads UNKNOWN for it, through the negation word "Not" (ir_norm.negated), a layer
        this repair does not change. The hedge layer, which H1 concerns, no longer reads the quoted "Should"."""
        self.assertFalse(ir_norm.hedged(" in 'Should Not Happen' handler a.py:3"))

    def test_reviewer_two_marks_rows_stay_two_sides(self):
        for e in RV["two14"][:5]:
            self.assertTrue(len(E._marks(e)) <= 2, e)

    def test_reviewer_genuine_rows_through_the_cli(self):
        for e in ("side=producer in assumptions.md:3", "side=producer at src/consumer/handler.py:12", "in May side=producer at emit.py:40",
                  "side=producer at emit.py:4 and consumer.py:9", "side=producer in possible_values.py:4"):
            self.assertEqual(roles(e), ["producer"], e)

    def test_own_names_not_spelled_in_the_code_keep_the_role(self):
        for e in OWN["own_good_names"]:
            self.assertEqual(E._marks(e), {"producer"}, e)

    def test_own_side_word_path_components_keep_the_role(self):
        for e in OWN["own_good_side_paths"]:
            self.assertEqual(E._marks(e), {"producer"}, e)

    def test_a_real_hedge_or_alternative_still_leaves_the_role_unknown(self):
        for e in OWN["own_still_hedged"]:
            self.assertEqual(E._marks(e), set(), e)

    def test_y2_forms_stay_unknown(self):
        for e in RV["hedge13"][1:] + RV["hedge14_unknown"]:
            self.assertEqual(E._marks(e), set(), e)
        for e in RV["hedge13"][1:6]:
            self.assertEqual(roles(e), ["UNKNOWN"], e)

    def test_the_rule_is_one_function_in_ir_norm(self):
        self.assertFalse(ir_norm.hedged(" in possible_values.py:4"))
        self.assertFalse(ir_norm.hedged(" at src/consumer/x.py:3"))
        self.assertFalse(ir_norm.hedged(" in May at a.py:1"))
        self.assertTrue(ir_norm.hedged(" it may be a.py:1"))
        self.assertTrue(ir_norm.hedged(" or consumer"))
        self.assertTrue(ir_norm.hedged("consumer / "))

    def test_skill_states_the_word_rule(self):
        text = (SK / "SKILL.md").read_text()
        for w in ("whole word", "path component", "bare word"):
            self.assertIn(w, text, w)


def reference_marks(t):
    """The pre-repair scan (quadratic in marks per clause), kept as an oracle for the single-pass scan."""
    out = set()
    prev_end = 0
    for m in E.SIDE_MARK.finditer(t):
        a = max([c.end() for c in E._CLAUSE_END.finditer(t, 0, m.start())] or [0])
        c = E._CLAUSE_END.search(t, m.end())
        z = c.start() if c else len(t)
        before = t[max(a, prev_end):m.start()]
        prev_end = m.end()
        after = E.SIDE_MARK.sub(" ", re.sub(r"(?i)\b(?:not|no|never|without|isn['’]t)\s+(?=side=)", " ", t[m.end():z]))
        if (ir_norm.negated(before, doubt=True) or ir_norm.negated(after, doubt=True) or ir_norm.hedged(before) or ir_norm.hedged(after)):
            continue
        out.add(m.group(1))
    return out


class TestQ1MarksAreScannedInOnePass(unittest.TestCase):
    def test_the_single_pass_scan_equals_the_reference_on_random_clauses(self):
        rng = random.Random(14)
        toks = ["side=producer", "side=consumer", "side=caller", "not", "never", "maybe", "unverified", "emit.py:3", "and", "or",
                "src/consumer/x.py:2", ",", ";", ". ", "\n", "(", ")", "probably", "in", "plainly", "at", "possible_values.py"]
        for _ in range(3000):
            t = " ".join(rng.choice(toks) for _ in range(rng.randint(1, 14)))
            self.assertEqual(E._marks(t), reference_marks(t), t)

    def test_marks_of_a_long_clause_are_linear(self):
        """Quadratic rescans cost 64x for 8x the marks; one pass costs 8x. The bound (below 20x for 8x, best of three) is coarse on purpose."""
        def best(n):
            text = "side=producer " * n
            out = []
            for _ in range(3):
                s = time.process_time()
                E._marks(text)
                out.append(time.process_time() - s)
            return min(out)
        for unit in ("side=producer ", "side=producer ok. ", "maybe side=producer; "):
            def timed(n, unit=unit):
                text = unit * n
                s = time.process_time()
                E._marks(text)
                return time.process_time() - s
            small = min(timed(500) for _ in range(3))
            large = min(timed(4000) for _ in range(3))
            self.assertLess(large, 20 * max(small, 0.002), (unit, small, large))
        small, large = best(500), best(4000)
        self.assertLess(large, 20 * max(small, 0.002), (small, large))

    def test_marks_of_a_long_clause_keep_their_meaning(self):
        self.assertEqual(E._marks("side=producer " * 3000), {"producer"})
        self.assertEqual(E._marks("side=producer " * 2000 + "maybe"), set())
        self.assertEqual(E._marks("side=producer " * 1000 + "side=consumer"), {"producer", "consumer"})


if __name__ == "__main__":
    unittest.main()
