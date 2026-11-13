"""Regression tests for the third independent exact-head review of 2904d701 (DEFECT-1..DEFECT-13).
One class per defect, each closing the defect as a class. Source-only: synthetic envelopes, no production claim.
Every test gets its clock by injection (`now=` / `--now`); nothing here reads the host date.
Credential canaries are assembled at run time from fragments and are never printed or stored in a fixture."""
import copy
import itertools
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

from helpers import FIX, FIXTURE_NOW, SKILL, codes, load

import envelope_validate as ev
import queue_adapter as qa
import recommend as rc

RECOMMEND = str(SKILL / "scripts" / "recommend.py")
VALIDATE = str(SKILL / "scripts" / "envelope_validate.py")
ADAPTER = str(SKILL / "scripts" / "queue_adapter.py")
NOW = FIXTURE_NOW
OTHER_HEAD = "ffff0000aaaa1111"
HEAD = "abc123def4567890"


def cli(script, *args):
    return subprocess.run([sys.executable, "-I", script, *args], capture_output=True, text=True)


def running(tid="SYN-100", repo="synthetic/repo-a", branch="syn/b1"):
    d = load("good_running")
    d.update(task_id=tid)
    d["target"].update(repo=repo, branch=branch, head=HEAD)
    d["evidence"][0].update(task_id=tid)
    return d


def ready(tid="SYN-100", repo="synthetic/repo-z", branch="syn/z"):
    d = running(tid, repo, branch)
    d.update(state="NOT_STARTED", owner_reachable=True)
    d["effect"].update(state="none")
    d["worker"].update(host="UNKNOWN", unit="UNKNOWN", child="UNKNOWN", invocation="UNKNOWN", session="UNKNOWN")
    d["observed_at"]["worker"] = "UNKNOWN"
    return d


def done(tid="SYN-100"):
    d = load("done_unreviewed")
    d["task_id"] = tid
    d["result"]["task_id"] = tid
    for e in d["evidence"]:
        e["task_id"] = tid
    return d


def rec(objs, now=NOW):
    return rc.recommend_set(objs, now=now)


def one(d, now=NOW):
    return rec([d], now)[0]


def tmp_json(obj, name="in.json"):
    td = tempfile.mkdtemp(prefix="wf3-")
    p = pathlib.Path(td) / name
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj))
    return str(p)


class D01_DuplicateTaskIsStateAware(unittest.TestCase):
    def test_running_original_wins_in_every_record_order(self):
        kinds = {"run": running(), "ready": ready(), "ns2": ready(repo="synthetic/repo-y", branch="syn/y"), "done": done()}
        for order in itertools.permutations(kinds):
            if "run" not in order:
                continue
            out = rec([copy.deepcopy(kinds[k]) for k in order])
            for k, r in zip(order, out):
                if k == "run":
                    self.assertEqual(r["disposition"], "reuse-active-worker", order)
                else:
                    self.assertTrue(r["refused"], (order, k))
                    self.assertIn("DUPLICATE_TASK", r["reason_codes"], (order, k))
                self.assertNotEqual(r["disposition"], "ready-unowned-slice", (order, k))
                self.assertFalse(r["new_worker_recommended"])

    def test_two_running_same_id_first_kept(self):
        a, b = rec([running(), running(repo="synthetic/repo-q", branch="syn/q")])
        self.assertEqual(a["disposition"], "reuse-active-worker")
        self.assertIn("DUPLICATE_TASK", b["reason_codes"])

    def test_no_running_two_ready_one_slice_only(self):
        out = rec([ready(), ready(repo="synthetic/repo-y", branch="syn/y")])
        self.assertEqual([r["disposition"] for r in out].count("ready-unowned-slice"), 1)

    def test_task_id_case_and_space_variants_are_the_same_task(self):
        out = rec([ready(tid="syn-100 "), running(tid="SYN-100")])
        self.assertTrue(out[0]["refused"] and "DUPLICATE_TASK" in out[0]["reason_codes"])
        self.assertEqual(out[1]["disposition"], "reuse-active-worker")


class D02_UnknownTimestampsCannotGreen(unittest.TestCase):
    def blank_all(self, d):
        d["observed_at"] = {"envelope": "UNKNOWN", "worker": "UNKNOWN", "result": "UNKNOWN"}
        for e in d["evidence"]:
            e["observed_at"] = "UNKNOWN"
        d["source"].update(identity_at="UNKNOWN", revision_at="UNKNOWN")
        return d

    def test_all_unknown_for_every_state_is_refused(self):
        stale_done = self.blank_all(done())
        blocked = ready()
        blocked["state"] = "BLOCKED"
        for name, d in (("done", stale_done), ("ns", self.blank_all(ready())), ("blocked", self.blank_all(blocked)),
                        ("running", self.blank_all(running()))):
            r = one(d)
            self.assertTrue(r["refused"], name)
            self.assertEqual(r["disposition"], "UNKNOWN", name)
            self.assertIn("UNKNOWN_TIMESTAMP", r["reason_codes"], name)
            self.assertFalse(r["new_worker_recommended"], name)

    def test_each_required_timestamp_alone_unknown_is_refused(self):
        for state, mk in (("running", running), ("ns", ready), ("done", done)):
            d = mk()
            d["observed_at"]["envelope"] = "UNKNOWN"
            self.assertIn("UNKNOWN_TIMESTAMP", codes(ev.validate(d, now=NOW)), state)
        d = running()
        d["observed_at"]["worker"] = "UNKNOWN"
        self.assertTrue(one(d)["refused"])
        d = running()
        d["evidence"][0]["observed_at"] = "UNKNOWN"
        self.assertIn("UNKNOWN_TIMESTAMP", codes(ev.validate(d, now=NOW)))
        d = done()
        d["observed_at"]["result"] = "UNKNOWN"
        self.assertIn("UNKNOWN_TIMESTAMP", codes(ev.validate(d, now=NOW)))

    def test_known_timestamps_still_green(self):
        self.assertEqual(ev.validate(running(), now=NOW), [])
        self.assertEqual(ev.validate(ready(), now=NOW), [])
        self.assertEqual(ev.validate(done(), now=NOW), [])


class D03_D12_D11_MalformedNeverCrashes(unittest.TestCase):
    EXTREME = ("9999-12-31T23:59:59-05:00", "0001-01-01T00:00:00+05:00")

    def test_extreme_timestamp_is_a_finding_not_an_exception(self):
        for t in self.EXTREME:
            d = running()
            d["observed_at"]["envelope"] = t
            f = ev.validate(d, now=NOW)
            self.assertTrue({"BAD_TIMESTAMP"} & codes(f), t)

    def test_one_bad_record_does_not_kill_the_set(self):
        bad = running(tid="SYN-200", repo="synthetic/repo-b", branch="syn/b2")
        bad["observed_at"]["envelope"] = self.EXTREME[0]
        out = rec([running(), bad])
        self.assertEqual(out[0]["disposition"], "reuse-active-worker")
        self.assertTrue(out[1]["refused"])

    def test_cli_set_with_extreme_timestamp(self):
        bad = running(tid="SYN-200", repo="synthetic/repo-b", branch="syn/b2")
        bad["observed_at"]["envelope"] = self.EXTREME[0]
        p = tmp_json([running(), bad])
        r = cli(RECOMMEND, "--format", "json", "--now", NOW, p)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(json.loads(r.stdout)[0]["disposition"], "reuse-active-worker")

    def test_cli_extreme_now_is_unreadable_exit_2(self):
        p = tmp_json([running()])
        for script in (RECOMMEND, VALIDATE):
            for t in self.EXTREME:
                r = cli(script, "--now", t, p)
                self.assertEqual(r.returncode, 2, (script, t, r.stderr[-200:]))
                self.assertNotIn("Traceback", r.stderr)

    def test_deep_nesting_is_unreadable_exit_2(self):
        p = tmp_json("[" * 100000)
        for script in (RECOMMEND, VALIDATE):
            r = cli(script, "--now", NOW, p)
            self.assertEqual(r.returncode, 2, (script, r.stderr[-200:]))
            self.assertNotIn("Traceback", r.stderr)
        r = cli(ADAPTER, p)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)

    def test_library_deep_nesting(self):
        with self.assertRaises(ValueError):
            ev.load_json_text("[" * 100000)
        deep = []
        for _ in range(5000):
            deep = [deep]
        out = rec([running(), deep])
        self.assertEqual(out[0]["disposition"], "reuse-active-worker")
        self.assertTrue(out[1]["refused"])

    def test_naive_datetime_now_is_valueerror(self):
        import datetime
        naive = datetime.datetime(2026, 11, 13, 7, 0)
        for call in (lambda: ev.as_now(naive), lambda: ev.validate(running(), now=naive),
                     lambda: ev.validate_set([running()], now=naive), lambda: rc.recommend_set([running()], now=naive),
                     lambda: ev.as_now(12345), lambda: ev.as_now(datetime.datetime.max.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=-5))))):
            with self.assertRaises(ValueError):
                call()

    def test_validator_now_system_uses_the_patchable_host_clock(self):
        src = (SKILL / "scripts" / "envelope_validate.py").read_text()
        self.assertLessEqual(len(re.findall(r"datetime\.now\(", src)), 1, "at most one host-clock call site: host_now()")
        self.assertIn("host_now()", src.split("def parse_args")[1].split("def main")[0])


PLACEHOLDER_VALUES = ["unknown", " Unknown ", "UNK", "unk", "?", "??", "-", "--", "tbd", "TBD", "n/a", "N/A.", "na", "none", "None",
                      "null", "nil", "undefined", "not available", "Not  Available", "Unknown.", "<unknown>", "[tbd]",
                      "(none)", "'null'", '"n/a"', "unknown​", "﻿none", "un​known", " n/a ",
                      "ＵＮＫＮＯＷＮ", "not available", "UNKNOWN!", "  ", "\t\n", "⁠tbd"]


class D04_D07_OnePlaceholderNormalizer(unittest.TestCase):
    def test_normalizer_unit(self):
        for v in PLACEHOLDER_VALUES:
            self.assertTrue(ev.is_unknown(v), repr(v))
        for v in ("syn-worker-100.service", "pid:4242", "ryzen7", "ledger row L-77 grant", "abc123def4567890", "verifier-1", "unknown-host-7"):
            self.assertFalse(ev.is_unknown(v), v)

    def test_running_evidence_fields(self):
        for v in PLACEHOLDER_VALUES:
            for f in ("host", "unit", "child"):
                d = running()
                d["worker"][f] = v
                self.assertIn("RUNNING_NO_EVIDENCE", codes(ev.validate(d, now=NOW)), (f, v))

    def test_done_artifact(self):
        for v in PLACEHOLDER_VALUES:
            d = done()
            d["result"]["artifact"] = v
            d["result"]["event"] = None
            self.assertIn("DONE_NO_ARTIFACT", codes(ev.validate(d, now=NOW)), v)

    def test_ack_evidence(self):
        for v in PLACEHOLDER_VALUES:
            d = done()
            d["ack"] = {"accepted": True, "evidence": v}
            self.assertIn("INVENTED_ACK", codes(ev.validate(d, now=NOW)), v)

    def test_consumer_named_placeholder_is_not_a_consumer(self):
        for v in PLACEHOLDER_VALUES:
            d = done()
            d["consumer"]["named"] = v
            r = one(d)
            self.assertEqual(r["next_consumer"], "UNKNOWN", v)
            self.assertEqual(r["later_consumers"], [], v)

    def test_authorization_refs(self):
        for field in ("alternate_authorization_ref",):
            for v in PLACEHOLDER_VALUES:
                if not v.strip():
                    continue
                d = done()
                d["consumer"].update(available=False, alternate="verifier-9", alternate_authorized=True)
                d["consumer"][field] = v
                self.assertNotIn("verifier-9", one(d)["later_consumers"], v)
        d = done()
        d["consumer"].update(available=False, alternate="verifier-9", alternate_authorized=True,
                             alternate_authorization_ref="ledger row L-77 grant")
        self.assertIn("verifier-9", one(d)["later_consumers"])

    def test_reviewed_by_placeholder_keeps_independent_verification(self):
        for v in PLACEHOLDER_VALUES:
            if not v.strip():
                continue
            d = done()
            d["result"].update(reviewed=True, reviewed_by=v)
            self.assertEqual(one(d)["role"], "independent-verification", v)
        d = done()
        d["result"].update(reviewed=True, reviewed_by="verifier-7")
        self.assertEqual(one(d)["role"], "coordinator-decision")

    def test_declared_complete_head_and_account(self):
        base = load("complete_all_known")
        self.assertEqual(ev.validate(base, now=NOW), [])
        for v in PLACEHOLDER_VALUES:
            for path in (("target", "head"), ("worker", "account"), ("worker", "model"), ("consumer", "named")):
                d = copy.deepcopy(base)
                d[path[0]][path[1]] = v
                self.assertIn("FALSE_COMPLETE", codes(ev.validate(d, now=NOW)), (path, v))
        d = copy.deepcopy(base)
        d["target"]["head"] = "not-a-sha-just-words"
        self.assertIn("FALSE_COMPLETE", codes(ev.validate(d, now=NOW)))


def _frag(n, seed):
    """run-time fragment of n letters/digits; never a literal in the repo"""
    alpha = "qzxvkjwmbtrhdp0123456789"
    return "".join(alpha[(i * 7 + seed) % len(alpha)] for i in range(n))


def canaries():
    """(label, text, fragments that must not survive redaction); built at run time from pieces."""
    a, b, c = _frag(24, 1), _frag(18, 5), _frag(30, 9)
    sk = "s" + "k-" + "an" + "t-" + a
    out = [
        ("sk-quoted", "key '%s' used" % sk, [a]),
        ("sk-paren", "see (%s) here" % sk, [a]),
        ("sk-bare", "use %s now" % sk, [a]),
        ("pw-spaces", 'pass' + 'word="%s %s" end' % (a, b), [a, b]),
        ("pw-eq", "pass" + "word=" + a, [a]),
        ("auth-basic", "Author" + "ization: Ba" + "sic " + a + "==", [a]),
        ("auth-bearer", "Author" + "ization: Bea" + "rer " + a, [a]),
        ("bearer-bare", "Bea" + "rer " + a, [a]),
        ("url-creds", "https://usr:" + a + "@host.example/x", [a]),
        ("url-userinfo-only", "https://" + a + "@host.example/x", [a]),
        ("ghp", "tok " + "gh" + "p_" + c + b[:6], [c]),
        ("jwt", "eyJ" + a + "." + "eyJ" + b + "." + c, [a, b, c]),
        ("pem", "-----BEGIN " + "PRIVATE " + "KEY-----\n" + a + "\n" + b + "\n-----END " + "PRIVATE " + "KEY-----", [a, b]),
        ("apikey-json", '{"api' + '_key": "' + a + '"}', [a]),
        ("apikey-json-compact", '{"api' + '_key":"' + a + '"}', [a]),
        ("apikey-header", "x-api-" + "key: " + a, [a]),
        ("secret-colon", "sec" + "ret : " + a, [a]),
        ("env-export", "export AWS_SECRET_" + "ACCESS_KEY=" + a, [a]),
        ("token-quoted", 'tok' + 'en="' + a + '"', [a]),
        ("token-single-spaces", "tok" + "en: '" + a + " " + b + "'", [a, b]),
    ]
    return out


class D06_RedactionCoversShapes(unittest.TestCase):
    def test_redact_unit_all_shapes(self):
        for label, text, frags in canaries():
            red = ev.redact("ref " + text + " tail")
            for f in frags:
                self.assertFalse(f in red, label)
            self.assertIn("[REDACTED]", red, label)
            self.assertTrue(red.endswith("tail") or red.endswith("tail\n"), label)

    def test_redact_is_linear_on_hostile_input(self):
        import time
        start = time.monotonic()
        for s in ("a" * 200000, "key" * 50000, "x" * 50000 + "tok" + "en" + "y" * 50000, "sk-" * 50000, "eyJ" * 60000,
                  "http://" * 30000, "a" * 100000 + "://", "tok" + 'en="' * 30000, "bea" + "rer " * 30000,
                  "-----BEGIN PRIVATE " + "KEY-----" + "a" * 200000):
            ev.redact(s)
        self.assertLess(time.monotonic() - start, 20)

    def test_long_name_still_redacted(self):
        a = _frag(16, 2)
        self.assertFalse(a in ev.redact("tok" + "en" + "_" * 150 + "=" + a))

    def test_redact_keeps_plain_text(self):
        for s in ("unit-read head=abc123", "worker.unit=syn-worker-100.service", "task SYN-100 rev 3", "pid:4242 ryzen7",
                  "monitor 3 items", "a-b: c"):
            self.assertEqual(ev.redact(s), s, s)

    def _env_with(self, text):
        d = running()
        d["evidence"][0]["ref"] = "unit-read " + text
        d["current_owner"] = "r7 " + text
        d["worker"]["session"] = "sess " + text
        d["coverage_gaps"] = ["gap " + text]
        return d

    def test_every_recommend_output_path(self):
        for label, text, frags in canaries():
            p = tmp_json([self._env_with(text)])
            for fmt in ("json", "text"):
                r = cli(RECOMMEND, "--format", fmt, "--now", NOW, p)
                self.assertEqual(r.returncode, 0, label)
                for f in frags:
                    self.assertFalse(f in r.stdout, (label, fmt))
                    self.assertFalse(f in r.stderr, (label, fmt))

    def test_validator_output_paths(self):
        for label, text, frags in canaries():
            d = running()
            d["evidence"][0]["task_id"] = "id " + text
            d["evidence"][0]["head"] = text.replace("\n", " ")
            p = tmp_json([d], name="in-" + text[:0] + "x.json")
            r = cli(VALIDATE, "--now", NOW, p)
            for f in frags:
                self.assertFalse(f in r.stdout + r.stderr, label)

    def test_validator_unreadable_path_and_now_message_redacted(self):
        a = _frag(20, 3)
        r = cli(VALIDATE, "--now", "pass" + "word=" + a)
        self.assertEqual(r.returncode, 2)
        self.assertFalse(a in r.stdout + r.stderr)
        r = cli(RECOMMEND, "--now", "tok" + "en=" + a)
        self.assertEqual(r.returncode, 2)
        self.assertFalse(a in r.stdout + r.stderr)
        td = tempfile.mkdtemp(prefix="wf3-")
        missing = str(pathlib.Path(td) / ("sk-" + "xx-" + a + ".json"))
        for script in (VALIDATE, RECOMMEND, ADAPTER):
            r = cli(script, missing)
            self.assertFalse(a in r.stdout + r.stderr, script)

    def test_adapter_output_redacted(self):
        a = _frag(22, 11)
        rows = [{"ask_id": "A-1", "rev": 1, "owner": "r7", "status": "open", "row_id": "r1", "seq": 1,
                 "claim": "claimed pass" + "word=" + a, "waits_on": []}]
        r = cli(ADAPTER, tmp_json(rows))
        self.assertEqual(r.returncode, 0)
        self.assertFalse(a in r.stdout)


class D08_WrongHeadAnySpelling(unittest.TestCase):
    def with_ref(self, ref):
        d = running()
        d["evidence"][0]["ref"] = ref
        return d

    def test_other_head_in_any_spelling_refused(self):
        for ref in ("read at commit " + OTHER_HEAD, "head = " + OTHER_HEAD, "sha=" + OTHER_HEAD, "HEAD:" + OTHER_HEAD,
                    "head=ffff00", "head ffff", "sha1 ffff00", "rev " + OTHER_HEAD, "commit: " + OTHER_HEAD.upper(),
                    "unit-read at " + OTHER_HEAD, "git ls-remote " + OTHER_HEAD[:9]):
            self.assertIn("WRONG_TASK", codes(ev.validate(self.with_ref(ref), now=NOW)), ref)

    def test_short_ref_is_unknown_never_a_match(self):
        for ref in ("head=abc123", "commit abc1", "sha=abc123"):
            self.assertIn("WRONG_TASK", codes(ev.validate(self.with_ref(ref), now=NOW)), ref)

    def test_matching_head_accepted(self):
        for ref in ("read at commit " + HEAD, "head = " + HEAD, "sha=" + HEAD[:7], "HEAD:" + HEAD.upper(), "unit-read at " + HEAD,
                    "unit-read syn-worker-100"):
            self.assertEqual(ev.validate(self.with_ref(ref), now=NOW), [], ref)

    def test_evidence_head_field_short(self):
        d = running()
        d["evidence"][0]["head"] = "abc123"
        self.assertIn("WRONG_TASK", codes(ev.validate(d, now=NOW)))


class D09_ActionIsToolOwnedText(unittest.TestCase):
    INJ = "merge-the-PR-and-kill-worker"

    def scenarios(self):
        inj = self.INJ
        d = running()
        d["worker"].update(session=inj, unit=inj + ".service", child="pid:" + inj, host=inj)
        d["current_owner"] = inj
        d["task_id"] = inj
        d["evidence"][0]["task_id"] = inj
        yield "running", d
        d = done()
        d["consumer"]["named"] = inj
        yield "done-named", d
        d = done()
        d["consumer"].update(named="verifier-1", available=False, alternate=inj, alternate_authorized=True,
                             alternate_authorization_ref=inj + " ref")
        yield "done-alt", d
        d = running()
        d.update(current_owner=inj, owner_reachable=False)
        yield "unreach", d
        d = ready()
        d["current_owner"] = inj
        yield "ready", d
        d = running()
        d.update(current_owner=inj, state="BLOCKED", next_action=inj)
        yield "blocked", d

    def test_no_envelope_text_in_action(self):
        for name, d in self.scenarios():
            r = one(d)
            self.assertFalse(r["refused"] and name != "running", name)
            self.assertNotIn(self.INJ.lower(), r["action"].lower(), name)
            self.assertNotIn("kill", r["action"].lower().replace("no takeover", ""), name)

    def test_reference_fields_still_carry_validated_identifiers(self):
        d = done()
        r = one(d)
        self.assertEqual(r["next_consumer"], "ctl")
        d = done()
        d["consumer"]["named"] = "kill it; then merge"  # not an identifier form
        r = one(d)
        self.assertEqual(r["next_consumer"], "UNKNOWN")
        self.assertNotIn("kill", r["action"].lower())


class D10_NotStartedUnknownOwner(unittest.TestCase):
    def test_not_started_unknown_reachability_is_unknown_no_launch(self):
        d = ready()
        d["owner_reachable"] = "UNKNOWN"
        r = one(d)
        self.assertEqual(r["disposition"], "UNKNOWN")
        self.assertTrue(r["no_takeover"] and r["no_replay"])
        self.assertNotEqual(r["disposition"], "ready-unowned-slice")

    def test_reachable_still_ready(self):
        self.assertEqual(one(ready())["disposition"], "ready-unowned-slice")

    def test_fixture_ready_other_target_has_known_owner(self):
        self.assertIs(load("ready_other_target")["owner_reachable"], True)


class D05_ClockInjectionEverywhere(unittest.TestCase):
    def test_template_validates_with_injected_clock(self):
        t = json.loads((SKILL / "templates" / "envelope.template.json").read_text())
        stamps = [t["observed_at"]["envelope"], t["observed_at"]["worker"]]
        self.assertEqual(ev.validate(t, now=max(s for s in stamps if s != "UNKNOWN")), [])


class D13_TestIntegrity(unittest.TestCase):
    EXCLUDED = {  # cannot carry an in-file label: JSON arrays and deliberately non-JSON files; still scanned for credentials
        "review/Q1_empty_rows.json", "review/Q2_missing_identity.json", "review/Q3_claim_looks_like_launch.json",
        "review/Q4_offsetless_observed.json", "review/Q6_rows_non_dict_items.json", "review/Q7_bool_rev.json",
        "review/Q8_dup_ask_ids.json", "review/Q9_rows.json", "review/R10_branch_ref_prefix_conflict.json",
        "review/R9_target_case_conflict.json", "review/c_bad_dup.json", "review/c_bad_target.json", "review/c_good.json",
        "review/e_nonobject.json", "review/S3_empty_file.json", "review/S4_adapter_bad.json"}

    def test_every_fixture_labelled_or_listed(self):
        files = sorted(p for p in FIX.rglob("*") if p.is_file())
        self.assertGreater(len(files), 100)
        rels = {str(p.relative_to(FIX)) for p in files}
        self.assertLessEqual(self.EXCLUDED, rels)
        for p in files:
            rel = str(p.relative_to(FIX))
            if rel in self.EXCLUDED:
                continue
            self.assertIn("source-only", p.read_text(), rel)

    def test_no_fixture_holds_credential_shapes(self):
        bad = re.compile(r"token=|sk-ant|password|bearer|PRIVATE KEY|api[_-]?key|FAKE", re.I)
        for p in FIX.rglob("*"):
            if p.is_file():
                self.assertIsNone(bad.search(p.read_text()), str(p.relative_to(FIX)))

    def test_blank_artifacts_are_asserted_refused(self):
        src = (pathlib.Path(__file__).parent / "test_review.py").read_text()
        self.assertNotRegex(src, r"or v\.strip\(\)\s*==")


if __name__ == "__main__":
    unittest.main()
