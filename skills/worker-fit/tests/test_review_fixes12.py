"""Regression tests for the twelfth independent exact-head review (re-review 11 of 74551e2c): DEF-1 .. DEF-5 and the unconfirmed
concerns. Design under test (unchanged): FIELD-AWARE validated identities. Each identity field has its OWN grammar; a value prints
only through the ONE trust gate (that field's grammar AND the closed vocabulary / bounds), else an opaque keyed ref. DEF-4 is closed
by per-field grammar (effort enum, systemd unit, peer id, branch, owner/repo, session), not by words; DEF-5 by a cap on vocabulary
words per identity value, stated in SKILL.md and compared with the code here.
Every legitimate value is paired with a credential of similar shape. Source-only: synthetic envelopes, canaries assembled at run
time from fragments and never printed (assertion labels carry an index or a template, never a canary)."""
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import unittest

from helpers import SKILL, install_fixture_clock, remove_fixture_clock

import envelope_validate as ev
import test_review_fixes3 as t3
from test_review_fixes10 import probe

running = t3.running
TESTS = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(str(SKILL), "scripts")
RECOMMEND = os.path.join(SCRIPTS, "recommend.py")


def setUpModule():
    install_fixture_clock()


def tearDownModule():
    remove_fixture_clock()


_R = random.Random(12)
HEXD = "0123456789abcdef"
LOWER = "abcdefghijklmnopqrstuvwxyz"
B62 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
DIG = "0123456789"


def rnd(alpha, n):
    return "".join(_R.choice(alpha) for _ in range(n))


def hexmix(n):
    while True:
        s = rnd(HEXD, n)
        if any(c.isdigit() for c in s) and any(c.isalpha() for c in s):
            return s


def uu():
    return "-".join(hexmix(k) for k in (8, 4, 4, 4, 12))


def num(n):
    return str(_R.randint(1, 9)) + rnd(DIG, n - 1)


# ---------------------------------------------------------------------------------------------------------------- DEF-1
CRED_STEMS = ("mfa", "recovery", "unlock", "totp", "code", "verification", "signing", "foo", "xyzzy", "hush", "mypass", "dbpw",
              "otp", "pin", "password", "token", "secret", "apikey", "seed", "key", "backup", "card", "login", "vault")
NUM_SUFFIXES = ("count", "size", "bytes", "seconds", "lines", "total", "length", "number", "version", "index", "retries", "attempts",
                "timeout", "duration", "limit", "wait", "seq", "delay", "interval", "max", "min", "age", "ttl", "num", "id")
FORMS = ("%s=%s", "%s: %s", "--%s %s", '{"%s": "%s"}', '%s="%s"', "?%s=%s&state=1", '{"%s": %s}')


class NumberUnderANumericSuffix(unittest.TestCase):
    """DEF-1: a number never prints under a name only because it ENDS in a numeric word: every credential stem x every numeric
    suffix x short and long values x every form. A number prints only under a name of the closed numeric list."""

    def test_class_hidden_for_long_values(self):
        bad = []
        for stem in CRED_STEMS:
            for suf in NUM_SUFFIXES:
                for join in ("_", "-", "", "."):
                    name = stem + join + suf
                    for v in (num(3), num(4), num(6), num(10)):
                        for f in FORMS:
                            if v in ev.redact(f % (name, v)):
                                bad.append(f % (name, "<%d digits>" % len(v)))
        self.assertEqual(bad, [], "%d leaks, first: %s" % (len(bad), bad[:5]))

    def test_camel_case_names_too(self):
        for stem in ("mfa", "recovery", "unlock", "totp"):
            for suf in ("Number", "Count", "Limit", "Index", "Timeout"):
                v = num(8)
                for f in FORMS[:4]:
                    self.assertNotIn(v, ev.redact(f % (stem + suf, v)), f % (stem + suf, "<8 digits>"))

    def test_the_closed_numeric_names_still_print_long_numbers(self):
        for pos in ("line_number=482917", "retry_count=4", "max_retries=3", "file_size=1048576", "pid=482917", "seq=4829175",
                    "timeout_seconds=300", "exit_code=2", "status_code=404", "lineCount=12345", "--timeout 30", "total=1234567",
                    "elapsed_seconds=86400", '{"line_number": 482917}', "byte_count=123456", "retry-count=4",
                    "offset=1048576", "epoch=1789000000"):
            self.assertEqual(ev.redact(pos), pos, pos)

    def test_every_positive_has_a_negative_of_the_same_shape(self):
        for pos, neg, v in (("line_number=482917", "recovery_number=482917", "482917"), ("retry_count=4821", "mfacount=4821", "4821"),
                            ("file_size=1048576", "unlock_limit=1048576", "1048576"), ("max_retries=3000", "mfa_timeout=3000", "3000"),
                            ("pid=482917", "totp_index=482917", "482917")):
            self.assertEqual(ev.redact(pos), pos, pos)
            self.assertNotIn(v, ev.redact(neg), neg)

    def test_the_source_has_no_suffix_rule(self):
        self.assertFalse(hasattr(ev, "_NUMERIC_SUFFIX"))
        for name in ("mfa_number", "recovery_number", "mfacount", "unlock_limit", "totp_index", "mfa_timeout", "mfa_wait", "mfa_seq"):
            self.assertFalse(ev._numeric_name(name), name)
        for name in ("line_number", "retry_count", "max_retries", "file_size", "pid", "lineCount", "exit_code", "status_code"):
            self.assertTrue(ev._numeric_name(name), name)


# ---------------------------------------------------------------------------------------------------------------- DEF-2
PROSE_NAMES = ("api_key", "api key", "apikey", "secret key", "private key", "client_secret", "clientSecret", "client secret",
               "access_token", "access token", "X-Auth-Token", "creds", "auth", "key", "the key", "mfa_secret", "signing key",
               "password", "token", "secret", "passphrase", "pin", "bearer", "credentials", "refresh_token", "session_key")
PROSE_JOINS = (" ", " is ", " is: ", ": ", " = ", " := ", " set to ", " was ", ' is "', " is '", ' "')


class CredentialCompoundsInProse(unittest.TestCase):
    """DEF-2: a credential-named compound followed by its value hides the value across separator forms and value lengths."""

    def value(self, n):
        """a value whose characters occur in no name or joiner of the table, so a substring test cannot be fooled by a short value;
        under two characters only capitals (a one- or two-digit number is a small count by size)"""
        return rnd("QZJKVHGBNM" + ("" if n < 3 else DIG), n)

    def test_class_hidden(self):
        bad = []
        for name in PROSE_NAMES:
            for join in PROSE_JOINS:
                for n in (1, 2, 3, 6, 12, 18, 24):
                    v = self.value(n)
                    closer = join[-1] if join[-1] in "\"'" else ""
                    for lead in ("", "the ", "my "):
                        text = "%s%s%s%s%s" % (lead, name, join, v, closer)
                        if v in ev.redact(text):
                            bad.append((name, join, n))
        self.assertEqual(bad, [], "%d leaks, first: %s" % (len(bad), bad[:6]))

    def test_value_in_a_sentence_and_in_the_cli(self):
        for t in ("the api_key is %s and then it failed", "use api key %s for the build", "client_secret %s was rotated",
                  "private key %s", "the access_token is %s."):
            v = self.value(12)
            self.assertNotIn(v, ev.redact(t % v), t)
            self.assertNotIn(v, probe("coverage_gaps.0", t % v), t)

    def test_a_bearer_header_in_prose_hides_the_token_after_the_word_bearer(self):
        for text in ("bearer: Bearer %s", "bearer is Bearer %s", "bearer Bearer %s", "Bearer %s", "bearer is %s"):
            v = self.value(12)
            self.assertNotIn(v, ev.redact(text % v), text)

    def test_state_words_and_ordinary_prose_still_print(self):
        for pos in ("the build is ok", "the api_key is missing", "private key rotated", "client_secret required",
                    "the key is not set", "auth failed", "creds unknown", "the api key is stored in the vault",
                    "secret key present", "api key not found"):
            self.assertEqual(ev.redact(pos), pos, pos)


# ---------------------------------------------------------------------------------------------------------------- DEF-3
class UsageErrorEchoIsDeterministic(unittest.TestCase):
    """DEF-3: the usage error names each extra file. The test uses fixed, legitimately printable names (a relative path under a
    temp cwd), so no random path suffix decides whether redaction hides it."""

    def test_fixed_names_are_printable_by_the_tools_own_gate(self):
        for name in ("extra-one.json", "extra-two.json", "a.json", "b.json"):
            self.assertEqual(ev.redact_tool(name), name)
            self.assertEqual(ev.redact_tool("UNREADABLE usage: extra argument(s) not evaluated: " + name),
                             "UNREADABLE usage: extra argument(s) not evaluated: " + name)

    def test_extra_files_are_named_through_the_cli_with_fixed_names(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("one.json", "extra-one.json", "extra-two.json"):
                with open(os.path.join(d, n), "w") as fh:
                    json.dump([running()], fh)
            for fmt in ("json", "text"):
                r = subprocess.run([sys.executable, "-I", RECOMMEND, "--format", fmt, "--now", "2026-11-13T07:00:00Z", "one.json",
                                    "extra-one.json", "extra-two.json"], capture_output=True, text=True, cwd=d)
                self.assertEqual(r.returncode, 2, fmt)
                out = r.stdout + r.stderr
                self.assertIn("extra-one.json", out, fmt)
                self.assertIn("extra-two.json", out, fmt)

    def test_the_old_test_no_longer_asserts_on_random_paths(self):
        with open(os.path.join(TESTS, "test_review_fixes4.py")) as fh:
            src = fh.read()
        body = src.split("def test_extra_files_are_a_usage_error_naming_them", 1)[1].split("    def test_", 1)[0]
        self.assertNotIn("tmp_json(", body)
        self.assertIn("cwd=cwd", body)
        self.assertIn('"a.json"', body)


# ---------------------------------------------------------------------------------------------------------------- DEF-4
def lc(n):
    return rnd(LOWER, n)


def b62(n):
    return rnd(B62, n)


class PerFieldGrammars(unittest.TestCase):
    """DEF-4: each legitimate fleet value prints in its OWN field, and a credential of similar shape in the same field is an opaque
    ref. Positives are the reviewer's list (probes/pos11.py) plus siblings of each grammar."""

    def pos(self):
        U = uu()
        return [("worker.effort", "ident", v) for v in ("medium", "normal", "default", "minimal", "low", "high", "xhigh", "max")] + [
            ("worker.unit", "ident", v) for v in (
                "wm-decide-regrade.service", "agorabus-reap.timer", "memlog-witness.service", "fleet-merge.timer",
                "seat-tick@rb.service", "tmux-spawn-%s.scope" % U, "app-gnome-Terminal-12345.scope", "swarm-decide-regrade.timer",
                "wm-build-r7-wfr11-20261113.service", "fleet-token-429-watch.service", "claude-code-session-1234.scope")] + [
            ("consumer.named", "ident", v) for v in (
                "claude-3947245-r7-a1303rv8-20261113-worker", "claude-2927248-r7-wfr11-20261113", "claude-182735-r7-a1296p5rv5-20261113-worker",
                "claude-569512-r7-a1572rv1-20261113", "hermes-aae-worker")] + [
            ("current_owner", "ident", v) for v in ("claude-3947245-r7-a1303rv8-20261113", "claude-1094579-r7-a17rv2-20261113")] + [
            ("target.branch", "ident", v) for v in ("feat/A1663-repair-11", "r7/wfr11-20261113", "worker-fit-skill", "fix/A1663-repair-12")] + [
            ("task_id", "ident", v) for v in ("a1303rv8", "a1296p5rv5", "a17rv2", "wfr11", "A1663")] + [
            ("worker.session", "ident", v) for v in ("session-" + U, "sess-3947245", "sess-" + U)] + [
            ("worker.model", "ident", v) for v in ("claude-opus-5-5[1m]", "claude-opus-5-5", "claude-fable-5-1")] + [
            ("target.repo", "ident", v) for v in ("j0yen/swarm-decide", "j0yen/vibecode-kit", "j0yen/mcphost")] + [
            ("result.artifact", "path", "/home/jsy/Notes/hermes-director-bootstrap-proof-20261108.json")]

    def test_positives_print_in_their_own_field(self):
        bad = [(f, v) for f, k, v in self.pos() if v not in ev.show(f, v, k)]
        self.assertEqual(bad, [])

    def test_the_reviewers_positive_table_prints_whole(self):
        r = subprocess.run([sys.executable, os.path.join(TESTS, "probes", "pos11.py")], capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("positives opaque: 0/70", r.stdout)

    def test_the_end_to_end_cli_prints_the_effort_and_a_unit(self):
        for f, v in (("worker.effort", "medium"), ("worker.unit", "wm-decide-regrade.service"), ("worker.unit", "agorabus-reap.timer"),
                     ("target.repo", "j0yen/swarm-decide")):
            self.assertIn(v, probe(f, v), (f, v))

    def neg(self):
        U = uu()
        out = []
        for _ in range(12):
            out += [("worker.effort", "ident", b62(12)), ("worker.effort", "ident", "medium-" + b62(10)), ("worker.effort", "ident", lc(10)),
                    ("worker.unit", "ident", "wm-decide-%s.service" % b62(14)), ("worker.unit", "ident", "agorabus-%s.timer" % lc(14)),
                    ("worker.unit", "ident", "memlog-%s.service" % b62(12)), ("worker.unit", "ident", "%s.service" % lc(16)),
                    ("consumer.named", "ident", "claude-3947245-r7-%s-20261113-worker" % b62(10)),
                    ("consumer.named", "ident", "claude-3947245-r7-%s-20261113-worker" % lc(12)),
                    ("current_owner", "ident", "claude-3947245-r7-%s-20261113" % b62(12)),
                    ("target.branch", "ident", "feat/A1663-%s" % b62(14)), ("target.branch", "ident", "feat/%s" % lc(16)),
                    ("target.branch", "ident", "feat/A1663-%s-%s" % (lc(12), lc(12))),
                    ("task_id", "ident", b62(10)), ("task_id", "ident", rnd(LOWER + DIG, 12)),
                    ("worker.session", "ident", "session-" + b62(24)), ("worker.session", "ident", "session-" + hexmix(40)),
                    ("worker.model", "ident", "claude-" + b62(14)),
                    ("target.repo", "ident", "j0yen/%s" % lc(14)), ("target.repo", "ident", "%s/swarm-decide" % b62(14)),
                    ("target.repo", "ident", "%s/%s" % (lc(10), lc(10)))]
        out.append(("worker.session", "ident", "session-" + hexmix(64)))
        out.append(("worker.session", "ident", "session-" + U))  # a session-<uuid> is the session field's own template: prints (positive)
        return out

    def test_negatives_of_similar_shape_are_opaque(self):
        bad = []
        for f, k, v in self.neg():
            if v.startswith("session-") and re.fullmatch(r"session-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", v):
                continue
            if v in ev.show(f, v, k):
                bad.append((f, len(v)))
        self.assertEqual(bad, [], "%d leaks, first %s" % (len(bad), bad[:5]))

    def test_random_lowercase_pieces_are_not_words(self):
        """The word grammar of a unit/branch/repo name is phonotactic and bounded: a random lowercase run of 10 letters passes in about
        2 % of draws, of 12 in under 1 %, and none of 13 or more (a word has at most 12 letters)."""
        for n, limit in ((6, 0.12), (8, 0.06), (10, 0.03), (12, 0.015), (13, 0.0), (16, 0.0)):
            hits = sum(1 for _ in range(4000) if ev._pronounceable(lc(n)))
            self.assertLessEqual(hits / 4000.0, limit, n)
        for w in ("decide", "regrade", "memlog", "witness", "agorabus", "repair", "claude", "terminal", "director", "bootstrap"):
            self.assertTrue(ev._pronounceable(w), w)

    def test_effort_is_an_enum(self):
        for v in ("medium", "normal", "default", "minimal"):
            self.assertIn(v, ev.show("worker.effort", v))
        for v in ("mediumx", "med1um", "hunter2", "sunshine", "abcdef"):
            self.assertNotIn(v, ev.show("worker.effort", v), v)

    def test_a_peer_id_template_is_strict(self):
        pid = "claude-3947245-r7-a1303rv8-20261113-worker"
        self.assertIn(pid, ev.show("consumer", pid))
        for neg in ("claude-3947245-r7-%s-20261113-worker" % b62(10), "claude-%s-r7-a1303rv8-20261113-worker" % b62(10),
                    "claude-3947245-r7-a1303rv8-%s-worker" % b62(8), pid + "-" + b62(12), "claude-3947245-r7-a1303rv8-a1303rv8-20261113",
                    "claude-3947245-r7-a1303rv8-20261113-worker-" + lc(12)):
            self.assertNotIn(neg, ev.show("consumer", neg), neg)

    def test_the_grammar_does_not_apply_to_an_unknown_label_or_a_row(self):
        for v in ("wm-decide-regrade.service", "claude-3947245-r7-a1303rv8-20261113-worker", "j0yen/swarm-decide"):
            self.assertNotIn(v, ev.show("zzz-unknown", v))


# ---------------------------------------------------------------------------------------------------------------- DEF-5
class VocabularyWordsAreCapped(unittest.TestCase):
    """DEF-5: a value made only of vocabulary words prints only up to the cap; a passphrase of more words is an opaque ref, in every
    identity field. SKILL.md states the cap the code has."""

    FIELDS = (("worker.account", "ident"), ("current_owner", "ident"), ("worker.unit", "ident"), ("consumer.named", "ident"),
              ("target.branch", "ident"), ("target.repo", "ident"), ("worker.child", "ident"), ("worker.model", "ident"),
              ("task_id", "ident"), ("worker.host", "host"), ("result.artifact", "path"))
    WORDS = sorted(w for w in ev._ID_WORDS if w.isalpha() and len(w) >= 3 and not ev._cred_name(w) and w not in ev._STRUCT_WORDS)

    def passphrase(self, n, sep="-"):
        return sep.join(_R.sample(self.WORDS, n))

    def test_a_long_vocabulary_passphrase_is_opaque_in_every_field(self):
        bad = []
        cap = ev._MAX_VOCAB_WORDS
        for f, k in self.FIELDS:
            for n in (cap + 1, cap + 2, 8, 10, 16):
                for _ in range(40):
                    for sep in ("-", "_", ".", "/"):
                        p = self.passphrase(n, sep)
                        if p in ev.show(f, p, k):
                            bad.append((f, n, sep))
        self.assertEqual(bad, [], "%d leaks, first: %s" % (len(bad), bad[:5]))

    def test_through_the_cli_for_the_reviewers_three_fields(self):
        p = self.passphrase(12)
        for f in ("worker.account", "current_owner", "worker.unit"):
            self.assertNotIn(p, probe(f, p + (".service" if f == "worker.unit" else "")), f)

    def test_the_cap_and_a_short_name_print(self):
        for f, k in (("worker.unit", "ident"), ("current_owner", "ident"), ("consumer.named", "ident")):
            ok = "-".join(("wm", "build", "queue", "fleet"))
            self.assertIn(ok, ev.show(f, ok, k), f)

    def test_the_documented_cap_is_the_code_cap(self):
        with open(os.path.join(str(SKILL), "SKILL.md")) as fh:
            doc = fh.read()
        m = re.search(r"at most (\w+) vocabulary words", doc)
        self.assertIsNotNone(m, "SKILL.md states the cap")
        words = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
        self.assertEqual(words.get(m.group(1), None) or int(m.group(1)), ev._MAX_VOCAB_WORDS)


# ----------------------------------------------------------------------------------------------------------- the concerns
class UnconfirmedConcerns(unittest.TestCase):
    def test_the_opaque_ref_does_not_depend_on_the_interpreter_string_hash(self):
        """A fixed PYTHONHASHSEED makes str hashing deterministic; the ref must not be a function of hash(): HMAC with a per-process key."""
        import builtins
        real = builtins.hash
        builtins.hash = lambda x: 7
        try:
            a, b = ev.opaque("account", "alpha-value-1"), ev.opaque("account", "beta-value-2")
        finally:
            builtins.hash = real
        self.assertNotEqual(a, b)

    def test_refs_differ_per_process_under_a_fixed_hash_seed(self):
        code = "import sys; sys.path.insert(0, %r); import envelope_validate as ev; print(ev.opaque('account', 'same-value'))" % SCRIPTS
        outs = set()
        for _ in range(3):
            r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, env={"PYTHONHASHSEED": "0"})
            outs.add(r.stdout.strip())
        self.assertEqual(len(outs), 3)
        for o in outs:
            self.assertRegex(o, r"^\[opaque account [0-9a-f]{8}\]$")

    def test_equal_values_equal_refs_inside_a_run_and_labels_separate_them(self):
        self.assertEqual(ev.opaque("account", "x1"), ev.opaque("account", "x1"))
        self.assertNotEqual(ev.opaque("account", "x1"), ev.opaque("owner", "x1"))

    def test_target_head_is_a_hex_id_not_any_digit_run(self):
        for v in ("4111111111111111", "1234567", "12345678901234567890", "9" * 40, "0" * 64, "4" * 13):
            self.assertNotIn(v, ev.show("head", v, "sha"), v)
            self.assertNotIn(v, probe("target.head", v), v)
        for v in ("a9d096aa9f8d8cc45f9398375d1593579f8565ec", "74551e2", "74551e2c1813", hexmix(64), hexmix(40)):
            self.assertIn(v, ev.show("head", v, "sha"), v)

    def test_a_name_ending_in_a_hash_word_is_not_a_schema_field(self):
        for name in ("mfa-hash", "signing-rev", "unlock-digest", "mfa.hash", "my-head", "blob-sha", "x.digest", "secret-commit", "api-oid"):
            for v in (hexmix(12), hexmix(32), hexmix(56), hexmix(64)):
                self.assertNotIn(v, ev.redact("%s=%s" % (name, v)), name)
                self.assertNotIn(v, ev.redact('{"%s": "%s"}' % (name, v)), name)
        for pos in ("head=a1b2c3d4e5f6", "target.head=" + hexmix(40), "sha256=" + hexmix(64), "commit=" + hexmix(12), "rev=" + hexmix(12)):
            self.assertEqual(ev.redact(pos), pos, pos)

    def test_an_ipv6_literal_with_random_groups_is_not_a_host(self):
        for _ in range(60):
            g = [hexmix(4) for _ in range(4)]
            for lit in (":".join(g) + "::", "::" + ":".join(g), ":".join(g[:2]) + "::" + ":".join(g[2:]), "fe80::" + ":".join(g[:3])):
                self.assertNotIn(lit, ev.show("host", lit, "host"), lit)
        for ok in ("fe80::1%eth0", "2001:db8::1", "2001:db8:0:0:0:0:0:1", "fd00::2"):
            self.assertIn(ok, ev.show("host", ok, "host"), ok)


class GrammarEdges(unittest.TestCase):
    """Edges of the per-field grammars found while closing DEF-4 / DEF-5."""

    def test_structure_words_are_free_only_in_a_path_and_as_a_final_extension(self):
        words = sorted(w for w in ev._ID_WORDS if w.isalpha() and len(w) >= 3 and not ev._cred_name(w) and w not in ev._STRUCT_WORDS)
        for _ in range(60):
            p = "-".join(_R.sample(words, ev._MAX_VOCAB_WORDS) + ["mnt", "ssd", "tmp"])
            self.assertNotIn(p, ev.show("worker.account", p), "struct words count outside a path")
            self.assertNotIn(p, ev.show("current_owner", p))
        ok = "/mnt/ssd/cargo-target/r7-wfit-20261112/out/report.md"
        self.assertIn(ok, ev.show("result.artifact", ok, "path"))
        six = "-".join(_R.sample(words, ev._MAX_VOCAB_WORDS))
        self.assertIn(six + ".service", ev.show("worker.unit", six + ".service"))

    def test_a_slug_is_one_per_value_and_never_beside_an_id(self):
        self.assertIn("claude-3947245-r7-a1303rv8-20261113", ev.show("current_owner", "claude-3947245-r7-a1303rv8-20261113"))
        self.assertNotIn("a1303rv8-b2404sx9", ev.show("current_owner", "a1303rv8-b2404sx9"))
        h = hexmix(12)
        self.assertNotIn("a1303rv8-" + h, ev.show("task_id", "a1303rv8-" + h))
        self.assertNotIn("decide-" + h, ev.show("task_id", "decide-" + h))

    def test_slug_shaped_random_runs_are_rare(self):
        alnum = LOWER + DIG
        for n in (8, 9, 10):
            hits = sum(1 for _ in range(6000) if ev._slug(rnd(alnum, n)))
            self.assertLessEqual(hits / 6000.0, 0.02, n)

    def test_the_name_grammar_is_absent_from_account_model_session_host_and_rows(self):
        for f in ("worker.account", "worker.model", "worker.session", "worker.invocation", "worker.host"):
            for v in ("decide-regrade", "swarm-decide", "a1303rv8", "claude-bootstrap"):
                self.assertNotIn(v, ev.show(f, v), (f, v))
        for v in ("decide-regrade", "a1303rv8", "bootstrap-proof"):
            self.assertNotIn(v, __import__("queue_adapter")._gate("owner", v), v)

    def test_a_repo_owner_is_one_short_piece(self):
        self.assertIn("j0yen/swarm-decide", ev.show("target.repo", "j0yen/swarm-decide"))
        for v in ("%s/swarm-decide" % lc(9), "%s/swarm-decide" % b62(8), "j0yen/%s" % b62(12)):
            self.assertNotIn(v, ev.show("target.repo", v), v)

    def test_long_numbers_need_a_wide_numeric_name(self):
        for pos in ("file_size=1048576000", "epoch=1789000000", "bytes=123456789", "seq=1234567", "pid=482917", "line_number=1234567"):
            self.assertEqual(ev.redact(pos), pos, pos)
        for neg, v in (("seq=%s" % num(9), None), ("pid=%s" % num(9), None), ("line_number=%s" % num(8), None), ("port=%s" % num(10), None)):
            self.assertNotIn(neg.split("=")[1], ev.redact(neg), neg[:6])

    def test_a_model_context_tag_is_only_for_a_model(self):
        self.assertIn("claude-opus-5-5[1m]", ev.show("worker.model", "claude-opus-5-5[1m]"))
        self.assertNotIn("claude-opus-5-5[1m]", ev.show("worker.account", "claude-opus-5-5[1m]"))
        self.assertNotIn("[1m]", ev.show("worker.model", "%s[1m]" % b62(14)))

    def test_a_host_with_colons_is_an_exact_ip_literal(self):
        for v in ("a1b2:c3d4:e5f6", "ab12:cd34:ef56:7890:abcd", "12:34:56", "host:1:2"):
            self.assertNotIn(v, ev.show("worker.host", v, "host"), v)
        for v in ("redbaron:22", "10.0.1.23:8080", "fe80::1%eth0"):
            self.assertIn(v, ev.show("worker.host", v, "host"), v)

    def test_a_dotted_flag_name_is_a_flag(self):
        v = rnd("QZJKVHGBNM", 9)
        for t in ("--api.key %s", "--db.pass=%s", "--mfa.count %s", "--svc.secret %s"):
            self.assertNotIn(v, ev.redact(t % v), t)

    def test_the_walrus_separator_is_a_separator(self):
        v = rnd("QZJKVHGBNM", 9)
        for t in ("api_key := %s", "password:=%s", "token := %s", "x := %s"):
            self.assertNotIn(v, ev.redact(t % v), t)


class RetainedReviewerProbes12(unittest.TestCase):
    """The reviewer's own probes of re-review 11 (tests/probes/), run against this tree. pairs11 is the 78-pair table (27 identity
    pairs, 5 row pairs, 46 free-text forms); two pairs stay unmet and are DISPUTED, each with its reproducer:
    `dbpw=42` (a two-digit number is a small count by size: `a=1`, `exit code=2` and `retries: 3` are positives of the same pair
    table and of test_review_fixes11, and nothing but the name tells them apart) and `hush=ab-cd` (four characters in two pieces
    is the stated free-text size residual, R2). Every other pair passes."""

    def run_probe(self, name, *args):
        r = subprocess.run([sys.executable, os.path.join(TESTS, "probes", name), *args], capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, name + r.stderr[-300:])
        return r.stdout

    def test_pairs11_all_but_the_two_disputed_pairs(self):
        out = self.run_probe("pairs11.py")
        self.assertIn("PAIRS 76/78", out)
        unmet = sorted(l.split()[0] for l in out.splitlines() if "<<<" in l)
        self.assertEqual(unmet, ["free/mid-word", "free/unlisted-name-num2"])

    def test_matrix11_no_passphrase_or_digit_run_prints_in_any_field(self):
        out = self.run_probe("matrix11.py")
        for bad in ("words8", "digits16"):
            self.assertNotIn(bad, out)
        ids, rows = out.split("--- rows")
        for part, names in ((ids, {"host", "model", "effort", "consumer", "alternate", "repo", "branch", "task", "task_id", "named"}),
                            (rows, {"row", "owner", "claim", "status", "waits-on", "seq"})):
            seen = set()
            for line in part.splitlines():
                if line.split() and line.split()[0] in names and "prints:" in line:
                    seen.add(line.split()[0])
                    self.assertEqual(line.split("prints:")[1].strip(), "", line)
            self.assertEqual(seen, names)

    def test_prose11_every_compound_form_is_hidden(self):
        out = self.run_probe("prose11.py").split()
        forms = [x for x in out if x.endswith(("=h", "=L"))]
        self.assertTrue(forms)
        self.assertEqual([x for x in forms if x.endswith("=L") and x != "%s=L"], [])


class BoundsFoundByMutants12(unittest.TestCase):
    """Edges the mutant runner (mutants12.py) found open on its first run: each bound is pinned by a case only it can refuse."""

    def test_a_numeric_name_has_at_most_three_qualifiers(self):
        self.assertTrue(ev._numeric_name("max_file_line_count"))
        self.assertFalse(ev._numeric_name("max_min_file_line_total_count"))
        v = num(8)
        self.assertNotIn(v, ev.redact("max_min_file_line_total_count=%s" % v))

    def test_a_compressed_ipv6_literal_has_at_most_four_explicit_groups_and_a_full_one_four_non_zero_groups(self):
        for lit in ("1:2:3:4:5::", "1:2:3:4:5:6:7::", "1:2:3:4:5:6:7:8", "1:2:3:4:5:6:0:8"):
            self.assertNotIn(lit, ev.show("worker.host", lit, "host"), lit)
        for lit in ("2001:db8::1:2", "1:0:0:0:0:0:0:1", "fe80::1%eth0"):
            self.assertIn(lit, ev.show("worker.host", lit, "host"), lit)

    def test_name_words_are_two_per_value_and_twenty_letters_in_all(self):
        three = "purple-monkey-casual.service"  # three 6-letter words: 18 letters, three words
        self.assertTrue(all(ev._pronounceable(w) for w in ("purple", "monkey", "casual")))
        self.assertNotIn(three, ev.show("worker.unit", three))
        long2 = "refrigerator-construction.service"  # two words, 24 letters
        self.assertTrue(all(ev._pronounceable(w) for w in ("refrigerator", "construction")))
        self.assertNotIn(long2, ev.show("worker.unit", long2))
        two = "purple-monkey.service"
        self.assertIn(two, ev.show("worker.unit", two))

    def test_a_name_word_never_sits_beside_a_hash_sized_id(self):
        h = hexmix(32)
        for v in ("wm-regrade-%s.service" % h, "wm-witness-%s.service" % uu()):
            self.assertNotIn(v, ev.show("worker.unit", v), v)
        self.assertIn("wm-build-%s.service" % h, ev.show("worker.unit", "wm-build-%s.service" % h))

    def test_a_repo_owner_has_the_short_budget_not_the_value_budget(self):
        for v in ("abc-def/vibecode-kit", "ab-cd-ef/vibecode-kit"):
            self.assertNotIn(v, ev.show("target.repo", v), v)
        self.assertIn("j0yen/vibecode-kit", ev.show("target.repo", "j0yen/vibecode-kit"))

    def test_plain_json_data_prints_only_with_plain_keys_and_values(self):
        for neg in ('{"meta": {"note": "sunshine"}}', '{"list": ["sunshine", "dragonfly"]}',
                    '{"items": [{"line": 1}, {"v": "hunterxx"}]}', '{"meta": {"zxqv": 7}}'):
            out = ev.redact(neg)
            for w in ("sunshine", "dragonfly", "hunterxx"):
                self.assertNotIn(w, out, neg)
        for pos in ('{"meta": {"line": 12}}', '{"lines": [1, 2]}', '{"state": "ok", "attempt": 2}'):
            self.assertEqual(ev.redact(pos), pos, pos)

    def test_a_bare_weak_noun_before_a_plain_word_is_prose(self):
        for pos in ("key point", "the key points", "auth service", "auth failed", "exit code 2", "code review", "the code is merged"):
            self.assertEqual(ev.redact(pos), pos, pos)
        for neg in ("api key %s", "private key %s", "recovery code %s", "the auth %s"):
            v = rnd("QZJKVHGBNM", 3) + rnd(DIG, 4)
            self.assertNotIn(v, ev.redact(neg % v), neg)


# ------------------------------------------------------------------------------------------- free-text positives of the pairs
class FreeTextPositivesPairedWithNegatives(unittest.TestCase):
    """Positives the reviewer chose that over-refused in free text, each paired with a credential of similar shape."""

    def test_pairs(self):
        z = rnd(B62, 12)
        z2 = rnd(B62, 12)
        pairs = (("Accept: text/plain", "Authorization: Bearer %s" % z, z), ("Content-Type: application/json", "X-Api-Key: %s" % z, z),
                 (json.dumps({"x": json.dumps({"line": 12})}), json.dumps({"x": json.dumps({"password": z})}), z),
                 ('{"meta": {"line": 12}}', '{"credentials": {"inner": {"v": "%s"}}}' % z, z),
                 ('{"lines": [1,2]}', '{"tokens": ["%s", "%s"]}' % (z, z2), z),
                 ("path=%2Fvar%2Flog", "password%%3D%s" % z, z),
                 ('{"meta": {"state": "ok", "attempt": 2}}', '{"meta": {"note": "%s"}}' % z, z),
                 ('{"items": [{"line": 1}, {"line": 2}]}', '{"items": [{"line": 1}, {"v": "%s"}]}' % z, z))
        for pos, neg, v in pairs:
            self.assertEqual(ev.redact(pos), pos, pos)
            self.assertNotIn(v, ev.redact(neg), neg[:30])


if __name__ == "__main__":
    unittest.main()
