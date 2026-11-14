"""Regression tests for the fifteenth independent exact-head review (re-review 14 of bffbfc29): DEF-A .. DEF-H, in that order, and
the review's unconfirmed concerns.

The invariant under test (decided before the code, see SKILL.md "Identity invariant"): a value prints only through the ONE trust gate:
the field's grammar AND every piece of the value, and every character between the pieces, charged to a counted budget after NFKC and
with ASCII-only digit classes, inside one bit budget per value; a placeholder prints as the canonical word UNKNOWN; no marker the
tool uses inside (the charged-piece sentinel, an opaque ref, an identity or hold mark) can be supplied by the input. In free text a
credential label is read through its decoration (punctuation, a bracketed group, format characters), and the credential-name rule
reads more spellings (full de-leet, edits from every closed stem of five letters or more, closed abbreviation and non-English sets,
value-tail and weak-after-strong compounds, every quote pair).

Canaries are assembled at run time from fragments and never printed: every assertion is assertTrue/assertFalse/assertEqual on a
boolean or a count, and its label carries a field, a form index or a name index, never a value."""
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import unicodedata
import unittest

from helpers import SKILL, install_fixture_clock, remove_fixture_clock

import envelope_validate as ev
import queue_adapter as qa
import recommend as rc
import test_review_fixes3 as t3
from test_review_fixes7 import setp
from test_review_fixes10 import probe
from test_review_fixes7_pairs import everything
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


_R = random.Random(15)
LOWER = "abcdefghijklmnopqrstuvwxyz"
UPPER = LOWER.upper()
DIG = "0123456789"
B62 = UPPER + LOWER + DIG


def rnd(alpha, n):
    return "".join(_R.choice(alpha) for _ in range(n))


def J(*parts):
    return "".join(parts)


def key12():
    """a 12-character mixed key (one of each class first)"""
    return rnd(UPPER, 1) + rnd(DIG, 1) + rnd(LOWER, 1) + rnd(B62, 9)


def word10():
    return rnd(LOWER, 10)


def pin6():
    return rnd("123456789", 1) + rnd(DIG, 5)


def cli(args, env_obj=None, rows=None):
    """stdout+stderr of a script run on a temp file holding the envelope set (or the queue rows)"""
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with open(p, "w") as fh:
            json.dump(rows if rows is not None else {"envelopes": [env_obj]}, fh)
        r = subprocess.run([sys.executable, "-B"] + [a if a != "{}" else p for a in args], capture_output=True, text=True, timeout=300)
        return r.stdout + r.stderr
    finally:
        os.unlink(p)


def cli_all(d):
    return (cli([RECOMMEND, "--now", NOW, "{}"], d) + cli([RECOMMEND, "--now", NOW, "--format", "json", "{}"], d)
            + cli([VALIDATE, "--now", NOW, "{}"], d))


# ------------------------------------------------------------------------------------------------------------------ DEF-A
# re-review 14 probes/own/punct14.py: the 14 forms (12 credential labels with punctuation or a format character before the
# separator, 2 controls under a non-credential name whose value is key-shaped).
PUNCT14 = ['"password!": "%s"', '"password?": "%s"', '{"password!": ["%s"]}', 'password!=%s', 'password! %s', '"api key!": "%s"',
           '"token#": "%s"', '"secret*": "%s"', "password​: %s", "pass​word: %s", "pass⁠word=%s", "\"pass‍word\": \"%s\"",
           '"foo!": "%s"', "foo​=%s"]
# re-review 14 § 9 (the label list) and my own (the last 16): every one is a credential label, every value hides
LABELS = ["Password*: %s", "API key*: %s", "Secret**: %s", "*password*: %s", "Password (required): %s", "[password]: %s", "(token): %s",
          "PIN#: %s", "pass*=%s", "password - %s", '"password!": "%s"', "password​: %s",
          # own forms
          "Token (rotated monthly) = %s", "<password>: %s", "{secret}: %s", "password⁠: %s", "pass­word: %s",
          "pass‌word = %s", "token﻿: %s", "password?: %s", "password!!: %s", "password~: %s", "password†: %s",
          "api_key [prod]: %s", "Passwort (neu): %s", "password – %s", "password — %s", "Password*  %s", "PIN #: %s",
          "the secret (do not share): %s"]
SEP_LABELS = [f for f in LABELS if re.search(r"[:=]\s*%s$", f)]


class DefACredentialLabelDecoration(unittest.TestCase):
    """DEF-A (major): a value after a credential label written with punctuation, brackets, a parenthetical or a format character before
    its separator is hidden exactly as after `<name>:`, in redact() and end to end; ordinary punctuated prose stays readable."""

    def test_the_reviewer_punct14_forms_hide_the_value_in_redact_and_redact_tool(self):
        for i, f in enumerate(PUNCT14):
            v = key12()
            self.assertFalse(v in ev.redact(f % v), "redact form %d" % i)
            self.assertFalse(v in ev.redact_tool(f % v), "redact_tool form %d" % i)  # bare prose too: redact_tool runs the prose layer

    def test_bare_prose_credential_names_hide_in_redact_tool(self):
        # a tool line can echo operator text (argv); a bare prose credential name with or without decoration hides its value there
        for n in ("pass" + "word", "secret", "API key", "pass" + "phrase"):
            for mid in (" ", "! ", "* ", " - ", " \u2013 ", "?? "):
                for mk in (key12, word10):
                    v = mk()
                    self.assertFalse(v in ev.redact_tool(n + mid + v), (n[:2], mid))
        for s in ("UNREADABLE usage: unknown option --verbose", "the password is required", "token missing for row A1663"):
            self.assertTrue(ev.redact_tool(s) == s)

    def test_every_label_form_hides_every_value_shape(self):
        for i, f in enumerate(LABELS):
            for shape, mk in (("key12", key12), ("word10", word10), ("pin6", pin6)):
                v = mk()
                self.assertFalse(v in ev.redact(f % v), "form %d %s" % (i, shape))

    def test_separator_label_forms_hide_in_the_credential_layers_too(self):
        for i, f in enumerate(SEP_LABELS):
            for shape, mk in (("key12", key12), ("word10", word10), ("pin6", pin6)):
                v = mk()
                self.assertFalse(v in ev.redact_tool(f % v), "form %d %s" % (i, shape))
                self.assertFalse(v in ev.redact_credentials(f % v), "form %d %s" % (i, shape))

    def test_the_plain_name_form_stays_hidden(self):
        for n in ("password", "API key", "secret", "PIN", "token"):
            for mk in (key12, word10, pin6):
                v = mk()
                self.assertFalse(v in ev.redact("%s: %s" % (n, v)), n)

    def test_ordinary_punctuated_prose_stays_readable(self):
        prose = ["Wow! This works.", "See section 3 (below).", "What? No!", "ratio 3:4 holds", "f(x) = y", "Done (3 of 4).",
                 "the build passed!", "Is the queue empty?", "items: 3", "step 2 (of 5): done", "the run [rb] is green",
                 "note* see the docs", "exit code 2 means a usage error", "code=ok", "status_code=404", "rc=0"]
        for i, p in enumerate(prose):
            self.assertTrue(ev.redact(p) == p, i)

    def test_end_to_end_in_coverage_gaps_and_prose_evidence_refs(self):
        texts = ["login notes: Password*: %s (rotate monthly)", "creds in the wiki, API key*: %s", "[password]: %s", "Password (required): %s",
                 "PIN#: %s", 'config {"password!": "%s"} was used', "password​: %s", "Token (rotated monthly) = %s", "{secret}: %s"]
        for i, t in enumerate(texts):
            for mk in (key12, pin6):
                v = mk()
                for where in ("coverage_gaps.0", "evidence.0.ref"):
                    self.assertFalse(v in probe(where, t % v), "text %d %s" % (i, where))

    def test_end_to_end_through_the_cli_text_json_and_validator(self):
        for i, t in enumerate(["Password*: %s", "PIN#: %s", "pass​word: %s", "Password (required): %s"]):
            v = key12() if i != 1 else pin6()
            d = dict(running(), coverage_gaps=[t % v])
            self.assertFalse(v in cli_all(d), "gap %d" % i)
            d = running()
            d["evidence"][0]["ref"] = t % v
            self.assertFalse(v in cli_all(d), "ref %d" % i)


# ------------------------------------------------------------------------------------------------------------------ DEF-B
def placeholder_values():
    card = "4" + rnd(DIG, 15)
    syms = [c for c in map(chr, list(range(0x2190, 0x2400)) + list(range(0x2500, 0x2800))) if not c.isalnum()]
    return [("unknown 16", "unknown " + card, card), ("unknown: 40", "unknown:" + rnd(DIG, 40), None),
            ("N/A 6", "N/A " + rnd(DIG, 6), None), ("tbd 4-4-4-4", "tbd-" + "-".join(card[i:i + 4] for i in range(0, 16, 4)), card[4:8]),
            ("pending 20", "pending " + rnd(DIG, 20) + " (not yet known)", None), ("unknown # 30", "unknown #" + rnd(DIG, 30), None),
            ("symbols", "".join(_R.choice(syms) for _ in range(40)), None), ("punct", "".join(_R.choice("!#$%^&*()[]{}<>?|~-_=+") for _ in range(24)), None)]


def payload(v, marker):
    """the material that must not print: the explicit marker, else the longest digit run, else the whole value"""
    if marker:
        return marker
    runs = re.findall(r"\d+", v)
    return max(runs, key=len) if runs else v


B_FIELDS = [("current_owner", "ident"), ("worker.account", "ident"), ("worker.unit", "ident"), ("consumer", "ident"), ("task_id", "ident"),
            ("target.repo", "ident"), ("worker.host", "host"), ("result", "path"), ("evidence-ref", "path"), ("target.head", "sha"),
            ("worker.model", "ident"), ("sess-id", "ident"), ("reviewed_by", "ident"), ("target.branch", "ident")]
ROW_FIELDS = ("row", "owner", "claim", "waits-on", "status", "seq")


class DefBPlaceholderIsCanonicalUnknown(unittest.TestCase):
    """DEF-B (minor): a value the placeholder test accepts prints as the canonical word UNKNOWN in every identity and queue-row field,
    never its digits, punctuation or symbols; UNKNOWN stays UNKNOWN."""

    def test_every_identity_field_prints_canonical_unknown(self):
        for name, v, m in placeholder_values():
            self.assertTrue(ev.is_unknown(v), name)
            for f, k in B_FIELDS:
                self.assertTrue(ev.unmark(ev.show(f, v, k)) == ev.UNKNOWN, (name, f))
            self.assertTrue(ev.unmark(ev.show_ref("evidence-ref", v)) == ev.UNKNOWN, name)

    def test_every_row_field_prints_canonical_unknown(self):
        for name, v, m in placeholder_values():
            for f in ROW_FIELDS:
                self.assertTrue(ev.show_row(f, v) == ev.UNKNOWN, (name, f))
                self.assertTrue(qa._gate(f, v) == ev.UNKNOWN, (name, f))

    def test_canonical_placeholders_still_read_as_unknown(self):
        """A value that is exactly one word of the closed placeholder set in a canonical case prints as given (bounded, ~7 bits);
        any other placeholder-shaped value prints UNKNOWN."""
        for v in ("UNKNOWN", "unknown", "n/a", "N/A", "TBD", "-", "?", "none"):
            self.assertTrue(ev.show("current_owner", v) == v, v)
            self.assertTrue(ev.show_row("owner", v) == v, v)
        for v in ("UnKnOwN", "unknown 7", "n/a.", "(unknown)", "unknown unknown", "TBD!"):
            self.assertTrue(ev.show("current_owner", v) == ev.UNKNOWN, v)
            self.assertTrue(ev.show_row("owner", v) == ev.UNKNOWN, v)
        self.assertIsNone(ev.show("result", None, "path"))

    def test_end_to_end_in_task_id_and_evidence_ref(self):
        for name, v, m in placeholder_values():
            p = payload(v, m)
            self.assertFalse(p in probe("task_id", v), (name, "task_id"))
            self.assertFalse(p in probe("evidence.0.ref", v), (name, "evidence.ref"))
            self.assertFalse(p in probe("current_owner", v), (name, "current_owner"))

    def test_end_to_end_through_the_cli(self):
        for name, v, m in placeholder_values()[:5]:
            p = payload(v, m)
            d = running()
            d["task_id"] = v
            d["evidence"][0]["task_id"] = v
            self.assertFalse(p in cli_all(d), (name, "task_id"))
            d = running()
            d["evidence"][0]["ref"] = v
            self.assertFalse(p in cli_all(d), (name, "evidence.ref"))

    def test_end_to_end_in_every_queue_row_field(self):
        for name, v, m in placeholder_values():
            p = payload(v, m)
            for rf in ("owner", "claim", "row_id", "waits_on", "status", "ask_id"):
                row = {"ask_id": "A1663", "rev": 3, "row_id": "d-20261113-0700-r7-a1b2", "owner": "r7", "status": "open", "seq": 12,
                       "claim": None, "waits_on": []}
                row[rf] = [v] if rf == "waits_on" else v
                self.assertFalse(p in adapter_out([row]), (name, rf, "adapter"))
                self.assertFalse(p in queue_recommend_out([row]), (name, rf, "recommend --queue"))
            out = cli([RECOMMEND, "--queue", "--now", NOW, "{}"], rows=[{"ask_id": "A1663", "rev": 3, "row_id": v, "owner": v}])
            self.assertFalse(p in out, (name, "cli --queue"))


# ------------------------------------------------------------------------------------------------------------------ DEF-C
class DefCInputCannotImitateAMarker(unittest.TestCase):
    """DEF-C (minor): the gate's internal placeholder for a charged piece, an opaque ref and the free-text hold mark are unforgeable
    from input: an input that carries one is opaque (identity, row) or hidden (free text)."""

    SENTINELS = ("", getattr(ev, "_CHARGED", ""))

    def values(self):
        out = []
        for s in self.SENTINELS:
            for _ in range(6):
                out.append("r7" + "".join(_R.choice("-_./:@") + s for _ in range(37)))
                out.append(" ".join(s + "".join(_R.choice("-_./:@") + s for _ in range(9)) for _ in range(4)))
                out.append("worker-" + s + "-" + s)
        return out

    def test_a_sentinel_from_input_is_opaque_in_every_row_field(self):
        for i, v in enumerate(self.values()):
            for f in ROW_FIELDS:
                self.assertTrue(ev.show_row(f, v) != v, (i, f))

    def test_a_sentinel_from_input_is_opaque_in_every_identity_field(self):
        for i, v in enumerate(self.values()):
            for f, k in B_FIELDS:
                self.assertTrue(ev.unmark(ev.show(f, v, k)) != v, (i, f))

    def test_the_sentinel_is_not_a_fixed_character(self):
        self.assertTrue(ev._CHARGED != "")
        self.assertGreaterEqual(len(ev._CHARGED), 8)

    def test_an_input_that_imitates_an_opaque_ref_is_itself_opaque(self):
        for i, f in enumerate(("current_owner", "worker.unit", "consumer", "task_id")):
            fake = "[opaque %s %s]" % (rnd(LOWER, 10), rnd("0123456789abcdef", 8))
            self.assertTrue(ev.unmark(ev.show(f, fake)) != fake, f)
            self.assertTrue(ev.show_row("owner", fake) != fake, i)
        minted = ev.opaque("owner", "Xx" + key12())
        self.assertTrue(ev.show("current_owner", minted) == minted)  # a ref this process minted passes through unchanged
        self.assertTrue(ev.show_row("owner", minted) == minted)

    def test_free_text_does_not_trust_a_ref_or_hold_mark_prefix(self):
        for i, pre in enumerate(("[opaque", "[REDACTED", "")):
            v = key12()
            self.assertFalse(v in ev.redact("note: %s%s" % (pre, v)), i)
            self.assertFalse(v in ev.redact("the %s: %s%s ok" % ("result", pre, v)), i)

    def test_end_to_end_a_sentinel_row_is_opaque(self):
        for s in self.SENTINELS:
            v = "r7" + "".join(_R.choice("-_./:@") + s for _ in range(37))
            for rf in ("owner", "claim", "row_id"):
                row = {"ask_id": "A1663", "rev": 3, "row_id": "d-20261113-0700-r7-a1b2", "owner": "r7", "status": "open"}
                row[rf] = v
                self.assertFalse(v in adapter_out([row]), rf)
                self.assertFalse(v in queue_recommend_out([row]), rf)


# ------------------------------------------------------------------------------------------------------------------ DEF-D
UD = [chr(c) for c in range(0x110000) if chr(c).isdecimal() and not chr(c).isascii()]


def ud(n):
    return "".join(_R.choice(UD) for _ in range(n))


class DefDAsciiDigitsAndCanonicalCase(unittest.TestCase):
    """DEF-D (minor): a non-ASCII decimal digit is never a digit of the gate (templates, the ISO gate, row digit pieces, the model tag);
    vocabulary words print only in a canonical case form; the model context tag is bounded and charged."""

    def test_unicode_digits_in_the_peer_template_are_opaque(self):
        for i in range(30):
            v = "claude-%s-r7-ab%sc%s-20%s1113" % (ud(7), ud(5), ud(2), ud(2))
            for f in ("consumer", "alternate", "consumer.named"):
                self.assertTrue(ev.unmark(ev.show(f, v)) != v, (i, f))

    def test_unicode_digits_in_the_inner_template_are_opaque(self):
        for i in range(30):
            v = "wm-build-inner%s-a.service" % ud(5)
            for f in ("worker.unit", "consumer", "alternate"):
                self.assertTrue(ev.unmark(ev.show(f, v)) != v, (i, f))

    def test_unicode_digits_in_a_prd_date_are_opaque(self):
        for i in range(20):
            v = "/home/jsy/Notes/prd-priority-20%s111%s.md" % (ud(2), ud(1))
            self.assertFalse("20" + v.split("-20", 1)[1][:2] in ev.unmark(ev.show("result", v, "path")), i)

    def test_unicode_digit_timestamps_and_digit_pieces_are_opaque_in_rows(self):
        for i in range(30):
            ts = "20%s-11-1%sT0%s:1%s:2%s.%s" % (ud(2), ud(1), ud(1), ud(1), ud(1), ud(9))
            for v in (ts, ts + "-" + ts, "claimed by r7 at " + ts, "r7-" + ud(6), "seq " + ud(7)):
                for f in ROW_FIELDS:
                    self.assertTrue(ev.show_row(f, v) != v, (i, f))
                self.assertFalse(v in queue_recommend_out([{"ask_id": "A1663", "rev": 3, "row_id": "d-1", "owner": "r7", "claim": v}]), i)

    def test_unicode_digits_never_print_in_an_identity_field(self):
        for i in range(20):
            for f, k in B_FIELDS:
                v = "r7-%s" % ud(6)
                self.assertTrue(ev.unmark(ev.show(f, v, k)) != v, (i, f))

    def test_the_model_tag_is_ascii_and_charged(self):
        for i in range(20):
            v = "claude-opus-5-5[%sm]" % ud(4)
            self.assertTrue(ev.unmark(ev.show("worker.model", v)) != v, i)
        self.assertTrue(ev.unmark(ev.show("worker.model", "claude-opus-5-5[1m]")) == "claude-opus-5-5[1m]")
        # the tag's digits are charged: a model carrying the digit cap already is opaque once a tag is added
        full = "claude-%s-%s[9999m]" % (rnd(DIG, 7), rnd(DIG, 7))
        self.assertTrue(ev.unmark(ev.show("worker.model", full)) != full)

    def test_a_free_dotted_tail_prints_only_in_a_tail_field(self):
        # a dotted name of vocabulary words ending in a DNS suffix is a host or path tail; in a field that names no host or
        # path (model, effort, account, session, task) it is the free word channel the bit budget charges, so it is opaque
        v = ".".join(("fixes", "merge", "wfit", "upstream", "verify", "bash", "dev"))
        for f in ("worker.model", "worker.effort", "worker.account", "worker.session", "task"):
            self.assertTrue(ev.unmark(ev.show(f, v)) != v, f)
        self.assertTrue(ev.unmark(ev.show("worker.host", v)) == v)

    def test_every_gate_regex_digit_slot_is_ascii(self):
        for name in ("_DATE_ID", "_TS_ID", "_DATE_TAIL", "_ISO_GATE", "_PRIO", "_SLUG", "_PEER_SLUG_RX", "_CTX_SUFFIX", "_ISO_TS", "_CLOCK"):
            rx = getattr(ev, name)
            self.assertTrue(rx.flags & re.ASCII, name)
        for name, rx in ev._TEMPLATES.items():
            self.assertTrue(rx.flags & re.ASCII, name)
        self.assertIsNone(ev._DATE_ID.fullmatch("٢٠٢٦١١١٣"))

    def test_vocabulary_case_is_canonical_in_rows_and_identities(self):
        words = ["invocation", "bootstrap", "controller", "wintermute", "production", "synthorg"]
        for i in range(30):
            v = " ".join("".join(c.upper() if _R.random() < .5 else c for c in w) for w in words)
            if all(w.islower() or w.isupper() or w.istitle() for w in v.split()):
                continue
            self.assertTrue(ev.show_row("claim", v) != v, i)
        for v in ("WoRkEr", "iNVOCATION", "reVIEW-worker", "BootStrap-r7"):
            self.assertTrue(ev.unmark(ev.show("current_owner", v)) != v, v)
            self.assertTrue(ev.show_row("owner", v) != v, v)
        for v in ("worker", "WORKER", "Worker", "app-gnome-Terminal-4242.scope"):
            f = "worker.unit" if v.endswith(".scope") else "current_owner"
            self.assertTrue(ev.unmark(ev.show(f, v)) == v, v)


    def test_the_structure_word_cap_binds_below_the_bit_budget(self):
        # nine structure words cost about 80 bits, far under the path bit budget: the count cap of 8 is what refuses them
        words = sorted(w for w in ev._STRUCT_WORDS if w not in ("md", "json", "txt", "log"))
        for i in range(20):
            eight = "/" + "/".join(_R.choice(words) for _ in range(8))
            nine = "/" + "/".join(_R.choice(words) for _ in range(9))
            self.assertTrue(ev.unmark(ev.show("result.artifact", eight, "path")) == eight, i)
            self.assertTrue(ev.unmark(ev.show("result.artifact", nine, "path")) != nine, i)


# ------------------------------------------------------------------------------------------------------------------ DEF-E
def slug_words(k):
    """k random lower-case words of 6-9 letters (a word slot's material; no list of real words is needed to show the slot). Each word is
    longer than the 5-character unlisted piece, so the ordinary gate (residual c) cannot print it either: only a slot could."""
    return "-".join(rnd(LOWER, _R.randint(6, 9)) for _ in range(k))


class DefEPrdSlugIsAnOpaqueRef(unittest.TestCase):
    """DEF-E (minor): the PRD slug slot is not a free word slot. A PRD note path prints its frame (user, Notes, prd, date) with the slug
    as an opaque ref, unless every slug word is a closed-vocabulary word (then the ordinary gate prints the whole path)."""

    NOUNS = ["anchor", "biscuit", "cabbage", "dancer", "giraffe", "hammer", "island", "jacket", "kettle", "ladder", "magnet", "napkin"]

    def test_a_slug_outside_the_vocabulary_never_prints_and_the_frame_does(self):
        cases = [slug_words(k) for k in (1, 2, 3, 4) for _ in range(10)] + self.NOUNS + ["%s-%s" % (a, b) for a, b in zip(self.NOUNS, self.NOUNS[1:])]
        for i, s in enumerate(cases):
            v = "/home/jsy/Notes/prd-%s-20261113.md" % s
            for f in ("result", "artifact", "evidence-ref", "event", "ref", "target"):
                out = ev.unmark(ev.show(f, v, "path"))
                self.assertFalse(("prd-" + s) in out, (i, f))
                if len(s.replace("-", "")) <= ev._PRD_SLUG_LETTERS:  # inside the slot bound: the frame prints, else the whole is opaque
                    self.assertTrue(out.startswith("/home/jsy/Notes/prd-[opaque ") and out.endswith("]-20261113.md"), (i, f))
                else:
                    self.assertTrue(out.startswith("[opaque "), (i, f))

    def test_the_slug_ref_is_keyed_and_stable_in_one_run(self):
        a = ev.show("result", "/home/jsy/Notes/prd-%s-20261113.md" % "kettle-ladder", "path")
        b = ev.show("result", "/home/jsy/Notes/prd-%s-20261113.md" % "kettle-ladder", "path")
        c = ev.show("result", "/home/jsy/Notes/prd-%s-20261113.md" % "kettle-magnet", "path")
        self.assertTrue(a == b)
        self.assertTrue(a != c)

    def test_the_real_fleet_prd_paths_behave_as_the_invariant_states(self):
        whole = "/home/jsy/Notes/prd-priority-selective-unpark-20261111.md"  # every slug word is closed vocabulary
        self.assertTrue(ev.unmark(ev.show("result", whole, "path")) == whole)
        framed = "/home/jsy/Notes/prd-dotfiles-prefix-admit-20261102.md"  # 'prefix', 'admit' are not: frame + opaque slug
        out = ev.unmark(ev.show("result", framed, "path"))
        self.assertFalse("prefix-admit" in out)
        self.assertTrue(out.startswith("/home/jsy/Notes/prd-[opaque prd-slug ") and out.endswith("]-20261102.md"))

    def test_a_credential_in_the_slot_is_never_printed_and_the_frame_is_only_in_path_fields(self):
        for i, s in enumerate((key12(), J("pass", "word"), J("tok", "en") + "-" + rnd(LOWER, 6), rnd(LOWER, 30))):
            v = "/home/jsy/Notes/prd-%s-20261113.md" % s
            self.assertFalse(s in ev.unmark(ev.show("result", v, "path")), i)
            for f in ("current_owner", "task_id", "worker.unit"):
                self.assertFalse(s in ev.unmark(ev.show(f, v)), (i, f))
        self.assertFalse(ev.keep("path", "/home/jsy/Notes/prd-kettle-ladder-20261113.md", "result") != "/home/jsy/Notes/prd-kettle-ladder-20261113.md")

    def test_end_to_end_in_result_artifact_and_evidence_ref(self):
        for i in range(6):
            s = slug_words(_R.randint(1, 4))
            v = "/home/jsy/Notes/prd-%s-20261113.md" % s
            self.assertFalse(("prd-" + s) in probe("result.artifact", v), (i, "artifact"))
            self.assertFalse(("prd-" + s) in probe("evidence.0.ref", v), (i, "ref"))
            self.assertFalse(("prd-" + s) in probe("coverage_gaps.0", "result: " + v), (i, "free text"))


    def test_a_slug_outside_the_frame_grammar_is_not_framed(self):
        # the frame's slot is lower-case words of at most 24 letters; any other slug (capitals, digits) is not the frame: whole opaque
        for i in range(10):
            for s in (rnd(LOWER, 4) + rnd(UPPER, 3) + "-" + rnd(LOWER, 6), rnd(LOWER, 5) + rnd(DIG, 2) + "-" + rnd(LOWER, 6)):
                v = "/home/jsy/Notes/prd-%s-20261113.md" % s
                out = ev.unmark(ev.show("result", v, "path"))
                self.assertFalse(s in out, i)
                self.assertFalse("[opaque prd-slug" in out, i)

    def test_a_credential_stem_in_the_peer_slug_is_opaque(self):
        # the peer slug grammar holds up to three letters then digits: a credential stem there ('pwd' + digits) is not an id
        for stem in (J("pw", "d"), J("pi", "n"), J("ot", "p"), J("ke", "y")):
            v = "claude-4242-r7-%s%s-20261113" % (stem, rnd(DIG, 2))
            for f in ("consumer", "alternate"):
                self.assertTrue(ev.unmark(ev.show(f, v)) != v, (stem[:1], f))
        self.assertTrue(ev.unmark(ev.show("consumer", "claude-4242-r7-ab12-20261113")) == "claude-4242-r7-ab12-20261113")


# ------------------------------------------------------------------------------------------------------------------ DEF-F
REVIEW_NAMES = {  # re-review 14 probes/own/prose14.py (76 names)
    "nonenglish": ["contrasena", "passwort", "motdepasse", "senha", "clave", "kennwort", "jelszo", "heslo", "geheimnis", "losenord",
                   "sifre", "parol", "wachtwoord", "salasana"],
    "abbrev": ["psw", "pss", "pwds", "tkn", "tok", "skey", "privk", "pinno", "totp", "otpcode", "mfacode", "seedphrase", "mnemonic",
               "passkey", "sesstoken", "apitok", "authtok"],
    "leet": ["p@ssword", "pa$$word", "pa55w0rd", "p455w0rd", "s3cr3t", "t0k3n", "secr3t", "p4ss", "c0de", "k3y", "pa55", "passw0rd!"],
    "misspelt": ["passowrd", "pasword", "paswrod", "pssword", "psswrd", "secrit", "secert", "toekn", "tokn", "crediental",
                 "credentails", "passwod", "passworf"],
    "compound": ["rootsecret", "mysecretz", "adminpin", "wifikey", "routerpw", "authcode", "accesscode", "securitycode", "smscode",
                 "oneTimeCode", "otpCode", "PIN_CODE", "pin-number", "unlockpin", "signingkey", "apisecret", "Login_Password",
                 "userPassphrase", "x-api-key", "sudo_pass"],
}
# my own names, in no list the code holds (checked below): each is recognised only by the RULE (de-leet, an edit from a closed stem,
# a glued qualifier, a value tail, a weak noun after a strong one)
OWN_NAMES = ["s3cr3ts", "t0k3ns", "cr3d3nt1als", "p4$$phrase", "pa$$c0de", "secreet", "tokken", "credntial", "passphase", "pascode",
             "vpnpassword", "bankpin", "routerToken", "wifiSecret", "gitpass", "kenwort", "wachtwort", "pin_no", "token-value",
             "secret_string", "otpKey", "s3cretz", "mnemonik", "dbs3cret", "apitokn"]
PROSE_FORMS = ["{n} {v}", "the {n} is {v}", "{n} was {v}.", "my {n} {v} please", "use {n} \"{v}\" now"]
PAIR_FORMS = ["{n}: {v}", "{n}={v}", "\"{n}\": \"{v}\"", "--{n} {v}", "{n} -> {v}", "{n} = \"{v}\"", "{{\"cfg\": {{\"{n}\": [\"{v}\"]}}}}"]
QUOTES = [("“", "”"), ("‘", "’"), ("„", "“"), ("‚", "‘"), ("«", "»"), ("»", "«"),
          ("‹", "›"), ("「", "」"), ("『", "』"), ("〝", "〞"), ("″", "″"), ("′", "′"),
          ("＂", "＂"), ("\"", "\""), ("'", "'"), ("`", "`")]
POSITIVE_PROSE = ["the result is code=ok today", "exit code 2 means a usage error", "the reply had status_code=404 twice", "rc=0 after the run",
                  "the keyboard layout changed", "the monkey test found a crash", "the turkey sandwich was cold", "the passage on page 4",
                  "a compass and a map", "encode the header first", "the barcode scanner failed", "decode the base64 header",
                  "signing the release took an hour", "the pinned issue moved"]
# re-review 14 probes/own/prose14.py ordinary sentences that are byte-identical at bffbfc29 (24 of 34): none may change
REVIEW_PROSE_SAME = ["the key point is that the queue drains", "exit code 2 means a usage error", "please sign in before the review",
                     "pass the test suite twice", "a code review of the patch", "a passport photo is attached", "the passage on page 4",
                     "a compass and a map", "the keyboard layout changed", "the monkey test found a crash", "the barcode scanner failed",
                     "decode the base64 header", "the keynote starts at noon", "the token expired at 09:00", "pin the version to 3.12",
                     "seed the random generator with 42", "the vault was sealed", "unlock the door at 8", "the auth service restarted",
                     "key rotation runs weekly", "the code is on main", "the pinned issue moved", "pins and needles", "a phrase from the book"]


def all_review_names():
    return [n for ns in REVIEW_NAMES.values() for n in ns]


class DefFCredentialNameRuleAndQuotes(unittest.TestCase):
    """DEF-F (minor): the credential-name RULE reads non-English and abbreviated names from closed stated sets, full de-leet (with @
    and $), an edit from every closed stem of five letters or more, value-tail and weak-after-strong compounds; every Unicode quote
    pair hides every word; the ordinary-prose positives stay readable."""

    def shapes(self):
        return (("mixed12", key12), ("lower10", word10), ("num6", pin6), ("word", lambda: _R.choice(["lantern", "biscuit", "walnut", "harbor"])),
                ("lower24", lambda: rnd(LOWER, 24)))

    def test_every_reviewer_name_hides_its_value_in_every_prose_and_pair_form(self):
        for ni, n in enumerate(all_review_names()):
            for fi, fm in enumerate(PROSE_FORMS + PAIR_FORMS):
                for shape, mk in self.shapes():
                    v = mk()
                    self.assertFalse(v in ev.redact(fm.format(n=n, v=v)), (ni, fi, shape))

    def test_my_own_names_are_in_no_code_list_and_hide_their_value(self):
        lists = (set(ev._CRED_WORDS) | set(ev._STRONG_NOUNS) | set(ev._CRED_NOUNS) | set(ev._WEAK_NOUNS) | set(ev._GLUE_NOUNS)
                 | set(getattr(ev, "_CRED_ABBREV", ())) | set(getattr(ev, "_CRED_FOREIGN", ())) | set(ev._READABLE_GLUED)
                 | set(ev._GLUE_ENGLISH) | set(ev._ID_WORDS))
        for ni, n in enumerate(OWN_NAMES):
            self.assertFalse(n.lower() in lists, ni)
        self.assertGreaterEqual(len(OWN_NAMES), 5)
        for ni, n in enumerate(OWN_NAMES):
            for fi, fm in enumerate(PROSE_FORMS):
                for shape, mk in self.shapes():
                    v = mk()
                    self.assertFalse(v in ev.redact(fm.format(n=n, v=v)), (ni, fi, shape))

    def test_every_quote_pair_hides_every_word_after_a_credential_name(self):
        for ni, n in enumerate(["password", "passphrase", "pin", "secret", "dbpass", "wifipass", "s3cret", "kennwort"]):
            for qi, (o, c) in enumerate(QUOTES):
                for fi, fm in enumerate(("{n} {o}{a} {b} {c}{q}", "the {n} is {o}{a} {b} {c}{q}", "{n}: {o}{a} {b} {c}{q}",
                                         "{n} = {o}{a} {b} {c}{q} ok")):
                    a, b, cc = rnd(LOWER, 6), rnd(LOWER, 7), rnd(LOWER, 5)
                    out = ev.redact(fm.format(n=n, o=o, a=a, b=b, c=cc, q=c))
                    self.assertFalse(a in out or b in out or cc in out, (ni, qi, fi))

    def test_the_ordinary_prose_positives_stay_readable(self):
        for i, p in enumerate(POSITIVE_PROSE):
            self.assertTrue(ev.redact(p) == p, i)

    def test_the_reviewer_sentences_that_were_readable_stay_readable(self):
        for i, p in enumerate(REVIEW_PROSE_SAME):
            self.assertTrue(ev.redact(p) == p, i)

    def test_the_closed_sets_are_data_with_a_source(self):
        with open(VALIDATE, encoding="utf-8") as fh:
            src = fh.read()
        for name in ("_CRED_ABBREV", "_CRED_FOREIGN", "_EDIT_ENGLISH", "_VALUE_TAILS"):
            self.assertTrue(hasattr(ev, name), name)
            self.assertTrue(isinstance(getattr(ev, name), frozenset), name)
        for name in ("_CRED_ABBREV", "_CRED_FOREIGN", "_EDIT_ENGLISH", "_VALUE_TAILS"):
            at = src.index(name + " = ")
            self.assertIn("source:", src[at:at + 900], name)

    def test_end_to_end_through_the_recommender(self):
        for i, n in enumerate(["kennwort", "p@ssword", "tkn", "secrit", "PIN_CODE", "vpnpassword"]):
            v = key12()
            self.assertFalse(v in probe("coverage_gaps.0", "the %s is %s for login" % (n, v)), i)
            a, b = rnd(LOWER, 6), rnd(LOWER, 7)
            out = probe("coverage_gaps.0", "%s “%s %s”" % (n, a, b))
            self.assertFalse(a in out or b in out, i)


    def test_in_word_at_and_dollar_leet_forms_are_names(self):
        # '$' for 's' and '@' for 'a' inside a word, not only before a digit run ('pa$s', 'p@$s')
        for n in (J("pa", "$s"), J("p@", "$s"), J("Pa", "$s")):
            for mid in (" ", " is "):
                v = word10()
                self.assertFalse(v in ev.redact(n + mid + v), (n[:1], mid))

    def test_english_words_glued_after_a_qualifier_stay_readable(self):
        # the English exclusion holds for the glued reading too: 'un' + 'taken' is not a misspelt name
        for w in ("untaken", "nonsecretary", "undeclare", "unpatrol", "subsecretary"):
            s = "%s %s" % (w, word10())
            self.assertTrue(ev.redact(s) == s, w)

    def test_a_misspelt_stem_with_a_value_tail_is_a_name(self):
        # N6 over an N2 stem: a misspelling followed by a closed value-tail word ('<misspelt>-string', '<misspelt>_value')
        for n in (J("passw", "rd") + "-string", J("sekr", "et") + "_value", J("secr", "it") + "Text"):
            for fn in (ev.redact, ev.redact_tool):
                v = word10()
                self.assertFalse(v in fn(n + " " + v), n[:2])

    def test_a_typographic_quoted_value_ends_at_its_closing_quote(self):
        # the pair layers read a typographic-quoted value as ONE value: hidden whole, and the text after the closing quote stays
        for a, b in (("\u201c", "\u201d"), ("\u2018", "\u2019"), ("\u00ab", "\u00bb"), ("\u300c", "\u300d")):
            for fn in (ev.redact, ev.redact_tool, ev.redact_credentials):
                x, y = word10(), word10()
                out = fn(J("pass", "word") + ": " + a + x + " " + y + b + " and the run is done")
                self.assertFalse(x in out or y in out, (a, fn.__name__))
                self.assertTrue(out.endswith(" and the run is done"), (a, fn.__name__))


# ------------------------------------------------------------------------------------------------------------------ DEF-G
class DefGRepoOwnerFromAClosedList(unittest.TestCase):
    """DEF-G (minor): a repo owner from the closed owner list is one vocabulary word, so the name keeps the value's budget:
    `j0yen/summa` and `j0yen/fleet-dash` print; a credential negative in the same position stays opaque."""

    def test_the_two_regressed_repos_print_in_their_field(self):
        for v in ("j0yen/summa", "j0yen/fleet-dash"):
            self.assertTrue(ev.unmark(ev.show("target.repo", v)) == v, v)
            self.assertIn(v, probe("target.repo", v), v)

    def test_credential_negatives_in_the_same_position_stay_opaque(self):
        negs = ["j0yen/%s" % key12(), "j0yen/%s" % J("pass", "word"), "j0yen/%s" % rnd(LOWER, 9), "%s/summa" % rnd(LOWER, 6),
                "j0yen/%s-%s" % (rnd(LOWER, 5), rnd(LOWER, 5)), "j0yen/fleet-%s" % key12()]
        for i, v in enumerate(negs):
            self.assertTrue(ev.unmark(ev.show("target.repo", v)) != v, i)

    def test_the_owner_list_is_closed_and_holds_no_credential_word(self):
        self.assertTrue(isinstance(getattr(ev, "_REPO_OWNERS", None), frozenset))
        for w in ev._REPO_OWNERS:
            self.assertFalse(ev._cred_name(w), w)


# ------------------------------------------------------------------------------------------------------------------ DEF-H
def peer_capacity():
    """the peer id template's capacity from its slot grammar (ASCII digits): pid 1-7 digits, a seat, the run slug, a date, -worker"""
    date = math.log2(100 * 12 * 31)
    pid = math.log2(sum(10 ** n for n in range(1, 8)))
    slug = ev._PEER_SLUG_MAX * math.log2(36)
    return pid + math.log2(len(ev._SEATS)) + slug + date + 1


class DefHDocStatesTheCode(unittest.TestCase):
    """DEF-H (minor): SKILL.md states the measured capacities, the bit budget and the actual paths; no sentence claims more than the
    code does."""

    def skill(self):
        with open(os.path.join(str(SKILL), "SKILL.md"), encoding="utf-8") as fh:
            return re.sub(r"\s+", " ", fh.read())

    def stated(self, pattern):
        m = re.search(pattern, self.skill())
        self.assertIsNotNone(m, pattern)
        return float(m.group(1))

    def test_the_peer_template_capacity_in_the_doc_is_the_measured_one(self):
        n = self.stated(r"peer id [^.]*?at most about (\d+) bits")
        self.assertGreaterEqual(n, peer_capacity() - 0.5)
        self.assertLessEqual(n, peer_capacity() + 2)
        self.assertLessEqual(n, 128)

    def test_the_bit_budget_in_the_doc_is_the_code_budget(self):
        self.assertTrue(self.stated(r"at most (\d+) bits of non-id material per value") == ev._MAX_VALUE_BITS)
        self.assertTrue(self.stated(r"(\d+) bits in a path field") == ev._MAX_PATH_BITS)

    def test_the_doc_states_the_actual_paths(self):
        s = self.skill()
        for phrase in ("prints as the canonical word `UNKNOWN`", "slug as an opaque ref", "ASCII digits", "per-process random",
                       "three case forms", "label decoration"):
            self.assertIn(phrase, s)
        for claim in ("nothing is removed or skipped before it is charged", "is not charged (about 2.6 bits a boundary",
                      "a placeholder stays UNKNOWN", "a lower-case word in the PRD slug slot prints"):
            self.assertNotIn(claim, s)


# ------------------------------------------------------------------------------------------------------------------ concerns
class UnconfirmedConcerns14(unittest.TestCase):
    """re-review 14 unconfirmed concerns given a code disposition: the per-value capacity bound, the reviewer equal to the worker's own
    unit, the mutant runner's import-breaking mutant."""

    def test_a_value_filling_every_cap_at_once_is_opaque(self):
        voc = sorted(w for w in ev._ID_WORDS if len(w) >= 3 and not ev._cred_name(w))
        for i in range(40):
            pieces = [_R.choice(DIG) for _ in range(14)] + [_R.choice(voc) for _ in range(6)] + [_R.choice("bcdfghjklmnpqstvxz") for _ in range(8)]
            _R.shuffle(pieces)
            v = "".join(p + _R.choice("-_./:@") for p in pieces[:-1]) + pieces[-1]
            for f, k in (("current_owner", "ident"), ("worker.unit", "ident"), ("task_id", "ident"), ("result", "path")):
                self.assertTrue(ev.unmark(ev.show(f, v, k)) != v, (i, f))
            self.assertTrue(ev.show_row("claim", v) != v, i)

    def test_a_reviewer_equal_to_the_workers_own_unit_is_not_distinct(self):
        d = done()
        d["worker"]["unit"] = "wm-build-rb-a1777-20261114.service"
        d["result"].update(reviewed=True, reviewed_by="wm-build-rb-a1777-20261114.service")
        self.assertTrue(one(d)["role"] != "coordinator-decision")
        d["result"]["reviewed_by"] = "verifier-7"
        self.assertTrue(one(d)["role"] == "coordinator-decision")

    def test_an_import_breaking_mutant_is_not_applied_never_caught(self):
        r = subprocess.run([sys.executable, os.path.join(TESTS, "mutants11.py"), "--selftest", "import-breaking"], capture_output=True,
                           text=True, timeout=600)
        self.assertTrue(r.returncode != 0)
        self.assertIn("NOT-APPLIED", r.stdout)
        self.assertFalse(re.search(r"^t4 .*\bcaught\b", r.stdout, re.M) is not None)
        self.assertIn("caught 0/1", r.stdout)


# ------------------------------------------------------------------------------------------------- retained reviewer probes
class RetainedReviewerProbes15(unittest.TestCase):
    """The reviewer's own re-review 14 reproducers (tests/probes/*14.py), run against this tree."""

    def run_probe(self, name, *args):
        r = subprocess.run([sys.executable, "-B", os.path.join(TESTS, "probes", name), *args], capture_output=True, text=True, timeout=1800)
        self.assertTrue(r.returncode == 0, name + r.stderr[-300:])
        return r.stdout

    def test_punct14_nothing_leaks(self):
        self.assertIn("PUNCT14 redact leaks 0/14", self.run_probe("punct14.py"))

    def test_unk14_no_raw_print(self):
        out = self.run_probe("unk14.py")
        lines = [l for l in out.splitlines() if "prints in" in l]
        self.assertTrue(len(lines) == 8)
        for l in lines:
            self.assertTrue(re.search(r"prints in  0/10 fields \[\] \| rows \[\] \| redact keeps=", l) is not None, l.split()[0])

    def test_gate14_sentinel_and_case_rows_opaque(self):
        out = self.run_probe("gate14.py")
        self.assertIn("rows print 0/30, owner prints 0/30", out)
        self.assertIn("row prints 0/30", out)

    def test_punct14e2e_and_label14e2e_hidden(self):
        for name in ("punct14e2e.py", "label14e2e.py"):
            out = self.run_probe(name)
            self.assertFalse("=True" in out, name)
            self.assertGreaterEqual(out.count("rec-text=False"), 12, name)

    def test_pos14_the_two_regressions_print(self):
        out = self.run_probe("pos14.py")
        opaque = [l.split()[2] for l in out.splitlines() if l.strip().startswith("OPAQUE")]
        self.assertFalse("j0yen/summa" in opaque)
        self.assertFalse("j0yen/fleet-dash" in opaque)
        self.assertIn("DEF-3 set: positives 8, opaque 0", out)

    def test_prose14_no_name_and_no_typographic_quote_leaks(self):
        out = self.run_probe("prose14.py")
        self.assertIn("names leaking a value in redact(): 0", out)
        self.assertIn("quoted multiword: 0/49", out)

    def test_human14_no_value_prints_through_the_prd_slot(self):
        """Every value the probe sees printing inside a PRD path form prints in a plain path outside the frame too (the ordinary gate,
        residual c or b): the slot itself admits nothing."""
        out = self.run_probe("human14.py")
        vals = sorted({l.split()[1] for l in out.splitlines() if l.startswith("HIT") and "prd-template-slot" in l})
        for i, v in enumerate(vals):
            self.assertTrue(ev.unmark(ev.show("result", "/tmp/%s.json" % v, "path")) == "/tmp/%s.json" % v, i)
        self.assertTrue(len(vals) <= 8, len(vals))

    def test_smuggle14_new_channels_closed(self):
        out = self.run_probe("smuggle14.py")
        for name in ("peer template, unicode digits", "inner template, unicode digits", "prd template, unicode date digits",
                     "prd template, 24 random letters", "ISO ts, unicode digits, frac 9", "two ISO ts, unicode digits",
                     "sentinel pieces + joiners (38)", "sentinel, 4 row tokens", "6 vocab words, random case", "model ctx tag, unicode digits",
                     "joiners + full charged caps"):
            line = [l for l in out.splitlines() if l.startswith(name)]
            self.assertTrue(len(line) == 1, name)
            self.assertTrue(line[0].rstrip().endswith("| fields: - | rows: -"), name)


if __name__ == "__main__":
    unittest.main()
