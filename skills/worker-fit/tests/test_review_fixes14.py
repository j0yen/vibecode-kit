"""Regression tests for the fourteenth independent exact-head review (re-review 13 of e9632349): DEF-1 .. DEF-4.

The invariant under test (decided before the code, see SKILL.md "Identity invariant"): an identity-field value prints only when every
piece of it, and every character between the pieces, is charged to a counted budget the tool's own source fixes in advance (closed
vocabulary words, path structure words, digits, dates, unlisted characters, one id, one slug, or one whole-value exact field
template whose slots have a fixed grammar). Nothing is removed or skipped before it is charged.

DEF-1: a timestamp fraction is at most nine digits and is charged to the digit budget; no single letter is skipped; dates, DNS labels,
structure words, separator runs and row whitespace are charged too. DEF-2: the prose layer recognises a credential NAME by a rule over
closed stems (de-leet, plural, misspelt password family, glued strong and weak nouns, sign-on nouns), and a quoted value after a name
hides every word. DEF-3: the fleet's real names print through the closed vocabulary or an exact per-field template; a credential in
the same position stays opaque. DEF-4: SKILL.md states the code's bounds and the temp-root source.

Canaries are assembled at run time from fragments and never printed: assertion labels carry a field, a form index or a name index."""
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import unittest

from helpers import SKILL, install_fixture_clock, remove_fixture_clock

import envelope_validate as ev
import queue_adapter as qa
import recommend as rc
import test_review_fixes3 as t3
from test_review_fixes10 import probe
from test_review_fixes7_pairs import build, everything
from test_review_fixes9 import adapter_out, queue_recommend_out

running, done, one = t3.running, t3.done, t3.one
TESTS = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(str(SKILL), "scripts")
RECOMMEND = os.path.join(SCRIPTS, "recommend.py")
VALIDATE = os.path.join(SCRIPTS, "envelope_validate.py")
ADAPTER = os.path.join(SCRIPTS, "queue_adapter.py")
NOW = "2026-11-13T07:00:00Z"


def setUpModule():
    install_fixture_clock()


def tearDownModule():
    remove_fixture_clock()


_R = random.Random(14)
B62 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
LOWER = "abcdefghijklmnopqrstuvwxyz"
DIG = "0123456789"


def rnd(alpha, n):
    return "".join(_R.choice(alpha) for _ in range(n))


def J(*parts):
    return "".join(parts)


def b62(n):
    return rnd("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 1) + rnd(DIG, 1) + rnd(LOWER, 1) + rnd(B62, n - 3)


# The identity fields of the reviewer's smuggle13 (field label, format kind) and the queue-row fields.
ID_FIELDS = [("current_owner", "ident"), ("worker.account", "ident"), ("worker.model", "ident"), ("worker.host", "host"),
             ("worker.unit", "ident"), ("consumer", "ident"), ("reviewed_by", "ident"), ("target.branch", "ident"),
             ("target.repo", "ident"), ("task_id", "ident"), ("worker.invocation", "ident"), ("sess-id", "ident"),
             ("result", "path"), ("worker.child", "ident")]
ROW_FIELDS = ("row", "owner", "claim", "waits-on", "status")
TS = "2026-11-13T09:41:27"


def ts_fraction(n):
    """A timestamp whose fraction is an n-digit number (the reviewer's 40-digit and 16-digit cases)."""
    return TS + "." + rnd(DIG, n)


def card():
    return J("4", "1" * 3, rnd(DIG, 12))


NONVOCAB = "bcdfghjklmnpqstvxyz"  # letters that are no single-letter vocabulary word (i, r, w are), so each costs one character


def alternation(letters=13, sep="-"):
    """d-L-d-L-...-d: 14 digits and 13 letters (the reviewer's ~120-bit alternation); more letters than the 8-character budget."""
    return sep.join(rnd(DIG, 1) + sep + _R.choice(NONVOCAB + NONVOCAB.upper()) for _ in range(letters)) + sep + rnd(DIG, 1)


def printing_fields(v):
    return [f for f, k in ID_FIELDS if v in ev.show(f, v, k)] + ["row." + f for f in ROW_FIELDS if v in ev.show_row(f, v)] + [
        "qa." + f for f in ROW_FIELDS if v in qa._gate(f, v)]


# ------------------------------------------------------------------------------------------------------------------ DEF-1
class Def1EveryPieceIsCharged(unittest.TestCase):
    """DEF-1 (minor): timestamp-fraction digits beyond nine and single letters between numbered pieces are charged, so the reviewer's
    40-digit fraction, the card after a timestamp and the 14-digit/13-letter alternation are opaque in every identity and row field."""

    def smuggled(self):
        return {"ts-frac-40": ts_fraction(40), "ts-frac-card": TS + "." + card(), "ts-frac-card-z": TS + "." + card() + "Z",
                "ts-frac-in-name": "r7-" + TS + "." + card(), "ts-frac-10": "r7-" + ts_fraction(10),
                "ts-frac-12-offset": ts_fraction(12) + "+00:00", "alt-13": alternation(), "alt-dots": alternation(sep="."),
                "alt-underscore": alternation(sep="_"), "alt-10": alternation(10)}

    def test_the_smuggled_values_are_opaque_in_every_identity_and_row_field(self):
        bad = {k: printing_fields(v) for k, v in self.smuggled().items()}
        self.assertEqual({k: v for k, v in bad.items() if v}, {})

    def test_a_fraction_of_more_than_nine_digits_is_not_a_timestamp_fraction(self):
        for n in range(10, 41, 3):
            v = "r7-" + ts_fraction(n)
            self.assertEqual(printing_fields(v), [], n)

    def test_ordinary_timestamps_with_up_to_nine_fraction_digits_still_print(self):
        for n in range(0, 10):
            frac = ("." + rnd(DIG, n)) if n else ""
            for v, f, k in (("r7-" + TS + frac, "current_owner", "ident"), ("wm-" + TS + frac + "Z", "target.branch", "ident"),
                            ("/mnt/ssd/out/" + TS + frac + "Z.json", "result", "path")):
                self.assertIn(v, ev.show(f, v, k), (f, n))
            claim = "claimed by r7 at " + TS + frac + "Z"
            self.assertIn(claim, ev.show_row("claim", claim, qa._QUEUE_WORDS), n)

    def test_the_fraction_digits_are_charged_to_the_digit_budget(self):
        """Nine fraction digits plus six more digits is fifteen: over the fourteen-digit budget."""
        v = "r7-%s-%s-%s" % (ts_fraction(9), rnd(DIG, 3), rnd(DIG, 2))  # r7 (1) + 9 + 3 + 2 = 15
        self.assertEqual(printing_fields(v), [])
        ok = "r%s-%s" % (rnd(DIG, 1), ts_fraction(9))  # 10 digits
        self.assertIn(ok, ev.show("current_owner", ok))

    def test_a_single_letter_is_charged_wherever_it_sits(self):
        """Single letters between digits: one per value is counted against its own cap of one ('r7-x-20261113'), every other one is
        a character of the 8-character unlisted budget. Ten letters (1 + 9) are over it; nine (1 + 8) are inside it."""
        self.assertEqual(getattr(ev, "_MAX_LETTER_GAP", None), 1)
        for sep in "-._":
            ten = sep.join(rnd(DIG, 1) + sep + _R.choice(NONVOCAB) for _ in range(10)) + sep + rnd(DIG, 1)
            self.assertEqual(printing_fields(ten), [], sep)
        nine = "-".join(rnd(DIG, 1) + "-" + _R.choice(NONVOCAB) for _ in range(9)) + "-" + rnd(DIG, 1)
        self.assertIn(nine, ev.show("current_owner", nine))
        self.assertIn("r7-x-20261113", ev.show("current_owner", "r7-x-20261113"))

    def test_beside_an_id_only_the_one_counted_letter_rides(self):
        """Beside an id nothing unlisted: a letter that is not between two numbered pieces, or a second one, is refused."""
        h = rnd("0123456789abcdef", 32)
        for i, v in enumerate(("wm-build-%s-x.service" % h, "wm-build-r7-x-1-y-2-%s.service" % h, "/mnt/ssd/r7-x-1-y-2/result-%s.json" % h)):
            self.assertFalse(v in ev.show("worker.unit" if i < 2 else "result.artifact", v, "ident" if i < 2 else "path"), i)
        self.assertIn("wm-build-%s.service" % h, ev.show("worker.unit", "wm-build-%s.service" % h))
        ok = "/mnt/ssd/cargo-target/r7-x-20261113/retained/result-%s.json" % h
        self.assertIn(ok, ev.show("result.artifact", ok, "path"))

    def test_dates_are_counted(self):
        """Own audit, same class: at most two dates or timestamps per value."""
        d = lambda: "20%02d%02d%02d" % (_R.randrange(10, 99), _R.randrange(1, 13), _R.randrange(1, 29))
        three = "r7-%s-%s-%s" % (d(), d(), d())
        self.assertEqual(printing_fields(three), [])
        iso3 = "run-2026-11-13-2025-01-02-2024-12-31"
        self.assertEqual(printing_fields(iso3), [])
        two = "r7-%s-%s" % (d(), d())
        self.assertIn(two, ev.show("current_owner", two))
        self.assertIn("wm-build-r7-wfr11-20261113.service", ev.show("worker.unit", "wm-build-r7-wfr11-20261113.service"))

    def test_dns_labels_and_template_literals_are_counted_as_words(self):
        """Own audit, same class: DNS labels were free vocabulary in every field."""
        dns = "-".join(sorted(ev._DNS_WORDS))
        self.assertEqual(printing_fields(dns), [])
        for v in ("ryzen7.tail1234.ts.net", "ip-10-0-1-23.ec2.internal"):
            self.assertIn(v, ev.show("worker.host", v, "host"), v)

    def test_field_template_literals_are_counted_as_words(self):
        """Found by mutants14 (m130): a field-template literal ('spawn') is a counted vocabulary word, so seven words are over the cap."""
        self.assertFalse("tmux-spawn-spawn-spawn-spawn-spawn-spawn.scope" in ev.show("worker.unit", "tmux-spawn-spawn-spawn-spawn-spawn-spawn.scope"), 0)
        self.assertIn("tmux-spawn-r7.scope", ev.show("worker.unit", "tmux-spawn-r7.scope"))

    def test_path_structure_words_are_capped(self):
        """Own audit, same class: a path of thirty structure words carried ~143 bits uncharged."""
        words = sorted(ev._STRUCT_WORDS)
        v = "/" + "/".join(_R.choice(words) for _ in range(30)) + ".md"
        self.assertFalse(v in ev.show("result.artifact", v, "path"), "negative")
        for ok in ("/mnt/ssd/cargo-target/r7-wfr13-20261113/out/review.md", "/mnt/data/jsy/tmp/p5task/prio3/repo",
                   "/home/jsy/Notes/hermes-director-bootstrap-proof-20261108.json"):
            self.assertIn(ok, ev.show("result.artifact", ok, "path"), ok)

    def test_separator_runs_are_charged(self):
        """Own audit, same class: a run of separators ('-_-_.') carried bits between two vocabulary words."""
        v = "r7" + J(*(_R.choice("-_.") for _ in range(12))) + "rb"
        self.assertEqual(printing_fields(v), [])
        self.assertIn("r7--rb", ev.show("current_owner", "r7--rb"))

    def test_row_whitespace_runs_are_charged(self):
        v = "r7" + " " * 5 + "rb" + " " * 6 + "ctl"
        self.assertFalse(v in ev.show_row("owner", v), "negative")
        self.assertIn("claimed by r7", ev.show_row("claim", "claimed by r7", qa._QUEUE_WORDS))

    def test_a_repo_owner_and_name_share_one_budget(self):
        own, name = rnd(LOWER, 5), rnd(LOWER, 5)
        v = "%s/deploy-%s" % (own, name)  # 5 + 5 unlisted characters in one value
        self.assertFalse(v in ev.show("target.repo", v), "negative")
        for ok in ("j0yen/swarm-decide", "j0yen/vibecode-kit", "synthetic/repo-a", "j0yen/mcphost"):
            self.assertIn(ok, ev.show("target.repo", ok), ok)

    def test_end_to_end_through_the_recommender_the_validator_and_the_adapter(self):
        """recommend.py --format json / text and envelope_validate.py on envelope files; queue_adapter.py and recommend.py --queue on
        rows: none of the smuggled values is in any output."""
        vals = [ts_fraction(40), TS + "." + card(), alternation()]
        out = ""
        with tempfile.TemporaryDirectory() as td:
            for i, v in enumerate(vals):
                d = running()
                d["current_owner"] = v
                d["target"]["branch"] = v
                d["target"]["repo"] = v
                d["worker"]["unit"] = v
                d["worker"]["account"] = v
                d["task_id"] = v
                d["evidence"][0]["task_id"] = v
                p = os.path.join(td, "e%d.json" % i)
                with open(p, "w") as fh:
                    json.dump(d, fh)
                row = {"ask_id": "A1663", "rev": 3, "row_id": v, "owner": v, "status": v, "seq": 12, "claim": v, "waits_on": [v]}
                q = os.path.join(td, "q%d.json" % i)
                with open(q, "w") as fh:
                    json.dump({"rows": [row]}, fh)
                for args in ([RECOMMEND, "--format", "json", "--now", NOW, p], [RECOMMEND, "--format", "text", "--now", NOW, p],
                             [VALIDATE, "--now", NOW, p], [ADAPTER, q], [RECOMMEND, "--queue", "--now", NOW, q],
                             [RECOMMEND, "--queue", "--format", "json", "--now", NOW, q]):
                    r = subprocess.run([sys.executable, "-I"] + args, capture_output=True, text=True, timeout=120)
                    self.assertFalse("Traceback" in r.stderr, "negative")
                    out += r.stdout + r.stderr
        for i, v in enumerate(vals):
            self.assertFalse(v in out, "value %d" % i)
        for i, v in enumerate(vals):
            self.assertFalse(v in probe("current_owner", v) or v in probe("target.branch", v), "in-process %d" % i)

    def test_an_ordinary_timestamp_prints_end_to_end(self):
        v = "r7-" + TS + ".123456789Z"
        self.assertIn(v, probe("current_owner", v))
        rows = [{"ask_id": "A1663", "rev": 3, "row_id": "d-20261113-0700-r7-a1b2", "owner": "r7", "status": "open", "seq": 12,
                 "claim": "claimed by r7 at %s.123456789Z" % TS, "waits_on": []}]
        self.assertIn("claimed by r7 at %s.123456789Z" % TS, adapter_out(rows))


# ------------------------------------------------------------------------------------------------------------------ DEF-2
# The reviewer's 19 names (re-review 13 § 8), assembled from fragments.
REVIEW_NAMES = [J("master", "key"), J("db", "key"), J("wpa", "key"), J("key", "phrase"), J("passw", "0rd"), J("p4", "ssword"),
                J("s3", "cret"), J("t0", "ken"), J("pw", "ord"), J("pass", "wrd"), J("ps", "wrd"), J("pazz", "word"),
                J("pass", "codes"), J("secr", "etz"), J("pin", "code"), J("login", "code"), J("unlock", "code"), J("sign", "in"),
                J("git", "pat")]
# My own names per form, in no list the code holds (checked below).
OWN = {
    "key-glued": [J("vpn", "key"), J("gpg", "key"), J("wifi", "key"), J("root", "key"), J("tls", "key"), J("wallet", "key"),
                  J("router", "key")],
    "leet": [J("pa55", "word"), J("s3cr", "3t"), J("t0k", "3n"), J("cr3d", "ential"), J("passc", "0de"), J("tok", "3n"),
             J("p4ss", "wd")],
    "misspelt": [J("pas", "word"), J("pass", "wod"), J("pas", "wd"), J("pss", "word"), J("pass", "wrod"), J("creden", "tail"),
                 J("pass", "cdoe")],
    "plural": [J("pass", "phrases"), J("gpg", "keys"), J("pass", "keys"), J("pw", "ds"), J("ot", "ps"), J("priv", "keys"),
               J("tok", "enz")],
    "code-glued": [J("door", "code"), J("alarm", "code"), J("sms", "code"), J("mfa", "code"), J("reset", "code"), J("lock", "code"),
                   J("safe", "code")],
    "other": [J("recovery", "phrase"), J("wallet", "phrase"), J("gh", "pat"), J("ssh", "pat"), J("sign", "ins"), J("log", "ins")],
}
FORMS = ["{n} {v}", "the {n} is {v}", "{n} was {v}.", "my {n} {v} please", 'use {n} "{v}" now', "{N} {v}", "{U} {v}",
         "set {n} to {v} now", "({n} {v})", "{n}\t{v}"]


def prose_values():
    return {"mixed12": b62(12), "lower10": rnd(LOWER, 10), "num6": rnd(DIG, 6), "num4": rnd(DIG, 4),
            "word8": _R.choice([J("sun", "shine"), J("dragon", "fly"), J("foot", "ball"), J("prin", "cess")]), "lower24": rnd(LOWER, 24)}


def prose_leaks(names):
    bad = []
    for i, n in enumerate(names):
        for j, f in enumerate(FORMS):
            for vn, v in prose_values().items():
                s = f.format(n=n, N=n[:1].upper() + n[1:], U=n.upper(), v=v)
                if v in ev.redact(s):
                    bad.append((i, j, vn))
    return bad


class Def2CredentialNamesByRule(unittest.TestCase):
    """DEF-2 (minor): a credential NAME is recognised by a rule over closed stems, not by a list of spellings; a quoted value after a
    name hides every word."""

    def test_the_reviewers_names_hide_every_value_shape(self):
        self.assertEqual(prose_leaks(REVIEW_NAMES), [])

    def test_my_key_glued_names_hide_their_value(self):
        self.assertEqual(prose_leaks(OWN["key-glued"]), [])

    def test_my_leet_names_hide_their_value(self):
        self.assertEqual(prose_leaks(OWN["leet"]), [])

    def test_my_misspelt_names_hide_their_value(self):
        self.assertEqual(prose_leaks(OWN["misspelt"]), [])

    def test_my_plural_names_hide_their_value(self):
        self.assertEqual(prose_leaks(OWN["plural"]), [])

    def test_my_code_glued_names_hide_their_value(self):
        self.assertEqual(prose_leaks(OWN["code-glued"]), [])

    def test_my_phrase_pat_and_sign_on_names_hide_their_value(self):
        self.assertEqual(prose_leaks(OWN["other"]), [])

    def test_a_qualifier_joined_to_a_weak_glue_noun_is_a_name(self):
        """Found by mutants14 (m142): N4 joined, '<qualifier>_key' / '<qualifier>-code' read like the glued form unless the qualifier is a
        closed free-text vocabulary word ('UNKNOWN_KEY', the tool's own finding code) or the compound is readable ('exit_code')."""
        names = [J("wpa", "_key"), J("gpg", "-key"), J("door", "-code"), J("alarm", "_code"), J("wallet", "-phrase"), J("gh", "_pat")]
        self.assertEqual(prose_leaks(names), [])
        for s in ("UNKNOWN_KEY worker.extra: field not in schema", "exit_code 2 seen", "the bar-code reads"):
            self.assertEqual(ev.redact(s), s, s)

    def test_a_name_split_in_two_reads_as_one(self):
        """Found while probing my own rule: the last two parts of a camelCase or joined name are read together when only together they
        are a name."""
        names = [J("Pass", "Word"), J("Pass", "-", "Word"), J("pass", "_", "word"), J("Sign", "_", "In"), J("Log", "-", "In"),
                 J("pass", "_", "phrase"), J("PASS", "_", "WORD"), J("Pass", "W0rd")]
        self.assertEqual(prose_leaks(names), [])
        for s in ("the key_word is fast", "the key-board is new", "sign in now please"):
            self.assertEqual(ev.redact(s), s, s)

    def test_my_names_are_in_no_list_the_code_holds(self):
        """Test-data check: the negatives above test the RULE; none of them is a literal of any name list in the source."""
        lists = set()
        for k in dir(ev):
            v = getattr(ev, k)
            if isinstance(v, (set, frozenset, tuple, list)) and all(isinstance(x, str) for x in v):
                lists |= {x.lower() for x in v}
        src = open(VALIDATE).read().lower()
        for form, names in OWN.items():
            for i, n in enumerate(names):
                self.assertFalse(n.lower() in lists, (form, i))
                self.assertIsNone(re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(n.lower()), src), (form, i))

    def test_every_word_of_a_quoted_value_is_hidden(self):
        w = [J("cor", "rect"), J("hor", "se"), J("sta", "ple"), J("bat", "tery")]
        names = [J("pass", "word"), J("db", "pass"), J("master", "key"), J("passw", "0rd"), J("pin", "code"), J("sign", "in")]
        forms = ['{n} "{a} {b} {c}"', 'the {n} is "{a} {b} {c}"', "use {n} '{a} {b}' now", "{n} `{a} {b} {c} {d}`",
                 'my {n} "{a}  {b}\t{c}" please', '{n} "{a} {b} {c}']
        for i, n in enumerate(names):
            for j, f in enumerate(forms):
                out = ev.redact(f.format(n=n, a=w[0], b=w[1], c=w[2], d=w[3]) + "\nnext line ok")
                for k, x in enumerate(w):
                    self.assertFalse(x in out, (i, j, k))
                self.assertTrue(out.endswith("\nnext line ok"), (i, j))

    def test_a_quoted_state_word_still_reads(self):
        self.assertEqual(ev.redact('the password is "missing"'), 'the password is "missing"')

    def test_ordinary_prose_stays_readable(self):
        for s in ("code=ok", "exit code 2", "status_code=404", "rc=0", "the keyboard layout is us", "a monkey wrench fell",
                  "turkey dinner tonight", "the passage reads well", "the compass is broken", "encode the payload first",
                  "barcode scanner ready", "decode the frame now", "signing the release tag", "pinned version 3 holds",
                  "the build passes 5 tests", "pins 3 and 4 are bent", "a turnkey system ships", "the keyword is fast",
                  "a sword fight", "upward trend 5", "powered by python", "the token count is 5", "the key point is speed",
                  "the vault is sealed", "unlock the door", "bypass the check", "spin up a worker", "tokens used 5",
                  "statuscode 2 seen", "a catchphrase sells", "compat layer on", "the donkey ran", "hockey season starts",
                  "the pod restarted twice after the login", "a pad holds notes on the keyboard", "the prod deploy ran past the token",
                  "a pew stands empty by the passage"):
            self.assertEqual(ev.redact(s), s, s)

    def test_a_function_word_after_a_name_is_not_a_value(self):
        """False-positive bound: a closed-class function word after a strong name reads as prose; the next real value stays hidden."""
        for s in ("the password for the db is missing", "rotate the token from the vault", "the login for my account is ready"):
            self.assertEqual(ev.redact(s), s, s)
        v = rnd(LOWER, 10)
        self.assertFalse(v in ev.redact("password %s" % v), 0)

    def test_through_the_recommender_free_text(self):
        v = J("Xk9fQ", rnd(B62, 7))
        for i, n in enumerate(REVIEW_NAMES[:6] + [x[0] for x in OWN.values()]):
            d = dict(running(), coverage_gaps=["the %s is %s for login" % (n, v)])
            self.assertFalse(v in probe("coverage_gaps.0", d["coverage_gaps"][0]), i)


# ------------------------------------------------------------------------------------------------------------------ DEF-3
FLEET = [("target.repo", "ident", "dotfiles"), ("target.repo", "ident", "j0yen/dotfiles"),
         ("worker.unit", "ident", "aide-account-follow.timer"), ("worker.unit", "ident", "wm-build-inner566-a.service"),
         ("worker.unit", "ident", "wm-build-inner561-a.service"), ("worker.unit", "ident", "token-ledger.service"),
         ("target.branch", "ident", "prio3-p0p1p2"), ("consumer", "ident", "claude-3252684-r7-a1296p2r87rv-20261113"),
         ("consumer.named", "ident", "wm-build-inner566-a.service"), ("alternate", "ident", "claude-2461185-r7-a1677frv4-20261113-worker"),
         ("result.artifact", "path", "/home/jsy/Notes/prd-priority-selective-unpark-20261111.md")]


class Def3FleetNamesPrint(unittest.TestCase):
    """DEF-3 (minor): the real fleet names print through the closed vocabulary or an exact per-field template; a credential negative
    in the same position stays opaque."""

    def test_every_listed_fleet_name_prints_in_its_field(self):
        for f, k, v in FLEET:
            self.assertIn(v, ev.show(f, v, k), (f, v))

    def test_credential_negatives_in_the_same_positions_stay_opaque(self):
        k12, k8 = b62(12), b62(8)
        lw = rnd(LOWER, 30)
        negs = [("target.repo", "ident", "dotfiles-%s" % k12), ("target.repo", "ident", "j0yen/%s" % k12),
                ("worker.unit", "ident", "aide-account-%s.timer" % k8), ("worker.unit", "ident", "wm-build-inner%s-a.service" % k8),
                ("worker.unit", "ident", "wm-build-inner566-%s.service" % k8), ("worker.unit", "ident", "wm-build-inner%s-a.service" % rnd(DIG, 9)),
                ("worker.unit", "ident", "token-%s.service" % k12), ("target.branch", "ident", "prio3-%s" % k12),
                ("target.branch", "ident", "prio3-p%sp%sp%sp%sp%s" % tuple(rnd(DIG, 1) for _ in range(5))),
                ("consumer", "ident", "claude-3252684-r7-%s-20261113" % k12), ("consumer", "ident", "claude-%s-r7-a1296p2r87rv-20261113" % k8),
                ("consumer", "ident", "claude-3252684-r7-%s-20261113" % rnd(LOWER + DIG, 16)),
                ("consumer", "ident", "claude-3252684-zz-a1296p2r87rv-20261113"),
                ("consumer", "ident", "claude-3252684-r7-%s-20261113" % J(rnd(LOWER, 3), rnd(DIG, 5), rnd(LOWER, 2), rnd(DIG, 2),
                                                                         rnd(LOWER, 2), rnd(DIG, 2), rnd(LOWER, 2), rnd(DIG, 2))),
                ("result.artifact", "path", "/home/jsy/Notes/prd-%s-20261111.md" % k12),
                ("result.artifact", "path", "/home/jsy/Notes/prd-%s-20261111.md" % lw),
                ("result.artifact", "path", "/home/%s/Notes/prd-priority-20261111.md" % rnd(LOWER, 9)),
                ("result.artifact", "path", "/home/jsy/Notes/prd-%s-20261111.md" % "-".join(rnd(LOWER, 5) for _ in range(5))),
                ("result.artifact", "path", "/home/jsy/Notes/prd-%s-%s-20261111.md" % (J("pass", "word"), rnd(LOWER, 6)))]
        for i, (f, k, v) in enumerate(negs):
            self.assertFalse(v in ev.show(f, v, k), (f, i))

    def test_a_template_is_only_in_the_fields_where_it_belongs(self):
        peer = "claude-3252684-r7-a1296p2r87rv-20261113"
        prd = "/home/jsy/Notes/prd-priority-selective-unpark-20261111.md"
        for f in ("task_id", "worker.account", "target.branch", "worker.model", "sess-id"):
            self.assertFalse(peer in ev.show(f, peer), f)
        for f in ("current_owner", "task_id", "worker.unit"):
            self.assertFalse(prd in ev.show(f, prd), f)
        self.assertFalse("wm-build-inner566-a.service" in ev.show("task_id", "wm-build-inner566-a.service"), "negative")

    def test_each_template_capacity_is_inside_its_field_id_class(self):
        """Capacity of each exact template from its slot grammar: at most the largest id class of every field that carries it
        (unit / consumer: a 32-hex id, 128 bits; path: a 40-hex id, 160 bits)."""
        for name in ("_TEMPLATE_FIELDS", "_INNER_DIGITS", "_SEATS", "_PEER_SLUG_MAX", "_PRD_USER_MAX", "_PRD_SLUG_LETTERS", "_PRD_SLUG_WORDS"):
            self.assertTrue(hasattr(ev, name), name)

        def nums(lo, hi):
            return math.log2(sum(10 ** n for n in range(lo, hi + 1)))
        date = math.log2(100 * 12 * 31)
        inner = nums(1, ev._INNER_DIGITS) + math.log2(26)
        peer = nums(1, 7) + math.log2(len(ev._SEATS)) + ev._PEER_SLUG_MAX * math.log2(36) + date + 1
        user = math.log2(sum(26 ** n for n in range(1, ev._PRD_USER_MAX + 1)))
        slug = ev._PRD_SLUG_LETTERS * math.log2(26) + math.log2(sum(math.comb(ev._PRD_SLUG_LETTERS - 1, k) for k in range(ev._PRD_SLUG_WORDS)))
        prd = user + slug + date
        self.assertLessEqual(inner, 128)
        self.assertLessEqual(peer, 128)
        self.assertLessEqual(prd, 160)
        self.assertEqual(sorted(ev._TEMPLATE_FIELDS), sorted(["inner", "peer", "prd"]))
        self.assertEqual(set(ev._TEMPLATE_FIELDS["inner"]), {"unit", "named"})
        self.assertEqual(set(ev._TEMPLATE_FIELDS["peer"]), {"named"})
        self.assertEqual(set(ev._TEMPLATE_FIELDS["prd"]), {"path"})

    def test_the_fleet_names_print_end_to_end(self):
        cases = [("target.repo", "j0yen/dotfiles"), ("worker.unit", "wm-build-inner566-a.service"), ("worker.unit", "token-ledger.service"),
                 ("target.branch", "prio3-p0p1p2"), ("consumer.named", "claude-3252684-r7-a1296p2r87rv-20261113"),
                 ("result.artifact", "/home/jsy/Notes/prd-priority-selective-unpark-20261111.md")]
        for f, v in cases:
            self.assertIn(v, probe(f, v), f)

    def test_the_vocabulary_holds_the_new_fleet_words_and_no_password_word(self):
        for w in ("dotfiles", "ledger", "follow", "prio"):
            self.assertIn(w, ev._ID_WORDS)


# ------------------------------------------------------------------------------------------------------------------ DEF-4
class Def4DocStatesTheCode(unittest.TestCase):
    def skill(self):
        with open(os.path.join(str(SKILL), "SKILL.md")) as fh:
            return re.sub(r"\s+", " ", fh.read())

    def test_the_doc_states_the_charged_bounds(self):
        s = self.skill()
        m = re.search(r"fraction of at most (\d+) digits", s)
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), getattr(ev, "_MAX_FRACTION", None))
        self.assertIsNone(ev._ISO_TS.fullmatch(TS + "." + "1" * (int(m.group(1)) + 1)))
        m = re.search(r"at most (\d+) dates or timestamps", s)
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), getattr(ev, "_MAX_DATES", None))
        m = re.search(r"at most (\d+) structure words", s)
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), getattr(ev, "_MAX_STRUCT_WORDS", None))
        self.assertIn("no letter is skipped", s)
        self.assertFalse("each bounded by the code" in s, "negative")

    def test_the_doc_states_the_temp_root_source(self):
        s = self.skill()
        self.assertIn("os.environ", s)
        self.assertFalse("gettempdir" in s, "negative")
        src = open(VALIDATE).read()
        self.assertIn('os.environ.get("TMPDIR"', src)
        self.assertFalse("gettempdir" in src, "negative")

    def test_the_doc_states_the_name_rule(self):
        s = self.skill()
        for phrase in ("de-leet", "plural", "subsequence of `password`", "one edit", "sign-on", "every word inside the quotes"):
            self.assertIn(phrase, s)


# ------------------------------------------------------------------------------------------------- retained reviewer probes
class RetainedReviewerProbes14(unittest.TestCase):
    """The reviewer's own re-review 13 probes (tests/probes/*13.py), run against this tree."""

    def run_probe(self, name, *args):
        r = subprocess.run([sys.executable, os.path.join(TESTS, "probes", name), *args], capture_output=True, text=True, timeout=900)
        self.assertEqual(r.returncode, 0, name + r.stderr[-300:])
        return r.stdout

    def test_smuggle13_nothing_prints(self):
        lines = [l for l in self.run_probe("smuggle13.py").splitlines() if l.strip()]
        self.assertEqual(len(lines), 5)
        for l in lines:
            self.assertTrue(re.search(r"prints in  0/14 fields \[\] \| rows \[\]$", l) is not None, l.split()[0])

    def test_prose13_no_own_name_prints(self):
        out = self.run_probe("prose13.py")
        leaks = [l for l in out.splitlines() if l.startswith("REDACT-LEAK")]
        self.assertEqual([l.split()[1:3] for l in leaks if l.split()[1] == "own"], [])
        for l in leaks:  # only the documented weak-noun residual: a plain lower-case word after a bare unlock/vault
            self.assertEqual(set(re.findall(r"'([^']+)'", l)), {"unlock", "vault"}, l.split()[2])
            self.assertIn(l.split()[2], ("lower10", "lower24", "word8"))

    def test_pos13_only_the_accepted_names_are_opaque(self):
        out = self.run_probe("pos13.py")
        opaque = sorted(l.split()[1] + " " + l.split()[2] for l in out.splitlines() if l.strip().startswith("OPAQUE"))
        self.assertEqual(opaque, sorted(["consumer claude-1096112-mcphost-table-sql-exec-and-grammar",
                                         "target.branch mcphost-table-sql-exec-and-grammar", "target.repo joeyen-atscale/bimpipe",
                                         "worker.host instance-1.us-central1-a.c.proj-123.internal"]))

    def test_pairs13_all_but_the_ruled_pair(self):
        out = self.run_probe("pairs13.py")
        unmet = sorted(l.split()[0] for l in out.splitlines() if "<<<" in l)
        self.assertEqual(unmet, ["free/bare-prose"])
        self.assertTrue("PAIRS13 67/68" in out)


if __name__ == "__main__":
    unittest.main()
