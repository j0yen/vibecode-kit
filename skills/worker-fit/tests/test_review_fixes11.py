"""Regression tests for the eleventh independent exact-head review (re-review 10 of 8f250d8e): DEF-1 .. DEF-5.
Design under test: FIELD-AWARE validated identities. Every identity field has its OWN profile (ev._PROFILES): the id shapes it
accepts (hex of 7-12, 32, 40, 64 characters, a uuid, a ULID, an instance id) and the form each takes (alone, or beside a field
template such as `verifier-<hex32>`, `sess-<uuid>`, `<name>.service`). A value prints only through the ONE trust gate: the closed
vocabulary and bounds AND this field's profile; otherwise it is an opaque keyed ref. A grammar-valid id of a shape another
field carries is opaque here. No denylist gates an identity, a row field or a key name. Free text: a number prints only under a
name of the closed numeric list, and no unlisted material prints under any name.
Every legitimate identity is paired with a credential of similar shape. Source-only: synthetic envelopes, canaries assembled at
run time from fragments, nothing printed (assertion labels carry an index, never a canary)."""
import contextlib
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest

from helpers import SKILL, install_fixture_clock, remove_fixture_clock

import envelope_validate as ev
import queue_adapter as qa
import test_review_fixes3 as t3
from test_review_fixes10 import IDENT_FIELDS, probe
from test_review_fixes7_pairs import build, everything, shown
from test_review_fixes9 import adapter_out, queue_recommend_out

running, done, one = t3.running, t3.done, t3.one
TESTS = os.path.dirname(os.path.abspath(__file__))


def setUpModule():
    install_fixture_clock()


def tearDownModule():
    remove_fixture_clock()


_R = random.Random(11)
HEXD = "0123456789abcdef"
LOWER = "abcdefghijklmnopqrstuvwxyz"
B62 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


def rnd(alpha, n):
    return "".join(_R.choice(alpha) for _ in range(n))


def hexmix(n):
    """n hex characters with digits and letters both present"""
    while True:
        s = rnd(HEXD, n)
        if any(c.isdigit() for c in s) and any(c.isalpha() for c in s):
            return s


def uu():
    return "-".join(hexmix(k) for k in (8, 4, 4, 4, 12))


def shapes():
    """credential-shaped values of the class the reviewer found printing in 15 of 16 fields"""
    h12, h32, h64 = hexmix(12), hexmix(32), hexmix(64)
    return {"hex32": h32, "hex40": hexmix(40), "hex64": h64, "uuid": uu(), "build-hex32": "build-" + h32,
            "run-hex12": "run-" + h12, "run-hex12-7d-7d": "run-%s-%s-%s" % (h12, rnd("0123456789", 7), rnd("0123456789", 7)),
            "task-hex64-7d-7d-words": "task-%s-%s-%s-build-claude-merge" % (h64, rnd("0123456789", 7), rnd("0123456789", 7)),
            "hex12+14digits": "%s-%s-%s" % (h12, rnd("0123456789", 7), rnd("0123456789", 7))}


# the ONLY (field, shape) pairs where a BARE value of that shape is a legitimate identity of the field
LEGIT_ALONE = {("worker.invocation", "hex32"), ("worker.invocation", "hex64"), ("worker.invocation", "uuid"),
               ("worker.session", "hex32"), ("worker.session", "uuid"), ("target.head", "hex40"), ("target.head", "hex32"),
               ("target.head", "hex64")}
ALL_FIELDS = IDENT_FIELDS + ["target.head"]


class FieldAwareGrammar(unittest.TestCase):
    """DEF-1: every identity field x every credential shape."""

    def test_every_field_prints_only_the_shapes_its_own_grammar_names(self):
        for fi, f in enumerate(ALL_FIELDS):
            for name, v in shapes().items():
                out = probe(f, v)
                if (f, name) in LEGIT_ALONE:
                    self.assertIn(v, out, "field %d shape %s should print" % (fi, name))
                else:
                    self.assertNotIn(v, out, "field %d shape %s" % (fi, name))

    def test_no_piece_of_a_credential_shape_leaks_either(self):
        for fi, f in enumerate(ALL_FIELDS):
            for name, v in shapes().items():
                if (f, name) in LEGIT_ALONE:
                    continue
                out = probe(f, v)
                for piece in v.split("-"):
                    if len(piece) >= 12 and not (f == "target.head" and piece in v):
                        self.assertNotIn(piece, out, "field %d shape %s piece" % (fi, name))

    def test_the_profile_table_names_every_identity_label(self):
        for label in ("host", "unit", "child", "session", "sess-id", "invocation", "account", "model", "effort", "owner",
                      "current_owner", "reviewed_by", "consumer", "named", "alternate", "repo", "branch", "task", "task_id",
                      "result", "artifact", "event", "evidence-ref", "ref"):
            self.assertIsInstance(ev._profile(label), dict, label)
        self.assertEqual(ev._profile("no-such-field")["alone"], frozenset())  # unknown label: strict
        # the hash-sized shapes are carried by their own fields only
        for label in ("account", "model", "repo", "branch", "host", "owner", "effort", "task"):
            p = ev._profile(label)
            for shape in ("h32", "h40", "h64", "uuid"):
                self.assertNotIn(shape, p["alone"], (label, shape))
        for label in ("account", "model", "repo", "branch", "host", "owner", "effort", "task", "invocation"):
            for shape in ("h64", "h40"):
                if label != "invocation":
                    self.assertNotIn(shape, ev._profile(label)["beside"], (label, shape))

    def test_legitimate_hash_forms_stay_in_their_own_fields(self):
        h32, h40, h12, U = hexmix(32), hexmix(40), hexmix(12), uu()
        pos = [("worker.invocation", h32), ("worker.invocation", U), ("worker.session", U), ("worker.session", "sess-" + U),
               ("worker.session", h32), ("target.head", h40), ("worker.unit", "wm-build-%s.service" % h32),
               ("worker.unit", "run-r%s.scope" % h32), ("worker.unit", "coder@%s.service" % U),
               ("worker.child", "child-%s" % h40), ("consumer.named", "verifier-%s" % h32), ("result.event", "evt-%s" % h32),
               ("result.artifact", "/retained/WF-1/result-%s.json" % h32), ("task_id", "task-%s" % h32),
               ("worker.invocation", h12), ("worker.invocation", "inv-%s" % h12), ("task_id", "task-%s" % h12), ("consumer.named", "verifier-%s" % h12)]
        for i, (f, v) in enumerate(pos):
            self.assertIn(v, probe(f, v), "positive %d %s" % (i, f))

    def test_paired_negatives_of_similar_shape_hide(self):
        h32, U = hexmix(32), uu()
        neg = [("worker.invocation", "build-" + h32), ("worker.invocation", "task-" + hexmix(64)),
               ("worker.unit", "build-" + h32), ("worker.unit", h32), ("worker.unit", "run-r%s.timer-x" % h32),
               ("worker.session", "build-" + h32), ("worker.session", "task-" + U), ("consumer.named", "build-" + h32),
               ("consumer.named", h32), ("result.event", h32), ("result.event", "build-" + h32), ("task_id", "task-" + hexmix(64)),
               ("task_id", U), ("worker.account", h32), ("worker.account", "acct-" + h32), ("current_owner", U),
               ("target.repo", "j0yen/" + h32), ("target.branch", "r7/" + hexmix(40)), ("worker.model", "claude-" + h32),
               ("worker.host", h32), ("worker.host", "ip-" + h32 + ".ec2.internal"), ("worker.child", h32)]
        for i, (f, v) in enumerate(neg):
            self.assertNotIn(v, probe(f, v), "negative %d %s" % (i, f))

    def test_digits_beside_an_id_are_bounded(self):
        h12 = hexmix(12)
        for f in ("worker.unit", "worker.child", "worker.session", "task_id", "consumer.named", "worker.account"):
            v = "run-%s-%s-%s" % (h12, rnd("0123456789", 7), rnd("0123456789", 7))
            self.assertNotIn(v, probe(f, v), f)
        self.assertFalse(ev._gate_values(["run-%s-%s-%s" % (h12, rnd("0123456789", 7), rnd("0123456789", 7))],
                                         profile=ev._profile("unit")))

    def test_the_adapter_and_rows_carry_no_hash_shape(self):
        for name, v in shapes().items():
            row = [{"ask_id": "WF-1", "rev": 1, "owner": v, "row_id": "d-20261112-224051-r7-3b84", "status": "open", "seq": 7}]
            self.assertNotIn(v, adapter_out(row), name)
            self.assertNotIn(v, queue_recommend_out(row), name)
            row2 = [{"ask_id": "WF-1", "rev": 1, "owner": "r7", "row_id": v, "status": "open", "seq": 7}]
            self.assertNotIn(v, adapter_out(row2), name)

    def test_mismatch_and_echo_paths_stay_opaque(self):
        for name, v in shapes().items():
            d = running()
            d["evidence"][0]["task_id"] = v
            self.assertNotIn(v, everything(one(d)), name)

    def test_unknown_stays_unknown(self):
        self.assertEqual(ev.show("account", "UNKNOWN"), "UNKNOWN")
        self.assertEqual(ev.show("account", "unknown"), "unknown")


class EightGroupIpv6(unittest.TestCase):
    """author-claim discrepancy (e): a short 8-group literal prints in the host field, a random one does not, no other field
    carries an address."""

    def test_documentation_literal_prints_in_a_host_and_random_does_not(self):
        self.assertIn("2001:db8:0:0:0:0:0:1", ev.show("host", "2001:db8:0:0:0:0:0:1", "host"))
        rand = ":".join(hexmix(4) for _ in range(8))
        self.assertNotIn(rand, ev.show("host", rand, "host"))
        self.assertNotIn(rand, ev.show("account", rand))
        for f in ("worker.account", "current_owner", "worker.model"):
            self.assertNotIn(rand, probe(f, rand), f)


class CodeIsNotCarvedOut(unittest.TestCase):
    """DEF-2: the `code` exception is gone; a genuine numeric or state value prints, the credential of similar shape hides."""

    def test_letters_under_code_are_hidden_on_every_form_and_through_the_cli(self):
        v = rnd(LOWER, 8)
        for text in ("code=%s", "code: %s", '{"code": "%s"}', "?code=%s", "https://x.example/cb?code=%s&state=1", "--code %s",
                     "oauth callback code=%s seen"):
            self.assertNotIn(v, ev.redact(text % v), text)
        for t in ("code=%s", "https://x.example/cb?code=%s&state=1"):
            self.assertNotIn(v, probe("coverage_gaps.0", t % v), t)
        for w in ("sunshine", "hunterxx", "qwertyui", "abcdefgh"):
            self.assertNotIn(w, ev.redact("code=%s" % w), w)
            self.assertNotIn(w, probe("coverage_gaps.0", "?code=%s" % w), w)

    def test_a_numeric_or_state_positive_prints_with_a_credential_negative_of_similar_shape(self):
        for pos in ("exit_code=2", "status_code=404", "code=ok", "code=ready", "exit code=2", '{"exit_code": 0}'):
            self.assertEqual(ev.redact(pos), pos, pos)
        for neg, v in (("code=4821", "4821"), ("code=123456", "123456"), ("?code=abcdefgh", "abcdefgh"), ("code=abc-def", "abc-def")):
            self.assertNotIn(v, ev.redact(neg), neg)

    def test_the_name_exception_is_removed_from_the_source(self):
        self.assertFalse(hasattr(ev, "_PLAIN_VALUE_NAMES"))
        with open(os.path.join(str(SKILL), "scripts", "envelope_validate.py")) as fh:
            self.assertNotIn("_PLAIN_VALUE_NAMES", fh.read())


class ShortValuesUnderUnlistedNames(unittest.TestCase):
    """DEF-3: no unlisted material and no number prints under a name outside the closed lists, whatever the value's size."""

    NAMES = ("mfa", "totp", "recoverycode", "mypass", "unlock", "seedphrase", "unlockpw", "foo", "xyzzy", "blob", "val", "data",
             "thesauce", "hush", "sekrit", "privateval", "access_pin", "card_pin", "pin", "dbpw", "k", "z1", "s")
    VALUES = ("1234", "0000", "4821", "123456", "abc-def", "xk2-9q7", "q-w-e-r-t-y", "ab-cd-ef",
              "golden-shadow-nested", "abc def")
    TEMPLATES = ("%s=%s", "%s: %s", "--%s %s", '{"%s":"%s"}', '%s="%s"', "?%s=%s", '{\\"%s\\": \\"%s\\"}', "&%s=%s")

    def test_class_hidden(self):
        bad = []
        for n in self.NAMES:
            for v in self.VALUES:
                for t in self.TEMPLATES:
                    if " " in v and '"' not in t:
                        continue  # an unquoted value ends at the space: only a quoted value carries a space
                    text = t % (n, v)
                    if v in ev.redact(text):
                        bad.append(text)
        self.assertEqual(bad, [], "%d leaks" % len(bad))

    def test_named_reproducers_through_the_cli(self):
        for text, v in (("mfa=4821 entered", "4821"), ("recoverycode=1234", "1234"), ("mypass=1234", "1234"),
                        ("seedphrase=abc-def", "abc-def"), ("--unlockpw 1234", "1234"), ('{"totp":"4821"}', "4821"),
                        ('blob="abc def"', "abc def")):
            self.assertNotIn(v, probe("coverage_gaps.0", text), text)

    def test_legitimate_numbers_states_and_words_still_print(self):
        for pos in ("count=1234", "pid=4242", "exit=0", "retry=3", "--timeout 30", '{"line": 12}', 'name="build ok"',
                    "status=running", "attempt=2", "port=22", "mode=ready", "head=a1b2c3d4e5f6", "retries=3 of 5"):
            self.assertEqual(ev.redact(pos), pos, pos)

    def test_every_positive_is_paired_with_a_negative_of_similar_shape(self):
        pairs = [("count=1234", "mfa=1234"), ("pid=4242", "mypass=4242"), ("exit=0", "seedphrase=nested-golden-shadow"),
                 ("retry=3", "recoverycode=1234"), ("--timeout 30", "--unlockpw 1234"), ('{"line": 12}', '{"totp": "4821"}'),
                 ('name="build ok"', 'blob="abc def"'), ("code=ok", "code=abcdefgh")]
        for pos, neg in pairs:
            self.assertEqual(ev.redact(pos), pos, pos)
            v = neg.replace('"', " ").replace("=", " ").replace(":", " ").replace("{", " ").replace("}", " ").split()
            for piece in v[-2:]:
                if piece not in ("blob", "totp", "code", "seedphrase", "recoverycode", "--unlockpw", "mfa", "mypass"):
                    self.assertNotIn(piece, ev.redact(neg), neg)


class FleetIdentifiers(unittest.TestCase):
    """DEF-4: real fleet names print in their own field; the credential of the same shape does not."""

    def test_positives(self):
        for f, v in (("current_owner", "controller"), ("worker.host", "carbon"), ("worker.host", "hetzner-hub"),
                     ("worker.account", "josephsyen"), ("worker.unit", "fleet-token-429-watch.service"),
                     ("worker.unit", "wm-build-tail9z8y7.service"), ("worker.host", "ryzen7"), ("current_owner", "aide"),
                     ("consumer.named", "controller")):
            self.assertIn(v, probe(f, v), (f, v))

    def test_negatives_of_similar_shape(self):
        h = hexmix(12)
        for f, v in (("current_owner", "controller-" + rnd(B62, 9)), ("worker.host", "carbon-" + rnd(B62, 9)),
                     ("worker.host", "hetzner-" + rnd(B62, 11) + "-hub"), ("worker.account", "josephsyen" + rnd(B62, 9)),
                     ("worker.unit", "fleet-token-%s.service" % rnd(B62, 10)), ("worker.unit", "fleet-token-%s-watch.service" % h),
                     ("worker.unit", "wm-build-tail%s.service" % rnd(B62, 9)), ("worker.unit", "token-%s.service" % hexmix(32)),
                     ("worker.account", "token-" + rnd(B62, 8))):
            self.assertNotIn(v, probe(f, v), (f, v[-6:]))

    def test_the_credential_path_is_not_opened(self):
        v = rnd(B62, 12)
        for text in ("token=" + v, "fleet-token=" + v, "controller_token=" + v, "carbon: password " + v):
            self.assertNotIn(v, ev.redact(text), text)


class RetainedReviewerProbes(unittest.TestCase):
    """The reviewer's own probes of re-review 10 (tests/probes/), run against this tree. pairs10 is the 37-pair identity and
    free-text table, pairs10b the 29 credential forms of the free-text gate, pos10 the legitimate-identity positives, g10 the
    bounded-shape table. The one pair that stays unmet is DISPUTED: unit `run-r<hex32>.scope` (the reviewer's negative) is
    the shape of a real systemd transient scope and the positive of test_review_fixes7_pairs.positives()."""

    def run_probe(self, name):
        r = subprocess.run([sys.executable, os.path.join(TESTS, "probes", name)], capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, name)
        return r.stdout

    def test_pairs10_all_but_the_disputed_scope_pair(self):
        out = self.run_probe("pairs10.py")
        self.assertIn("pairs ok 36/37", out)
        leaks = [l.split()[0] for l in out.splitlines() if "NEG-LEAK" in l]
        self.assertEqual(leaks, ["unit-hex"])
        for l in out.splitlines():
            if l.startswith("unit-hex"):
                self.assertIn("pos_prints=True", l)

    def test_pairs10b_every_credential_form_is_hidden_by_redact(self):
        rows = [l.split() for l in self.run_probe("pairs10b.py").splitlines() if len(l.split()) == 3]
        redact_rows = [r for r in rows if r[1] == "redact"]
        self.assertEqual(len(redact_rows), 30)
        self.assertEqual([r[0] for r in redact_rows if r[2] != "hid"], [])

    def test_pos10_only_the_person_handle_ids_stay_opaque(self):
        out = self.run_probe("pos10.py")
        opaque = [l.split()[-1].split("-")[0] for l in out.splitlines() if " OPQ " in l]
        self.assertEqual(sorted(opaque), ["alice", "jsy"])
        for needle in ("carbon", "josephsyen", "wm-build-tail9z8y7.service", "2001:db8:0:0:0:0:0:1"):
            self.assertTrue(any(" PRINT " in l and needle in l for l in out.splitlines()), needle)

    def test_g10_hash_shapes_are_opaque_in_the_account_row_and_task_columns(self):
        for l in self.run_probe("g10.py").splitlines():
            for key in ("vocab+hex32", "hex32 bare", "hex64 bare", "hex40 bare", "vocab+hex64", "hex12+vocab", "uuid bare",
                        "hex40 build", "num+id grammar"):
                if l.startswith(key + " "):
                    self.assertEqual(l.split()[-4:-1], ["opq", "opq", "opq"], key)


class ClosedGapsFoundByMutants11(unittest.TestCase):
    """Edges the mutant runner (mutants11.py) found open."""

    def test_unit_credential_word_needs_the_unit_suffix_and_vocabulary(self):
        for v in ("fleet-token-429-watch", "token-" + rnd(B62, 10) + ".service", "token-secret-watch.service",
                  "fleet-token-" + rnd(B62, 4) + "-watch.service"):
            self.assertNotIn(v, probe("worker.unit", v), v)
        self.assertIn("fleet-token-429-watch.service", probe("worker.unit", "fleet-token-429-watch.service"))
        self.assertNotIn("fleet-token-429-watch.service", probe("worker.account", "fleet-token-429-watch.service"))

    def test_a_vocabulary_word_with_a_long_suffix_is_not_an_identity_piece(self):
        self.assertIsNone(ev.ident("wm-build-tail" + rnd(B62, 14) + ".service"))
        self.assertEqual(ev.ident("wm-build-tail9z8y7.service"), "wm-build-tail9z8y7.service")

    def test_port_mapping_prints_only_under_a_port_name(self):
        self.assertEqual(ev.redact("docker run -p 8080:80 img"), "docker run -p 8080:80 img")
        for text in ("mypass=1234:5678", "mfa: 4821:1234", "--unlockpw 1234:5678"):
            self.assertNotIn("1234", ev.redact(text), text)

    def test_numbers_beside_a_vocabulary_word_are_bounded_and_pair_names_are_closed(self):
        self.assertEqual(ev.redact("ticket=WF-1663"), "ticket=WF-1663")
        self.assertNotIn("12345678", ev.redact("mypass=task-12345678"))
        for text in ("foo_bar=123456", "extra_info=12345678", "my_otp=123456", "lunch_order=4821"):
            self.assertNotIn(text.split("=")[1], ev.redact(text), text)

    def test_a_random_eight_group_literal_is_not_an_address_in_a_host(self):
        for _ in range(5):
            rand = ":".join(hexmix(4) for _ in range(8))
            self.assertNotIn(rand, probe("worker.host", rand))
        self.assertIn("2001:db8:0:0:0:0:0:1", probe("worker.host", "2001:db8:0:0:0:0:0:1"))

    def test_a_path_carries_at_most_two_ids(self):
        v = "/retained/%s/%s/%s/out.json" % (uu(), uu(), uu())
        self.assertNotIn(v, probe("result.artifact", v))
        v = "/retained/%s/result-%s/review-%s.json" % (uu(), hexmix(32), hexmix(12))
        self.assertNotIn(v, probe("result.artifact", v))
        two = "/retained/%s/%s/out.json" % (uu(), uu())
        self.assertIn(two, probe("result.artifact", two))
        ok = "/retained/%s/review-%s.json" % (uu(), hexmix(12))
        self.assertIn(ok, probe("result.artifact", ok))

    def test_digits_beside_an_id_are_bounded_in_a_unit_with_its_suffix(self):
        v = "codex-exec-%s-%s-%s.service" % (hexmix(12), rnd("0123456789", 7), rnd("0123456789", 7))
        self.assertNotIn(v, probe("worker.unit", v))
        ok = "codex-exec-%s-%s.service" % (hexmix(12), rnd("0123456789", 7))
        self.assertIn(ok, probe("worker.unit", ok))


class MutantRunnerExitStatus(unittest.TestCase):
    """DEF-5: the mutant runner exits non-zero on any survivor or NOT-APPLIED mutant, and prints every result."""

    def run_selftest(self, mode):
        r = subprocess.run([sys.executable, os.path.join(TESTS, "mutants11.py"), "--selftest", mode], capture_output=True, text=True,
                           timeout=300)
        return r.returncode, r.stdout

    def test_a_survivor_exits_non_zero(self):
        rc, out = self.run_selftest("survivor")
        self.assertNotEqual(rc, 0)
        self.assertIn("SURVIVED", out)

    def test_a_not_applied_mutant_exits_non_zero(self):
        rc, out = self.run_selftest("not-applied")
        self.assertNotEqual(rc, 0)
        self.assertIn("NOT-APPLIED", out)

    def test_a_caught_mutant_exits_zero(self):
        rc, out = self.run_selftest("caught")
        self.assertEqual(rc, 0, out)
        self.assertIn("caught", out)

    def test_the_corpus_covers_the_account_owner_model_shapes(self):
        for f in ("worker.account", "current_owner", "worker.model"):
            self.assertIn(f, ALL_FIELDS)
        self.assertIn("hex32", shapes())
        self.assertIn("uuid", shapes())


if __name__ == "__main__":
    unittest.main()
