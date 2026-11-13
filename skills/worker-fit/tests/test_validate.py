import json
import unittest

from helpers import FIXTURE_NOW, SKILL, codes, load, install_fixture_clock, remove_fixture_clock

import envelope_validate as ev



def setUpModule():
    install_fixture_clock()


def tearDownModule():
    remove_fixture_clock()


class ValidatorPairs(unittest.TestCase):
    def test_good_running_passes(self):
        self.assertEqual(ev.validate(load("good_running")), [])

    def test_good_done_unreviewed_passes(self):
        self.assertEqual(ev.validate(load("done_unreviewed")), [])

    # e: missing / malformed / stale evidence -> refusal, never a pass
    def test_missing_field_refused(self):
        self.assertIn("SCHEMA_MISSING", codes(ev.validate(load("missing_field"))))

    def test_wrong_type_refused(self):
        self.assertIn("SCHEMA_TYPE", codes(ev.validate(load("malformed_type"))))

    def test_bad_enum_refused(self):
        self.assertIn("SCHEMA_ENUM", codes(ev.validate(load("malformed_enum"))))

    def test_bad_timestamp_refused(self):
        self.assertIn("BAD_TIMESTAMP", codes(ev.validate(load("bad_timestamp"))))

    def test_unknown_top_level_key_refused(self):
        d = load("good_running")
        d["surprise"] = 1
        self.assertIn("UNKNOWN_KEY", codes(ev.validate(d)))

    def test_not_an_object_refused(self):
        self.assertIn("SCHEMA_TYPE", codes(ev.validate(["x"])))

    def test_stale_worker_observation_refused(self):
        self.assertIn("STALE_EVIDENCE", codes(ev.validate(load("stale_running"))))

    def test_stale_evidence_item_refused(self):
        self.assertIn("STALE_EVIDENCE", codes(ev.validate(load("stale_running_evidence"))))

    # d: wrong task id / stale revision
    def test_wrong_task_evidence_refused(self):
        self.assertIn("WRONG_TASK", codes(ev.validate(load("wrong_task_evidence"))))

    def test_wrong_task_result_refused(self):
        self.assertIn("WRONG_TASK", codes(ev.validate(load("done_wrong_task_result"))))

    def test_stale_revision_refused(self):
        self.assertIn("STALE_REVISION", codes(ev.validate(load("stale_revision_evidence"))))

    def test_stale_revision_on_result_refused(self):
        self.assertIn("STALE_REVISION", codes(ev.validate(load("done_stale_revision_evidence"))))

    # RUNNING / DONE evidence
    def test_running_needs_unit_and_child(self):
        self.assertIn("RUNNING_NO_EVIDENCE", codes(ev.validate(load("running_no_child"))))
        self.assertIn("RUNNING_NO_EVIDENCE", codes(ev.validate(load("running_no_unit"))))

    def test_running_needs_host(self):
        d = load("good_running")
        d["worker"]["host"] = "UNKNOWN"
        self.assertIn("RUNNING_NO_EVIDENCE", codes(ev.validate(d)))

    def test_done_without_artifact_refused(self):
        self.assertIn("DONE_NO_ARTIFACT", codes(ev.validate(load("done_no_artifact"))))

    # f: false-complete
    def test_false_complete_refused(self):
        self.assertIn("FALSE_COMPLETE", codes(ev.validate(load("false_complete"))))

    def test_complete_with_all_required_known_passes(self):
        self.assertEqual(ev.validate(load("complete_all_known")), [])

    def test_complete_with_listed_gap_refused(self):
        d = load("complete_all_known")
        d["coverage_gaps"] = ["something unread"]
        self.assertIn("FALSE_COMPLETE", codes(ev.validate(d)))

    # no-replay policy / ACK
    def test_unknown_effect_requires_no_replay(self):
        self.assertIn("NO_REPLAY_POLICY", codes(ev.validate(load("replay_allowed_unknown_effect"))))

    def test_invented_ack_refused(self):
        self.assertIn("INVENTED_ACK", codes(ev.validate(load("done_consumer_busy_invented_ack"))))

    def test_ack_with_evidence_passes(self):
        d = load("done_unreviewed")
        d["ack"] = {"accepted": True, "evidence": "event kid x1 read back"}
        self.assertNotIn("INVENTED_ACK", codes(ev.validate(d)))

    # set level (c)
    def test_set_duplicate_task_refused(self):
        a, b = load("good_running"), load("good_running")
        res = ev.validate_set([a, b])
        self.assertIn("DUPLICATE_TASK", codes(res["set_findings"]))

    def test_set_conflicting_target_refused(self):
        res = ev.validate_set([load("good_running"), load("ready_conflicting_target")])
        self.assertIn("CONFLICTING_TARGET", codes(res["findings_by_index"][1]))
        self.assertNotIn("CONFLICTING_TARGET", codes(res["findings_by_index"][0]))

    def test_set_independent_target_allowed(self):
        res = ev.validate_set([load("good_running"), load("ready_other_target")])
        self.assertEqual(res["findings_by_index"], [[], []])
        self.assertEqual(res["set_findings"], [])

    def test_count_is_derived_not_declared(self):
        res = ev.validate_set({"declared_total": 99, "envelopes": [load("good_running")]})
        self.assertEqual(res["derived_count"], 1)
        self.assertIn("DECLARED_COUNT_MISMATCH", codes(res["set_findings"]))

    def test_schema_file_matches_validator_constants(self):
        schema = json.loads((SKILL / "schema" / "envelope.schema.json").read_text())
        self.assertEqual(sorted(schema["required"]), sorted(ev.REQUIRED_TOP))
        self.assertEqual(sorted(schema["properties"]["state"]["enum"]), sorted(ev.STATES))
        self.assertEqual(sorted(schema["properties"]["work_shape"]["enum"]), sorted(ev.SHAPES))

    def test_cli_exit_codes(self):
        import subprocess, sys, tempfile, pathlib
        script = str(SKILL / "scripts" / "envelope_validate.py")
        good = str(SKILL / "tests" / "fixtures" / "good_running.json")
        bad = str(SKILL / "tests" / "fixtures" / "false_complete.json")
        self.assertEqual(subprocess.run([sys.executable, "-I", script, "--now", FIXTURE_NOW, good], capture_output=True).returncode, 0)
        r = subprocess.run([sys.executable, "-I", script, "--now", FIXTURE_NOW, bad], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FALSE_COMPLETE", r.stdout)


if __name__ == "__main__":
    unittest.main()
