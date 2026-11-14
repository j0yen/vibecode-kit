"""Regression tests for the thirteenth independent exact-head review (re-review 12 of d970f49c): DEF-1 .. DEF-4.

The invariant under test (decided before the code, see SKILL.md "Identity invariant"): an identity-field value prints only when
every piece of it is accounted for by something the tool's own reviewed source fixes in advance (a closed-vocabulary word or a
literal of the field's own template, an exact id template the field carries, a bounded number or date) and the rest fits the
bounded unlisted budget (at most 5 characters a piece, 8 a value). How a value looks as language is never evidence:
pronounceability, dictionary membership, case and syllable structure admit human passwords and pronounceable-generator output.

Negatives are dictionary words, human passwords and CV/CVC-built generator words in every identity field the review names, in the
field's own forms, Title-case, glued to digits, two per value and beside vocabulary words, through the gate, JSON + text output and
the CLIs. Canaries are assembled at run time from fragments and never printed: assertion labels carry a field and an index only."""
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import unittest

from helpers import FIX, SKILL, install_fixture_clock, remove_fixture_clock

import envelope_validate as ev
import test_review_fixes3 as t3
from test_review_fixes10 import probe

running = t3.running
TESTS = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(str(SKILL), "scripts")
RECOMMEND = os.path.join(SCRIPTS, "recommend.py")
VALIDATE = os.path.join(SCRIPTS, "envelope_validate.py")
NOW = "2026-11-13T07:00:00Z"


def setUpModule():
    install_fixture_clock()


def tearDownModule():
    remove_fixture_clock()


_R = random.Random(13)
B62 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
LOWER = "abcdefghijklmnopqrstuvwxyz"
DIG = "0123456789"
CONS, VOW = "bcdfghjklmnprstvwz", "aeiou"


def rnd(alpha, n):
    return "".join(_R.choice(alpha) for _ in range(n))


def J(*parts):
    return "".join(parts)


# ------------------------------------------------------------------------------------------------------- the word classes
# The reviewer's words (re-review 12, probes/human12.py and pairs12.py), assembled from fragments.
REVIEW_WORDS = [J("sun", "shine"), J("drag", "onfly"), J("prin", "cess"), J("mus", "tang"), J("foot", "ball"),
                J("correct", "horse"), J("battery", "staple"), J("tieg", "heng"), J("ohva", "esho")]
# Human-chosen passwords of the common-list kind (mine, not in any list the code holds).
HUMAN_WORDS = [J("let", "mein", "please"), J("trust", "no", "1"), J("ilove", "you"), J("qwerty", "uiop"), J("monkey", "business"),
               J("sand", "castle"), J("super", "man"), J("what", "ever"), J("star", "wars"), J("hunter", "22"), J("Winter", "2025"),
               J("gold", "fish", "99"), J("rain", "bow", "42"), J("blue", "berry", "7")]
# Ordinary dictionary words (mine, not in any list the code holds).
DICT_WORDS = [J("lan", "tern"), J("vel", "vet"), J("thun", "der"), J("bis", "cuit"), J("mea", "dow"), J("peli", "can"),
              J("saff", "ron"), J("mar", "malade"), J("whis", "per"), J("gar", "denia")]


def cv_word(n):
    """A pronounceable-generator word: consonant-vowel syllables (pwgen/diceware-style), n letters."""
    s = ""
    while len(s) < n:
        s += _R.choice(CONS) + _R.choice(VOW)
    return s[:n]


def cvc_word(k):
    return "".join(_R.choice(CONS) + _R.choice(VOW) + _R.choice(CONS) for _ in range(k))


def budget_explained(word):
    """True when the closed vocabulary and the stated unlisted budget account for an alphabetic piece: a vocabulary word, a piece of at
    most five characters, a vocabulary word with a suffix of at most five characters, or a run of vocabulary words. A piece only a
    name SHAPE could admit is not explained."""
    low = word.lower()
    if len(low) <= ev._MAX_SHORT or low in ev._ID_WORDS or ev._segment(low, frozenset()):
        return True
    return any(low.startswith(w) and 0 < len(low) - len(w) <= ev._MAX_SHORT for w in ev._ID_WORDS if len(w) >= 3)


# Each identity field the review names, with the forms its own grammar takes: `{a}` and `{b}` are the words under test.
FIELD_FORMS = {
    ("worker.unit", "ident"): ["{a}.service", "wm-{a}.service", "{a}-{b}.timer", "wm-{a}-build.service", "{a}42.service",
                               "fleet-{a}-watch.service"],
    ("worker.child", "ident"): ["{a}", "wm-{a}.scope", "child-{a}", "{a}-{b}"],
    ("current_owner", "ident"): ["{a}", "r7-{a}", "{a}-{b}", "{a}42", "claude-3947245-r7-{a}-20261113"],
    ("reviewed_by", "ident"): ["{a}", "ctl-{a}", "{a}-{b}", "claude-2765718-r7-{a}-20261113-worker"],
    ("result.reviewed_by", "ident"): ["{a}", "hermes-{a}"],
    ("consumer.named", "ident"): ["{a}", "{a}-worker", "verifier-{a}", "claude-3947245-r7-{a}-20261113-worker", "queue-{a}-merge"],
    ("consumer.alternate", "ident"): ["{a}", "{a}-{b}", "reviewer-{a}"],
    ("target.branch", "ident"): ["{a}", "feat/{a}", "r7/{a}-20261113", "feat/A1663-{a}", "{a}-{b}", "fix/{a}-12"],
    ("target.repo", "ident"): ["j0yen/{a}", "j0yen/{a}-kit", "j0yen/{a}-{b}", "j0yen/{a}42"],
    ("task_id", "ident"): ["{a}", "a1663-{a}", "{a}-{b}", "wf-{a}", "{a}42"],
    ("result.artifact", "path"): ["/mnt/ssd/{a}/x.md", "/mnt/ssd/cargo-target/{a}-{b}/out/report.md", "/home/jsy/Notes/{a}-20261108.json",
                                  "/mnt/ssd/out/{a}.md"],
    ("result.event", "path"): ["evt-{a}", "/retained/{a}/result.json"],
    ("evidence-ref", "path"): ["/mnt/ssd/{a}/review.md", "{a}-{b}.json"],
    ("ref", "path"): ["/retained/{a}-{b}/x.json"],
    ("target", "path"): ["/mnt/ssd/{a}.md"],
    ("result", "path"): ["/mnt/ssd/x/{a}.md"],
    ("artifact", "path"): ["/out/{a}/{b}.md"],
    ("event", "path"): ["evt-{a}-{b}"],
}


def forms_with(a, b):
    for (field, kind), forms in FIELD_FORMS.items():
        for f in forms:
            yield field, kind, f.format(a=a, b=b)


def variants(word):
    """The word as written, Title-case and upper-first: case is never evidence."""
    return [word, word[:1].upper() + word[1:], word.lower()]


class Def1NameShapeIsNotTrust(unittest.TestCase):
    """DEF-1 (major): a word that only LOOKS like a name (a dictionary word, a human password, a pronounceable-generator word) is an
    opaque ref in every identity field, in every form of that field, two per value and beside vocabulary words."""

    def leaks(self, words):
        bad = []
        for i, w in enumerate(words):
            other = words[(i + 1) % len(words)]
            for a in variants(w):
                for field, kind, v in forms_with(a, other):
                    if a in ev.show(field, v, kind):
                        bad.append((field, i))
        return bad

    def test_the_reviewers_words_are_opaque_in_every_identity_field(self):
        self.assertEqual(self.leaks(REVIEW_WORDS), [])

    def test_human_passwords_are_opaque_in_every_identity_field(self):
        self.assertEqual(self.leaks(HUMAN_WORDS), [])

    def test_dictionary_words_are_opaque_in_every_identity_field(self):
        self.assertEqual(self.leaks(DICT_WORDS), [])

    def test_my_negatives_are_not_explained_by_the_stated_budget(self):
        """Test-data check: every word above is longer than the 5-character piece budget and is not a vocabulary word plus a short
        suffix, so only a name-SHAPE rule could print it."""
        for i, w in enumerate(REVIEW_WORDS + HUMAN_WORDS + DICT_WORDS):
            alpha = [x for x in re.findall(r"[A-Za-z]+", w)]
            self.assertTrue(any(not budget_explained(x) for x in alpha), i)

    def test_generator_words_are_opaque_two_per_value(self):
        """CV- and CVC-built generator words of 10-12 letters, two per value: none prints in any field."""
        bad = []
        for n in (10, 11, 12):
            for k in range(25):
                a, b = cv_word(n), (cvc_word(4) if k % 2 else cv_word(n))
                for field, kind, v in forms_with(a, b):
                    if a in ev.show(field, v, kind):
                        bad.append((field, n, k))
        self.assertEqual(bad, [], "%d leaks, first %s" % (len(bad), bad[:4]))

    def test_generator_words_of_any_length_print_only_when_the_budget_explains_them(self):
        """CV/CVC words of 6-9 letters: a print is allowed only where a closed-vocabulary prefix plus a suffix of at most five characters
        accounts for the word (the stated budget); a print that only the syllable shape could explain is a leak."""
        unexplained = 0
        for n in (6, 7, 8, 9):
            for _ in range(150):
                w = cv_word(n) if n % 2 == 0 else cvc_word(3)[:n]
                for field, kind in (("current_owner", "ident"), ("worker.unit", "ident"), ("target.branch", "ident"),
                                    ("task_id", "ident"), ("result.artifact", "path"), ("consumer.named", "ident")):
                    v = {"worker.unit": w + ".service", "result.artifact": "/mnt/ssd/" + w + ".md"}.get(field, w)
                    if w in ev.show(field, v, kind) and not budget_explained(w):
                        unexplained += 1
        self.assertEqual(unexplained, 0)

    def test_end_to_end_through_the_recommender_json_and_text(self):
        """probe(): the recommender's JSON and text output for an envelope with the word in the field."""
        fields = {"current_owner": "{a}", "target.branch": "feat/{a}", "target.repo": "j0yen/{a}", "worker.unit": "wm-{a}.service",
                  "worker.child": "wm-{a}.scope", "consumer.named": "{a}-worker", "task_id": "{a}", "result.artifact": "/mnt/ssd/{a}/x.md",
                  "result.event": "evt-{a}"}
        bad = []
        for i, w in enumerate(REVIEW_WORDS[:4] + HUMAN_WORDS[:2] + DICT_WORDS[:2] + [cv_word(10)]):
            for f, form in fields.items():
                if w in probe(f, form.format(a=w)):
                    bad.append((f, i))
        self.assertEqual(bad, [])

    def test_end_to_end_through_both_clis(self):
        """recommend.py --format json / text and envelope_validate.py on envelope files: the word is in none of their output."""
        w1, w2 = J("sun", "shine"), J("velv", "et")
        d = running()
        d["current_owner"] = w1
        d["target"]["branch"] = "feat/" + w1
        d["worker"]["unit"] = "wm-%s-%s.service" % (w1, w2)
        d["task_id"] = w2
        d["evidence"][0]["task_id"] = w2
        d2 = t3.done()
        d2["consumer"]["named"] = w1 + "-worker"
        d2["result"]["artifact"] = "/mnt/ssd/%s/x.md" % w2
        with tempfile.TemporaryDirectory() as td:
            out = ""
            for k, env in enumerate((d, d2)):
                p = os.path.join(td, "e%d.json" % k)
                with open(p, "w") as fh:
                    json.dump(env, fh)
                for args in ([RECOMMEND, "--format", "json"], [RECOMMEND, "--format", "text"], [VALIDATE]):
                    r = subprocess.run([sys.executable, "-I"] + args + ["--now", NOW, p], capture_output=True, text=True, timeout=120)
                    self.assertNotIn("Traceback", r.stderr)
                    out += r.stdout + r.stderr
        self.assertFalse(w1 in out, "word 1")
        self.assertFalse(w2 in out, "word 2")

    def test_the_source_has_no_name_shape_trust(self):
        """The syllable grammar and the name-word budget are gone; no trust rule reads vowels or syllables."""
        self.assertFalse(hasattr(ev, "_pronounceable"))
        src = open(os.path.join(SCRIPTS, "envelope_validate.py")).read()
        for gone in ("_PRON", "lang_letters", "_LANG_WORD"):
            self.assertNotIn(gone, src)

    def test_the_real_fleet_names_still_print(self):
        """No over-refusal: the fleet names that printed only through the syllable grammar print through the closed vocabulary."""
        for f, k, v in (("worker.unit", "ident", "wm-decide-regrade.service"), ("worker.unit", "ident", "agorabus-reap.timer"),
                        ("worker.unit", "ident", "memlog-witness.service"), ("worker.unit", "ident", "swarm-decide-regrade.timer"),
                        ("worker.unit", "ident", "app-gnome-Terminal-12345.scope"), ("target.branch", "ident", "feat/A1663-repair-12"),
                        ("target.repo", "ident", "j0yen/swarm-decide"), ("target.repo", "ident", "synthetic/repo-a"),
                        ("result.artifact", "path", "/home/jsy/Notes/hermes-director-bootstrap-proof-20261108.json"),
                        ("consumer.named", "ident", "wm-decide-regrade.service"), ("current_owner", "ident", "controller")):
            self.assertIn(v, ev.show(f, v, k), (f, v))

    def test_vocabulary_holds_no_common_password_word(self):
        """The closed vocabulary is reviewed source: no word of six or more letters from the common human-password lists is in it
        (a shorter one is inside the 5-character budget anyway)."""
        common = [J("pass", "word"), J("dra", "gon"), J("mon", "key"), J("let", "mein"), J("foot", "ball"), J("base", "ball"),
                  J("mas", "ter"), J("sha", "dow"), J("sun", "shine"), J("prin", "cess"), J("wel", "come"), J("super", "man"),
                  J("bat", "man"), J("trust", "no1"), J("ilove", "you"), J("star", "wars"), J("what", "ever"), J("free", "dom"),
                  J("hun", "ter"), J("ran", "ger"), J("bus", "ter"), J("soc", "cer"), J("hoc", "key"), J("kil", "ler"),
                  J("char", "lie"), J("jor", "dan"), J("har", "ley"), J("mus", "tang"), J("sum", "mer"), J("flo", "wer"),
                  J("coo", "kie"), J("pep", "per"), J("gin", "ger"), J("sil", "ver"), J("ora", "nge"), J("pur", "ple"),
                  J("ban", "ana"), J("che", "ese"), J("compu", "ter"), J("inter", "net"), J("sec", "ret"), J("ac", "cess"),
                  J("q", "werty"), J("a", "bc123"), J("login", "123"), J("ad", "min123"), J("pass", "w0rd")]
        self.assertEqual(sorted(w for w in common if len(w) >= 6 and w in ev._ID_WORDS), [])


# ------------------------------------------------------------------------------------------------------------------ DEF-2
GLUED_NAMES = [J("db", "pass"), J("user", "pass"), J("my", "pass"), J("root", "pw"), J("db", "pw"),
               J("admin", "pwd"), J("wifi", "pass"), J("svc", "token"), J("app", "secret"), J("sudo", "pw"), J("vpn", "pin"),
               J("mail", "passwd")]
WEAK_NAMES = [J("un", "lock"), J("va", "ult")]
FORMS2 = ["{n} {v}", "the {n} is {v}", "{N} {v}", "{n} was {v} yesterday", "set {n} to {v} now", "({n} {v})", "{n}\t{v}",
          "{U} {v}", "my {n} {v} and more", "use {n} {v}"]


class Def2GluedCredentialNamesInProse(unittest.TestCase):
    """DEF-2 (minor): a credential name whose credential noun is glued to a qualifier (`dbpass`, `rootpw`) followed in bare prose by
    its value hides the value, across separator forms and value lengths; `unlock` and `vault` hide a key-shaped value."""

    def values(self, strong):
        out = [rnd(B62, n) for n in (6, 9, 12, 16, 24)] + [J("Xk9", rnd(B62, 9))] + [rnd(DIG, 6), rnd(DIG, 10)]
        if strong:
            out += [J("hun", "ter"), rnd(LOWER, 8), rnd(LOWER, 14)]
        return out

    def check(self, names, strong):
        bad = []
        for i, n in enumerate(names):
            for j, f in enumerate(FORMS2):
                for v in self.values(strong):
                    s = f.format(n=n, N=n[:1].upper() + n[1:], U=n.upper(), v=v)
                    if v in ev.redact(s):
                        bad.append((i, j, len(v)))
        return bad

    def test_glued_strong_names_hide_their_value(self):
        self.assertEqual(self.check(GLUED_NAMES, True), [])

    def test_unlock_and_vault_hide_a_key_shaped_value(self):
        self.assertEqual(self.check(WEAK_NAMES, False), [])

    def test_through_the_recommender_free_text(self):
        v = J("Xk9fQ", rnd(B62, 7))
        for n in GLUED_NAMES[:5] + WEAK_NAMES:
            d = dict(running(), coverage_gaps=["the %s is %s for login" % (n, v)])
            self.assertFalse(v in probe("coverage_gaps.0", d["coverage_gaps"][0]), n[:2])

    def test_ordinary_prose_still_prints(self):
        for s in ("bypass the check", "the compass is broken", "spin up a worker", "unlock the door", "the vault is sealed",
                  "a hairpin turn ahead", "surpass the limit", "sacred ground", "trespass notice posted", "the overpass is closed",
                  "tokens used 5", "the kingpin moved"):
            self.assertEqual(ev.redact(s), s, s)

    def test_a_value_that_ends_in_a_glued_noun_is_a_value_not_more_name(self):
        """Guard found while fixing DEF-2: after a credential name, a value shaped like a glued name (a word ending in a credential
        noun) is the value and stays hidden; only bare nouns ('secret key', 'api key secret') chain into the name."""
        vals = [J("super", "secret"), J("letmein", "pass"), J("dog", "pw"), J("my", "token"), J("hunter", "pin"), J("root", "pw")]
        for i, v in enumerate(vals):
            for f in ("the password is %s", "pass %s", "my pin %s", "the %s is %s" % (J("db", "pass"), "%s"), "secret key %s"):
                self.assertFalse(v in ev.redact(f % v), (i, f[:8]))

    def test_the_value_after_an_explicit_separator_stays_hidden(self):
        v = rnd(B62, 12)
        for n in GLUED_NAMES + WEAK_NAMES:
            for s in ("%s=%s", "%s: %s", '{"%s": "%s"}', "--%s %s"):
                self.assertFalse(v in ev.redact(s % (n, v)), n[:2])


# ------------------------------------------------------------------------------------------------------------------ DEF-3
class Def3HeadTemplate(unittest.TestCase):
    """DEF-3a: `target.head` is a git object id: one-case hex; digits only at the abbreviated lengths 7-12 or as the null object id."""

    def test_all_digit_abbreviated_heads_print(self):
        for n in range(7, 13):
            for _ in range(5):
                v = rnd(DIG, n)
                self.assertIn(v, ev.show("target.head", v, "sha"), n)
        for v in ("1234567", "74551234"):
            self.assertIn(v, probe("target.head", v), v)

    def test_the_null_object_id_prints(self):
        for v in ("0" * 40, "0" * 64):
            self.assertIn(v, ev.show("target.head", v, "sha"))
            self.assertIn(v, probe("target.head", v))

    def test_the_approved_fixture_head_prints_through_the_cli(self):
        r = subprocess.run([sys.executable, "-I", RECOMMEND, "--format", "json", "--now", NOW, str(FIX / "complete_all_known.json")],
                           capture_output=True, text=True, timeout=120)
        self.assertIn("0" * 40, r.stdout)
        self.assertNotIn("[opaque head", r.stdout)

    def test_digit_runs_that_are_numbers_stay_opaque(self):
        negs = ["4111111111111111", "12345678901234567890", "9" * 40, "4" * 13, "5555555555554444", rnd(DIG, 13), rnd(DIG, 16),
                rnd(DIG, 19), rnd(DIG, 33), "1" * 40, "1" * 64, J("4111", "1" * 36), rnd(DIG, 40), rnd(DIG, 64)]
        for i, v in enumerate(negs):
            self.assertFalse(v in ev.show("target.head", v, "sha"), i)
            self.assertFalse(v in probe("target.head", v), i)

    def test_hex_heads_still_print(self):
        for v in ("a9d096aa9f8d8cc45f9398375d1593579f8565ec", "74551e2", "74551e2c1813", "d970f49c"):
            self.assertIn(v, ev.show("target.head", v, "sha"), v)


class Def3UsageEchoTempPaths(unittest.TestCase):
    """DEF-3b: an ordinary temp path (Python's own tempfile name) echoes in a usage error; credential-shaped paths stay hidden."""

    LINE = "UNREADABLE usage: recommend.py takes exactly one FILE; extra argument(s) not evaluated: %s"

    def test_random_temp_suffixes_echo(self):
        alph = "abcdefghijklmnopqrstuvwxyz0123456789_"
        bad = 0
        for _ in range(3000):
            p = "/tmp/wf3-%s/b.json" % rnd(alph, 8)
            bad += p not in ev.redact_tool(self.LINE % p)
        self.assertEqual(bad, 0)

    def test_real_mkdtemp_paths_echo(self):
        bad = 0
        made = []
        try:
            for i in range(300):
                d = tempfile.mkdtemp(prefix="wf3-" if i % 2 else "tmp")
                made.append(d)
                p = os.path.join(d, "b.json")
                bad += p not in ev.redact_tool(self.LINE % p)
        finally:
            for d in made:
                os.rmdir(d)
        self.assertEqual(bad, 0)

    def test_the_cli_names_both_absolute_temp_paths(self):
        for _ in range(30):
            with tempfile.TemporaryDirectory(prefix="wf3-") as td:
                a, b = os.path.join(td, "a.json"), os.path.join(td, "b.json")
                for p in (a, b):
                    with open(p, "w") as fh:
                        json.dump([running()], fh)
                r = subprocess.run([sys.executable, "-I", RECOMMEND, "--now", NOW, a, b], capture_output=True, text=True, timeout=120)
                self.assertEqual(r.returncode, 2)
                self.assertIn(b, r.stdout + r.stderr)

    def keyish8(self):
        classes = [B62[:26], LOWER, DIG]
        return "".join(_R.choice(classes[i % 3]) for i in range(8))

    def test_credential_shaped_paths_stay_hidden(self):
        for i in range(40):
            k8, run = self.keyish8(), rnd(B62, 40)
            lowmix = "".join(_R.choice("ghjkmnpqrstvwxyz") + _R.choice(DIG) for _ in range(4))
            cases = [("/tmp/wf3-%s/b.json" % run, run), ("/tmp/%s/b.json" % k8, k8), ("/tmp/wf3-x/%s.json" % k8, k8),
                     ("/tmp/%sabcdefgh/b.json" % k8, k8), ("/home/x/%s/b.json" % lowmix, lowmix), ("/nonexistent/%s.json" % run, run),
                     ("/tmp/%s=%s/b.json" % (J("tok", "en"), k8), k8), ("/var/tmp/%s/b.json" % k8, k8),
                     ("/tmp/%s/b.json" % lowmix, lowmix), ("/tmp/wf3-%s/b.json" % k8, k8)]  # no prefix; random part not [a-z0-9_]
            for j, (p, secret) in enumerate(cases):
                self.assertFalse(secret in ev.redact_tool(self.LINE % p), (i, j))
                self.assertFalse(secret in ev.redact("dir: %s" % p), (i, j))


class Def3SyntheticRepo(unittest.TestCase):
    def test_the_fixture_repo_prints(self):
        self.assertIn("synthetic/repo-a", ev.show("target.repo", "synthetic/repo-a"))
        self.assertIn("synthetic/repo-a", probe("target.repo", "synthetic/repo-a"))
        for v in ("%s/repo-a" % J("sun", "shine"), "synthetic/%s" % J("drag", "onfly"), "synthetic/" + rnd(B62, 12)):
            self.assertFalse(v in ev.show("target.repo", v), len(v))


# ------------------------------------------------------------------------------------------------------------------ DEF-4
class Def4DocMatchesCode(unittest.TestCase):
    def skill(self):
        with open(os.path.join(str(SKILL), "SKILL.md")) as fh:
            return fh.read()

    def test_the_key_size_is_the_code_key_size(self):
        bits = len(ev._OPQ_KEY) * 8
        found = set(int(x) for x in re.findall(r"(\d+)-bit key", self.skill()))
        self.assertEqual(found, {bits})

    def test_no_name_shape_rule_or_shape_residual_is_documented(self):
        s = self.skill()
        self.assertFalse("4-8 %" in s)
        self.assertIsNone(re.search(r"pronounceable words of 6-12 letters", s))
        self.assertTrue("never evidence" in s)

    def test_the_stated_residual_numbers_are_the_code_numbers(self):
        s = self.skill()
        m = re.search(r"closed\s+vocabulary\s+of\s+(\d+)\s+words", s)
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), len(ev._ID_WORDS))
        m = re.search(r"about\s+(\d+)\s+bits\s+when\s+drawn\s+at\s+random", s)
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), round(ev._MAX_VOCAB_WORDS * math.log2(len(ev._ID_WORDS))))


# ------------------------------------------------------------------------------------------------- retained reviewer probes
class RetainedReviewerProbes13(unittest.TestCase):
    """The reviewer's own probes of re-review 12 (tests/probes/*12.py), run against this tree. pairs12 is the 67-pair table: two pairs
    stay unmet, each as the reviewer ruled it: `free/bare` (residual a, a bare token after no credential name, accepted) and
    `host/tailnet` (the reviewer's own invented positive shape, ruled not a defect)."""

    def run_probe(self, name, *args):
        r = subprocess.run([sys.executable, os.path.join(TESTS, "probes", name), *args], capture_output=True, text=True, timeout=900)
        self.assertEqual(r.returncode, 0, name + r.stderr[-300:])
        return r.stdout

    def test_pairs12_all_but_the_ruled_pairs(self):
        out = self.run_probe("pairs12.py")
        self.assertTrue("PAIRS12 65/67" in out, [l.split()[0] for l in out.splitlines() if "<<<" in l])
        unmet = sorted(l.split()[0] for l in out.splitlines() if "<<<" in l)
        self.assertEqual(unmet, ["free/bare", "host/tailnet"])

    def test_human12_no_word_prints_in_any_field(self):
        lines = self.run_probe("human12.py").splitlines()
        fields = [l for l in lines if " prints " in l]
        self.assertEqual(len(fields), 9)
        for l in fields:
            self.assertTrue(re.search(r" prints 0/\d+: \[\]$", l) is not None, l.split()[0])  # label only: the line may hold words
        composites = [l for l in lines if " prints " not in l and l.strip()]
        self.assertEqual(len(composites), 4)
        self.assertTrue(all(l.rstrip().endswith("[]") for l in composites))

    def test_pron12_generator_words_print_only_inside_the_budget(self):
        out = self.run_probe("pron12.py")
        for l in out.splitlines():
            cells = dict(c.split("=") for c in l.split()[1:] if "=" in c)
            for shape in ("cv5(10)", "cvc3(9)", "cv3-cv3", "cv4.cv4"):
                self.assertEqual(cells[shape], "0%", (l.split()[0], shape))
            self.assertTrue(all(int(v.rstrip("%")) <= 5 for v in cells.values()), l.split()[0])

    def test_prose12_glued_names_hide_every_value(self):
        for l in self.run_probe("prose12.py").splitlines():
            vn, names = l.split(" ", 1)
            names = set(re.findall(r"'([^']+)'", names))
            allowed = {"hush", "sekrit"} | ({"auth", "key", "unlock", "vault"} if vn in ("l9", "l16", "l6") else set())
            self.assertTrue(names <= allowed, (vn, len(names - allowed)))

    def test_flake12_no_temp_path_is_hidden(self):
        out = self.run_probe("flake12.py", SCRIPTS, "5", "3000")
        self.assertTrue("rate 0/3000" in out, out.split("[")[0])

    def test_ref12_refs_are_per_process_and_per_label(self):
        lines = self.run_probe("ref12.py").splitlines()
        self.assertEqual(len(lines), 5)
        refs = [re.findall(r"\[opaque [a-z_.]+ ([0-9a-f]{8})\]", l) for l in lines]
        for r in refs:
            self.assertEqual(len(r), 3)
            self.assertEqual(r[0], r[2])
            self.assertNotEqual(r[0], r[1])
        self.assertEqual(len(set(r[0] for r in refs)), 5)


class BoundsFoundByMutants13(unittest.TestCase):
    """Edges the mutant runner (mutants13.py) found open on its first run at this repair's head."""

    def test_a_slug_never_sits_beside_a_hash_sized_id_even_where_the_template_matches(self):
        """m74: the unit template takes anything around the id, so only the slug-beside-id bound refuses a slug next to a 32-hex id."""
        hx = lambda n: J(*(_R.choice("0123456789abcdef") for _ in range(n)))
        for v, f, k in (("wm-a1303rv8-%s.service" % hx(32), "worker.unit", "ident"), ("wfr11-%s.scope" % hx(32), "worker.unit", "ident"),
                        ("/mnt/ssd/a1296p5rv5/result-%s.json" % hx(32), "result.artifact", "path")):
            self.assertFalse(v in ev.show(f, v, k), (f, len(v)))
        h = hx(32)
        self.assertIn("wm-build-%s.service" % h, ev.show("worker.unit", "wm-build-%s.service" % h))
        self.assertIn("wm-build-r7-a1303rv8-20261113.service", ev.show("worker.unit", "wm-build-r7-a1303rv8-20261113.service"))


if __name__ == "__main__":
    unittest.main()
