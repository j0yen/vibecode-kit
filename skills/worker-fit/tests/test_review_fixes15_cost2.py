"""Repair 15 recovery, part 2 (A1663, same source lineage): the end-to-end recommend path must not pay the repair-15 prose layer per
word occurrence either.

Found at 5e1ac354 by interleaved timing on one host (12 rounds, medians): the test_review_fixes7 DefG end-to-end input (a
coverage gap of 'mysql -u r ' x 8000) took base 0.93 s, 263a1a69 3.61 s, 5e1ac354 2.29 s. The profile shows _cred_noun called
32064 times (one per word occurrence, each re-reading _name_parts / _deleet / _noun_of for the same three words) and the DEF-A
format-character view scanning every character of every ASCII view, which can hold no format character (no ASCII character is in
Unicode category Cf). Both are pure: _cred_noun reads one word and a flag over frozen module data; _drop_format leaves ASCII text
as it is. These tests count evaluations, never wall-clock time, and check equal answers. No value is printed."""
import random
import string
import unicodedata
import unittest
from unittest import mock

import helpers  # noqa: F401  (puts scripts/ on sys.path)
import envelope_validate as ev
import test_review_fixes3 as t3

from test_review_fixes15_cost import _clear_rule_caches


def _name_parts_calls(fn):
    _clear_rule_caches()
    seen = [0]
    real = ev._name_parts

    def counting(word):
        seen[0] += 1
        return real(word)

    with mock.patch.object(ev, "_name_parts", counting):
        fn()
    return seen[0]


class ProseNameLayerCostDoesNotGrowWithRepetition(unittest.TestCase):
    def test_repeated_command_words_read_each_name_once(self):
        few = _name_parts_calls(lambda: ev.redact("mysql -u r " * 300))
        many = _name_parts_calls(lambda: ev.redact("mysql -u r " * 3000))
        self.assertEqual(many, few, "%d name readings at x300, %d at x3000" % (few, many))

    def test_end_to_end_recommend_reads_each_name_once(self):
        def run(n):
            return lambda: t3.one(dict(t3.running(), coverage_gaps=["mysql -u r " * n]))
        self.assertEqual(_name_parts_calls(run(4000)), _name_parts_calls(run(400)))

    def test_format_view_does_not_scan_ascii_text(self):
        seen = [0]
        real = unicodedata.category

        def counting(c):
            seen[0] += 1
            return real(c)

        text = "mysql -u r " * 1000
        with mock.patch.object(ev.unicodedata, "category", counting):
            out = ev._drop_format(text)
        self.assertTrue(out is text or out == text)
        self.assertEqual(seen[0], 0, "%d category reads for ASCII text" % seen[0])


class MemoisedNameLayerAnswersAsBefore(unittest.TestCase):
    def words(self):
        rnd = random.Random(16632)
        stems = sorted(w for w in (ev._STRONG_NOUNS | ev._WEAK_NOUNS | ev._CRED_ABBREV | ev._CRED_FOREIGN | ev._EDIT_ENGLISH)
                       if w.isalpha())
        out = set()
        for w in stems:
            out.update((w, w.upper(), w.capitalize(), "my" + w, "api_" + w, "X-" + w.capitalize(), w + "Code", w + "_value",
                        w.replace("a", "@").replace("s", "$").replace("o", "0"), w + "123", "the" + w))
        for _ in range(3000):
            out.add("".join(rnd.choice(string.ascii_letters + "_-.@$0123456789") for _ in range(rnd.randint(1, 18))))
        return sorted(out)

    def test_cred_noun_cold_warm_and_reference_are_equal(self):
        ref = getattr(ev, "_cred_noun_eval", ev._cred_noun)
        words = self.words()
        self.assertTrue(len(words) > 3000)
        for glued in (True, False):
            _clear_rule_caches()
            expected = [ref(w, glued) for w in words]
            _clear_rule_caches()
            cold = [ev._cred_noun(w, glued) for w in words]
            warm = [ev._cred_noun(w, glued) for w in words]
            for i in range(len(words)):
                self.assertEqual(cold[i], expected[i], "cold %d glued=%s" % (i, glued))
                self.assertEqual(warm[i], expected[i], "warm %d glued=%s" % (i, glued))
            self.assertTrue(any(expected) and not all(expected))
        # the flag is part of the answer: some word reads as a name glued but not bare
        _clear_rule_caches()
        self.assertTrue(any(ev._cred_noun(w, True) != ev._cred_noun(w, False) for w in words))

    def test_cred_noun_cache_stays_bounded_and_correct_after_a_reset(self):
        ref = getattr(ev, "_cred_noun_eval", ev._cred_noun)
        words = self.words()
        _clear_rule_caches()
        rnd = random.Random(1515)
        for _ in range(20000):
            ev._cred_noun("".join(rnd.choice(string.ascii_lowercase) for _ in range(10)), rnd.random() < 0.5)
        self.assertTrue(len(getattr(ev, "_CRED_NOUN_CACHE", {})) <= 8193)
        for i, w in enumerate(words):
            self.assertEqual(ev._cred_noun(w), ref(w, True), "after reset %d" % i)

    def test_format_view_answers_as_before(self):
        zw = "​"
        samples = ["", "plain ascii", "pass" + zw + "word: x", "café", "a­b", "﻿bom", "x⁠y‍z", "é" * 50]
        for i, s in enumerate(samples):
            expected = "".join(c for c in s if unicodedata.category(c) != "Cf")
            self.assertEqual(ev._drop_format(s), expected, "sample %d" % i)


if __name__ == "__main__":
    unittest.main()
