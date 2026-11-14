"""Repairs for the seventeenth independent exact-head review of bfa49033 (D1-D7), each pinned test-first.
Fixtures are synthetic and source-only (tests/fixtures/review/fixes17.json); they exercise the rules, not production behavior.
The reference clock is injected (NOW via the shared helpers); no test reads the wall clock or the host time zone.

THE NAME-VS-HEDGE RULE, default inverted (ir_norm._is_name, ir_norm._is_hedge_word; still one rule per concept): a hedge word stays a
hedge unless POSITIVE name evidence holds; a mark, a following word, a modifier or a context the rule does not recognise leaves the
role UNKNOWN.
  D6 a bare dotted name is code only as a whole token, and a hedge that heads it ("probably.ok", "cf.maybe") is no member of it;
     "#" cuts a segment ("emit.py#maybe").
  D1 only "." "/" "_", "::" "://", a pin's "@" and a hyphen inside a file or directory name join a word into code; every other mark
     (em and en dash after a name, "#", brackets, quotes, "|", "&", "+", "~", "!", "*", "%", "^", "$", any unlisted mark) cuts.
  D2 a quoted Capitalised label names an artifact only when an artifact noun follows the closed quote AND a location follows the noun;
     a status or state word after the quote takes the label as its value.
  D3 "may" is the month only on date evidence: a day or year after it (a lowercase "may" needs the date to end there), or a time word
     before it and then the clause end, a location, or a month range.
  D4 an alternative connective (word or standalone symbol) reaches a side word across up to three tokens of any kind.
  D5 a newline after an abbreviation's dot still ends the clause.
  D7 a source version that only says it is not known ("pending", "tbc", "unknown (pending)") is UNKNOWN for a complete claim."""
import copy
import json
import random
import re
import sys
import unittest
from pathlib import Path

from test_register import SK, base
from test_review_fixes2 import NOW, check   # noqa: F401  (NOW: injected clock)
from test_review_fixes16 import cli_roles, role, title

sys.path.insert(0, str(SK / "scripts"))
import extract_register as E  # noqa: E402
import ir_norm  # noqa: E402

FXD = Path(__file__).resolve().parent / "fixtures" / "review"
FX = json.loads((FXD / "fixes17.json").read_text(encoding="utf-8"))
P, U = "producer", "UNKNOWN"


def cases(w):
    return [w, w[0].upper() + w[1:], w.upper()]


def wrong(rows):
    """[(text, want, got)] for every (text, want) whose role differs."""
    return [(e, want, got) for e, want in rows for got in [role(e)] if got != want]


# ---- D6 ---------------------------------------------------------------------------------------------------------------------------
def d6_forms():
    out = []
    for st in FX["stems"]:
        for w in (st, st[0].upper() + st[1:]):
            for an in FX["d6_anchors"].values():
                for c in FX["d6_cuts"]:
                    for tail in FX["d6_tails"]:
                        out.append("side=producer at %s%s%s.%s" % (an, c, w, tail))
                    for f in FX["d6_hash_files"]:
                        out.append("side=producer at %s%s%s#%s" % (an, c, f, w))
    return out


class TestD6SegmentRuleCreatesNoName(unittest.TestCase):
    """D6 (fail-open regression of bfa49033 against 22176759): a hedge heading a dotted segment, or after "#", is no name."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d6_reviewer"]]), [])

    def test_generated_dotted_and_hash_segments_are_unknown(self):
        forms = d6_forms()
        self.assertEqual(len(forms), 25 * 2 * 3 * 6 * 7)
        bad = [e for e in forms if role(e) != U]
        self.assertEqual(bad, [], "%d of %d asserted, e.g. %r" % (len(bad), len(forms), bad[:5]))

    def test_own_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d6_own"]]), [])

    def test_names_with_positive_evidence_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["d6_keep"]]), [])

    def test_through_the_cli(self):
        rows = FX["d6_reviewer"][:4] + FX["d6_keep"][:3]
        self.assertEqual(cli_roles(rows), [U] * 4 + [P] * 3)


# ---- D1 ---------------------------------------------------------------------------------------------------------------------------
def d1_forms():
    """(text, want): every known stem x 3 cases x 7 anchors x every ASCII punctuation mark, em and en dash and curly quote, before and
    after the anchor, plus 13 wrappers after it. `want` is producer only where FX["d1_positive"] names positive name evidence for that
    (mark, position, anchor): an identifier ("_"), a path, URL or dotted member ("/", "\\", "."), a key ("maybe=..."), a dashed file
    or directory name ("maybe-emit.py", "maybe-src/emit.py"), or a clause break (";" before the hedge); everything else is UNKNOWN."""
    pos = {k: (set(FX["d1_anchors"]) if v == "*" else set(v.split())) for k, v in FX["d1_positive"].items()}
    out = []
    for st in FX["stems"]:
        for w in cases(st):
            for an, a in FX["d1_anchors"].items():
                for g in FX["d1_glue"]:
                    out.append(("side=producer at %s%s%s" % (a, g, w), P if an in pos.get(g + " after", ()) else U))
                    out.append(("side=producer at %s%s%s" % (w, g, a), P if an in pos.get(g + " before", ()) else U))
                for o, c in FX["d1_wrap"]:
                    out.append(("side=producer at %s%s%s%s" % (a, o, w, c), U))
    return out


class TestD1GlueOutsideTheJoinSetCuts(unittest.TestCase):
    """D1 (N2 remnant, undisclosed regression of bfa49033 against 5de4632b): only the marks that join a code name keep a glued hedge
    inside one; any other mark cuts it off, so the hedge is judged alone and refuses the role."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d1_reviewer"]]), [])

    def test_generated_glue_forms(self):
        forms = d1_forms()
        self.assertEqual(len(forms), 25 * 3 * 7 * (len(FX["d1_glue"]) * 2 + len(FX["d1_wrap"])))
        bad = wrong(forms)
        self.assertEqual(bad, [], "%d of %d wrong, e.g. %r" % (len(bad), len(forms), bad[:6]))

    def test_own_unlisted_marks_cut(self):
        self.assertEqual(wrong([(e, U) for e in FX["d1_own"]]), [])

    def test_names_with_positive_evidence_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["d1_keep"]]), [])

    def test_through_the_cli(self):
        rows = FX["d1_reviewer"][:5] + FX["d1_keep"][:3]
        self.assertEqual(cli_roles(rows), [U] * 5 + [P] * 3)


# ---- D2 ---------------------------------------------------------------------------------------------------------------------------
def d2_forms():
    nouns = sorted(ir_norm._NAME_HEADS | set(FX["d2_verbs"])) if hasattr(ir_norm, "_NAME_HEADS") else FX["d2_verbs"]
    out = []
    for h in FX["d2_hedges"]:
        for w in (title(h), h.upper()):
            for o, c in FX["d2_quotes"]:
                for n in nouns:
                    for tp in FX["d2_templates"]:
                        out.append(tp.format(q=o + w + c, n=n))
    return out


class TestD2QuotedLabelNeedsALocatedArtifact(unittest.TestCase):
    """D2 (N1 remnant, the author's residual f): a quoted hedge followed by a noun that is used as a verb or holds the label as a
    status is prose; a quoted name needs its artifact noun and a location after it."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d2_reviewer"]]), [])

    def test_generated_unlocated_labels_are_unknown(self):
        forms = d2_forms()
        bad = [e for e in forms if role(e) != U]
        self.assertEqual(bad, [], "%d of %d asserted, e.g. %r" % (len(bad), len(forms), bad[:5]))

    def test_caps_and_value_nouns_are_no_name_even_when_located(self):
        rows = ["side=producer in the 'MAYBE' handler at h.py:3", "side=producer in the `PROBABLY` queue at q.py:3",
                "side=producer, marked it 'Maybe' status at a.py:3", "side=producer in 'Likely' state at s.py:2"]
        self.assertEqual(wrong([(e, U) for e in rows]), [])

    def test_own_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d2_own"]]), [])

    def test_located_quoted_names_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["d2_keep"]]), [])

    def test_through_the_cli(self):
        rows = FX["d2_reviewer"][:3] + FX["d2_keep"][:3]
        self.assertEqual(cli_roles(rows), [U] * 3 + [P] * 3)


# ---- D3 ---------------------------------------------------------------------------------------------------------------------------
def d3_forms():
    """may17's hedged shapes (stranded time preposition, preposition + early/late/mid/end, "the front end", "it") with every follower;
    a follower that ends the clause right after "may" is split out (see test_clause_end_after_a_time_word_is_the_month)."""
    lead = [("strand-%s" % p, "side=producer, but %s " % s) for p, s in FX["d3_stranded"].items()]
    for pa in FX["d3_part_after"]:
        for part in FX["d3_parts"]:
            lead.append(("part-%s-%s" % (pa, part), "side=producer, though the call to %s " % part if pa == "to"
                         else "side=producer, though %s %s " % (pa, part)))
    lead += [("front end", "side=producer, though the front end "), ("it", "side=producer, though it ")]
    hed = [(k, fk, s + f) for k, s in lead for fk, f in FX["d3_follow"].items()]
    end = [(k, fk, s + f) for k, s in lead for fk, f in FX["d3_clause_end"].items()]
    return hed, end


class TestD3ModalMayNeedsDateEvidence(unittest.TestCase):
    """D3 (N3 remnant, pre-existing): a stranded time preposition, "to end", a bare count or an enumeration gives "may" no date."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d3_reviewer"]]), [])

    def test_generated_modal_forms_are_unknown(self):
        hed, _ = d3_forms()
        bad = [e for _, _, e in hed if role(e) != U]
        self.assertEqual(bad, [], "%d of %d asserted, e.g. %r" % (len(bad), len(hed), bad[:5]))

    def test_clause_end_after_a_time_word_is_the_month(self):
        """Disputed rows of may17 (end, dot-end after a time word): token for token the pinned genuine 'side=producer since May.' and
        'shipped in may.'; no verb follows, so the modal reading needs an ellipsis. Without a time word the modal stays a hedge."""
        _, end = d3_forms()
        for k, fk, e in end:
            want = U if k in ("front end", "it") else P
            self.assertEqual(role(e), want, e)

    def test_own_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d3_own"]]), [])

    def test_genuine_months_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["d3_keep"]]), [])

    def test_through_the_cli(self):
        rows = FX["d3_reviewer"][:3] + FX["d3_keep"][:3]
        self.assertEqual(cli_roles(rows), [U] * 3 + [P] * 3)


# ---- D4 ---------------------------------------------------------------------------------------------------------------------------
def d4_forms():
    return [(ck, mk, t.format(m=m, s=s)) for ck, t in FX["d4_conn"].items() for mk, m in FX["d4_mods"].items() for s in FX["d4_sides"]]


class TestD4AlternativeReachesAcrossAnyModifier(unittest.TestCase):
    """D4 (N5 remnant, pre-existing): the reach after an alternative connective crosses any token kind (number, ordinal, version,
    hyphen, quote, backtick, preposition, comma, symbol), word or symbol connective alike."""

    def test_reviewer_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d4_reviewer"]]), [])

    def test_generated_alternatives_are_unknown(self):
        forms = d4_forms()
        self.assertEqual(len(forms), 12 * 23 * 4)
        bad = [(ck, mk, e) for ck, mk, e in forms if role(e) != U]
        self.assertEqual(bad, [], "%d of %d asserted, e.g. %r" % (len(bad), len(forms), bad[:5]))

    def test_own_rows_are_unknown(self):
        self.assertEqual(wrong([(e, U) for e in FX["d4_own"]]), [])

    def test_locations_and_far_words_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["d4_keep"]]), [])

    def test_through_the_cli(self):
        rows = FX["d4_reviewer"][:3] + FX["d4_keep"][:2]
        self.assertEqual(cli_roles(rows), [U] * 3 + [P] * 2)


# ---- D5 ---------------------------------------------------------------------------------------------------------------------------
_CHAR_END = re.compile(r"[;\n]|\.[^\S\n]")


def char_scan_ends(t):
    """Independent clause-end oracle written from SKILL.md (not E._clause_ends): ";" and every newline end a clause; a full stop and a
    blank end one unless the word before the dot is an abbreviation (ir_norm.abbreviation, the one list)."""
    out = []
    for c in _CHAR_END.finditer(t):
        i = c.start()
        if t[i] == ".":
            j = i
            while j > 0 and not t[j - 1].isspace():
                j -= 1
            if ir_norm.abbreviation(t[j:i]):
                continue
        out.append(c.span())
    return out


def reference_marks(t):
    """test_review_fixes16.reference_marks with the clause ends taken from char_scan_ends (so the oracle shares nothing with the
    implementation's own clause boundary)."""
    out = set()
    prev_end = 0
    ends = char_scan_ends(t)
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


class TestD5NewlineAfterAnAbbreviationEndsTheClause(unittest.TestCase):
    """D5 (new in bfa49033, fail-closed): "etc.\\n" ends the clause at the newline, as SKILL.md states; "etc. " still joins."""

    def test_reviewer_rows_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["d5_reviewer"]]), [])

    def test_every_listed_abbreviation_and_a_newline(self):
        rows = [tp.format(a=a) for a in FX["d5_abbr"] for tp in FX["d5_templates"]]
        self.assertEqual(wrong([(e, P) for e in rows]), [])

    def test_a_blank_after_the_dot_still_joins(self):
        rows = [tp.format(a=a) for a in FX["d5_abbr"] for tp in FX["d5_joined_templates"]]
        self.assertEqual(wrong([(e, U) for e in rows]), [])

    def test_own_rows_keep_the_role(self):
        self.assertEqual(wrong([(e, P) for e in FX["d5_own"]]), [])

    def test_clause_ends_equal_the_character_scan(self):
        rng = random.Random(17)
        vocab = FX["d5_vocab"]
        for _ in range(4000):
            t = "".join(rng.choice(vocab) + rng.choice((" ", "", " ", "\n")) for _ in range(rng.randint(1, 14)))
            self.assertEqual(E._clause_ends(t), char_scan_ends(t), repr(t))
            self.assertEqual(E._marks(t), reference_marks(t), repr(t))


# ---- D7 ---------------------------------------------------------------------------------------------------------------------------
class TestD7PlaceholderVersionIsNoVersion(unittest.TestCase):
    """D7 (pre-existing, outside the delta): complete refuses a source version that only says it is not known."""

    def reg(self, version):
        reg = base()
        reg["records"][0]["source_identity"]["version"] = version
        return reg

    def codes(self, version):
        return [(f["code"], f["message"]) for f in check(self.reg(version))["findings"] if f["severity"] == "error"]

    def test_reviewer_versions_are_refused(self):
        for v in FX["d7_reviewer"]:
            res = check(self.reg(v))
            self.assertFalse(res["ok"], v)
            self.assertIn(("unknown-field", "source_identity source version UNKNOWN"), self.codes(v), v)

    def test_own_placeholder_versions_are_refused(self):
        for v in FX["d7_own"]:
            self.assertFalse(check(self.reg(v))["ok"], v)

    def test_stated_versions_pass(self):
        for v in FX["d7_keep"]:
            self.assertTrue(check(self.reg(v))["ok"], (v, self.codes(v)))

    def test_partial_keeps_the_record(self):
        reg = self.reg("pending")
        reg["coverage"]["declared"] = "partial"
        self.assertTrue(check(reg)["ok"])


# ---- structure ----------------------------------------------------------------------------------------------------------------------
class TestOneRulePerConcept(unittest.TestCase):

    def test_one_location_rule_for_keys_and_quoted_names(self):
        src = Path(ir_norm.__file__).read_text()
        self.assertEqual(len(re.findall(r"def located\(", src)), 1)
        self.assertGreaterEqual(src.count(".located("), 2, "the answer key and the quoted name read one location rule")

    def test_one_placeholder_wording_rule_for_commits_and_versions(self):
        import register_validate as rv
        self.assertIn("_N.unstated_version(", Path(rv.__file__).read_text())
        self.assertTrue(ir_norm.unstated_version("unknown (pending)"))
        self.assertIs(ir_norm.commit_id("unknown (pending)"), None)

    def test_skill_states_the_inverted_default(self):
        text = (SK / "SKILL.md").read_text()
        for w in ("positive name evidence", "every other mark", "a location after the noun", "a month range", "three tokens of any kind",
                  "a newline after an abbreviation", "only says it is not known"):
            self.assertIn(w, text, w)


if __name__ == "__main__":
    unittest.main()
