"""register_validate.py and schema_compat.py controls."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SK = HERE.parent
sys.path.insert(0, str(SK / "scripts"))
import register_validate as rv  # noqa: E402
import schema_compat as sc  # noqa: E402


def rec(rid, family="IF001", role="producer", comp="svc-a", **kw):
    r = {"record_id": rid, "family": family, "role": role, "host": "ryzen7",
         "component": comp, "interface_kind": "event",
         "source_identity": {"repo": "j0yen/x", "commit": "a" * 40, "path": "bin/x",
                             "sha256": "b" * 64, "version": "1.0.0",
                             "captured_at": "2026-11-12T10:00:00Z", "available": True},
         "installed_state": "installed", "label": "positive-control",
         "evidence": [{"ref": "file:x#1", "observed_at": "2026-11-12T11:00:00Z"}],
         "owner_row": None}
    r.update(kw)
    return r


def base(declared="all-interfaces-complete"):
    return {"schema_version": 1,
            "coverage": {"declared": declared, "declared_counts": {"records": 999}},
            "families": [{"id": "IF001", "registered_callers": ["cli-a"]}],
            "records": [rec("R1", role="producer"),
                        rec("R2", role="consumer", comp="svc-b"),
                        rec("R3", role="caller", comp="cli-a")]}


def check(reg):
    return rv.validate(reg, rv.load_schema())


def codes(res):
    return {f["code"] for f in res["findings"]}


class Complete(unittest.TestCase):
    def test_clean_complete_accepted(self):
        res = check(base())
        self.assertTrue(res["ok"], res["findings"])

    def test_counts_derived_not_declared(self):
        res = check(base())
        self.assertEqual(res["counts"]["records"], 3)
        self.assertEqual(res["counts"]["by_role"]["caller"], 1)

    def test_unknown_installed_version_refused(self):
        reg = base()
        reg["records"][1]["source_identity"]["version"] = "UNKNOWN"
        res = check(reg)
        self.assertFalse(res["ok"])
        self.assertIn("unknown-field", codes(res))
        self.assertIn("R2", json.dumps(res["findings"]))

    def test_unknown_installed_state_refused(self):
        reg = base()
        reg["records"][0]["installed_state"] = "UNKNOWN"
        self.assertFalse(check(reg)["ok"])

    def test_unclassified_caller_refused(self):
        reg = base()
        reg["records"][2]["label"] = "unclassified"
        res = check(reg)
        self.assertFalse(res["ok"])
        self.assertIn("unclassified", codes(res))
        self.assertIn("R3", json.dumps(res["findings"]))

    def test_missing_endpoint_refused(self):
        reg = base()
        reg["records"] = [r for r in reg["records"] if r["role"] != "consumer"]
        res = check(reg)
        self.assertFalse(res["ok"])
        self.assertIn("missing-endpoint", codes(res))

    def test_unknown_component_is_missing_endpoint(self):
        reg = base()
        reg["records"][1]["component"] = "UNKNOWN"
        self.assertFalse(check(reg)["ok"])

    def test_same_register_declared_partial_accepted(self):
        for mut in ("version", "label", "endpoint"):
            reg = base("partial")
            if mut == "version":
                reg["records"][1]["source_identity"]["version"] = "UNKNOWN"
            elif mut == "label":
                reg["records"][2]["label"] = "unclassified"
            else:
                reg["records"] = [r for r in reg["records"] if r["role"] != "consumer"]
            res = check(reg)
            self.assertTrue(res["ok"], (mut, res["findings"]))
            self.assertTrue(res["findings"], "gaps still reported")

    def test_cli_refuses_with_nonzero_and_names_record(self):
        reg = base()
        reg["records"][2]["label"] = "unclassified"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "reg.json"
            p.write_text(json.dumps(reg))
            r = subprocess.run([sys.executable, "-I", str(SK / "scripts" / "register_validate.py"), str(p)],
                               capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("R3", r.stdout + r.stderr)

    def test_cli_accepts_partial_exit_zero(self):
        reg = base("partial")
        reg["records"][2]["label"] = "unclassified"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "reg.json"
            p.write_text(json.dumps(reg))
            r = subprocess.run([sys.executable, "-I", str(SK / "scripts" / "register_validate.py"), str(p)],
                               capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class Controls(unittest.TestCase):
    def test_duplicate_caller_record(self):
        reg = base("partial")
        reg["records"].append(rec("R4", role="caller", comp="cli-a"))
        res = check(reg)
        self.assertFalse(res["ok"])
        self.assertIn("duplicate-record", codes(res))

    def test_extra_unregistered_caller(self):
        reg = base("partial")
        reg["records"].append(rec("R4", role="caller", comp="cli-rogue"))
        res = check(reg)
        self.assertFalse(res["ok"])
        self.assertIn("unregistered-caller", codes(res))
        self.assertIn("R4", json.dumps(res["findings"]))

    def test_stale_evidence_blocks_complete_only(self):
        reg = base()
        reg["records"][0]["evidence"][0]["observed_at"] = "2026-11-11T00:00:00Z"
        res = check(reg)
        self.assertFalse(res["ok"])
        self.assertIn("stale-evidence", codes(res))
        reg["coverage"]["declared"] = "partial"
        res = check(reg)
        self.assertTrue(res["ok"])
        self.assertIn("stale-evidence", codes(res))

    def test_unknown_effect_never_replayed(self):
        reg = base("partial")
        reg["records"][0]["effect_state"] = "UNKNOWN"
        reg["records"][0]["replay"] = "retried"
        res = check(reg)
        self.assertFalse(res["ok"])
        self.assertIn("unknown-effect-replayed", codes(res))
        reg["records"][0]["replay"] = "none"
        self.assertTrue(check(reg)["ok"])

    def test_unavailable_source_is_unknown_not_pass(self):
        reg = base("partial")
        reg["records"][0]["source_identity"]["available"] = False
        res = check(reg)
        self.assertFalse(res["ok"])
        self.assertIn("unavailable-source-not-unknown", codes(res))
        reg["records"][0]["installed_state"] = "UNKNOWN"
        reg["records"][0]["label"] = "unclassified"
        self.assertTrue(check(reg)["ok"])
        reg["coverage"]["declared"] = "all-interfaces-complete"
        self.assertFalse(check(reg)["ok"])

    def test_committed_publish_pending_is_positive_control(self):
        reg = base()
        reg["records"][0]["condition"] = "committed-publish-pending"
        reg["records"][0]["label"] = "positive-control"
        self.assertTrue(check(reg)["ok"])
        reg["records"][0]["label"] = "observed-defect"
        res = check(reg)
        self.assertFalse(res["ok"])
        self.assertIn("pending-mislabelled", codes(res))

    def test_enum_violation_rejected(self):
        reg = base("partial")
        reg["records"][0]["interface_kind"] = "carrier-pigeon"
        res = check(reg)
        self.assertFalse(res["ok"])
        self.assertIn("schema", codes(res))

    def test_label_set_is_exactly_five(self):
        schema = rv.load_schema()
        lab = schema["definitions"]["record"]["properties"]["label"]["enum"]
        self.assertEqual(set(lab) - {"unclassified"},
                         {"observed-defect", "conditional-risk", "historical-evidence",
                          "hypothesis", "positive-control"})


class SchemaCompat(unittest.TestCase):
    OLD = {"type": "object", "required": ["a"],
           "properties": {"a": {"type": "string", "enum": ["x", "y"]}, "b": {"type": "integer"}}}

    def test_additive_optional_and_enum_value_compatible(self):
        new = copy.deepcopy(self.OLD)
        new["properties"]["c"] = {"type": "string"}
        new["properties"]["a"]["enum"].append("z")
        res = sc.compare(self.OLD, new)
        self.assertTrue(res["compatible"], res)
        self.assertTrue(res["additive"])

    def test_enum_value_removed_incompatible(self):
        new = copy.deepcopy(self.OLD)
        new["properties"]["a"]["enum"] = ["x"]
        res = sc.compare(self.OLD, new)
        self.assertFalse(res["compatible"])

    def test_new_required_incompatible(self):
        new = copy.deepcopy(self.OLD)
        new["required"].append("b")
        self.assertFalse(sc.compare(self.OLD, new)["compatible"])

    def test_type_change_incompatible(self):
        new = copy.deepcopy(self.OLD)
        new["properties"]["b"]["type"] = "string"
        self.assertFalse(sc.compare(self.OLD, new)["compatible"])

    def test_unknown_keyword_incompatible(self):
        new = copy.deepcopy(self.OLD)
        new["properties"]["a"]["x-novel-keyword"] = 1
        res = sc.compare(self.OLD, new)
        self.assertFalse(res["compatible"])
        self.assertIn("keyword", json.dumps(res["breaking"]))

    def test_property_removed_incompatible(self):
        new = copy.deepcopy(self.OLD)
        del new["properties"]["b"]
        self.assertFalse(sc.compare(self.OLD, new)["compatible"])


if __name__ == "__main__":
    unittest.main()
