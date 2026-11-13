"""Integration of extract_register.py + register_validate.py on the real child-B endpoints.jsonl
(copied to tests/fixtures; sha256 recorded). Source-only evidence: this exercises the conversion and
validator on captured extraction rows, it does not prove any production behavior."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SK = Path(__file__).resolve().parent.parent
FIX = SK / "tests" / "fixtures" / "endpoints.jsonl"
PY = [sys.executable, "-I"]


def run(*a):
    return subprocess.run(PY + [str(x) for x in a], capture_output=True, text=True)


class RealInput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.rows = [json.loads(l) for l in FIX.read_text().splitlines() if l.strip()]
        cls.ex = run(SK / "scripts" / "extract_register.py", "--heuristic-fusion", FIX, cls.out)
        cls.partial = json.loads((cls.out / "register-partial.json").read_text())
        cls.complete = json.loads((cls.out / "register-declared-complete.json").read_text())
        cls.vp = run(SK / "scripts" / "register_validate.py", cls.out / "register-partial.json")
        cls.vc = run(SK / "scripts" / "register_validate.py", cls.out / "register-declared-complete.json")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_fixture_is_the_captured_input(self):
        want = (SK / "tests" / "fixtures" / "endpoints.jsonl.sha256").read_text().split()[0]
        self.assertEqual(hashlib.sha256(FIX.read_bytes()).hexdigest(), want)
        self.assertEqual(len(self.rows), 507)

    def test_extractor_clean_exit_no_rejections(self):
        self.assertEqual(self.ex.returncode, 0, self.ex.stderr)
        self.assertEqual(json.loads((self.out / "rejected.json").read_text()), [])

    def test_partial_passes_with_warnings(self):
        self.assertEqual(self.vp.returncode, 0, self.vp.stdout[-800:])
        self.assertIn("WARN unassigned", self.vp.stdout)
        self.assertIn("WARN unknown-field", self.vp.stdout)
        self.assertNotIn("ERROR", self.vp.stdout)

    def test_same_records_declared_complete_refused_with_records_named(self):
        self.assertEqual(self.vc.returncode, 1)
        last = [l for l in self.vp.stdout.splitlines()] and [l for l in self.vc.stdout.splitlines() if l.startswith("REFUSED")][-1]
        self.assertIn("unassigned", last)
        an_unassigned = next(r["record_id"] for r in self.complete["records"] if r["family"] == "UNASSIGNED")
        self.assertIn(f"{an_unassigned}:unassigned", last)
        an_assigned = next(r["record_id"] for r in self.complete["records"] if r["family"] != "UNASSIGNED")
        self.assertIn(f"ERROR unknown-field [{an_assigned}]", self.vc.stdout)

    def test_records_identical_between_partial_and_complete(self):
        self.assertEqual(self.partial["records"], self.complete["records"])

    def test_every_row_accounted_for_exactly_once(self):
        seen = sorted(n for r in self.partial["records"] for n in r["source_rows"])
        self.assertEqual(seen, list(range(1, 508)))

    def test_unassigned_total_equals_enumerated_unassigned(self):
        recs = [r for r in self.partial["records"] if r["family"] == "UNASSIGNED"]
        rows_in = sum(len(r["source_rows"]) for r in recs)
        self.assertEqual(rows_in, sum(1 for r in self.rows if r["family"] == "UNASSIGNED"))
        self.assertEqual(rows_in, 237)
        self.assertIn(f'"unassigned": {len(recs)}', self.vp.stdout)

    def test_all_58_families_present(self):
        self.assertEqual(len(self.partial["families"]), 58)

    def test_no_invented_sides_loaded_or_labels(self):
        for r in self.partial["records"]:
            self.assertEqual(r["role"], "UNKNOWN", r["record_id"])
            self.assertNotEqual(r["installed_state"], "loaded")
            self.assertEqual(r["label"], "unclassified")
        claimed = sum(1 for r in self.partial["records"] if "loaded" in r.get("claimed_installed_states", []))
        self.assertEqual(claimed, 9)

    def test_installed_only_with_stated_path_sha(self):
        for r in self.partial["records"]:
            if r["installed_state"] == "installed":
                for s in r.get("sources") or [r["source_identity"]]:
                    self.assertIn("sha256", s)

    def test_raw_identity_and_evidence_verbatim(self):
        raws = {s["raw"] for r in self.partial["records"] for s in (r.get("sources") or [r["source_identity"]])}
        refs = {e["ref"] for r in self.partial["records"] for e in r["evidence"]}
        for row in self.rows:
            self.assertIn(row["source_identity"], raws)
            self.assertIn(row["evidence"], refs)

    def test_summa_recall_pairs_fused_without_qualifier(self):
        fused = [r for r in self.partial["records"] if "sources" in r]
        self.assertEqual(len(fused), 6)
        for r in fused:
            self.assertEqual(sorted(s["repo"] for s in r["sources"]), ["recall", "summa"])
            self.assertNotIn("@", r["component"])
        self.assertFalse([r for r in self.partial["records"] if " @ " in r["component"]])

    def test_validator_derived_counts_match_enumerated(self):
        counts = json.loads(self.vp.stdout[: self.vp.stdout.index("}\n") + 1])
        self.assertEqual(counts["records"], len(self.partial["records"]))
        self.assertEqual(counts["families"], 58)


if __name__ == "__main__":
    unittest.main()
