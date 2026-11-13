"""Regression tests for the fifth independent exact-head review (re-review 4 of 85ddd05a), DEFECT 1..6.
Each class closes its defect as a class. Source-only: synthetic envelopes, no production claim.
Clocks are injected (`now=` / `--now`); nothing here reads the host date for a verdict.
Credential canaries are assembled at run time from fragments and are never printed or stored."""
import itertools
import json
import re
import unittest
from unittest import mock

from helpers import FIXTURE_NOW, FIX, SKILL, codes, load

import envelope_validate as ev
import queue_adapter as qa
import recommend as rc
import test_review_fixes3 as t3

RECOMMEND = str(SKILL / "scripts" / "recommend.py")
VALIDATE = str(SKILL / "scripts" / "envelope_validate.py")
ADAPTER = str(SKILL / "scripts" / "queue_adapter.py")
NOW = FIXTURE_NOW
cli, running, done, one, rec, tmp_json = t3.cli, t3.running, t3.done, t3.one, t3.rec, t3.tmp_json
_frag = t3._frag


def hex32():
    return "".join("0123456789abcdef"[(i * 5 + 3) % 16] for i in range(32))


def shapes():
    """(label, text, secret fragment that must not survive): provider shapes and name forms, built at run time."""
    a, h = _frag(22, 3), hex32()
    up = a.upper()
    return [
        ("twilio-sk", "key S" + "K" + h, h),
        ("twilio-ac", "sid A" + "C" + h, h),
        ("mailgun", "mg ke" + "y-" + h, h),
        ("telegram", "bot 123456789:A" + "A" + a + "_-x", a),
        ("atlassian", "AT" + "ATT3xFfGF0" + a + "ABCD=EF123456", a),
        ("databricks", "da" + "pi" + h, h),
        ("grafana", "gl" + "sa_" + a + "_abcd1234", a),
        ("vault", "hv" + "s." + a + "abcd", a),
        ("notion", "sec" + "ret_" + a + "abcdefgh", a),
        ("notion2", "nt" + "n_" + a + "abcdefgh", a),
        ("linear", "lin" + "_api_" + a + "abcd", a),
        ("sentry", "sntr" + "ys_" + a + "abcd", a),
        ("postman", "PM" + "AK-" + a + "-abcd", a),
        ("square", "sq0" + "atp-" + a + "abcd", a),
        ("facebook", "EA" + "AB" + a + "abcdefghijkl", a),
        ("age", "AGE-" + "SECRET-KEY-1" + up + "QQQQ", up),
        ("fly", "fo" + "1_" + a + "abcd", a),
        ("passphrase", "passph" + "rase=" + a, a),
        ("pass-eq", "pa" + "ss=" + a, a),
        ("auth-eq", "au" + "th=" + a, a),
        ("cookie", "cook" + "ie: sess" + "ion=" + a, a),
        ("set-cookie", "Set-Coo" + "kie: sid=" + a + "; Path=/", a),
        ("amz-sig", "https://h.example/p?X-Amz-Sign" + "ature=" + a, a),
        ("curl-u", "curl -" + "u admin:" + a + " https://h", a),
        ("curl-user-long", "curl --us" + "er admin:" + a + " https://h", a),
        ("x-api-key", "x-api-" + "key: " + a, a),
        ("apikey-json", '{"api' + 'Key": "' + a + '"}', a),
        ("url-pw", "postgres://user:" + a + "@db.example/x", a),
        ("url-pw-at", "https://u:p@ss" + a + "@h.example/", a),
        ("url-token-only", "https://" + a + "@github.com/x", a),
        ("url-query", "https://h.example/p?access_" + "token=" + a + "&x=1", a),
        ("url-query-sess", "https://h.example/p?sess" + "ion=" + a, a),
        ("env-export", "export GITHUB_TOK" + "EN=" + a, a),
        ("yaml-colon-nospace", "pass" + "word:" + a, a),
        ("quoted-name", '"client_sec' + 'ret":"' + a + '"', a),
        ("basic-b64", "Author" + "ization: Basic dXNlcjpwYXNz" + a, a),
        ("azure-key", "AccountName=x;Account" + "Key=" + a + "==;Suffix=core", a),
        ("dsn", "d" + "sn=" + a, a),
        ("private", "priv" + "ate: " + a, a),
        ("cert", "ce" + "rt=" + a, a),
        ("credential", "credent" + "ial: " + a, a),
        ("session", "sess" + "ion=" + a, a),
        ("sig", "s" + "ig=" + a, a),
        ("api", "a" + "pi=" + a, a),
        ("flag-pass", "tool --pass" + "word " + a, a),
        ("flag-auth", "tool --au" + "th " + a, a),
        ("flag-passphrase", "tool -passph" + "rase " + a, a),
        # structural rule (b): no name, no known prefix, only the shape of a secret
        ("bare-random-mixed", "see " + a + h[:8] + " here", a),
        ("bare-hex32", "id " + h + " ok", h),
        ("bare-b64ish", "v " + a + "/" + a.upper() + "+" + a[:6] + "== end", a),
    ]


WORDS_NO_DIGIT = ["correcthorsebattery", "hunter", "swordfish"]
NAME_FORMS = ["pass", "passphrase", "auth", "cookie", "signature", "sig", "session", "credential", "bearer", "api",
              "private", "dsn", "cert", "pwd", "passwd", "secret", "token", "key", "apikey", "api_key", "client-secret",
              "AccountKey", "accessToken", "x-auth-token", "sessionid"]


class D01_RedactionIsStructural(unittest.TestCase):
    def test_every_shape_redacted_by_library(self):
        for label, text, frag in shapes():
            red = ev.redact("ref " + text + " tail")
            self.assertNotIn(frag, red, label)
            self.assertIn("[REDACTED]", red, label)

    def test_every_shape_redacted_end_to_end(self):
        for label, text, frag in shapes():
            d = running()
            d["evidence"][0]["ref"] = text
            d["worker"]["account"] = text
            p = tmp_json(d)
            for args in (["--format", "json"], ["--format", "text"]):
                r = cli(RECOMMEND, "--now", NOW, *args, p)
                self.assertNotIn(frag, r.stdout + r.stderr, (label, args))
            r = cli(VALIDATE, "--now", NOW, p)
            self.assertNotIn(frag, r.stdout + r.stderr, (label, "validator"))

    def test_name_forms_redact_any_value_even_a_plain_word(self):
        for name, val in itertools.product(NAME_FORMS, WORDS_NO_DIGIT):
            for text in ("%s=%s" % (name, val), "%s: %s" % (name, val), '{"%s": "%s"}' % (name, val),
                         "tool --%s %s" % (name, val), "https://h.example/p?%s=%s&z=1" % (name, val)):
                red = ev.redact("ref " + text)
                self.assertNotIn(val, red, text)

    def test_headers_redact_the_whole_value(self):
        a = _frag(20, 2)
        for h in ("Cook" + "ie", "Set-Cook" + "ie", "Author" + "ization", "Proxy-Author" + "ization"):
            red = ev.redact("%s: a=%s; b=%s; Path=/\nnext line" % (h, a, a[::-1]))
            self.assertNotIn(a, red, h)
            self.assertNotIn(a[::-1], red, h)
            self.assertIn("next line", red)

    def test_curl_user_flag_forms(self):
        a = _frag(14, 4)
        for text in ("curl -u me:%s https://h" % a, "curl --user me:%s https://h" % a, "curl --proxy-user me:%s h" % a,
                     "curl -u 'me:%s' https://h" % a):
            self.assertNotIn(a, ev.redact(text), text)

    def test_url_userinfo_and_credential_query_values(self):
        a = _frag(16, 6)
        for text in ("https://u:%s@h/x" % a, "ssh://%s@h" % a, "https://h/x?api_key=%s&b=2" % a, "https://h/x?b=2&sig=%s" % a,
                     "https://h/x?b=2;token=%s" % a):
            self.assertNotIn(a, ev.redact(text), text)
        # a query value of an ordinary parameter stays readable
        self.assertEqual(ev.redact("https://h.example/p?page=2&sort=name"), "https://h.example/p?page=2&sort=name")

    def test_hex_digest_kept_only_in_a_digest_field(self):
        sha40 = "".join("0123456789abcdef"[(i * 7 + 1) % 16] for i in range(40))
        sha64 = sha40 + "".join("0123456789abcdef"[(i * 3 + 2) % 16] for i in range(24))
        for field in ("head=", "sha=", "sha256=", "head ", "commit ", "digest: ", "rev=", "oid=", "hash="):
            for s in (sha40, sha64):
                self.assertEqual(ev.redact("%s%s" % (field, s)), "%s%s" % (field, s), field)
        for s in (sha40, sha64):
            self.assertNotIn(s, ev.redact("value %s here" % s))

    def test_over_redaction_check_legitimate_output_fields_still_print(self):
        keep = [
            "head=abc123def4567890", "target=acme/app@feat/one head=abc123def4567890",
            "worker.unit=wfit-20261112-worker.service", "worker.host=ryzen7", "worker.child=pid:77", "worker.child=%12",
            "state=RUNNING", "owner=r7 reachable=True", "effect=applied no_replay=True",
            "observed 2026-11-13T07:00:00Z and 2026-11-13T06:55:12.123456+00:00",
            "/mnt/ssd/cargo-target/r7-wfit-20261112/fix5/out/report.md",
            "branch feat/a-fairly-long-branch-name-for-task-12345", "unit mcphost-wfit-20261112-worker.service active",
            "evidence unit-read (task WF-1 rev 2 at 2026-11-13T06:50:00Z)", "queue row d-20261101-173305-aide-f24a seq 4 rev 2",
            "coverage gap: queue row is silent about worker, effect, consumer and target; all UNKNOWN",
            "UNKNOWN_KEY worker.extra: field not in schema", "RUNNING needs observed host+unit+child (missing: unit)",
            "tmux:%12", "https://h.example/p?page=2&sort=name", "result=/retained/WF-1.json reviewed=False",
            "passed review", "bypass the queue", "designed for reuse", "signal=ready", "author=bob", "monkey=1", "keyboard=us",
        ]
        for text in keep:
            self.assertEqual(ev.redact(text), text, text)

    def test_controls_fixtures_print_unchanged_evidence_lines(self):
        checked = 0
        for p in sorted(FIX.glob("*.json")):
            d = load(p.stem)
            if not isinstance(d, dict) or d.get("schema") != ev.SCHEMA_ID:
                continue
            if ev.validate(d, now=NOW):
                continue
            lines = rc._evidence(d)
            self.assertEqual(lines, ev.scrub(lines), p.stem)
            checked += 1
        self.assertGreater(checked, 3)

    def test_tool_owned_sentences_are_not_altered_by_redaction(self):
        """every message the scripts write themselves (action sentences, reasons, finding messages, report lines) must
        survive redact() untouched, so only envelope-owned text is ever hidden"""
        import ast
        import inspect
        checked = 0
        for mod in (rc, ev, qa):
            tree = ast.parse(inspect.getsource(mod))
            docs = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs \
                        and len(n.value) > 15 and " " in n.value and "REDACTED" not in n.value:
                    text = re.sub(r"%[sdr]", "x", n.value)
                    self.assertEqual(ev.redact(text), text, text)
                    checked += 1
        self.assertGreater(checked, 40)

    def test_consumer_that_redaction_would_change_is_not_an_identifier(self):
        a = _frag(18, 8)
        for v in ("passw" + "ord=" + a, "client_sec" + "ret=" + a, "verifier-" + a + "9"):
            self.assertIsNone(ev.ident(v), v)
        self.assertEqual(ev.ident("verifier-1"), "verifier-1")
        self.assertEqual(ev.ident("tmux:%12"), "tmux:%12")


class D02_PlaceholdersAsAClass(unittest.TestCase):
    HOSTLIKE = ["unidentified", "undetermined", "unobserved", "unverified", "unconfirmed", "unreported", "unclear", "unnamed",
                "unrecorded", "unlisted", "undisclosed", "unresolved", "unchecked", "unseen", "undecided", "unattested",
                "nobody", "nothing", "no-one", "noone", "blank", "void", "placeholder", "redacted", "later", "soon",
                "waiting", "xxx", "someone", "something", "dummy", "not-yet-known", "not_known", "not known yet",
                "to-be-determined", "TBA/TBD", "null/null", "none/none", "?/?", "N/A (unknown)", "unknown (pending)",
                "no data", "no value", "no evidence", "not recorded", "not observed", "not provided", "pending…",
                "UNIDENTIFIED", "Un-Observed", "unobserved.", "unverified-", "tbd-tbd", "unknown unknown", "n/a n/a",
                "unknown-1", "pending 7", "TBD #2"]

    def test_running_with_placeholder_host_unit_child_is_refused(self):
        for v in self.HOSTLIKE:
            for k in ("host", "unit", "child"):
                d = running()
                d["worker"][k] = v
                r = one(d)
                self.assertTrue(r["refused"], (k, v))
                self.assertIn("RUNNING_NO_EVIDENCE", r["reason_codes"], (k, v))

    def test_is_unknown_and_ident_agree_on_the_class(self):
        for v in self.HOSTLIKE:
            self.assertTrue(ev.is_unknown(v), v)
            self.assertIsNone(ev.ident(v), v)

    def test_lookalike_real_names_are_not_placeholders(self):
        for v in ["unknown-host-7", "pending-review-svc", "na-east-1", "none-of-the-above.service", "tbd.example.com",
                  "not-set-up", "empty-box", "null-ptr", "no-reply", "unified-gateway", "united", "verifier-1", "ryzen7",
                  "unit-9.service", "later-gator-3"]:
            self.assertFalse(ev.is_unknown(v), v)
            d = running()
            d["worker"]["host"] = v
            self.assertEqual(one(d)["disposition"], "reuse-active-worker", v)

    def test_placeholder_evidence_refs_do_not_make_running_evidence(self):
        for v in ["unidentified", "unobserved", "no data", "TBA/TBD", "unverified"]:
            d = running()
            d["evidence"][0]["ref"] = v
            self.assertTrue(one(d)["refused"], v)

    ACKS_BAD = ["yes 1", "ok 1", "unknown:0", "pending:1", "tbd #1", "n/a 1", "yes/no", "N / A 1", "n\\a 1", "yes", "ack",
                "approved by me", "self-authorized", "same as above", "see above", "trust me", "unverified:2",
                "unconfirmed 3", "unidentified #4", "no data 0", "not yet known 1", "to be determined 2", "TBA/TBD 1",
                "confirmed 1", "authorized 1", "done 1", "acknowledged:1", "ack 1", "ok #1", "yes@1", "yes/1"]

    @staticmethod
    def done_with_ack(v):
        d = done()
        d["ack"] = {"accepted": True, "evidence": v}
        return d

    def test_ack_evidence_that_is_not_a_reference_is_refused(self):
        for v in self.ACKS_BAD:
            self.assertIn("INVENTED_ACK", codes(ev.validate(self.done_with_ack(v), now=NOW)), v)
            self.assertTrue(one(self.done_with_ack(v))["refused"], v)

    ACKS_GOOD = ["msg-4412", "message 4412 from verifier-1", "event:consumer-ack-42", "https://example.test/ack/17",
                 "#123", "ticket#88", "@verifier-1 msg 5", "/retained/ack-17.json", "ack:msg-77", "wm-asks ack 9981",
                 "12345", "thread 2026-11-13T06:55:00Z"]

    def test_ack_evidence_that_is_a_reference_is_accepted(self):
        for v in self.ACKS_GOOD:
            self.assertNotIn("INVENTED_ACK", codes(ev.validate(self.done_with_ack(v), now=NOW)), v)

    @staticmethod
    def alt(ref):
        d = done()
        d["consumer"].update(named="busy-1", available=False, alternate="alt-9", alternate_authorized=True,
                             alternate_authorization_ref=ref)
        return d

    def test_authorization_ref_that_is_not_a_reference_gives_no_alternate(self):
        for v in ["ok 1", "tbd:1", "yes 1", "pending:1", "unknown:0", "n/a 1", "approved 1", "unverified #1", "yes/no",
                  "by me", "authorized", "same as above", "no data 1"]:
            self.assertNotIn("alt-9", one(self.alt(v))["later_consumers"], v)

    def test_authorization_ref_that_is_a_reference_gives_the_alternate(self):
        for v in ["decision-note:77", "https://example.test/auth/1", "#41", "approval msg 12"]:
            self.assertIn("alt-9", one(self.alt(v))["later_consumers"], v)

    def test_ref_like_locator_rule_is_pinned(self):
        # the locator clause: a reference with substantive words but no digit and none of : / # @ is not a reference
        for v in ["see the thread", "handled it verbally", "the verifier agreed", "message from verifier"]:
            self.assertFalse(ev.ref_like(v), v)
        for v in ["see the thread 2", "message from verifier:", "thread/x", "thread#", "verifier@host"]:
            self.assertTrue(ev.ref_like(v), v)
        # a placeholder or assertion with a locator is still not a reference
        for v in ["yes 1", "unknown:0", "tbd #1", "ok@1", "n/a/1"]:
            self.assertFalse(ev.ref_like(v), v)
        self.assertFalse(ev.ref_like(None))
        self.assertFalse(ev.ref_like(7))
        self.assertFalse(ev.ref_like(""))


class D03_DeepQueueRowsNeverTraceback(unittest.TestCase):
    DEPTHS = (900, 1100, 1500, 5000, 20000, 50000)

    @staticmethod
    def nest(n):
        return "[" * n + "]" * n

    def rows_text(self, n, key):
        return ('[{"ask_id": "Q-1", "rev": 1, "row_id": "r1", "status": "open", "%s": %s}, '
                '{"ask_id": "Q-2", "rev": 3, "row_id": "r2"}]' % (key, self.nest(n)))

    def check(self, r, what):
        self.assertNotIn("Traceback", r.stdout + r.stderr, what)
        self.assertNotIn("RecursionError", r.stdout + r.stderr, what)

    def test_recommend_queue_no_traceback_at_any_depth(self):
        for n in self.DEPTHS:
            for key in ("extra", "claim", "owner", "waits_on", "row_id"):
                r = cli(RECOMMEND, "--queue", "--format", "json", "--now", NOW, tmp_json(self.rows_text(n, key)))
                self.check(r, (n, key))
                self.assertIn(r.returncode, (0, 2), (n, key))
                self.assertEqual(r.returncode, 0, (n, key))
                out = json.loads(r.stdout)
                self.assertEqual(len(out), 2, (n, key))
                self.assertEqual(out[1]["task_id"], "Q-2", (n, key))
                self.assertIn(out[0]["task_id"], ("Q-1", "UNKNOWN"), (n, key))
                if out[0]["task_id"] == "UNKNOWN":  # a row the interpreter could not render: refused alone, no identity
                    self.assertTrue(out[0]["refused"], (n, key))

    def test_adapter_no_traceback_at_any_depth(self):
        for n in self.DEPTHS:
            for key in ("extra", "claim", "owner", "waits_on", "row_id"):
                r = cli(ADAPTER, tmp_json(self.rows_text(n, key)))
                self.check(r, (n, key))
                self.assertIn(r.returncode, (0, 2), (n, key))

    def test_deep_row_is_read_and_the_sibling_is_evaluated(self):
        r = cli(RECOMMEND, "--queue", "--format", "json", "--now", NOW, tmp_json(self.rows_text(1100, "claim")))
        out = json.loads(r.stdout)
        self.assertEqual(r.returncode, 0)
        self.assertEqual([x["task_id"] for x in out], ["Q-1", "Q-2"])

    def test_row_the_interpreter_cannot_render_is_refused_alone(self):
        # the interpreter's recursion limit while rendering one row: that row gets an empty identity, the sibling is kept
        real = qa.row_to_envelope

        def flaky(row, observed_at=qa.UNKNOWN):
            if row.get("ask_id") == "Q-1":
                raise RecursionError("simulated")
            return real(row, observed_at)
        with mock.patch.object(qa, "row_to_envelope", flaky):
            envs = qa.rows_to_envelopes([{"ask_id": "Q-1", "rev": 1}, {"ask_id": "Q-2", "rev": 1}])
        self.assertEqual([e["task_id"] for e in envs], ["", "Q-2"])
        self.assertTrue(any("nested too deep" in g for g in envs[0]["coverage_gaps"]))
        out = rc.recommend_set({"envelopes": envs}, now=NOW)
        self.assertTrue(out[0]["refused"])
        self.assertIn("SCHEMA_TYPE", out[0]["reason_codes"])

    def test_find_dups_is_iterative_and_keeps_its_paths(self):
        deep = []
        for _ in range(5000):
            deep = [deep]
        self.assertEqual(ev.find_dups(deep), [])
        d = ev.load_json_text('{"a": {"b": 1, "b": 2}, "c": [{"x": 1, "x": 2}], "d": 1, "d": 2}')
        self.assertEqual(sorted(ev.find_dups(d)), sorted(["$ (d)", "$.a (b)", "$.c[0] (x)"]))

    def test_deep_envelope_record_inside_a_set_still_refused_alone(self):
        for n in (900, 1100, 5000):
            d = running()
            d["worker"]["account"] = "@@D@@"
            sib = running("SYN-200", "synthetic/repo-b", "syn/b2")
            text = "[" + json.dumps(d).replace('"@@D@@"', self.nest(n)) + "," + json.dumps(sib) + "]"
            r = cli(RECOMMEND, "--format", "json", "--now", NOW, tmp_json(text))
            self.check(r, n)
            out = json.loads(r.stdout)
            self.assertTrue(out[0]["refused"])
            self.assertEqual(out[1]["disposition"], "reuse-active-worker")


class D04_AdapterExtraArguments(unittest.TestCase):
    def test_extra_arguments_are_a_usage_error_naming_them(self):
        p = tmp_json([{"ask_id": "Q-1", "rev": 1}])
        r = cli(ADAPTER, p, "2026-11-13T00:00:00Z", "EXTRA.json", "MORE")
        self.assertEqual(r.returncode, 2)
        self.assertIn("EXTRA.json", r.stdout)
        self.assertIn("MORE", r.stdout)
        self.assertNotIn("envelopes", r.stdout)

    def test_one_extra_and_unknown_option(self):
        p = tmp_json([{"ask_id": "Q-1", "rev": 1}])
        r = cli(ADAPTER, p, "UNKNOWN", "EXTRA.json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("EXTRA.json", r.stdout)
        r = cli(ADAPTER, "--bogus", p)
        self.assertEqual(r.returncode, 2)
        self.assertIn("--bogus", r.stdout)

    def test_valid_forms_still_work(self):
        p = tmp_json([{"ask_id": "Q-1", "rev": 1}])
        self.assertEqual(cli(ADAPTER, p).returncode, 0)
        self.assertEqual(cli(ADAPTER, p, "2026-11-13T00:00:00Z").returncode, 0)

    def test_main_returns_2_in_process(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(qa.main(["a.json", "UNKNOWN", "b.json"]), 2)
        self.assertIn("b.json", buf.getvalue())


class D05_ReferenceClockProvenance(unittest.TestCase):
    def test_injected_clock_is_recorded_and_not_live(self):
        r = one(running())
        self.assertEqual(r["reference_clock"]["source"], "injected")
        self.assertFalse(r["reference_clock"]["live"])
        self.assertEqual(r["reference_clock"]["now"], "2026-11-13T07:00:00Z")

    def test_host_clock_default_is_recorded_as_host(self):
        out = rc.recommend_set([running()])
        self.assertEqual(out[0]["reference_clock"]["source"], "host")
        self.assertTrue(out[0]["reference_clock"]["live"])
        self.assertRegex(out[0]["reference_clock"]["now"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_every_recommendation_carries_it_refused_and_wrapper_included(self):
        out = rec([running(), {"not": "an envelope"}, running("SYN-9", "a/b", "c")])
        self.assertTrue(all(r["reference_clock"]["source"] == "injected" for r in out))
        self.assertTrue(any(r["refused"] for r in out))
        w = rc.recommend_set({"envelopes": None}, now=NOW)
        self.assertEqual(w[0]["reference_clock"]["source"], "injected")

    def test_cli_json_and_text(self):
        p = tmp_json(running())
        j = json.loads(cli(RECOMMEND, "--format", "json", "--now", NOW, p).stdout)
        self.assertEqual(j[0]["reference_clock"], {"now": "2026-11-13T07:00:00Z", "source": "injected", "live": False})
        t = cli(RECOMMEND, "--now", NOW, p).stdout
        self.assertRegex(t, r"reference clock: 2026-11-13T07:00:00Z \(INJECTED")
        self.assertIn("not a live result", t)
        j = json.loads(cli(RECOMMEND, "--format", "json", p).stdout)
        self.assertEqual(j[0]["reference_clock"]["source"], "host")
        self.assertTrue(j[0]["reference_clock"]["live"])
        t = cli(RECOMMEND, p).stdout
        self.assertRegex(t, r"reference clock: \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ \(host clock\)")
        # --now system is the host clock, not an injection
        j = json.loads(cli(RECOMMEND, "--format", "json", "--now", "system", p).stdout)
        self.assertEqual(j[0]["reference_clock"]["source"], "host")

    def test_queue_path_is_stamped_too(self):
        p = tmp_json([{"ask_id": "Q-1", "rev": 1}])
        j = json.loads(cli(RECOMMEND, "--queue", "--format", "json", "--now", NOW, p).stdout)
        self.assertEqual(j[0]["reference_clock"]["source"], "injected")


class D06_TestGapRefLike(unittest.TestCase):
    def test_ref_like_does_not_return_true_after_the_placeholder_checks(self):
        # kills the mutation: ref_like's last line replaced by `return True`
        self.assertFalse(ev.ref_like("signed off verbally"))
        self.assertFalse(ev.ref_like("looks fine to the reviewer"))
        self.assertTrue(ev.ref_like("looks fine to the reviewer 2"))

    def test_ack_without_locator_is_invented(self):
        d = done()
        d["ack"] = {"accepted": True, "evidence": "the consumer replied verbally"}
        self.assertIn("INVENTED_ACK", codes(ev.validate(d, now=NOW)))

    def test_authorization_ref_without_locator_gives_no_alternate(self):
        d = done()
        d["consumer"].update(named="busy-1", available=False, alternate="alt-9", alternate_authorized=True,
                             alternate_authorization_ref="the owner said it was fine")
        self.assertNotIn("alt-9", one(d)["later_consumers"])


if __name__ == "__main__":
    unittest.main()
