"""Repairs for the eighteenth independent exact-head review of 53946c23 (DEFECTS 1-8), each pinned test-first.
Fixtures are synthetic and source-only (tests/fixtures/review/fixes18.json, written by S/fix18/gen/mkfix18.py from re-review 18's
reproducers and generator parameters, plus own rows that no list in the code holds); they exercise the rules, not production behavior.
The reference clock is injected (NOW via the shared helpers); no test reads the wall clock or the host time zone.

THE NAME-VS-HEDGE RULE, default inverted (ir_norm._is_name, ir_norm._is_hedge_word; one rule per concept):
  D1 (major) a dash always cuts, before any fold: an em or en dash or any other dash or minus look-alike, and a fullwidth or
     compatibility form of a mark, never joins a hedge into a file, directory, pin or URL host; a "-" or "+" after a pin's version
     cuts too.
  D7 a zero-width, format, control or combining character, or a modifier letter, glued between a name and a hedge cuts there; inside a
     word it hides nothing (the word is read with it removed as well).
  D5 a question mark before a dot is a question mark ("side=producer?." before a newline).
  D6 a word at the TAIL of a path, file, URL or pin segment after a cut ("x+docs/maybe", "x#src/emit.py/maybe") is prose.
  D8 a ")" closes a date inside a parenthesis opened up to two tokens before "may" ("(since May 12)").
  D2 a quoted label names an artifact only on stronger evidence: at the text end the noun must name a program structure; before a
     location it must also stand in a noun slot (after a preposition or determiner), be followed by the code token itself, or name a
     program structure; a quoted hedge PHRASE ("Needs Verification") is never a name.
  D3 a lowercase or capitals "may" needs its date to END: a year (19xx/20xx), a location, or a comma and a year or location; a bare day
     at the clause end needs a time word before "may"; any other 4-digit number is no year.
  D4 (DEFECT 4 of the review, D7 of the remnant list) a source version is stated only with a number that is not all zeros and no word
     that says it is not known."""
import json
import random
import sys
import time
import unittest
from pathlib import Path

from test_register import SK, base
from test_review_fixes2 import NOW, check   # noqa: F401  (NOW: injected clock)
from test_review_fixes16 import cli_roles, role

sys.path.insert(0, str(SK / "scripts"))
import extract_register as E  # noqa: E402
import ir_norm  # noqa: E402

FXD = Path(__file__).resolve().parent / "fixtures" / "review"
FX = json.loads((FXD / "fixes18.json").read_text(encoding="utf-8"))
P, U = "producer", "UNKNOWN"


def cases(w):
    return [w, w[0].upper() + w[1:], w.upper()]


def wrong(rows):
    """[(text, want, got)] for every (text, want) whose role differs."""
    return [(e, want, got) for e, want in rows for got in [role(e)] if got != want]


def summary(bad, n):
    return "%d of %d wrong, e.g. %r" % (len(bad), n, [(ascii(e), w, g) for e, w, g in bad[:6]])


# ---- DEFECT 1 (major): a dash cuts before any fold --------------------------------------------------------------------------------
def glue_forms(marks, after_only=None, before_only=None):
    """re-review 18 glue18 shapes: every stem x 3 cases x 10 anchors x mark, the mark after the anchor ("src/emit.py<m>maybe") and
    before it ("maybe<m>src/emit.py"). Every form is a hedge (UNKNOWN): the mark is no code joiner."""
    out = []
    for st in FX["stems"]:
        for w in cases(st):
            for a in FX["anchors"].values():
                for g in marks if after_only is None else after_only:
                    out.append("side=producer at %s%s%s" % (a, g, w))
                for g in marks if before_only is None else before_only:
                    out.append("side=producer at %s%s%s" % (w, g, a))
    return out


class TestD1ADashCutsBeforeTheFold(unittest.TestCase):
    """DEFECT 1 (major, D1 class): canon() folded an em or en dash to "-" before the segment cut, so a hedge glued by a dash to a file
    or directory name, a pin version or a URL host read as part of the name. SKILL.md: "an em or en dash" always cuts."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d1_reviewer"]]), [])

    def test_file_pin_and_url_host_sets(self):
        rows = []
        for d in FX["d1_dashes"].values():
            for st in FX["stems"]:
                for w in cases(st):
                    rows += [(tp.format(w=w, d=d), U) for tp in FX["d1_dash_templates"].values()]
        self.assertEqual(len(rows), len(FX["d1_dashes"]) * 24 * 3 * len(FX["d1_dash_templates"]))
        bad = wrong(rows)
        self.assertEqual(bad, [], summary(bad, len(rows)))

    def test_every_non_ascii_mark_cuts(self):
        """glue18's 34 Unicode marks and 32 fullwidth forms: a look-alike of a joiner is no joiner (fullwidth "." "/" "_" "+" "=")."""
        forms = glue_forms(list(FX["d1_marks"].values()))
        self.assertEqual(len(forms), 24 * 3 * 10 * 66 * 2)
        bad = wrong([(e, U) for e in forms])
        self.assertEqual(bad, [], summary(bad, len(forms)))

    def test_ascii_marks_outside_the_join_set_cut(self):
        """Every ASCII mark but the stated joins ("." "/" "\\" "_", a ";" clause break after, a key "=" and a file or directory
        hyphen before) cuts; "-" and "+" after a pin's version ("lib@1.2.3+maybe", "lib@1.2.3-maybe") cut too."""
        forms = glue_forms(None, FX["d1_ascii_after"], FX["d1_ascii_before"])
        bad = wrong([(e, U) for e in forms])
        self.assertEqual(bad, [], summary(bad, len(forms)))

    def test_own_dashes_no_list_names(self):
        self.assertEqual(wrong([(e, U) for e in FX["d1_own"]]), [])

    def test_names_with_positive_evidence_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["d1_keep"]]), [])

    def test_through_the_cli(self):
        rows = FX["d1_reviewer"][:4] + FX["d1_keep"][:3]
        self.assertEqual(cli_roles(rows), [U] * 4 + [P] * 3)


# ---- DEFECT 7: zero-width and format glue ------------------------------------------------------------------------------------------
class TestZeroWidthGlueCuts(unittest.TestCase):
    """DEFECT 7 (pre-existing): canon() deleted zero-width, format and combining characters before the hedge was read, so a hedge glued
    by one to a name became part of that name ("src/emit.py<ZWSP>probably"). Such a character cuts there; a hedge word with one inside
    it is still the hedge word."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["zw_reviewer"]]), [])

    def test_generated_zero_width_glue(self):
        forms = glue_forms(list(FX["zw_marks"].values()))
        self.assertEqual(len(forms), 24 * 3 * 10 * 8 * 2)
        bad = wrong([(e, U) for e in forms])
        self.assertEqual(bad, [], summary(bad, len(forms)))

    def test_own_format_characters_no_list_names(self):
        self.assertEqual(wrong([(e, U) for e in FX["zw_own"]]), [])

    def test_a_hedge_word_with_a_zero_width_character_inside_stays_a_hedge(self):
        self.assertEqual(wrong([(e, U) for e in FX["zw_inside"]]), [])

    def test_zero_width_beside_no_hedge_keeps_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["zw_keep"]]), [])

    def test_one_pass_equals_each_suffix_judged_whole(self):
        """doubted_suffixes stays exact when the glue reading is needed: random pieces with dashes, zero-width and fullwidth glue."""
        rnd = random.Random(18)
        alphabet = ["maybe", "src/emit.py", "lib@1.2.3", "—", "​", "＋", "-", "obj.attr", "or", "consumer", "may", "12",
                    "(", ")", "?", ".", " ", "  ", "since", "'Maybe'", "handler", "at", "a.py:3", "­", "x"]
        for _ in range(400):
            pieces = ["".join(rnd.choice(alphabet) for _ in range(rnd.randint(1, 6))) for _ in range(rnd.randint(1, 5))]
            want = [ir_norm.negated(" ".join(pieces[i:]), doubt=True) or ir_norm.hedged(" ".join(pieces[i:])) for i in range(len(pieces))]
            self.assertEqual(ir_norm.doubted_suffixes(pieces), want, [ascii(p) for p in pieces])

    def test_through_the_cli(self):
        rows = FX["zw_reviewer"] + FX["zw_keep"][:2]
        self.assertEqual(cli_roles(rows), [U] * 3 + [P] * 2)


# ---- DEFECT 5: "?." before a newline -----------------------------------------------------------------------------------------------
class TestD5AQuestionMarkBeforeADotIsAQuestion(unittest.TestCase):
    """DEFECT 5 (regression of 53946c23): the D5 clause end keeps the dot before a newline in the clause, and the question-mark rule
    did not read "?" before "." as a question mark, so "side=producer?.\\n" asserted."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d5_reviewer"]]), [])

    def test_generated_question_dot_forms(self):
        rows = [((pre + q + nl + f).format(s="producer"), U) for pre in FX["d5_pre"] for q in FX["d5_q"] for nl in FX["d5_nl"]
                for f in FX["d5_follow"]]
        self.assertEqual(len(rows), 3 * 3 * 5 * 3)
        bad = wrong(rows)
        self.assertEqual(bad, [], summary(bad, len(rows)))

    def test_own_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d5_own"]]), [])

    def test_a_question_mark_inside_code_is_none(self):
        self.assertEqual(wrong([(e, P) for e in FX["d5_keep"]]), [])

    def test_through_the_cli(self):
        self.assertEqual(cli_roles(FX["d5_reviewer"] + FX["d5_keep"][:1]), [U, U, P])


# ---- DEFECT 6: a path, file, URL or pin tail after a cut -------------------------------------------------------------------------
def d6_forms():
    out = []
    for h in FX["d6_hedges"]:
        for sk, s in FX["d6_segs"].items():
            for p in FX["d6_prefixes"]:
                out.append((sk, "cut", FX["d6_template"].format(p=p, s=s.format(h=h))))
            for p in FX["d6_wrappers"] + [""]:
                out.append((sk, "whole", FX["d6_template"].format(p=p, s=s.format(h=h))))
    return out


class TestD6ACodeTailAfterACutIsProse(unittest.TestCase):
    """DEFECT 6 (regression of 53946c23 against bfa49033 and 22176759): after a cut, a segment of path or file kind was code, so a hedge
    that is its last component ("x+docs/maybe") or is dot-glued to it ("a.py:3,src/emit.py.probably") read as a name. A word at the
    tail of a path, file, URL or pin segment is code only when the segment is the whole token, as a dotted name is (D6 of review 17)."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d6_reviewer"]]), [])

    def test_generated_tails_after_a_cut_are_unknown(self):
        forms = [e for _, where, e in d6_forms() if where == "cut"]
        self.assertEqual(len(forms), 8 * 10 * len(FX["d6_prefixes"]))
        bad = wrong([(e, U) for e in forms])
        self.assertEqual(bad, [], summary(bad, len(forms)))

    def test_whole_slash_paths_keep_the_role(self):
        forms = [e for sk, where, e in d6_forms() if where == "whole" and sk in ("path/", "dir/", "url/")]
        self.assertEqual(wrong([(e, P) for e in forms]), [])

    def test_own_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d6_own"]]), [])

    def test_positive_path_evidence_keeps_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["d6_keep"]]), [])

    def test_through_the_cli(self):
        self.assertEqual(cli_roles(FX["d6_reviewer"][:2] + FX["d6_keep"][:2]), [U, U, P, P])


class TestAnAbbreviationRunHeadsNoMember(unittest.TestCase):
    """Found by re-review 18's eq18 reference on this repair's own head (seed 18, pre-existing on 53946c23): a word after dotted single
    letters AND a listed abbreviation ("a.k.a.cf.maybe") read as a member of a dotted name, because only the single-letter run counted
    as an abbreviation. A word that follows only abbreviations is prose (fix17 D6, residual i)."""

    def test_reviewer_row_is_unknown(self):
        bad = [e for e in FX["abbr_run_reviewer"] if E._marks(e) != set()]
        self.assertEqual(bad, [])

    def test_generated_runs_are_unknown(self):
        rows = [(tp.format(w=w), U) for tp in FX["abbr_run_forms"] for st in FX["stems"] for w in cases(st)]
        bad = wrong(rows)
        self.assertEqual(bad, [], summary(bad, len(rows)))

    def test_own_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["abbr_run_own"]]), [])

    def test_a_member_after_a_name_keeps_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["abbr_run_keep"]]), [])


# ---- DEFECT 8: a parenthesised month -------------------------------------------------------------------------------------------------
class TestD8AParenthesisedMonthIsTheMonth(unittest.TestCase):
    """DEFECT 8 (fail-closed regression of 53946c23 against bfa49033): a ")" closed a date only when the token holding "may" opened the
    parenthesis, so "(since May 12)" was refused."""

    def test_reviewer_rows_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["d8_reviewer"]]), [])

    def test_own_rows_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["d8_own"]]), [])

    def test_an_enumeration_stays_modal(self):
        self.assertEqual(wrong([(e, U) for e in FX["d8_still_modal"]]), [])

    def test_through_the_cli(self):
        self.assertEqual(cli_roles(FX["d8_reviewer"][:2]), [P, P])


# ---- DEFECT 2: quoted label remnant ---------------------------------------------------------------------------------------------------
class TestD2AQuotedLabelNeedsStrongNameEvidence(unittest.TestCase):
    """DEFECT 2 (D2 remnant, the author's residual k): a quoted Title-case hedge and a listed noun that ends the clause or has a location
    after it asserted: label, column, stage, queue, tag and flag hold a value, and test, check, alert, step are verbs as well."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d2_reviewer"]]), [])

    def test_generated_listed_and_unlisted_nouns(self):
        rows = []
        for h in FX["d2_hq"]:
            for q in FX["d2_quotes"]:
                for n in FX["d2_nouns_verb"]:
                    rows += [(tp.format(q=q % h, n=n), U) for tp in FX["d2_shapes"]]
                for n in FX["d2_unlisted"]:
                    rows += [(tp.format(q=q % h, n=n), U) for tp in FX["d2_unlisted_shapes"]]
        self.assertEqual(len(rows), 9240)
        bad = wrong(rows)
        self.assertEqual(bad, [], summary(bad, len(rows)))

    def test_own_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d2_own"]]), [])

    def test_quoted_names_with_strong_evidence_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["d2_keep"]]), [])

    def test_through_the_cli(self):
        self.assertEqual(cli_roles(FX["d2_reviewer"][:2] + FX["d2_keep"][:2]), [U, U, P, P])


# ---- DEFECT 3: the date-shape month remnant -----------------------------------------------------------------------------------------
def d3_forms():
    """may18's 1,890 modal forms, without the 280 a Title-case "May" and a day 1-31 give (residual l: a capital May with a day is the
    month whatever follows, pinned by fixes13/fixes17 "May 12 log:" and "May 3 release a.py:1")."""
    out = []
    for may in FX["d3_may"]:
        for num in FX["d3_nums"]:
            for p in FX["d3_punct"]:
                for f in FX["d3_follow"]:
                    for s in FX["d3_subj"]:
                        if may == "May" and len(num) <= 2 and int(num) <= 31 and p != ")":
                            continue
                        out.append(FX["d3_template"].format(s=s, may=may, num=num, p=p, f=f))
    return out


class TestD3ADateMustEndForAModalShape(unittest.TestCase):
    """DEFECT 3 (pre-existing): any 4-digit number was a year, and a day with glued ". , :" or at the clause end "ended" a date."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d3_reviewer"]]), [])

    def test_generated_modal_forms_are_unknown(self):
        forms = d3_forms()
        self.assertEqual(len(forms), 1890 - 280)
        bad = wrong([(e, U) for e in forms])
        self.assertEqual(bad, [], summary(bad, len(forms)))

    def test_own_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d3_own"]]), [])

    def test_genuine_months_keep_the_role(self):
        self.assertEqual(wrong([("side=producer, " + g, P) for g in FX["d3_genuine"]]), [])

    def test_through_the_cli(self):
        self.assertEqual(cli_roles(FX["d3_reviewer"][:2] + ["side=producer, " + FX["d3_genuine"][0]]), [U, U, P])


# ---- DEFECT 4 (D7 remnant): a version that only says it is not known -------------------------------------------------------------
class TestD7AStatedVersionNeedsANumber(unittest.TestCase):
    """DEFECT 4 of re-review 18 (D7 remnant, pre-existing): any word other than a listed placeholder counted as a stated version."""

    def reg(self, version):
        reg = base()
        reg["records"][0]["source_identity"]["version"] = version
        return reg

    def codes(self, version):
        return [(f["code"], f["message"]) for f in check(self.reg(version))["findings"] if f["severity"] == "error"]

    def test_reviewer_versions_are_refused(self):
        for v in FX["d7_reviewer"]:
            self.assertIn(("unknown-field", "source_identity source version UNKNOWN"), self.codes(v), v)

    def test_own_versions_are_refused(self):
        for v in FX["d7_own"]:
            self.assertIn(("unknown-field", "source_identity source version UNKNOWN"), self.codes(v), v)

    def test_stated_versions_pass(self):
        for v in FX["d7_keep"]:
            self.assertTrue(check(self.reg(v))["ok"], (v, self.codes(v)))

    def test_partial_keeps_the_record(self):
        reg = self.reg("unreleased")
        reg["coverage"]["declared"] = "partial"
        self.assertTrue(check(reg)["ok"])


# ---- time and structure ---------------------------------------------------------------------------------------------------------------
class TestGlueReadingStaysLinear(unittest.TestCase):
    """The glue reading is canon() once more with the glue marks as cuts, only for a text that holds one: 80K characters cost under
    24x the CPU time of 10K (linear is 8x). CPU time, best of 3, so host load does not flake it."""

    SHAPES = {"zw-glue": "side=producer at " + "src/emit.py​maybe " * 4000, "dash-pins": "side=producer at " + "lib@1.2.3—x " * 6000,
              "fw-marks": "side=producer at " + "a＋b／c " * 9000, "paren-may": "side=producer " + "(since may 1) " * 6000,
              "quoted": "side=producer " + "in 'Maybe' handler " * 4000}

    def cpu(self, t):
        best = 1e9
        for _ in range(3):
            a = time.process_time()
            ir_norm.hedged(t)
            E._marks(t)
            best = min(best, time.process_time() - a)
        return best

    def test_80k_costs_under_24x_of_10k(self):
        for k, t in self.SHAPES.items():
            small, big = t[:10000], t[:80000]
            ratio = self.cpu(big) / max(self.cpu(small), 1e-4)
            self.assertLess(ratio, 24, (k, ratio))


class TestOneCanonAndTheSkillText(unittest.TestCase):

    def test_the_glue_reading_is_canon_itself(self):
        import inspect
        src = inspect.getsource(ir_norm)
        self.assertEqual(src.count("def canon("), 1)
        self.assertEqual(src.count("def _canon_chars("), 1)
        self.assertIn("glue", inspect.signature(ir_norm._canon_chars).parameters)

    def test_skill_states_the_dash_cut_and_the_glue_rule(self):
        text = (SK / "SKILL.md").read_text()
        for w in ("before any fold", "zero-width", "a program structure", "the date must end", "holds a number"):
            self.assertIn(w, text, w)


if __name__ == "__main__":
    unittest.main()
