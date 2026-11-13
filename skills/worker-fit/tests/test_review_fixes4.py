"""Regression tests for the fourth independent exact-head review (re-review 3 of 03cc6d63), DEFECT 1..5.
Each class closes its defect as a class. Source-only: synthetic envelopes, no production claim.
Clocks are injected (`now=` / `--now`); nothing here reads the host date.
Credential canaries are assembled at run time from fragments and are never printed or stored."""
import copy
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

from helpers import FIXTURE_NOW, SKILL, codes, load

import envelope_validate as ev
import recommend as rc
import test_review_fixes3 as t3

RECOMMEND = str(SKILL / "scripts" / "recommend.py")
VALIDATE = str(SKILL / "scripts" / "envelope_validate.py")
NOW = FIXTURE_NOW
cli, running, done, one, rec, tmp_json = t3.cli, t3.running, t3.done, t3.one, t3.rec, t3.tmp_json
_frag = t3._frag


def prefixed_canaries():
    """(label, text, secret fragment): provider token shapes built from pieces at run time."""
    a = _frag(22, 4)
    aws_tail = a.upper()[:18]
    P = [
        ("aws-akia", "AK" + "IA" + aws_tail, aws_tail),
        ("aws-asia", "AS" + "IA" + aws_tail, aws_tail),
        ("aws-agpa", "AG" + "PA" + aws_tail, aws_tail),
        ("aws-aroa", "AR" + "OA" + aws_tail, aws_tail),
        ("aws-aida", "AI" + "DA" + aws_tail, aws_tail),
        ("aws-anpa", "AN" + "PA" + aws_tail, aws_tail),
        ("aws-abia", "AB" + "IA" + aws_tail, aws_tail),
        ("aws-acca", "AC" + "CA" + aws_tail, aws_tail),
        ("slack-xoxb", "xo" + "xb-" + a, a),
        ("slack-xoxp", "xo" + "xp-1-" + a, a),
        ("slack-xoxa", "xo" + "xa-2-" + a, a),
        ("slack-xoxr", "xo" + "xr-" + a, a),
        ("slack-xoxs", "xo" + "xs-" + a, a),
        ("slack-xoxe", "xo" + "xe-1-" + a, a),
        ("slack-xoxe-dot", "xo" + "xe.xo" + "xp-1-" + a, a),
        ("slack-xapp", "xa" + "pp-1-A0-" + a, a),
        ("slack-webhook", "https://hooks.sl" + "ack.com/services/T0AAA/B0BBB/" + a, a),
        ("google-ya29", "ya" + "29." + a, a),
        ("google-aiza", "AI" + "za" + a + "ABCDEFGH", a),
        ("google-gocspx", "GOC" + "SPX-" + a, a),
        ("google-refresh", "1/" + "/0g" + a, a),
        ("npm", "np" + "m_" + a, a),
        ("gitlab-pat", "gl" + "pat-" + a, a),
        ("gitlab-ptt", "gl" + "ptt-" + a, a),
        ("gitlab-rt", "gl" + "rt-" + a, a),
        ("github-ghp", "gh" + "p_" + a, a),
        ("github-gho", "gh" + "o_" + a, a),
        ("github-ghu", "gh" + "u_" + a, a),
        ("github-ghs", "gh" + "s_" + a, a),
        ("github-ghr", "gh" + "r_" + a, a),
        ("github-pat", "github" + "_pat_" + a, a),
        ("anthropic", "s" + "k-an" + "t-api03-" + a, a),
        ("openai-proj", "s" + "k-pr" + "oj-" + a, a),
        ("stripe-live", "s" + "k_li" + "ve_" + a, a),
        ("stripe-restricted", "r" + "k_li" + "ve_" + a, a),
        ("stripe-whsec", "wh" + "sec_" + a, a),
        ("sendgrid", "S" + "G." + a + "." + _frag(22, 6), a),
        ("huggingface", "h" + "f_" + a, a),
        ("pypi", "py" + "pi-AgEI" + a, a),
        ("docker", "dc" + "kr_pat_" + a, a),
        ("shopify", "sh" + "pat_" + a, a),
        ("digitalocean", "do" + "p_v1_" + a, a),
        ("jwt", "ey" + "J" + a + ".ey" + "J" + a[::-1] + "." + a, a),
        ("pem", "-----BEGIN " + "PRIVATE " + "KEY-----\n" + a + "\n-----END " + "PRIVATE " + "KEY-----", a),
        ("pem-ec", "-----BEGIN EC " + "PRIVATE " + "KEY-----\n" + a + "\n-----END EC " + "PRIVATE " + "KEY-----", a),
        ("url-pw", "https://usr:" + a + "@host.example/x", a),
        ("url-pw-at", "https://usr:p@" + a + "@host.example", a),
        ("url-pw-slash", "https://usr:pa/" + a + "@host.example", a),
        ("url-pw-at-slash", "ftp://usr:a@b/" + a + "@host.example/p", a),
        ("url-pw-empty-user", "redis://:p/" + a + "@h:6379", a),
        ("url-token-only", "https://" + a + "@host.example/p", a),
    ]
    return P


class D1_ProviderTokensAreRedactedAsAClass(unittest.TestCase):
    def test_redact_unit(self):
        for label, text, frag in prefixed_canaries():
            red = ev.redact("ref " + text + " tail")
            self.assertFalse(frag in red, label)
            self.assertIn("[REDACTED]", red, label)
            self.assertTrue(red.endswith("tail"), label)

    def test_redact_alone_and_in_json_context(self):
        for label, text, frag in prefixed_canaries():
            for tpl in ("%s", '{"v": "%s"}', "(%s)", "'%s'", "x=%s;", "<%s>"):
                self.assertFalse(frag in ev.redact(tpl % text), (label, tpl))

    def test_new_patterns_are_linear_on_hostile_input(self):
        import time
        start = time.monotonic()
        for s in ("eyJ" * 100000, "SG." * 100000, "xoxe." * 60000, "hooks.slack.com/services/" * 20000, "http://u:" * 30000,
                  "a:" * 100000 + "@", "1//0" * 50000, "AKIA" * 60000, "://" * 60000, "xapp-" * 50000, "glpat-" * 50000,
                  "https://" + "u:" * 200000):
            ev.redact(s)
        self.assertLess(time.monotonic() - start, 10)

    def test_plain_text_is_kept(self):
        for s in ("unit-read head=abc123def456", "https://example.org/a@b/path", "host:8080 ok", "xox", "npm install",
                  "task SYN-100 rev 3", "ghost_writer", "ask-1 glob-2", "ya29 is a prefix", "AKIA", "see ASIA region"):
            self.assertEqual(ev.redact(s), s, s)

    def _env(self, text):
        d = running()
        d["evidence"][0]["ref"] = "unit-read " + text
        d["current_owner"] = "r7 " + text
        d["consumer"]["named"] = "c " + text
        d["coverage_gaps"] = ["gap " + text]
        return d

    def test_every_output_path(self):
        for label, text, frag in prefixed_canaries():
            p = tmp_json([self._env(text)])
            for fmt in ("json", "text"):
                r = cli(RECOMMEND, "--format", fmt, "--now", NOW, p)
                self.assertEqual(r.returncode, 0, label)
                self.assertFalse(frag in r.stdout + r.stderr, (label, fmt))
            r = cli(VALIDATE, "--now", NOW, p)
            self.assertFalse(frag in r.stdout + r.stderr, (label, "validator"))

    def test_refusal_reasons_and_validator_messages(self):
        for label, text, frag in prefixed_canaries():
            d = running()
            d["evidence"][0]["task_id"] = "id " + text      # WRONG_TASK message echoes the evidence task id
            d["evidence"][0]["head"] = "ffff" + text.replace("\n", " ")
            p = tmp_json([d])
            r = cli(RECOMMEND, "--format", "json", "--now", NOW, p)
            self.assertIn('"refused": true', r.stdout, label)
            self.assertFalse(frag in r.stdout + r.stderr, label)
            r = cli(VALIDATE, "--now", NOW, p)
            self.assertEqual(r.returncode, 1, label)
            self.assertFalse(frag in r.stdout + r.stderr, label)

    def test_unreadable_messages(self):
        for label, text, frag in prefixed_canaries()[:12]:
            r = cli(RECOMMEND, "--now", text.replace("\n", " "))
            self.assertFalse(frag in r.stdout + r.stderr, label)
            r = cli(VALIDATE, "--now", text.replace("\n", " "))
            self.assertFalse(frag in r.stdout + r.stderr, label)


PLACEHOLDER_CLASS = ["pending", "Pending.", "PENDING!", "unavailable", "Unavailable", "tbc", "TBC", "tbd", "TBD.", "unset", "UNSET",
                     "unknown-", "unknown--", "UNKNOWN_", "unknown?", "n/a", "N/A", "n/a/", "/n/a", "N / A", "n /a", "n/ a", "n\\a", "N\\A",
                     "n\\ a", " n / a ", "n.a.", "n-a", "(pending)", "[tbd]", "pending.", "not set", "Not  Set", "not-set", "unassigned",
                     "unk", "none", "null", "nil", "undefined", "unspecified", "missing", "empty", "?", "--", "TBA", "todo",
                     "not available", "n/a.", "N/A;", "unknown ", "​pending", "pend­ING", "ｔｂｄ"]
NOT_AN_IDENT = ["yes", "no", "true", "false", "ok", "OK", "okay", "self", "Self.", "authorized", "approved", "confirmed",
                "accepted", "y", "n", "me", "same", "own"]


class D2_PlaceholderClass(unittest.TestCase):
    def test_normalizer_class(self):
        for v in PLACEHOLDER_CLASS:
            self.assertTrue(ev.is_unknown(v), repr(v))
        for v in ("syn-worker-100.service", "pid:4242", "ryzen7", "verifier-1", "unknown-host-7", "pending-review-agent-2",
                  "abc123def4567890", "ledger row L-77 grant"):
            self.assertFalse(ev.is_unknown(v), v)

    def test_words_are_not_identities_or_refs(self):
        for v in NOT_AN_IDENT:
            self.assertIsNone(ev.ident(v), v)
            self.assertFalse(ev.ref_like(v), v)
        for v in PLACEHOLDER_CLASS:
            self.assertFalse(ev.ref_like(v), repr(v))
            self.assertIsNone(ev.ident(v), repr(v))
        for v in ("ledger row L-77 grant", "approvals #187", "msg:abc", "https://x.example/a/1", "joe-20261101", "A1663/AC4", "L-77"):
            self.assertTrue(ev.ref_like(v), v)
        for v in (None, 5, True, ["a1"], {"a": 1}):
            self.assertFalse(ev.ref_like(v), repr(v))

    def test_running_worker_fields(self):
        for v in PLACEHOLDER_CLASS + NOT_AN_IDENT:
            for f in ("host", "unit", "child"):
                d = running()
                d["worker"][f] = v
                self.assertIn("RUNNING_NO_EVIDENCE", codes(ev.validate(d, now=NOW)), (f, v))
            d = running()
            d["worker"].update(host=v, unit=v, child=v)
            r = one(d)
            self.assertNotEqual(r["disposition"], "reuse-active-worker", v)
            self.assertTrue(r["refused"], v)

    def test_running_evidence_ref_placeholder(self):
        for v in PLACEHOLDER_CLASS:
            d = running()
            d["evidence"][0]["ref"] = v
            self.assertIn("RUNNING_NO_EVIDENCE", codes(ev.validate(d, now=NOW)), repr(v))

    def test_ack_evidence(self):
        for v in PLACEHOLDER_CLASS + NOT_AN_IDENT:
            d = done()
            d["ack"] = {"accepted": True, "evidence": v}
            self.assertIn("INVENTED_ACK", codes(ev.validate(d, now=NOW)), repr(v))
        d = done()
        d["ack"] = {"accepted": True, "evidence": "msg:consumer-ack-0042"}
        self.assertNotIn("INVENTED_ACK", codes(ev.validate(d, now=NOW)))

    def test_authorization_refs(self):
        for v in PLACEHOLDER_CLASS + NOT_AN_IDENT:
            if not v.strip():
                continue
            d = done()
            d["consumer"].update(available=False, alternate="verifier-9", alternate_authorized=True,
                                 alternate_authorization_ref=v)
            self.assertNotIn("verifier-9", one(d)["later_consumers"], repr(v))
        d = done()
        d["consumer"].update(available=False, alternate="verifier-9", alternate_authorized=True,
                             alternate_authorization_ref="ledger row L-77 grant")
        self.assertIn("verifier-9", one(d)["later_consumers"])

    def test_consumer_and_reviewer(self):
        for v in PLACEHOLDER_CLASS + NOT_AN_IDENT:
            if not v.strip():
                continue
            d = done()
            d["consumer"]["named"] = v
            r = one(d)
            self.assertEqual(r["next_consumer"], "UNKNOWN", repr(v))
            d = done()
            d["result"].update(reviewed=True, reviewed_by=v)
            self.assertEqual(one(d)["role"], "independent-verification", repr(v))

    def test_artifact_head_account(self):
        for v in PLACEHOLDER_CLASS:
            d = done()
            d["result"].update(artifact=v, event=None)
            self.assertIn("DONE_NO_ARTIFACT", codes(ev.validate(d, now=NOW)), repr(v))
            d = copy.deepcopy(load("complete_all_known"))
            for path in (("target", "head"), ("worker", "account")):
                e = copy.deepcopy(d)
                e[path[0]][path[1]] = v
                self.assertIn("FALSE_COMPLETE", codes(ev.validate(e, now=NOW)), (path, v))


SURR = "WF-1\ud800"


class D3_UnencodableTextNeverTraces(unittest.TestCase):
    def _fields(self):
        for path in (("task_id",), ("parent",), ("current_owner",), ("next_action",), ("target", "branch"), ("worker", "host"),
                     ("worker", "account"), ("consumer", "named"), ("result", "artifact"), ("source", "identity")):
            yield path

    def _put(self, d, path, v):
        t = d
        for p in path[:-1]:
            t = t[p]
        t[path[-1]] = v

    def test_every_mode_every_field(self):
        raw = json.dumps  # ensure_ascii keeps the escape as \ud800 in the file
        for path in self._fields():
            d = done()
            self._put(d, path, "x\ud800y")
            p = tmp_json(raw([d, running("SYN-2", "synthetic/r2", "b2")]))
            for args in (("--format", "text"), ("--format", "json")):
                r = cli(RECOMMEND, *args, "--now", NOW, p)
                self.assertNotIn("Traceback", r.stderr, (path, args))
                self.assertIn(r.returncode, (0, 2), (path, args))
            r = cli(VALIDATE, "--now", NOW, p)
            self.assertNotIn("Traceback", r.stderr, path)
            self.assertIn(r.returncode, (0, 1, 2), path)

    def test_text_output_is_escaped_and_other_record_still_evaluated(self):
        p = tmp_json(json.dumps([running(SURR), running("SYN-2", "synthetic/r2", "b2")]))
        r = cli(RECOMMEND, "--format", "text", "--now", NOW, p)
        self.assertEqual(r.returncode, 0, r.stderr[-200:])
        self.assertIn("SYN-2", r.stdout)
        self.assertNotIn("\ud800", r.stdout)
        r = cli(VALIDATE, "--now", NOW, p)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn(r.returncode, (0, 1))

    def test_surrogate_in_path_and_now(self):
        for script in (RECOMMEND, VALIDATE):
            r = cli(script, "--now", "2026-11-13T07:00:00Z\udcff", "x.json")
            self.assertNotIn("Traceback", r.stderr, script)
            self.assertEqual(r.returncode, 2, script)
            r = cli(script, "no-such-dir-\udcff/x.json")
            self.assertNotIn("Traceback", r.stderr, script)
            self.assertEqual(r.returncode, 2, script)

    def test_invalid_utf8_input_is_unreadable(self):
        td = tempfile.mkdtemp(prefix="wf4-")
        p = pathlib.Path(td) / "bad.json"
        p.write_bytes(b'[{"task_id": "\xff\xfe"}]')
        for script in (RECOMMEND, VALIDATE):
            r = cli(script, "--now", NOW, str(p))
            self.assertNotIn("Traceback", r.stderr, script)
            self.assertEqual(r.returncode, 2, script)

    def test_ascii_only_stdout(self):
        import os
        p = tmp_json(json.dumps([running("WF-é\ud800")]))
        env = dict(os.environ, PYTHONIOENCODING="ascii", PYTHONUTF8="0")
        for script, a in ((RECOMMEND, ("--format", "text")), (VALIDATE, ())):
            r = subprocess.run([sys.executable, "-I", script, *a, "--now", NOW, p], capture_output=True, text=True, env=env)
            self.assertNotIn("Traceback", r.stderr, script)

    def test_library_render_text_does_not_raise(self):
        out = rec([running(SURR)])
        self.assertIsInstance(rc.render_text(out), str)
        self.assertEqual(ev.safe_text("a\ud800b").encode("utf-8").decode("utf-8"), "a\\ud800b")


class D4_OneFileOrUsageError(unittest.TestCase):
    def test_extra_files_are_a_usage_error_naming_them(self):
        a = tmp_json([running()], "a.json")
        b = tmp_json([running("SYN-2", "synthetic/r2", "b2")], "b.json")
        for fmt in ("json", "text"):
            r = cli(RECOMMEND, "--format", fmt, "--now", NOW, a, b)
            self.assertEqual(r.returncode, 2, fmt)
            self.assertIn(b, r.stdout + r.stderr)
            self.assertNotIn("Traceback", r.stderr)
            self.assertNotIn("SYN-2", r.stdout.replace(b, ""))  # no partial evaluation is printed as a result
        r = cli(RECOMMEND, "--now", NOW, b, a)
        self.assertEqual(r.returncode, 2)
        self.assertIn(a, r.stdout + r.stderr)

    def test_single_file_still_works_either_position(self):
        a = tmp_json([running()], "a.json")
        for args in (("--now", NOW, a), (a, "--now", NOW), ("--format", "json", a, "--now", NOW)):
            r = cli(RECOMMEND, *args)
            self.assertEqual(r.returncode, 0, args)

    def test_unknown_option_and_bad_format_are_usage_errors(self):
        a = tmp_json([running()], "a.json")
        for args in (("--bogus", a), ("--format", "yaml", a), ("--format",), ("--observed-at",)):
            r = cli(RECOMMEND, "--now", NOW, *args)
            self.assertEqual(r.returncode, 2, args)
            self.assertNotIn("Traceback", r.stderr, args)

    def test_validator_still_takes_many_files(self):
        a = tmp_json([running()], "a.json")
        b = tmp_json([running("SYN-2", "synthetic/r2", "b2")], "b.json")
        r = cli(VALIDATE, "--now", NOW, a, b)
        self.assertEqual(r.stdout.count("envelope(s) enumerated"), 2)

    def test_the_other_script_with_two_files_in_queue_mode(self):
        a = tmp_json([], "a.json")
        r = cli(RECOMMEND, "--queue", "--now", NOW, a, a)
        self.assertEqual(r.returncode, 2)


class D5_NestingBehaviourMatchesSkillMd(unittest.TestCase):
    def test_moderate_nesting_is_refused_per_record(self):
        deep = []
        for _ in range(5000):
            deep = [deep]
        out = rec([running(), deep, running("SYN-2", "synthetic/r2", "b2")])
        self.assertEqual([o["refused"] for o in out], [False, True, False])

    def test_beyond_parser_limit_is_unreadable_whole_file(self):
        p = tmp_json("[" + '{"a":' * 150000 + "1" + "}" * 150000 + "]")
        for script in (RECOMMEND, VALIDATE):
            r = cli(script, "--now", NOW, p)
            self.assertEqual(r.returncode, 2, script)
            self.assertIn("UNREADABLE", r.stdout, script)
            self.assertNotIn("Traceback", r.stderr, script)

    def test_skill_md_states_exactly_that(self):
        txt = (SKILL / "SKILL.md").read_text()
        flat = " ".join(txt.split())
        self.assertIn("whole-file UNREADABLE (exit 2)", flat)
        self.assertRegex(flat, r"beyond the JSON parser(?:'s)? (?:recursion )?limit")
        self.assertNotRegex(flat, r"absurd nesting\) is refused for that record only")
        self.assertRegex(flat, r"recommend\.py takes exactly one FILE")


class D1b_SeparatorAndFlagShapes(unittest.TestCase):
    """the reviewer's N5 shapes that are not provider prefixes: separators, flags, header colon forms"""
    def test_shapes(self):
        a = _frag(20, 8)
        for label, text in (
                ("bearer-colon", "bea" + "rer: " + a), ("bearer-eq", "bea" + "rer=" + a),
                ("cli-flag", "--pass" + "word " + a), ("cli-flag-short", "-tok" + "en " + a),
                ("cli-flag-quoted", "--api-" + "key '" + a + " x'"), ("cli-flag-eq", "--sec" + "ret=" + a),
                ("fullwidth-eq", "pass" + "word\uff1d" + a), ("fullwidth-colon", "tok" + "en\uff1a " + a),
                ("arrow", "sec" + "ret => " + a), ("arrow2", "ke" + "y -> " + a),
                ("auth-fullwidth", "Author" + "ization\uff1a Bea" + "rer " + a)):
            red = ev.redact("x " + text + " tail")
            self.assertFalse(a in red, label)
            self.assertTrue(red.endswith("tail") or "tail" in red, label)

    def test_plain_flags_and_words_kept(self):
        for s in ("cmd --no-cache --verbose ok", "pass the key to the door", "--format json", "key point"):
            self.assertEqual(ev.redact(s), s, s)

    def test_hostile_linear(self):
        import time
        start = time.monotonic()
        for s in ("bea" + "rer " * 60000, "--tok" + "en " * 60000, "-" * 200000, "--" + "a-" * 100000, "pass" + "word=>" * 40000):
            ev.redact(s)
        self.assertLess(time.monotonic() - start, 10)


class D6_CheapUnconfirmedConcerns(unittest.TestCase):
    def test_real_worker_ids_are_not_over_refused(self):
        for v in ("pid=77", "%12", "tmux:%12", "fe80::1%eth0"):
            d = running()
            d["worker"]["child"] = v
            self.assertNotIn("RUNNING_NO_EVIDENCE", codes(ev.validate(d, now=NOW)), v)
        for v in ("two words", "", "a b"):
            d = running()
            d["worker"]["child"] = v
            if v:
                self.assertIn("RUNNING_NO_EVIDENCE", codes(ev.validate(d, now=NOW)), v)

    def test_placeholder_task_id_names_no_task(self):
        for v in ("TBD", "UNKNOWN", "pending", "n/a", "?"):
            d = running(v)
            d["evidence"][0]["task_id"] = v
            r = one(d)
            self.assertTrue(r["refused"], v)
            self.assertIn("SCHEMA_TYPE", r["reason_codes"], v)


if __name__ == "__main__":
    unittest.main()
