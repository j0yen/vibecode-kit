"""Repairs for the sixteenth independent exact-head review of 22176759 (N1-N5), each pinned test-first.
Fixtures are synthetic and source-only (tests/fixtures/review/fixes16*.json); they exercise the rules, not production behavior.
The reference clock is injected (NOW via the shared helpers); no test reads the wall clock or the host time zone.

THE NAME-VS-HEDGE RULE, amended (ir_norm._is_name, ir_norm._is_hedge_word; still one rule per concept):
  N2 code evidence belongs to the SEGMENT of a token that holds the word, not to the whole token: a hedge glued by "=", "(", ")", ",",
     "?" or a lone ":" to a path, file or call ("src/emit.py:3(probably)", "emit.py(probably)", "src/emit.py,maybe", "emit(),maybe")
     is judged on its own segment ("probably"), which is prose. A call name ("maybe()") and a key ("maybe=1") keep their evidence; a key
     whose value is only a yes/no answer ("likely=yes", "maybe=true") is a key only when a location follows it ("assumed=true in
     cfg.toml:2"); otherwise it reads as the hedge with its answer.
  N1 a quoted Capitalised word is a name only when the quote closes and an artifact noun follows it ("in 'Might' handler", "'Probably
     Fine' alert"); a quoted label at the end of a clause or before any other word ("status 'Needs Verification'", "'Might' be right")
     is prose.
  N3 the month needs date evidence: a date-shaped number after "may" ("May 12", "may 2026", "May 3rd"; not "may 2x"), or a time word
     before it, where "early late mid end" count only after a preposition ("by end may", "in early may"; not "the front end may").
  N4 a dot after an abbreviation ("vs.", "e.g.", "i.e.", "etc." ...; ir_norm.ABBREVIATIONS, one list) ends no clause.
  N5 an alternative connective reaches a side word across up to three plain words (a determiner, possessive or adjective: "or the
     legacy consumer", "or rather consumer"); a conjunction still needs the side word beside it."""
import json
import random
import re
import sys
import tempfile
import unittest
from pathlib import Path

from test_register import SK
from test_review_fixes2 import NOW, check, run   # noqa: F401  (NOW: injected clock)
from test_review_fixes11 import erow

sys.path.insert(0, str(SK / "scripts"))
import extract_register as E  # noqa: E402
import ir_norm  # noqa: E402

FXD = Path(__file__).resolve().parent / "fixtures" / "review"
RV = json.loads((FXD / "fixes16_reviewer.json").read_text(encoding="utf-8"))
OWN = json.loads((FXD / "fixes16.json").read_text(encoding="utf-8"))
P, U = "producer", "UNKNOWN"


def role(evidence):
    """The extractor's role for one row claiming producer whose evidence is `evidence` (norm_role, the CLI's own decision)."""
    return E.norm_role({"role": "producer"}, [evidence])[0]


def cli_roles(evidences):
    """One extractor CLI run over many rows (distinct components, so nothing fuses); the partial register is then validated with the
    injected clock. Returns the role of each row, in order."""
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "in.jsonl"
        rows = [erow("1" * 40, evidence=e, component="c%04d" % i, path_or_command="svc/c%04d.py" % i) for i, e in enumerate(evidences)]
        src.write_text("".join(json.dumps(r) + "\n" for r in rows))
        out = Path(d) / "out"
        rc, text = run("extract_register.py", str(src), str(out))
        assert rc == 0, text
        reg = json.loads((out / "register-partial.json").read_text())
        assert "findings" in check(reg, now=NOW)
        by = {r["component"]: r["role"] for r in reg["records"]}
        return [by["c%04d" % i] for i in range(len(evidences))]


def title(w):
    return " ".join(x[0].upper() + x[1:] for x in w.split())


def wrong(cases):
    return [(e, want, role(e)) for e, want in cases if role(e) != want]


def n2_grid():
    return [(k, w, t.format(w=w)) for k, t in RV["n2_shapes"].items() for w in RV["n2_stems"]]


def n2_controls():
    return [(k, w, t.format(w=w)) for k, t in RV["n2_spaced_controls"].items() for w in RV["n2_stems"]]


class TestN2GluedHedgeIsNoName(unittest.TestCase):
    """N2 (regression of 22176759 against 5de4632b): a hedge glued to a path, file, call or key is still a hedge."""

    def test_108_glued_forms_are_unknown(self):
        grid = n2_grid()
        self.assertEqual(len(grid), 108)
        bad = [(k, e, role(e)) for k, _w, e in grid if role(e) != U]
        self.assertEqual(bad, [], "asserted %d/108: %r" % (len(bad), bad[:12]))

    def test_36_spaced_controls_stay_unknown(self):
        ctl = n2_controls()
        self.assertEqual(len(ctl), 36)
        bad = [(k, e, role(e)) for k, _w, e in ctl if role(e) != U]
        self.assertEqual(bad, [], "asserted %d/36: %r" % (len(bad), bad[:12]))

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in RV["n2_rows"]]), [])

    def test_own_glued_hedges_are_unknown(self):
        self.assertGreaterEqual(len(OWN["n2_own_hedges"]), 3)
        self.assertEqual(wrong([(e, U) for e in OWN["n2_own_hedges"]]), [])

    def test_own_code_names_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in OWN["n2_own_names"]]), [])

    def test_the_segment_carries_the_evidence(self):
        for tail in (" maybe()", " x.maybe()", " maybe=1", " src/maybe.rs:3", " possible-values.md:3", " Presumably::emit",
                     " tests/test_maybe.py::t", " https://h.io/maybe/p?q=1", " C:\\x\\maybe.py"):
            self.assertFalse(ir_norm.hedged(tail), tail)
        for tail in (" src/emit.py:3(maybe)", " emit.py(maybe)", " src/emit.py,maybe", " emit(),maybe", " likely=yes", " maybe=true",
                     " a.py:3,possibly", " https://ci.example/run/12?maybe", " e.g.maybe"):
            self.assertTrue(ir_norm.hedged(tail), tail)

    def test_other_glue_shapes(self):
        """url?w and dotted.w (glue16): a URL query key and a word glued to an abbreviation are prose too (5de4632b refused both
        url forms; both trees asserted dotted.w)."""
        rows = [t.format(w=w) for t in RV["n2_other_glue"].values() for w in RV["n2_stems"]]
        self.assertEqual(wrong([(e, U) for e in rows]), [])

    def test_through_the_cli(self):
        grid = [e for _k, _w, e in n2_grid()] + [e for _k, _w, e in n2_controls()]
        got = cli_roles(grid)
        self.assertEqual([e for e, g in zip(grid, got) if g != U], [])


class TestN1QuotedLabelIsNoName(unittest.TestCase):
    """N1: a quoted Capitalised hedge after a word is a name only when an artifact noun follows the closed quote."""

    def test_100_quoted_and_25_backtick_review_forms_are_unknown(self):
        rows = [t.format(T=title(w)) for t in RV["n1_quoted_shapes"].values() for w in RV["grid_stems"]]
        self.assertEqual(len(rows), 100)
        bad = wrong([(e, U) for e in rows])
        self.assertEqual(bad, [], "asserted %d/100: %r" % (len(bad), bad[:12]))
        rows = [t.format(T=title(w)) for t in RV["n1_backtick_shapes"].values() for w in RV["grid_stems"]]
        self.assertEqual(len(rows), 25)
        bad = wrong([(e, U) for e in rows])
        self.assertEqual(bad, [], "asserted %d/25: %r" % (len(bad), bad[:12]))

    def test_guard_shapes_stay_unknown(self):
        rows = [t.format(T=title(w), w=w) for t in RV["n1_guard_shapes"].values() for w in RV["grid_stems"]]
        self.assertEqual(wrong([(e, U) for e in rows]), [])

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in RV["n1_rows"]]), [])

    def test_generated_quoted_labels_are_unknown(self):
        rows = [c.format(q=q.format(T=title(w))) for c in OWN["n1_contexts"] for q in OWN["n1_quotes"] for w in RV["grid_stems"]]
        self.assertEqual(len(rows), 625)
        bad = wrong([(e, U) for e in rows])
        self.assertEqual(bad, [], "asserted %d/625: %r" % (len(bad), bad[:12]))

    def test_generated_quoted_names_keep_the_role(self):
        stems = [w for w in RV["grid_stems"] if w != "not sure"]          # "Not" is read by the negation layer
        rows = [c.format(q=q.format(T=title(w))) for c in OWN["n1_name_contexts"] for q in OWN["n1_quotes"] for w in stems]
        bad = wrong([(e, P) for e in rows])
        self.assertEqual(bad, [], "refused %d/%d: %r" % (len(bad), len(rows), bad[:12]))

    def test_own_rows(self):
        self.assertGreaterEqual(len(OWN["n1_own_hedges"]), 3)
        self.assertEqual(wrong([(e, U) for e in OWN["n1_own_hedges"]] + [(e, P) for e in OWN["n1_own_names"]]), [])


class TestN3ModalMayIsNoMonth(unittest.TestCase):
    """N3: "may" is the month only on date evidence; a modal followed by an adverbial, a comma or a number hedges."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in RV["n3_rows"]]), [])

    def test_generated_modal_forms_are_unknown(self):
        rows = [p + " " + s if not s.startswith(",") else p + s for p in OWN["n3_prefixes"] for s in OWN["n3_suffixes"]]
        self.assertEqual(len(rows), 55)
        bad = wrong([(e, U) for e in rows])
        self.assertEqual(bad, [], "asserted %d/55: %r" % (len(bad), bad[:12]))

    def test_own_rows(self):
        self.assertGreaterEqual(len(OWN["n3_own_hedges"]), 3)
        self.assertEqual(wrong([(e, U) for e in OWN["n3_own_hedges"]] + [(e, P) for e in OWN["n3_own_months"]]), [])

    def test_through_the_cli(self):
        rows = RV["n3_rows"][:6] + OWN["n3_own_months"]
        self.assertEqual(cli_roles(rows), [U] * 6 + [P] * len(OWN["n3_own_months"]))


class TestN4AbbreviationDotEndsNoClause(unittest.TestCase):
    """N4: a dot after an abbreviation does not end the clause, so an alternative or a hedge after it still counts."""

    def abbreviations(self):
        self.assertTrue(hasattr(ir_norm, "ABBREVIATIONS"), "ir_norm.ABBREVIATIONS is the one abbreviation list")
        return sorted(a + "." for a in ir_norm.ABBREVIATIONS) + ["e.g.", "i.e."]

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in RV["n4_rows"]]), [])

    def test_every_abbreviation_with_an_alternative_and_a_hedge(self):
        rows = [t.format(a=a) for a in self.abbreviations() for t in OWN["n4_templates"]]
        self.assertGreaterEqual(len(rows), 40)
        bad = wrong([(e, U) for e in rows])
        self.assertEqual(bad, [], "asserted %d/%d: %r" % (len(bad), len(rows), bad[:12]))

    def test_own_rows(self):
        self.assertGreaterEqual(len(OWN["n4_own_hedges"]), 3)
        self.assertEqual(wrong([(e, U) for e in OWN["n4_own_hedges"]]), [])

    def test_a_real_sentence_end_still_ends_the_clause(self):
        self.assertEqual(wrong([(e, P) for e in OWN["n4_own_sentence_ends"]]), [])

    def test_through_the_cli(self):
        self.assertEqual(cli_roles(RV["n4_rows"] + OWN["n4_own_sentence_ends"][:1]), [U, U, U, P])


class TestN5AlternativeAcrossModifiers(unittest.TestCase):
    """N5: an alternative connective reaches a side word across a determiner, possessive or adjective."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in RV["n5_rows"]]), [])

    def test_generated_alternatives_are_unknown(self):
        rows = ["side=producer %s %s %s" % (c, f, s) for c in OWN["n5_connectives"] for f in OWN["n5_fillers"] for s in OWN["n5_sides"]]
        self.assertEqual(len(rows), 90)
        bad = wrong([(e, U) for e in rows])
        self.assertEqual(bad, [], "asserted %d/90: %r" % (len(bad), bad[:12]))

    def test_own_rows(self):
        self.assertGreaterEqual(len(OWN["n5_own_hedges"]), 3)
        self.assertEqual(wrong([(e, U) for e in OWN["n5_own_hedges"]] + [(e, P) for e in OWN["n5_own_kept"]]), [])

    def test_through_the_cli(self):
        self.assertEqual(cli_roles(RV["n5_rows"] + OWN["n5_own_kept"][:1]), [U] * len(RV["n5_rows"]) + [P])


def reference_marks(t):
    """test_review_fixes14.reference_marks (the pre-repair quadratic scan) with the clause ends now in force (E._clause_ends: an
    abbreviation's dot ends no clause, N4); kept as the oracle for the single-pass scan."""
    out = set()
    prev_end = 0
    ends = E._clause_ends(t)
    for m in E.SIDE_MARK.finditer(t):
        a = max([b for _, b in ends if b <= m.start()] or [0])
        z = min([c for c, _ in ends if c >= m.end()] or [len(t)])
        before = t[max(a, prev_end):m.start()]
        prev_end = m.end()
        after = E.SIDE_MARK.sub(" ", re.sub(r"(?i)\b(?:not|no|never|without|isn['’]t)\s+(?=side=)", " ", t[m.end():z]))
        if (ir_norm.negated(before, doubt=True) or ir_norm.negated(after, doubt=True) or ir_norm.hedged(before) or ir_norm.hedged(after)):
            continue
        out.add(m.group(1))
    return out


class TestOnePassStaysExact(unittest.TestCase):
    """The amended rule reads at most two tokens left of a word (N3) and only rightward for the reach (N5) and the artifact noun (N1),
    so the one-pass after-text scan still equals each suffix judged whole."""

    def test_doubted_suffixes_equals_each_suffix_judged_whole(self):
        rng = random.Random(16)
        vocab = OWN["eq16_vocab"]
        for _ in range(3000):
            pieces = [" ".join(rng.choice(vocab) for _ in range(rng.randint(0, 6))) for _ in range(rng.randint(1, 5))]
            want = [ir_norm.negated(" ".join(pieces[i:]), doubt=True) or ir_norm.hedged(" ".join(pieces[i:])) for i in range(len(pieces))]
            self.assertEqual(ir_norm.doubted_suffixes(pieces), want, pieces)

    def test_marks_equal_the_joined_reference(self):
        rng = random.Random(1616)
        vocab = OWN["eq16_vocab"] + ["side=producer", "side=consumer", "side=caller", ";", ".", ","]
        for _ in range(3000):
            t = " ".join(rng.choice(vocab) for _ in range(rng.randint(1, 14)))
            self.assertEqual(E._marks(t), reference_marks(t), t)


class TestPreserved(unittest.TestCase):
    """The genuine rows of review 16 keep the role; its five documented refusals stay refusals and no other genuine row is refused."""

    def test_genuine_rows_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in RV["genuine_rows"]]), [])

    def test_documented_refusals_are_the_only_refusals(self):
        for e in RV["genuine_refused_before"]:
            self.assertEqual(role(e), U, e)

    def test_one_abbreviation_list_and_one_name_rule(self):
        self.assertTrue(hasattr(ir_norm, "ABBREVIATIONS"))
        self.assertEqual(E._N.ABBREVIATIONS, ir_norm.ABBREVIATIONS)
        src = Path(E.__file__).read_text()
        self.assertFalse(re.search(r"\bviz\b|\bincl\b|\bresp\b", src), "the extractor holds no abbreviation list of its own")
        self.assertIn("_N.abbreviation(", src)

    def test_skill_states_the_amendment(self):
        text = (SK / "SKILL.md").read_text()
        for w in ("segment", "artifact noun", "date-shaped number", "abbreviation", "three plain words"):
            self.assertIn(w, text, w)


if __name__ == "__main__":
    unittest.main()
