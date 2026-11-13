"""Continuation controls: explicit endpoint identity, multi-source, unassigned preservation."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_register import base, check, codes, rec, rv

SK = Path(__file__).resolve().parent.parent


def src(repo, commit="c" * 40, version=None, **kw):
    s = {"repo": repo, "commit": commit, "version": version or commit, "available": True}
    s.update(kw)
    return s


def multi(rid, comp="ctx", **kw):
    r = rec(rid, role="UNKNOWN", comp=comp, **kw)
    del r["source_identity"]
    r["sources"] = [src("summa", path_or_command="summa/README.md"),
                    src("recall", commit="d" * 40, path_or_command="recall/README.md")]
    return r


class EndpointIdentity(unittest.TestCase):
    def test_two_endpoints_one_component_distinct_by_path(self):
        reg = base("partial")
        a = rec("E1", role="producer", comp="svc-a", path_or_command="/bin/one")
        b = rec("E2", role="producer", comp="svc-a", path_or_command="/bin/two")
        reg["records"] += [a, b]
        res = check(reg)
        self.assertTrue(res["ok"], res["findings"])
        self.assertNotIn("duplicate-record", codes(res))

    def test_true_duplicate_same_path_refused(self):
        reg = base("partial")
        reg["records"] += [rec("E1", comp="svc-z", path_or_command="/bin/one"),
                           rec("E2", comp="svc-z", path_or_command="/bin/one")]
        res = check(reg)
        self.assertFalse(res["ok"])
        self.assertIn("duplicate-record", codes(res))
        self.assertIn("E1", json.dumps(res["findings"]))
        self.assertIn("E2", json.dumps(res["findings"]))

    def test_slice1_duplicate_without_path_still_refused(self):
        reg = base("partial")
        reg["records"] += [rec("E1", comp="svc-z"), rec("E2", comp="svc-z")]
        self.assertIn("duplicate-record", codes(check(reg)))

    def test_path_vs_no_path_are_distinct(self):
        reg = base("partial")
        reg["records"] += [rec("E1", comp="svc-z"), rec("E2", comp="svc-z", path_or_command="/x")]
        self.assertNotIn("duplicate-record", codes(check(reg)))


class MultiSource(unittest.TestCase):
    def test_summa_recall_pair_kept_with_both_sources(self):
        reg = base("partial")
        reg["records"].append(multi("M1"))
        res = check(reg)
        self.assertTrue(res["ok"], res["findings"])
        got = [r for r in reg["records"] if r["record_id"] == "M1"][0]
        self.assertEqual([s["repo"] for s in got["sources"]], ["summa", "recall"])
        self.assertNotIn("@", got["component"])

    def test_both_source_forms_refused(self):
        reg = base("partial")
        m = multi("M1")
        m["source_identity"] = src("summa")
        reg["records"].append(m)
        self.assertIn("source-form", codes(check(reg)))

    def test_neither_source_form_refused(self):
        reg = base("partial")
        m = multi("M1")
        del m["sources"]
        reg["records"].append(m)
        self.assertIn("source-form", codes(check(reg)))

    def test_empty_sources_refused(self):
        reg = base("partial")
        m = multi("M1")
        m["sources"] = []
        reg["records"].append(m)
        self.assertFalse(check(reg)["ok"])

    def test_one_unknown_source_blocks_complete_names_source(self):
        reg = base()
        m = multi("M1", role="consumer") if False else multi("M1")
        m["role"] = "consumer"
        m["sources"][1]["version"] = "UNKNOWN"
        reg["records"].append(m)
        res = check(reg)
        self.assertFalse(res["ok"])
        msgs = [f["message"] for f in res["findings"] if f["record"] == "M1" and f["code"] == "unknown-field"]
        self.assertTrue(any("sources[1]" in m for m in msgs), msgs)
        self.assertFalse(any("sources[0]" in m for m in msgs), msgs)

    def test_unavailable_second_source_needs_unknown_state(self):
        reg = base("partial")
        m = multi("M1")
        m["sources"][1]["available"] = False
        m["installed_state"] = "installed"
        reg["records"].append(m)
        self.assertIn("unavailable-source-not-unknown", codes(check(reg)))


class Unassigned(unittest.TestCase):
    def ua(self, rid, comp):
        return rec(rid, family="UNASSIGNED", role="UNKNOWN", comp=comp, label="unclassified",
                   installed_state="UNKNOWN")

    def test_unassigned_kept_in_partial_with_marker_warning(self):
        reg = base("partial")
        reg["records"] += [self.ua("U1", "unit-a"), self.ua("U2", "unit-b")]
        res = check(reg)
        self.assertTrue(res["ok"], res["findings"])
        warns = [f for f in res["findings"] if f["code"] == "unassigned"]
        self.assertEqual({f["record"] for f in warns}, {"U1", "U2"})
        self.assertNotIn("unknown-family", codes(res))

    def test_unassigned_totals_equal_enumerated_rows(self):
        reg = base("partial")
        reg["records"] += [self.ua("U%d" % i, "unit-%d" % i) for i in range(7)]
        reg["coverage"]["declared_counts"] = {"unassigned": 0, "records": 3}
        res = check(reg)
        c = res["counts"]
        self.assertEqual(c["unassigned"], 7)
        self.assertEqual(c["records"], 10)
        self.assertEqual(c["by_role"]["UNKNOWN"], 7)
        self.assertEqual(c["by_label"]["unclassified"], 7)
        self.assertEqual(c["by_installed_state"]["UNKNOWN"], 7)
        self.assertEqual(c["families"], 1)
        self.assertIn("declared-count-ignored", codes(res))

    def test_complete_with_any_unassigned_refused_names_it(self):
        reg = base()
        reg["records"].append(self.ua("U1", "unit-a"))
        res = check(reg)
        self.assertFalse(res["ok"])
        errs = [f for f in res["findings"] if f["severity"] == "error" and f["code"] == "unassigned"]
        self.assertEqual([f["record"] for f in errs], ["U1"])

    def test_lowercase_marker_rejected_by_schema(self):
        reg = base("partial")
        r = self.ua("U1", "unit-a")
        r["family"] = "unassigned"
        reg["records"].append(r)
        self.assertIn("schema", codes(check(reg)))

    def test_cli_refusal_names_record_and_reason(self):
        reg = base()
        reg["records"].append(self.ua("U1", "unit-a"))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.json"
            p.write_text(json.dumps(reg))
            out = subprocess.run([sys.executable, "-I", str(SK / "scripts" / "register_validate.py"), str(p)],
                                 capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        last = [l for l in out.stdout.splitlines() if l.startswith("REFUSED")][-1]
        self.assertIn("U1:unassigned", last)


class MissingEvidence(unittest.TestCase):
    def test_empty_evidence_is_missing_warn_then_refused_complete(self):
        reg = base("partial")
        reg["records"][0]["evidence"] = []
        res = check(reg)
        self.assertTrue(res["ok"])
        self.assertIn("missing-evidence", codes(res))
        reg["coverage"]["declared"] = "all-interfaces-complete"
        res = check(reg)
        self.assertFalse(res["ok"])
        self.assertIn("R1", json.dumps([f for f in res["findings"] if f["code"] == "missing-evidence"]))


if __name__ == "__main__":
    unittest.main()
