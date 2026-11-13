"""Paired known-good / known-bad controls a-h. Source-only: they exercise the decision logic on
synthetic or derived fixtures and do not prove production behavior."""
import unittest

from helpers import codes, load

import recommend as rc


def one(name):
    return rc.recommend_set([load(name)])[0]


def many(*names):
    return rc.recommend_set([load(n) for n in names])


class ControlA_HealthyWorkerReuse(unittest.TestCase):
    def test_good_healthy_worker_is_reused(self):
        r = one("good_running")
        self.assertEqual((r["disposition"], r["role"]), ("reuse-active-worker", "implementation"))
        self.assertFalse(r["new_worker_recommended"])
        self.assertTrue(r["evidence_used"])

    def test_bad_stale_or_unproven_worker_is_not_reused(self):
        for n in ("stale_running", "running_no_child", "running_no_unit"):
            r = one(n)
            self.assertTrue(r["refused"], n)
            self.assertNotEqual(r["disposition"], "reuse-active-worker", n)
            self.assertFalse(r["new_worker_recommended"], n)


class ControlB_CompletedSourceGoesToReview(unittest.TestCase):
    def test_good_completed_unreviewed_is_consumed_for_review(self):
        r = one("done_unreviewed")
        self.assertEqual((r["disposition"], r["role"]), ("consume-completed-terminal", "independent-verification"))
        self.assertFalse(r["new_worker_recommended"])
        self.assertEqual(r["next_consumer"], "ctl")

    def test_bad_artifactless_done_is_refused_not_recoded(self):
        r = one("done_no_artifact")
        self.assertTrue(r["refused"])
        self.assertFalse(r["new_worker_recommended"])
        self.assertNotEqual(r["disposition"], "consume-completed-terminal")


class ControlC_DuplicateAndConflict(unittest.TestCase):
    def test_good_independent_target_progresses(self):
        a, b = many("good_running", "ready_other_target")
        self.assertEqual(a["disposition"], "reuse-active-worker")
        self.assertEqual(b["disposition"], "ready-unowned-slice")
        self.assertFalse(b["refused"])
        self.assertEqual(b["role"], "implementation")

    def test_bad_duplicate_task_refused(self):
        a, b = many("good_running", "good_running")
        self.assertTrue(a["refused"] and b["refused"])
        self.assertIn("DUPLICATE_TASK", a["reason_codes"])

    def test_bad_second_worker_on_conflicting_target_refused(self):
        a, b = many("good_running", "ready_conflicting_target")
        self.assertEqual(a["disposition"], "reuse-active-worker")  # the running one is not disturbed
        self.assertTrue(b["refused"])
        self.assertIn("CONFLICTING_TARGET", b["reason_codes"])
        self.assertNotEqual(b["disposition"], "ready-unowned-slice")


class ControlD_WrongTaskStaleRevision(unittest.TestCase):
    def test_good_matching_evidence(self):
        self.assertFalse(one("good_running")["refused"])

    def test_bad_wrong_task_and_stale_revision_refused(self):
        for n, code in (("wrong_task_evidence", "WRONG_TASK"), ("done_wrong_task_result", "WRONG_TASK"),
                        ("stale_revision_evidence", "STALE_REVISION"), ("done_stale_revision_evidence", "STALE_REVISION")):
            r = one(n)
            self.assertTrue(r["refused"], n)
            self.assertIn(code, r["reason_codes"], n)
            self.assertEqual(r["disposition"], "UNKNOWN", n)


class ControlE_MissingMalformedStale(unittest.TestCase):
    def test_good_complete_record_is_not_refused(self):
        self.assertFalse(one("good_running")["refused"])

    def test_bad_evidence_is_refused_never_passed(self):
        for n in ("missing_field", "malformed_type", "malformed_enum", "bad_timestamp", "stale_running", "stale_running_evidence"):
            r = one(n)
            self.assertTrue(r["refused"], n)
            self.assertEqual((r["role"], r["disposition"]), ("UNKNOWN", "UNKNOWN"), n)
            self.assertFalse(r["new_worker_recommended"], n)

    def test_non_object_record_is_refused(self):
        self.assertTrue(rc.recommend_set(["junk"])[0]["refused"])


class ControlF_FalseComplete(unittest.TestCase):
    def test_good_truly_complete_passes(self):
        self.assertFalse(one("complete_all_known")["refused"])

    def test_bad_false_complete_refused(self):
        r = one("false_complete")
        self.assertTrue(r["refused"])
        self.assertIn("FALSE_COMPLETE", r["reason_codes"])


class ControlG_UnreachableOwnerUnknownEffect(unittest.TestCase):
    def test_good_reachable_owner_known_effect_is_reused(self):
        self.assertEqual(one("good_running")["disposition"], "reuse-active-worker")

    def test_bad_unreachable_owner_no_takeover_no_replay(self):
        r = one("unreachable_owner")
        self.assertEqual(r["disposition"], "blocked")
        self.assertTrue(r["no_takeover"] and r["no_replay"])
        self.assertFalse(r["new_worker_recommended"])
        self.assertNotIn("launch", r["action"].lower().replace("no launch", ""))

    def test_bad_unknown_effect_no_takeover_no_replay(self):
        r = one("unknown_effect")
        self.assertEqual(r["disposition"], "UNKNOWN")
        self.assertTrue(r["no_takeover"] and r["no_replay"])
        self.assertFalse(r["new_worker_recommended"])

    def test_bad_replay_permitted_on_unknown_effect_refused(self):
        r = one("replay_allowed_unknown_effect")
        self.assertTrue(r["refused"])
        self.assertTrue(r["no_replay"])

    def test_recommendation_grants_no_authority(self):
        for n in ("good_running", "done_unreviewed", "ready_other_target", "unreachable_owner"):
            self.assertFalse(one(n)["grants_authority"], n)


class ControlH_BusyConsumer(unittest.TestCase):
    def test_good_available_consumer_named(self):
        self.assertEqual(one("done_unreviewed")["next_consumer"], "ctl")

    def test_busy_consumer_keeps_terminal_and_names_authorized_alternate(self):
        r = one("done_consumer_busy")
        self.assertEqual(r["disposition"], "consume-completed-terminal")
        self.assertTrue(r["terminal_durable"])
        self.assertEqual(r["later_consumers"], ["ctl", "hermes"])
        self.assertFalse(r["ack_recorded"])
        self.assertFalse(r["new_worker_recommended"])

    def test_bad_unauthorized_alternate_gets_no_authority_from_label(self):
        r = one("done_consumer_busy_alt_unauth")
        self.assertEqual(r["later_consumers"], ["ctl"])
        self.assertIn("rb", r["action"])
        self.assertIn("no authority", r["action"])

    def test_no_alternate_is_reported_unknown(self):
        r = one("done_consumer_busy_no_alt")
        self.assertEqual(r["later_consumers"], ["ctl"])
        self.assertIn("UNKNOWN alternate", r["action"])

    def test_bad_invented_ack_refused(self):
        r = one("done_consumer_busy_invented_ack")
        self.assertTrue(r["refused"])
        self.assertIn("INVENTED_ACK", r["reason_codes"])


class UnknownReportedNotFilled(unittest.TestCase):
    def test_unknown_account_is_carried_through(self):
        r = one("done_unreviewed")
        self.assertIn("account=UNKNOWN", " ".join(r["evidence_used"]))
        self.assertIn("account", " ".join(r["unknown_fields"]))


if __name__ == "__main__":
    unittest.main()
