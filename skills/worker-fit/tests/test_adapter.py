import json
import unittest

from helpers import FIX, FIXTURE_NOW, codes, install_fixture_clock, remove_fixture_clock

import envelope_validate as ev
import queue_adapter as qa
import recommend as rc

ROWS = json.loads((FIX / "queue_rows.json").read_text())["rows"]



def setUpModule():
    install_fixture_clock()


def tearDownModule():
    remove_fixture_clock()


class QueueAdapter(unittest.TestCase):
    def test_adapter_keeps_unknown_where_row_is_silent(self):
        envs = qa.rows_to_envelopes(ROWS)
        self.assertEqual(len(envs), 3)
        for e in envs:
            self.assertEqual(ev.validate(e), [], e["task_id"])
            self.assertEqual(e["worker"]["account"], "UNKNOWN")
            self.assertEqual(e["worker"]["child"], "UNKNOWN")
            self.assertEqual(e["effect"]["state"], "UNKNOWN")
            self.assertEqual(e["consumer"]["named"], "UNKNOWN")
            self.assertEqual(e["state"], "UNKNOWN")
            self.assertEqual(e["work_shape"], "UNKNOWN")
            self.assertFalse(e["declared_complete"])

    def test_claim_string_is_not_a_worker_launch(self):
        e = [x for x in qa.rows_to_envelopes(ROWS) if x["task_id"] == "A1659"][0]
        self.assertIn("unit:r7-irv-a-221051", e["source"]["claim"])
        self.assertEqual(e["worker"]["unit"], "UNKNOWN")
        self.assertEqual(e["revision"], 8)
        self.assertTrue(any("not a worker launch" in g for g in e["coverage_gaps"]))

    def test_recommendation_on_queue_rows_is_unknown_without_takeover(self):
        for r in rc.recommend_set(qa.rows_to_envelopes(ROWS)):
            self.assertFalse(r["refused"])
            self.assertEqual(r["disposition"], "UNKNOWN")
            self.assertTrue(r["no_takeover"] and r["no_replay"])
            self.assertFalse(r["new_worker_recommended"])

    def test_bad_row_without_identity_is_refused_not_invented(self):
        e = qa.rows_to_envelopes([{"owner": "r7"}])[0]
        self.assertTrue(rc.recommend_set([e])[0]["refused"])

    def test_observed_at_is_only_what_the_caller_supplies(self):
        e = qa.rows_to_envelopes(ROWS, observed_at="2026-11-13T06:28:27Z")[0]
        self.assertEqual(e["observed_at"]["envelope"], "2026-11-13T06:28:27Z")
        self.assertEqual(e["source"]["revision_at"], "UNKNOWN")

    def test_cli_roundtrip(self):
        import subprocess, sys
        script = str(FIX.parent.parent / "scripts" / "recommend.py")
        out = subprocess.run([sys.executable, "-I", script, "--now", FIXTURE_NOW, "--queue", str(FIX / "queue_rows.json")],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("A1663", out.stdout)
        self.assertIn("recommendation only", out.stdout.lower())
        js = subprocess.run([sys.executable, "-I", script, "--now", FIXTURE_NOW, "--format", "json", str(FIX / "good_running.json")],
                            capture_output=True, text=True)
        self.assertEqual(json.loads(js.stdout)[0]["disposition"], "reuse-active-worker")


if __name__ == "__main__":
    unittest.main()
