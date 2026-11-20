"""Repair 15 recovery (A1663, same source lineage): the credential-name rule added for re-review 14 DEF-F must not make redact()
cost grow with each repetition of the same word.

Found at 263a1a69 on a loaded host: test_review_fixes4 D1 test_new_patterns_are_linear_on_hostile_input took 14.7 s against its
10 s bound; the 'hooks.slack.com/services/' x 20000 input spends ~11 of ~15 profiled seconds in _noun_by_rule (100000 calls, one per
word occurrence, 420000 _misspelt calls), where bffbfc29 spends ~0.9 s in total. The rule is a pure function of one lower-case word
over frozen module data, so a repeated word is evaluated once. These tests count rule evaluations, never wall-clock time, and check
that the memoised rule answers exactly as the rule does. No value is printed; labels carry an index or a count."""
import random
import string
import unittest
from unittest import mock

import helpers  # noqa: F401  (puts scripts/ on sys.path)
import envelope_validate as ev

# the hostile inputs of test_review_fixes4 D1 that reach the prose credential-name layer with alphabetic words
HOSTILE_UNITS = ("hooks.slack.com/services/", "xoxe.", "http://u:", "https://", "xapp-", "glpat-", "SG.", "eyJ")


def _clear_rule_caches():
    for name, value in vars(ev).items():
        if name.endswith("_CACHE") and isinstance(value, dict):
            value.clear()


def _misspelt_calls(text):
    _clear_rule_caches()
    seen = [0]
    real = ev._misspelt

    def counting(low):
        seen[0] += 1
        return real(low)

    with mock.patch.object(ev, "_misspelt", counting):
        ev.redact(text)
    return seen[0]


def _rule_reference():
    return getattr(ev, "_noun_by_rule_eval", ev._noun_by_rule)


class NameRuleCostDoesNotGrowWithRepetition(unittest.TestCase):
    def test_repeated_hostile_units_evaluate_the_rule_once_per_distinct_word(self):
        for i, unit in enumerate(HOSTILE_UNITS):
            few, many = _misspelt_calls(unit * 200), _misspelt_calls(unit * 2000)
            self.assertEqual(many, few, "unit %d: %d rule evaluations at x200, %d at x2000" % (i, few, many))

    def test_repeated_prose_names_evaluate_the_rule_once_per_distinct_word(self):
        line = "the deploy notes say passwrd is kept and the monkey test ran; "
        self.assertEqual(_misspelt_calls(line * 500), _misspelt_calls(line * 50))


class MemoisedRuleAnswersAsTheRule(unittest.TestCase):
    def corpus(self):
        words = set()
        for name in ("_STRONG_NOUNS", "_WEAK_NOUNS", "_CRED_ABBREV", "_CRED_FOREIGN", "_EDIT_ENGLISH", "_READABLE_GLUED", "_SIGN_ON",
                     "_GLUE_ENGLISH", "_VALUE_TAILS", "_PLURAL_EXCEPT"):
            words |= {w for w in getattr(ev, name, ()) if w.isalpha()}
        rnd = random.Random(1663)
        base = sorted(words)
        for w in base:
            for _ in range(3):  # one random edit of every closed word, then a qualifier or a tail glued on
                i = rnd.randrange(len(w) + 1)
                c = rnd.choice(string.ascii_lowercase)
                words.add(rnd.choice((w[:i] + c + w[i:], w[:i] + w[i + 1:], w[:i] + c + w[i + 1:])))
                words.add(rnd.choice(("my", "api", "db", "x", "user")) + w)
                words.add(w + rnd.choice(("s", "es", "number", "code", "value", "z")))
        for _ in range(3000):
            words.add("".join(rnd.choice(string.ascii_lowercase) for _ in range(rnd.randint(2, 16))))
        return sorted(w for w in words if w and w.isalpha() and w.islower())

    def test_cold_warm_and_reference_answers_are_equal(self):
        ref = _rule_reference()
        words = self.corpus()
        self.assertTrue(len(words) > 4000)
        _clear_rule_caches()
        expected = [ref(w) for w in words]
        _clear_rule_caches()
        cold = [ev._noun_by_rule(w) for w in words]
        warm = [ev._noun_by_rule(w) for w in words]
        for i, w in enumerate(words):
            self.assertEqual(cold[i], expected[i], "cold %d" % i)
            self.assertEqual(warm[i], expected[i], "warm %d" % i)
        self.assertTrue(any(e is not None for e in expected) and any(e is None for e in expected))

    def test_answers_hold_across_a_cache_reset(self):
        ref = _rule_reference()
        words = self.corpus()
        _clear_rule_caches()
        first = [ev._noun_by_rule(w) for w in words]
        rnd = random.Random(15)
        for _ in range(20000):  # more distinct words than any cache bound, so a bounded cache is reset at least once
            ev._noun_by_rule("".join(rnd.choice(string.ascii_lowercase) for _ in range(12)))
        self.assertTrue(len(getattr(ev, "_NOUN_RULE_CACHE", {})) <= 8193, "the rule cache stays bounded")
        again = [ev._noun_by_rule(w) for w in words]
        for i, w in enumerate(words):
            self.assertEqual(again[i], first[i], "after reset %d" % i)
            self.assertEqual(again[i], ref(w), "reference %d" % i)


if __name__ == "__main__":
    unittest.main()
