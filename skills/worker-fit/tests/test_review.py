"""Regression tests for the independent exact-head review of d9b9c676 (defects D1-D14).
One test class per defect. Fixtures under fixtures/review/ are the reviewer's synthetic case files,
copied verbatim (case id = file name). Source-only: they do not prove production behavior."""
import copy
import datetime
from unittest import mock
import json
import pathlib
import subprocess
import sys
import unittest

from helpers import FIX, SKILL, codes, install_fixture_clock, remove_fixture_clock

import envelope_validate as ev
import queue_adapter as qa
import recommend as rc

REAL_HOST_NOW = ev.host_now  # captured at import, before the fixture clock is installed
REV = FIX / "review"
RECOMMEND = str(SKILL / "scripts" / "recommend.py")
VALIDATE = str(SKILL / "scripts" / "envelope_validate.py")
ADAPTER = str(SKILL / "scripts" / "queue_adapter.py")
NOW = "2026-11-12T23:00:00Z"



def setUpModule():
    install_fixture_clock()


def tearDownModule():
    remove_fixture_clock()


def case(cid):
    return ev.load_json_file(str(REV / (cid + ".json")))


def env0(cid):
    return ev._records(case(cid))[0][0]


def recs(cid, now=None):
    return rc.recommend_set(case(cid), now=now) if now else rc.recommend_set(case(cid))


def first(cid, now=None):
    return recs(cid, now)[0]


def cli(script, *args):
    return subprocess.run([sys.executable, "-I", script, *args], capture_output=True, text=True)


def good():
    return copy.deepcopy(ev.load_json_file(str(FIX / "good_running.json")))


def known_target(d):
    d["target"] = {"repo": "acme/app", "branch": "feat/one", "head": "abc123def4567890"}
    return d


def done():
    return copy.deepcopy(ev.load_json_file(str(FIX / "done_unreviewed.json")))


class D01_MissingTaskIdNoCrash(unittest.TestCase):
    def test_validate_set_does_not_raise(self):
        res = ev.validate_set(case("S2_missing_task_id_single"))
        self.assertTrue(any(f["severity"] == "REFUSE" for f in res["findings_by_index"][0]))

    def test_recommend_refuses_with_exit_0(self):
        r = cli(RECOMMEND, "--format", "json", str(REV / "S2_missing_task_id_single.json"))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)[0]
        self.assertTrue(out["refused"])
        self.assertEqual((out["role"], out["disposition"]), ("UNKNOWN", "UNKNOWN"))

    def test_validator_cli_no_traceback(self):
        r = cli(VALIDATE, str(REV / "S2_missing_task_id_single.json"))
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.returncode, 1)


class D02_DuplicateTaskRefusesNewcomerOnly(unittest.TestCase):
    def test_original_undisturbed(self):
        a, b = recs("c_bad_dup")
        self.assertFalse(a["refused"])
        self.assertEqual(a["disposition"], "reuse-active-worker")
        self.assertTrue(b["refused"])
        self.assertIn("DUPLICATE_TASK", b["reason_codes"])


class D03_PlaceholdersAreUnknown(unittest.TestCase):
    def test_reviewer_cases_refused(self):
        for cid in ("U1_lowercase_unknown_unit", "U8_lowercase_unknown_child_running", "N1_child_none",
                    "R6_whitespace_unit", "F4_complete_lowercase_unknown", "F5_artifact_literal_UNKNOWN"):
            r = first(cid)
            self.assertTrue(r["refused"], cid)
            self.assertTrue({"RUNNING_NO_EVIDENCE", "DONE_NO_ARTIFACT", "FALSE_COMPLETE"} & set(r["reason_codes"]), cid)

    def test_variants_for_each_evidence_field(self):
        for v in ("unknown", " Unknown ", "NONE", "  ", "n/a", "null"):
            for f in ("host", "unit", "child"):
                d = good()
                d["worker"][f] = v
                self.assertIn("RUNNING_NO_EVIDENCE", codes(ev.validate(d)), (f, v))
            d = done()
            d["result"]["artifact"] = v
            self.assertTrue({"DONE_NO_ARTIFACT"} & codes(ev.validate(d)) or v.strip() == "", v)

    def test_placeholder_account_is_reported_unknown(self):
        d = good()
        d["worker"]["account"] = " unknown "
        out = rc.recommend_set([d])[0]
        self.assertIn("worker.account", out["unknown_fields"])


class D04_RunningNeedsEvidence(unittest.TestCase):
    def test_empty_evidence_refused(self):
        r = first("R8_empty_evidence")
        self.assertTrue(r["refused"])
        self.assertIn("RUNNING_NO_EVIDENCE", r["reason_codes"])


class D05_ObservationWindow(unittest.TestCase):
    def test_window_is_documented_constant(self):
        self.assertIsInstance(ev.STALE_WINDOW_SECONDS, int)
        self.assertIn("window", (SKILL / "SKILL.md").read_text().lower())

    def test_year_old_refused_against_explicit_now(self):
        r = first("N3_year_old_observation", now=NOW)
        self.assertTrue(r["refused"])
        self.assertIn("STALE_EVIDENCE", r["reason_codes"])

    def test_future_dated_refused(self):
        r = first("N6_future_timestamp", now=NOW)
        self.assertTrue(r["refused"])
        self.assertIn("FUTURE_TIMESTAMP", r["reason_codes"])

    def test_cli_now_argument(self):
        r = cli(RECOMMEND, "--format", "json", "--now", NOW, str(REV / "N3_year_old_observation.json"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout)[0]["refused"])

    def test_cli_bad_now_is_unreadable_exit_2(self):
        r = cli(RECOMMEND, "--now", "yesterday", str(REV / "N3_year_old_observation.json"))
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)


class TestD05Default(unittest.TestCase):
    """Live default: the reference clock is the trusted host clock; fixture dates are test clocks by injection."""

    def setUp(self):  # the live default: undo the module's injected fixture clock
        p = mock.patch.object(ev, "host_now", REAL_HOST_NOW)
        p.start()
        self.addCleanup(p.stop)

    GREEN = {"reuse-active-worker", "consume-completed-terminal", "ready-unowned-slice", "independent-verification"}

    def test_cli_default_refuses_stale_and_future(self):
        for cid, code in (("N3_year_old_observation", "STALE_EVIDENCE"), ("N6_future_timestamp", "FUTURE_TIMESTAMP")):
            r = cli(RECOMMEND, "--format", "json", str(REV / (cid + ".json")))
            self.assertEqual(r.returncode, 0, r.stderr)
            rec = json.loads(r.stdout)[0]
            self.assertTrue(rec["refused"], cid)
            self.assertIn(code, rec["reason_codes"], cid)
            self.assertNotIn(rec["disposition"], self.GREEN, cid)

    def test_cli_validate_default_refuses(self):
        for cid in ("N3_year_old_observation", "N6_future_timestamp"):
            self.assertEqual(cli(VALIDATE, str(REV / (cid + ".json"))).returncode, 1, cid)

    def test_library_default_refuses_stale_and_future(self):
        for cid, code in (("N3_year_old_observation", "STALE_EVIDENCE"), ("N6_future_timestamp", "FUTURE_TIMESTAMP")):
            r = rc.recommend_set(case(cid))[0]
            self.assertTrue(r["refused"], cid)
            self.assertIn(code, r["reason_codes"], cid)
            self.assertNotIn(r["disposition"], self.GREEN, cid)
            self.assertIn(code, codes(ev.validate(env0(cid))))

    def test_fresh_envelope_greens_against_injected_clock(self):
        d = good()
        stamps = [d["observed_at"]["envelope"], d["observed_at"]["worker"]] + [e["observed_at"] for e in d["evidence"]]
        newest = max(ev.parse_ts(t) for t in stamps if not ev.is_unknown(t))
        clock = (newest + datetime.timedelta(minutes=5)).isoformat()
        self.assertEqual(ev.validate(d, now=clock), [])
        self.assertEqual(rc.recommend_set([d], now=clock)[0]["disposition"], "reuse-active-worker")
        with mock.patch.object(ev, "host_now", lambda: ev.as_now(clock)):
            self.assertEqual(ev.validate(d), [])
            self.assertEqual(rc.recommend_set([d])[0]["disposition"], "reuse-active-worker")
        r = cli(RECOMMEND, "--format", "json", "--now", clock, str(FIX / "good_running.json"))
        self.assertEqual(json.loads(r.stdout)[0]["disposition"], "reuse-active-worker")

    def test_fresh_against_real_host_clock_greens(self):
        d = good()
        now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
        d["observed_at"]["envelope"] = d["observed_at"]["worker"] = now
        d["source"]["identity_at"] = d["source"]["revision_at"] = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2)).replace(microsecond=0).isoformat()
        for e in d["evidence"]:
            e["observed_at"] = now
        self.assertEqual(ev.validate(d), [])

    def test_set_with_stale_newest_refused_without_now(self):
        a = good()
        b = copy.deepcopy(a)
        b["task_id"] = "WF-8"
        b["target"] = {"repo": "acme/third", "branch": "b", "head": a["target"]["head"]}
        b["evidence"] = [dict(e, task_id="WF-8") for e in b["evidence"]]
        for d in (a, b):
            d["observed_at"]["envelope"] = d["observed_at"]["worker"] = "2025-01-01T00:00:00Z"
            d["source"]["identity_at"] = d["source"]["revision_at"] = "2024-12-31T00:00:00Z"
            for e in d["evidence"]:
                e["observed_at"] = "2025-01-01T00:00:00Z"
        res = ev.validate_set([a, b])
        for i in (0, 1):
            self.assertIn("STALE_EVIDENCE", codes(res["findings_by_index"][i]))
        for r in rc.recommend_set([a, b]):
            self.assertTrue(r["refused"])
            self.assertNotIn(r["disposition"], self.GREEN)

    def test_newest_in_set_is_never_the_reference(self):
        old = good()
        old["observed_at"]["envelope"] = old["observed_at"]["worker"] = "2025-01-01T00:00:00Z"
        old["source"]["identity_at"] = old["source"]["revision_at"] = "2024-12-31T00:00:00Z"
        for e in old["evidence"]:
            e["observed_at"] = "2025-01-01T00:00:00Z"
        new = copy.deepcopy(old)
        new["task_id"] = "WF-8"
        new["target"] = {"repo": "acme/third", "branch": "b", "head": old["target"]["head"]}
        new["evidence"] = [dict(e, task_id="WF-8") for e in new["evidence"]]
        for k in ("envelope", "worker"):
            new["observed_at"][k] = "2099-01-01T00:00:00Z"
        for e in new["evidence"]:
            e["observed_at"] = "2099-01-01T00:00:00Z"
        res = ev.validate_set([old, new])
        self.assertIn("FUTURE_TIMESTAMP", codes(res["findings_by_index"][1]))
        self.assertIn("STALE_EVIDENCE", codes(res["findings_by_index"][0]))

    def test_system_alias_and_bad_now(self):
        self.assertEqual(cli(RECOMMEND, "--now", "system", str(REV / "N3_year_old_observation.json")).returncode, 0)
        self.assertEqual(cli(VALIDATE, "--now", "garbage", str(REV / "N3_year_old_observation.json")).returncode, 2)

    def test_skill_documents_default_window_skew(self):
        t = (SKILL / "SKILL.md").read_text()
        for w in ("host clock", "24 h", "5 min"):
            self.assertIn(w, t)
        self.assertNotIn("newest observation in the set; a lone", t)


class D06_FalseCompleteStateAndReview(unittest.TestCase):
    def test_complete_but_running(self):
        r = first("F1_complete_but_running")
        self.assertTrue(r["refused"])
        self.assertIn("FALSE_COMPLETE", r["reason_codes"])

    def test_complete_with_reviewed_unknown(self):
        r = first("F3_complete_reviewed_unknown")
        self.assertTrue(r["refused"])
        self.assertIn("FALSE_COMPLETE", r["reason_codes"])


class D07_IndependentVerification(unittest.TestCase):
    def test_workers_own_session_is_not_the_consumer(self):
        r = first("F6_self_verification")
        self.assertEqual(r["role"], "independent-verification")
        self.assertNotEqual(r["next_consumer"], "sess-WF-1")
        self.assertNotIn("sess-WF-1 consumes", r["action"])
        self.assertIn("not independent", r["action"])

    def test_self_declared_reviewed_does_not_drop_independent_verification(self):
        r = first("F7_author_reviewed_flag")
        self.assertEqual(r["role"], "independent-verification")

    def test_reviewed_with_distinct_reviewer_identity_hands_to_coordinator(self):
        d = done()
        d["result"]["reviewed"] = True
        d["result"]["reviewed_by"] = "verifier-77"
        self.assertEqual(ev.validate(d), [])
        self.assertEqual(rc.recommend_set([d])[0]["role"], "coordinator-decision")

    def test_reviewer_equal_to_worker_session_is_not_distinct(self):
        d = done()
        d["result"]["reviewed"] = True
        d["result"]["reviewed_by"] = d["worker"]["session"]
        self.assertEqual(rc.recommend_set([d])[0]["role"], "independent-verification")

    def test_alternate_equal_to_worker_session_not_used(self):
        d = done()
        d["consumer"].update(available=False, alternate=d["worker"]["session"], alternate_authorized=True,
                             alternate_authorization_ref="grant#1")
        self.assertNotIn(d["worker"]["session"], rc.recommend_set([d])[0]["later_consumers"])


class D08_ReadySliceNeedsNoEffectNoWorker(unittest.TestCase):
    def test_applied_effect_is_not_ready(self):
        r = first("N4_not_started_effect_applied")
        self.assertNotEqual(r["disposition"], "ready-unowned-slice")
        self.assertTrue(r["no_replay"])

    def test_live_worker_on_not_started_is_refused(self):
        r = first("N5_not_started_with_live_worker")
        self.assertTrue(r["refused"])
        self.assertIn("NOT_STARTED_WITH_WORKER", r["reason_codes"])


class D09_TargetNormalisation(unittest.TestCase):
    def test_repo_case_conflicts(self):
        a, b = recs("R9_target_case_conflict")
        self.assertFalse(a["refused"])
        self.assertTrue(b["refused"])
        self.assertIn("CONFLICTING_TARGET", b["reason_codes"])

    def test_refs_heads_prefix_conflicts(self):
        a, b = recs("R10_branch_ref_prefix_conflict")
        self.assertFalse(a["refused"])
        self.assertIn("CONFLICTING_TARGET", b["reason_codes"])


class D10_DuplicateJsonKeys(unittest.TestCase):
    def test_duplicate_key_refused(self):
        r = first("R3_duplicate_json_keys")
        self.assertTrue(r["refused"])
        self.assertIn("DUPLICATE_KEY", r["reason_codes"])

    def test_nested_duplicate_key_refused(self):
        txt = json.dumps(good()).replace('"unit"', '"unit": "x", "unit"', 1)
        obj = ev.load_json_text(txt)
        self.assertIn("DUPLICATE_KEY", codes(ev.validate(obj)))

    def test_cli_refuses_duplicate_keys(self):
        r = cli(RECOMMEND, "--format", "json", str(REV / "R3_duplicate_json_keys.json"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout)[0]["refused"])


class D11_NoRelayedActionNoCredentialEcho(unittest.TestCase):
    def test_blocked_next_action_not_relayed(self):
        r = first("A1_next_action_relayed")
        self.assertEqual(r["disposition"], "blocked")
        for w in ("kill", "replay", "merge"):
            self.assertNotIn(w, r["action"].lower())

    def test_credential_shapes_redacted_everywhere(self):
        for cid in ("A4_credential_echo",):
            for fmt in ("json", "text"):
                out = cli(RECOMMEND, "--format", fmt, str(REV / (cid + ".json"))).stdout
                self.assertNotIn("FAKE", out)
                self.assertIn("[REDACTED]", out)

    def test_redact_unit(self):
        for s in ("token=abc123", "api_key: zzz", "password=hunter2", "Bearer abc.def", "sk-ant-api03-AAAA",
                  "key=ZZZ", "SECRET = q"):
            self.assertNotRegex(ev.redact("ref " + s), r"abc123|zzz|hunter2|abc\.def|AAAA|ZZZ|= q", s)
        self.assertEqual(ev.redact("unit-read head=abc123"), "unit-read head=abc123")

    def test_validator_output_redacted(self):
        d = good()
        d["evidence"][0]["task_id"] = "password=FAKEPW"
        p = pathlib.Path(__file__).parent / "_tmp_redact.json"
        try:
            p.write_text(json.dumps([d]))
            out = cli(VALIDATE, str(p)).stdout
        finally:
            p.unlink()
        self.assertNotIn("FAKEPW", out)


class D12_AlternateNeedsAuthorizationEvidence(unittest.TestCase):
    def test_bare_boolean_does_not_authorize(self):
        r = first("A2_alternate_self_authorized")
        self.assertNotIn("verifier-9", r["later_consumers"])
        self.assertIn("no authority", r["action"])

    def test_boolean_with_reference_authorizes(self):
        d = env0("A2_alternate_self_authorized")
        d["consumer"]["alternate_authorization_ref"] = "grant:ledger-row-42"
        self.assertEqual(ev.validate(d), [])
        self.assertIn("verifier-9", rc.recommend_set([d])[0]["later_consumers"])

    def test_placeholder_reference_does_not_authorize(self):
        d = env0("A2_alternate_self_authorized")
        d["consumer"]["alternate_authorization_ref"] = " unknown "
        self.assertNotIn("verifier-9", rc.recommend_set([d])[0]["later_consumers"])


class D13_StructuralNullsRefusedCleanly(unittest.TestCase):
    def test_envelopes_null(self):
        r = cli(RECOMMEND, "--format", "json", str(REV / "S1_envelopes_null.json"))
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("UNREADABLE", r.stdout)

    def test_rows_null_queue(self):
        r = cli(RECOMMEND, "--format", "json", "--queue", str(REV / "Q5_rows_null.json"))
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("UNREADABLE", r.stdout)

    def test_adapter_non_json(self):
        r = cli(ADAPTER, str(REV / "S4_adapter_bad.json"))
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("UNREADABLE", r.stdout)

    def test_adapter_rows_null(self):
        r = cli(ADAPTER, str(REV / "Q5_rows_null.json"))
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)

    def test_recommend_non_json(self):
        r = cli(RECOMMEND, str(REV / "S4_adapter_bad.json"))
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)

    def test_validator_envelopes_null(self):
        r = cli(VALIDATE, str(REV / "S1_envelopes_null.json"))
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn(r.returncode, (1, 2))


class D14_EvidenceHead(unittest.TestCase):
    def test_head_named_in_ref_must_match(self):
        r = first("W5_evidence_other_head_in_ref")
        self.assertTrue(r["refused"])
        self.assertIn("WRONG_TASK", r["reason_codes"])

    def test_head_field_mismatch_refused(self):
        d = known_target(good())
        d["evidence"][0]["head"] = "deadbeef0000"
        self.assertIn("WRONG_TASK", codes(ev.validate(d)))

    def test_head_field_prefix_match_passes(self):
        d = known_target(good())
        d["evidence"][0]["head"] = d["target"]["head"][:10]
        self.assertEqual(ev.validate(d), [])

    def test_evidence_repo_branch_mismatch_refused(self):
        d = known_target(good())
        d["evidence"][0]["repo"] = "other/repo"
        self.assertIn("WRONG_TASK", codes(ev.validate(d)))
        d = known_target(good())
        d["evidence"][0]["branch"] = "other"
        self.assertIn("WRONG_TASK", codes(ev.validate(d)))
        d = known_target(good())
        d["evidence"][0].update(repo="ACME/App", branch="refs/heads/feat/one")
        self.assertEqual(ev.validate(d), [])


if __name__ == "__main__":
    unittest.main()
