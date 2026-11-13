"""Regression tests for the tenth independent exact-head review (re-review 9 of a01bf2f2): DEF-1 .. DEF-5.
Design under test: ONE trust gate on every output path, opaque by default. A piece of an identity, a queue-row field or a
free-text value prints only when it is in a fixed, enumerated vocabulary, a bounded number, a validated date or an EXACT id
grammar (uuid, hex of fixed length, ULID, IP literal), or is a small amount of unlisted material inside a TOTAL budget per
value; everything else is an opaque keyed ref (identities, row fields) or hidden (free text), whatever the NAME of the field
or pair is. A credential-name list remains only as an extra layer on free text.
Every legitimate identity is paired with a credential of similar shape (the reviewer's pairs9 table, 42 pairs, secrets inside
the old bounds). Source-only: synthetic envelopes, canaries assembled at run time from fragments, nothing printed
(assertion labels carry an index, never a canary)."""
import contextlib
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest

from helpers import FIX, SKILL, install_fixture_clock, remove_fixture_clock

import envelope_validate as ev
import queue_adapter as qa
import recommend as rc
import test_review_fixes3 as t3
from test_review_fixes7 import hx, setp, uuid
from test_review_fixes7_pairs import build, everything, shown
from test_review_fixes9 import adapter_out, queue_recommend_out

running, done, one = t3.running, t3.done, t3.one
SCRIPTS = str(SKILL / "scripts")


def setUpModule():
    install_fixture_clock()


def tearDownModule():
    remove_fixture_clock()


_R = random.Random(10)
B62 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
LOWER = "abcdefghijklmnopqrstuvwxyz"
HEXD = "0123456789abcdef"


def rnd(alpha, n):
    return "".join(_R.choice(alpha) for _ in range(n))


def groups(alpha, n, k, sep="-"):
    return sep.join(rnd(alpha, n) for _ in range(k))


def probe(field, v):
    """the full output (JSON + text) of the recommender for an envelope with `v` in the named field"""
    if field == "task_id":
        d = running()
        d["task_id"] = v
        d["evidence"][0]["task_id"] = v
        return everything(one(d))
    if field in ("current_owner", "target.repo", "target.branch", "target.head", "worker.account", "worker.model",
                 "evidence.0.ref", "coverage_gaps.0"):
        d = setp(running(), field, v)
        return everything(one(d))
    return everything(one(build(field, v)))


IDENT_FIELDS = ["worker.host", "worker.unit", "worker.child", "worker.session", "worker.invocation", "consumer.named",
                "result.artifact", "result.event", "task_id", "evidence.0.ref", "worker.account", "worker.model",
                "current_owner", "target.repo", "target.branch"]


class RowFieldsHaveNoPieceCount(unittest.TestCase):
    """DEF-1: the queue-row gate is the same closed gate as identities; any number of short pieces is bounded in total."""

    FIELDS = ("row_id", "owner", "claim", "status", "waits_on")

    def values(self):
        return [groups(B62, 5, 8), groups(B62, 5, 8, " "), groups("0123456789", 10, 4),
                # the author's own negatives of the same class
                groups(B62, 3, 12), groups(B62, 4, 6, " "), groups("0123456789", 7, 5), groups(LOWER, 5, 6, "."),
                groups(HEXD, 4, 10), groups(LOWER, 2, 20, "_")]

    def row(self, field, v):
        row = {"ask_id": "WF-1", "rev": 1, "owner": "r7", "row_id": "d-20261112-224051-r7-3b84", "status": "open", "seq": 7}
        row[field] = [v] if field == "waits_on" else v
        return [row]

    def test_many_short_pieces_are_opaque_in_every_row_field_on_both_paths(self):
        for field in self.FIELDS:
            for i, v in enumerate(self.values()):
                rows = self.row(field, v)
                a, q = adapter_out(rows), queue_recommend_out(rows)
                self.assertNotIn(v, a, "%s #%d adapter" % (field, i))
                self.assertNotIn(v, q, "%s #%d recommend" % (field, i))
                head = v.split()[0] if " " in v else v
                self.assertNotIn(head, a, "%s #%d first piece" % (field, i))
                self.assertIn("[opaque", a, "%s #%d" % (field, i))

    def test_a_hex_id_is_not_a_row_field_piece(self):
        v = "d-20261112-" + hx(12, 5)
        for field in ("row_id", "claim", "waits_on"):
            self.assertNotIn(hx(12, 5), adapter_out(self.row(field, v)), field)

    def test_legitimate_rows_keep_printing(self):
        rows = json.loads((FIX / "queue_rows.json").read_text())["rows"]
        out = adapter_out(rows)
        for needle in ("d-20261111-015556-controller-dd8d", "host:ryzen7:unit:r7-irv-a-221051@2026-11-12T22:11", "A1659"):
            self.assertIn(needle, out)
        for field, v in (("waits_on", "A1659"), ("status", "running"), ("owner", "hermes"), ("row_id", "d-20261112-224051-r7-3b84")):
            self.assertIn(v, adapter_out(self.row(field, v)), field)


class IdentitiesAreOpaqueByDefault(unittest.TestCase):
    """DEF-2: credential-sized values built from bounded shapes (random letters, hex groups, digit groups, passphrases,
    vocabulary plus a short random piece) are opaque in every identity field."""

    def values(self):
        return [groups(LOWER, 8, 1) + "-" + rnd(LOWER, 7) + "-" + rnd(LOWER, 7), groups(HEXD, 8, 4), groups(HEXD, 8, 4, "."),
                ":".join(rnd(HEXD, 4) for _ in range(8)), groups("0123456789", 10, 3), "purple-monkey-dishwasher",
                "build-" + rnd(B62, 8), "".join(_R.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + _R.choice(LOWER) for _ in range(11)),
                "task-" + rnd(LOWER, 12) + "-run", "build-4829173650-wf", "Winter2026", "Tiger7Lemon42Piano",
                # the author's own negatives of the same class
                "correct-horse-battery-staple-lamp", groups(HEXD, 6, 6), groups(B62, 4, 5), rnd(LOWER + "0123456789", 24),
                "sess-" + groups(HEXD, 8, 3), groups("0123456789", 6, 5, "."), "run-" + rnd(LOWER, 9) + "-" + rnd(LOWER, 9),
                groups(LOWER, 4, 6)]

    def test_credential_sized_values_never_print_in_any_identity_field(self):
        for fi, f in enumerate(IDENT_FIELDS):
            for i, v in enumerate(self.values()):
                out = probe(f, v)
                self.assertNotIn(v, out, "field %d value %d" % (fi, i))
                for piece in v.replace(".", "-").replace(":", "-").split("-"):
                    if len(piece) >= 6:
                        self.assertNotIn(piece, out, "field %d value %d piece" % (fi, i))

    def test_the_value_is_still_a_valid_identity_so_dispositions_do_not_change(self):
        v = groups(LOWER, 8, 1) + "-" + rnd(LOWER, 7) + "-" + rnd(LOWER, 7)
        self.assertEqual(one(build("worker.unit", v))["disposition"], one(build("worker.unit", "unit-a"))["disposition"])

    def test_the_budgets_of_the_gate(self):
        g = ev._gate_values
        self.assertTrue(g(["wm-build-20261113T104303Z-0007"]))
        self.assertFalse(g([groups(B62, 5, 3)]))
        self.assertFalse(g([groups(HEXD, 8, 2)], max_ids=1))
        self.assertTrue(g([groups(HEXD, 8, 2)], max_ids=2))
        self.assertFalse(g(["4829173650"]))
        self.assertFalse(g(["build-4829173650-wf"]))
        self.assertTrue(g(["pid-2659106"]))
        self.assertFalse(g(["zebra-" + hx(12, 7)]))
        self.assertTrue(g(["jsy@ryzen7"]))

    def test_the_vocabulary_is_enumerated_in_the_source_and_holds_no_credential_word(self):
        for w in ev._ID_WORDS:
            self.assertFalse(ev._cred_name(w), "vocabulary word %d" % len(w))
        for w in ("hunter", "dragon", "sunshine", "password", "token", "secret"):
            self.assertNotIn(w, ev._ID_WORDS)


NEG_SHAPES = [("bare lc8-7-7", lambda: "%s-%s-%s" % (rnd(LOWER, 8), rnd(LOWER, 7), rnd(LOWER, 7)), True, "A"),
              ("bare 4xhex8", lambda: groups(HEXD, 8, 4), True, "A"),
              ("sessionkey=plain", lambda: "sunshine", False, "sessionkey=%s"),
              ("pswd: plain", lambda: "dragon", False, "pswd: %s"),
              ("--dbpw digits8", lambda: "12345678", False, "run --dbpw %s now"),
              ("bare 3-word", lambda: "purple-monkey-dishwasher", True, "A"),
              ("bare digit10x3", lambda: groups("0123456789", 10, 3), True, "A"),
              ("token=b62-40", lambda: rnd(B62, 40), False, "token=%s"),
              ("password: hex32", lambda: rnd(HEXD, 32), False, "password: %s"),
              ("bare camel22", lambda: "".join(_R.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + _R.choice(LOWER) for _ in range(11)), True, "A"),
              ("bare b62-16", lambda: rnd(B62, 16), True, "A"),
              ("apikey=mixed8", lambda: "hunter22", False, "apikey=%s")]


def positives():
    H32, H12, H40, U = hx(32, 3), hx(12, 5), hx(40, 4), uuid()
    return [("worker.unit", "wm-build-%s.service" % H32), ("worker.unit", "coder@%s.service" % U),
            ("worker.unit", "run-r%s.scope" % H32), ("worker.unit", "wmbuild1663impl2.service"),
            ("worker.unit", "codex-exec-%s.service" % H12), ("worker.unit", "w-WF-1663-r7.service"),
            ("worker.host", "ryzen7"), ("worker.host", "redbaron.tail1a2b3.ts.net"),
            ("worker.host", "ip-10-0-3-4.ec2.internal"), ("worker.host", "jsy@ryzen7"), ("worker.host", "fe80::1%eth0"),
            ("worker.host", "10.20.30.40:22"), ("worker.child", "pid:4242"), ("worker.child", "child-%s" % H40),
            ("worker.child", "run-r%s.scope" % H12), ("worker.session", U), ("worker.session", H32),
            ("worker.session", "sess-" + U), ("worker.session", "01HZX3K9Q2M7V5N8R4T6W1Y0AB"), ("worker.session", "%9"),
            ("worker.invocation", H32), ("worker.invocation", "inv-20261113T104303Z-0007"),
            ("worker.invocation", "inv-%s" % H12), ("consumer.named", "verifier-%s" % H12), ("consumer.named", "hermes"),
            ("consumer.named", "ctl-seat-2"), ("consumer.named", "WF1663Impl"), ("target.head", H40), ("target.head", H12),
            ("target.repo", "j0yen/vibecode-kit"), ("target.branch", "r7/worker-fit-skill"),
            ("result.artifact", "/mnt/ssd/cargo-target/r7-wfr9-20261113/out/review.md"),
            ("result.artifact", "/retained/WF-1/result-%s.json" % H32), ("result.event", "evt-%s" % H32),
            ("task_id", "WF-20261113T104303Z-0007"), ("task_id", "task-%s" % H32), ("task_id", "WF1663Impl"),
            ("task_id", "01HZX3K9Q2M7V5N8R4T6W1Y0AB"), ("evidence.0.ref", "/mnt/ssd/cargo-target/r7-wfr9-20261113/out/probes.log"),
            ("current_owner", "r7"), ("worker.model", "claude-opus-5-5"), ("worker.account", "acct-a")]


class ReviewerPairTable9(unittest.TestCase):
    """The reviewer's pairs9 table (42 legitimate identities, each paired with an in-bound credential of similar shape):
    every positive prints and its paired negative stays hidden."""

    def test_forty_two_pairs(self):
        pos = positives()
        self.assertEqual(len(pos), 42)
        bad = []
        for i, (f, v) in enumerate(pos):
            label, mk, bare, tpl = NEG_SHAPES[i % len(NEG_SHAPES)]
            V = mk()
            shown_ok = v in probe(f, v)
            out = probe(f, V) if bare else probe("coverage_gaps.0", tpl % V)
            leaked = V in out
            if not shown_ok or leaked:
                bad.append((i, f, label, shown_ok, leaked))
        self.assertEqual(bad, [])

    def test_each_negative_shape_against_every_positive_field(self):
        """wider than the cycle: every negative shape in every identity field the positives use"""
        fields = sorted({f for f, _ in positives()})
        bad = []
        for label, mk, bare, tpl in NEG_SHAPES:
            V = mk()
            for f in fields:
                out = probe(f, V) if bare else probe("coverage_gaps.0", tpl % V)
                if V in out:
                    bad.append((label, f))
        self.assertEqual(bad, [])


NAMES = ("sessionkey authkey tkn jwt xtoken tok pswd passw0rd credz ssn pin otp masterpw pwdhash dbpw secrt sekret apitkn "
         "bearer2 authtok privatekey_b64 sshpass hunter signingkey seed mnemonic passcode cvv "
         "zzvault hushcode kryptonite lockword opensesame nonsensename loginphrase unsealer gatecode k9 pw1 zk").split()
VALUES = ["sunshine", "dragon", "12345678", "123456", "qwertyui", "pineapple", "Summer", "abcd", "lemon42", "x7k2p",
          "monkey", "99887766", "zebra5", "letmein", "Tiger7"]
PAIR_SHAPES = ["%s=%s", "%s: %s", "--%s %s", "%s = %s", '{"%s": "%s"}', "?%s=%s&x=1"]


class FreeTextPairsDoNotAskTheName(unittest.TestCase):
    """DEF-3: the value of a pair in free text is hidden unless it is closed vocabulary or a bounded number, whatever the name
    is: plain words and plain numbers under names nobody listed are hidden."""

    def test_plain_values_under_unlisted_names_are_hidden(self):
        bad = []
        for n in NAMES:
            for V in VALUES:
                for shape in PAIR_SHAPES:
                    if V in ev.redact(shape % (n, V)):
                        bad.append((n, V, shape))
        self.assertEqual(len(bad), 0, "%d leaks, first %s" % (len(bad), bad[:1] and [bad[0][0], bad[0][2]]))

    def test_the_reviewer_counter_example_code_is_hidden(self):
        self.assertNotIn("12345678", ev.redact("code=12345678"))
        self.assertNotIn("12345678", ev.redact("--code 12345678"))
        self.assertNotIn("99887766", ev.redact("code: 99887766"))

    def test_end_to_end_through_the_free_text_fields(self):
        for field in ("coverage_gaps.0", "next_action", "source.owner"):
            for n, V in (("sessionkey", "sunshine"), ("pswd", "dragon"), ("dbpw", "12345678"), ("masterpw", "qwertyui"),
                         ("authtok", "pineapple"), ("secrt", "lemon42"), ("code", "12345678")):
                d = setp(running(), field, "see %s=%s here" % (n, V)) if field != "source.owner" else running()
                if field == "source.owner":
                    d["coverage_gaps"] = ["see %s: %s here" % (n, V)]
                self.assertNotIn(V, everything(one(d)), "%s %s" % (field, n))

    def test_the_end_to_end_cli_prints_no_plain_value(self):
        for n, V in (("sessionkey", "qwertyui"), ("pswd", "dragon"), ("dbpw", "12345678")):
            d = running()
            d["coverage_gaps"] = ["note %s=%s" % (n, V)]
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
                json.dump({"envelopes": [d]}, fh)
            try:
                for script, args in (("envelope_validate.py", [fh.name]), ("recommend.py", [fh.name]),
                                     ("recommend.py", ["--format", "json", fh.name])):
                    r = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, script)] + args, capture_output=True, text=True)
                    self.assertNotIn(V, r.stdout + r.stderr, "%s %s" % (script, n))
            finally:
                os.unlink(fh.name)

    def test_ordinary_pairs_still_read(self):
        keep = "pid=4242 rc=0 exit=1 attempt=3 count=3 mode=fast state=RUNNING status=ok-2 ts=20261113T104303Z head=%s" % hx(12, 5)
        self.assertEqual(ev.redact(keep), keep)
        for s in ("seq=1257", "line: 40", "port=8080", "owner=r7", "worker.unit=wm-build.service"):
            self.assertEqual(ev.redact(s), s)

    def test_a_long_plain_number_prints_only_under_a_numeric_field_name(self):
        self.assertIn("2659106", ev.redact("pid=2659106"))
        self.assertNotIn("2659106", ev.redact("sessionkey=2659106"))


class CredentialProse(unittest.TestCase):
    """DEF-4: a credential word followed by its value in prose, with no separator."""

    CASES = [("the password is sunshine", "sunshine"), ("pass swordfish", "swordfish"), ("my pin 482917", "482917"),
             ("login with pw sunshine", "sunshine"), ("db password is sunshine", "sunshine"),
             ("the password was swordfish.", "swordfish"), ("passwd swordfish", "swordfish"),
             ("password is hunter22", "hunter22"), ("the token is claude", "claude"), ("use secret pineapple now", "pineapple"),
             ("otp 482917", "482917"), ("the passcode is 7788", "7788"), ("set pswd to dragon", "dragon"),
             ("apikey is Summer2026", "Summer2026"), ("the passphrase is correct", "correct")]

    def test_the_word_after_a_credential_word_is_hidden(self):
        for i, (text, v) in enumerate(self.CASES):
            self.assertNotIn(v, ev.redact(text), "case %d" % i)
            self.assertNotIn(v, ev.redact(text.upper()) if not v.isdigit() else "", "case %d upper" % i)

    def test_end_to_end(self):
        base = everything(one(running()))
        for i, (text, v) in enumerate(self.CASES):
            if v in base:
                continue  # a word the unmodified output already carries cannot show a leak
            d = running()
            d["coverage_gaps"] = [text]
            d["next_action"] = text
            self.assertNotIn(v, everything(one(d)), "case %d" % i)

    def test_ordinary_prose_with_those_words_still_reads(self):
        for s in ("token refresh failed", "the password is required", "the secret is missing", "pass the test", "pin 1",
                  "bypass the check", "tokens used 5", "the token timer is running"):
            self.assertEqual(ev.redact(s), s, s)


class UsageLinesAreRedacted(unittest.TestCase):
    """DEF-5: the usage and UNREADABLE lines of the CLIs carry no credential from argv (mutant m9)."""

    def run_cli(self, script, args):
        r = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, script)] + args, capture_output=True, text=True)
        return r.stdout + r.stderr

    def test_recommend_usage_line_hides_a_credential_option_and_a_long_run(self):
        run = rnd(B62, 40)
        for args in (["--" + "pass" + "word=" + run], ["--" + "tok" + "en=" + run, "x.json"], ["a.json", run], ["a.json", "b.json", run]):
            self.assertNotIn(run, self.run_cli("recommend.py", args))

    def test_adapter_usage_line_hides_a_credential_option_and_a_long_run(self):
        run = rnd(B62, 40)
        for args in (["--" + "pass" + "word=" + run], ["a.json", "b", run]):
            self.assertNotIn(run, self.run_cli("queue_adapter.py", args))

    def test_in_process_usage_errors_are_redacted(self):
        run = rnd(B62, 40)
        for mod, argv in ((rc, ["--sec" + "ret=" + run]), (qa, ["--sec" + "ret=" + run]), (rc, ["f.json", "g.json", run])):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                mod.main(list(argv))
            self.assertNotIn(run, buf.getvalue())

    def test_an_unreadable_file_message_is_redacted(self):
        run = rnd(B62, 40)
        out = self.run_cli("recommend.py", ["/nonexistent/" + run + ".json"])
        self.assertNotIn(run, out)


class GateEdgesFoundByMutants(unittest.TestCase):
    """DEF-5: one test per source change of the gate that the first tests of this file did not catch (the reviewer's mutants
    m1..m9 and the author's analogues m10..m32 are run by probes/mut10.py)."""

    def test_random_dns_labels_are_opaque_in_a_host_field(self):
        for i, (alpha, n, tld) in enumerate(((LOWER + "0123456789", 18, "net"), (LOWER, 19, "io"), (LOWER + "0123456789", 12, "dev"))):
            v = ".".join(rnd(alpha, n) for _ in range(3)) + "." + tld
            out = probe("worker.host", v)
            self.assertNotIn(v, out, "host %d" % i)
            for label in v.split(".")[:-1]:
                self.assertNotIn(label, out, "host %d label" % i)

    def test_a_credential_word_glued_to_a_value_in_free_text_is_a_composite(self):
        for i, s in enumerate(("token-" + rnd(B62, 8), "apikey-task-" + rnd(B62, 8), "secret_run_" + rnd(LOWER, 16),
                               "bearer-" + rnd(LOWER, 12), "token" + rnd(B62, 10))):
            V = s.replace("apikey-task-", "").replace("secret_run_", "").replace("bearer-", "").replace("token-", "")
            V = V[5:] if s.startswith("token") and "-" not in s else V
            self.assertNotIn(V, ev.redact("see " + s + " now"), "case %d" % i)

    def test_a_queue_row_carries_no_id_grammar_even_beside_vocabulary(self):
        for field in ("row_id", "claim", "waits_on", "status"):
            row = {"ask_id": "WF-1", "rev": 1, "owner": "r7", "row_id": "d-1", "status": "open"}
            v = "wm-" + hx(12, 9)
            row[field] = [v] if field == "waits_on" else v
            self.assertNotIn(hx(12, 9), adapter_out([row]), field)

    def test_a_queue_row_value_keeps_the_credential_layers(self):
        """a value the closed gate accepts by size (two short pieces) but a credential layer names is hidden"""
        for v in ("ssh://a:b@c", "ftp://u:p@h"):
            self.assertTrue(ev._gate_values([v]), v)  # inside the budget: only the credential layer refuses it
            self.assertIn("[opaque row ", ev.show_row("row", v), v)
            for field in ("owner", "row_id", "claim"):
                row = {"ask_id": "WF-1", "rev": 1, "owner": "r7", "row_id": "d-1", "status": "open"}
                row[field] = v
                self.assertNotIn(v, adapter_out([row]), field)

    def test_a_digits_only_run_is_never_an_id_grammar(self):
        for v in ("wm12345678", "run1234567890", "task123456789012", "id99887766"):
            self.assertNotIn(v, probe("worker.unit", v + ".service"), v)
            self.assertFalse(ev._gate_values([v]), v)

    def test_a_compressed_ipv6_literal_has_a_bounded_number_of_groups(self):
        for v in ("fe80::1%eth0", "::1", "2001:db8::1", "fe80::a1b2:c3d4:1"):
            self.assertTrue(ev._gate_values([v]), v)
        for v in ("2001:db8:85a3::8a2e:370:7334", "ac60:992a:c792:dba9:b936:fbc9:69cc:bbd6"):
            self.assertFalse(ev._gate_values([v]), v)

    def test_a_run_of_many_vocabulary_words_is_not_one_vocabulary_piece(self):
        self.assertTrue(ev._gate_values(["wmbuild1663impl2"]))
        for v in ("buildtaskmergeprodtest", "claudebuildtaskreviewmerge", "workerhostqueuebranchcommitdeploy"):
            self.assertFalse(ev._gate_values([v]), v)

    def test_a_credential_sized_name_value_chunk_run_is_not_an_identity(self):
        self.assertTrue(ev._name_value_ok("pid=1&rev=2&step=3"))
        self.assertFalse(ev._name_value_ok("pid=1&rev=2&step=3&phase=4"))

    def test_hex_ids_have_exact_lengths(self):
        for n in (7, 8, 9, 10, 11, 12, 32, 40, 64):
            self.assertTrue(ev._gate_values(["task-" + hx(n, 5)]), n)
        for n in (6, 13, 14, 16, 20, 24, 28, 31, 33, 36, 48, 56, 63, 65):
            self.assertFalse(ev._gate_values(["task-" + hx(n, 5)]), n)

    def test_free_unlisted_material_has_a_total_budget(self):
        self.assertIn("ab-cd", ev.redact("tag=ab-cd"))
        for v in ("ab-cd-ef-gh-ij", "a1-b2-c3-d4-e5-f6", "q1-w2-e3-r4-t5-y6-u7"):
            self.assertNotIn(v, ev.redact("tag=" + v), v)

    def test_a_schema_name_does_not_make_any_value_a_hex_id(self):
        for n in ("head", "sha", "commit", "rev", "digest", "hash", "oid"):
            for v in ("sunshine", "dragon", "12345678", "hunter22", "zebra5"):
                if v.isdigit() and n in ev._NUMERIC_NAMES:
                    continue  # a number under a numeric field name (rev=12345678) is a number
                self.assertNotIn(v, ev.redact("%s=%s" % (n, v)), (n, v))
            self.assertIn(hx(12, 5), ev.redact("%s=%s" % (n, hx(12, 5))), n)

    def test_single_letters_are_free_only_between_numbered_pieces(self):
        self.assertTrue(ev._gate_values(["/mnt/ssd/cargo-target/r7-x-20261113/out"]))
        self.assertFalse(ev._gate_values(["q-e-t-y-u-o-p-k-m-z-x-b"]))
        self.assertFalse(ev._gate_values(["k.m.v.z.b.n.x.q.j.h.d.f.g"]))

    def test_uuids_count_against_the_id_budget(self):
        u1, u2, u3 = uuid(1), uuid(2), uuid(3)
        self.assertTrue(ev._gate_values(["sess-" + u1], max_ids=1))
        self.assertFalse(ev._gate_values(["sess-%s-%s" % (u1, u2)], max_ids=1))
        self.assertTrue(ev._gate_values(["sess-%s-%s" % (u1, u2)], max_ids=2))
        self.assertFalse(ev._gate_values(["sess-%s-%s-%s" % (u1, u2, u3)], max_ids=2))
        self.assertNotIn(u1, probe("worker.session", "sess-%s-%s" % (u1, u2)))

    def test_the_number_of_pieces_is_bounded(self):
        self.assertTrue(ev._gate_values(["-".join(["build"] * 30)]))
        self.assertFalse(ev._gate_values(["-".join(["build"] * 60)]))


if __name__ == "__main__":
    unittest.main()
