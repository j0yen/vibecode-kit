"""Lost-message rule: a "message lost" finding needs a traced producer -> alias adapter -> installed waiter path.
Fixtures are source-only; they exercise the rule, not production behavior."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_register import SK

sys.path.insert(0, str(SK / "scripts"))
import discriminator_check as dc  # noqa: E402
import lost_message_check as lm  # noqa: E402

SHA = "0d92184811e1881ff7130a7cf624c3aefe695b884b1e8b6a190c0266886f9fe8"
FIX = SK / "tests" / "fixtures" / "ctl-event-wait.sh"


def link(ref, **kw):
    d = {"ref": ref, "sha256": "a" * 64}
    d.update(kw)
    return d


def full(actor="bld", waiter_verdict="refuse"):
    return {"id": "F-lost", "claim": "message-lost", "label": "observed-defect",
            "trace": {"producer": link("p.sh:10", actor=actor),
                      "adapters": [link("adapter.py:5", maps_to=actor)],
                      "waiter": link("ctl-event-wait.sh:28", installed_state="installed",
                                     verdict_for_actor=waiter_verdict)}}


class LostMessage(unittest.TestCase):
    def test_complete_trace_with_refusal_may_be_observed_defect(self):
        res = lm.classify(full())
        self.assertEqual(res["label"], "observed-defect")
        self.assertEqual(res["missing_links"], [])
        self.assertTrue(res["ok"])

    def test_complete_trace_where_waiter_accepts_is_not_lost(self):
        res = lm.classify(full(waiter_verdict="accept"))
        self.assertEqual(res["label"], "positive-control")

    def test_missing_producer_is_conditional_risk_naming_link(self):
        f = full()
        del f["trace"]["producer"]
        res = lm.classify(f)
        self.assertEqual(res["label"], "conditional-risk")
        self.assertEqual(res["missing_links"], ["producer"])
        self.assertFalse(res["ok"])

    def test_missing_adapter_stage_named_unless_explicitly_none(self):
        f = full()
        del f["trace"]["adapters"]
        self.assertEqual(lm.classify(f)["missing_links"], ["adapter"])
        f["trace"]["adapters"] = []
        self.assertEqual(lm.classify(f)["missing_links"], ["adapter"])
        f["trace"]["adapters_none_evidence"] = "launcher.sh:3 publishes the actor name unchanged"
        self.assertEqual(lm.classify(f)["missing_links"], [])

    def test_waiter_must_be_installed_with_identity(self):
        f = full()
        f["trace"]["waiter"]["installed_state"] = "source-only"
        self.assertEqual(lm.classify(f)["missing_links"], ["waiter-installed"])
        f = full()
        del f["trace"]["waiter"]["sha256"]
        self.assertEqual(lm.classify(f)["missing_links"], ["waiter-installed"])

    def test_unavailable_link_is_missing(self):
        f = full()
        f["trace"]["producer"]["available"] = False
        self.assertIn("producer", lm.classify(f)["missing_links"])

    def test_refused_when_labelled_defect_without_trace(self):
        f = {"id": "F1", "claim": "message-lost", "label": "observed-defect"}
        res = lm.classify(f)
        self.assertFalse(res["ok"])
        self.assertEqual(res["missing_links"], ["producer", "adapter", "waiter-installed"])
        self.assertEqual(res["label"], "conditional-risk")

    def test_conditional_risk_label_with_missing_link_is_accepted(self):
        f = {"id": "F1", "claim": "message-lost", "label": "conditional-risk"}
        self.assertTrue(lm.classify(f)["ok"])

    def test_non_lost_claims_pass_through(self):
        self.assertTrue(lm.classify({"id": "F2", "claim": "schema-mismatch", "label": "observed-defect"})["ok"])

    def test_cli_refuses_with_missing_link_named(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.json"
            p.write_text(json.dumps({"id": "F1", "claim": "message-lost", "label": "observed-defect"}))
            out = subprocess.run([sys.executable, "-I", str(SK / "scripts" / "lost_message_check.py"), str(p)],
                                 capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn("producer", out.stdout)
        self.assertIn("REFUSED", out.stdout)

    def test_ops_bld_rls_discriminator_stays_conditional_risk(self):
        raw = FIX.read_bytes()
        self.assertEqual(__import__("hashlib").sha256(raw).hexdigest(), SHA)
        pat = dc.extract_pattern(raw.decode(), 28)
        v = dc.verdicts(pat, ["ops", "bld", "rls", "rb", "r7"])
        self.assertEqual([v[n] for n in ("ops", "bld", "rls")], ["refuse"] * 3)
        for n in ("ops", "bld", "rls"):
            f = {"id": f"IF010-{n}", "claim": "message-lost", "label": "observed-defect",
                 "trace": {"waiter": link("ctl-event-wait.sh:28", sha256=SHA, installed_state="installed",
                                          verdict_for_actor=v[n])}}
            res = lm.classify(f)
            self.assertEqual(res["label"], "conditional-risk", n)
            self.assertEqual(res["missing_links"], ["producer", "adapter"], n)
            self.assertFalse(res["ok"])


if __name__ == "__main__":
    unittest.main()
