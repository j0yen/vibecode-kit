"""schema_compat.py: keyword and enum changes classified by consumer direction and closed-enum handling.

direction producer-first: new schema is on producers, old consumers still run.
direction consumer-first: new schema is on consumers, old producers still run.
direction both (default): must be safe in either order. consumer closed (default): rejects values
outside its schema; open: tolerates them."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_register import SK, sc  # noqa: F401  (test_register puts scripts/ on sys.path)

OLD = {"type": "object", "required": ["a"],
       "properties": {"a": {"type": "string", "enum": ["x", "y"]}, "b": {"type": "integer"},
                      "c": {"type": "string", "pattern": "^a+$", "minLength": 2}}}


def mod(f):
    n = copy.deepcopy(OLD)
    f(n)
    return n


def cmp(new, direction="both", consumer="closed"):
    return sc.compare(OLD, new, direction=direction, consumer=consumer)


ADD = mod(lambda n: n["properties"]["a"]["enum"].append("z"))
RM = mod(lambda n: n["properties"]["a"].__setitem__("enum", ["x"]))


class EnumDirection(unittest.TestCase):
    def test_added_value_reaches_closed_old_consumer_incompatible(self):
        res = cmp(ADD, "producer-first", "closed")
        self.assertFalse(res["compatible"])
        txt = json.dumps(res["breaking"])
        self.assertIn("'z'", txt)
        self.assertIn("closed", txt)

    def test_added_value_open_consumer_compatible(self):
        res = cmp(ADD, "producer-first", "open")
        self.assertTrue(res["compatible"], res)
        self.assertTrue(res["additive"])

    def test_added_value_only_new_consumer_accepts_compatible(self):
        res = cmp(ADD, "consumer-first", "closed")
        self.assertTrue(res["compatible"], res)

    def test_added_value_default_is_conservative_not_blanket_compatible(self):
        self.assertFalse(sc.compare(OLD, ADD)["compatible"])

    def test_removed_value_by_direction(self):
        self.assertFalse(cmp(RM, "consumer-first", "closed")["compatible"])
        self.assertTrue(cmp(RM, "consumer-first", "open")["compatible"])
        self.assertTrue(cmp(RM, "producer-first", "closed")["compatible"])
        self.assertFalse(sc.compare(OLD, RM)["compatible"])

    def test_every_change_is_classified_with_direction_and_handling(self):
        res = cmp(ADD, "producer-first", "closed")
        c = res["classified"][0]
        self.assertEqual((c["direction"], c["handling"], c["verdict"]), ("producer-first", "closed", "incompatible"))
        self.assertIn("enum", c["change"])


class KeywordDirection(unittest.TestCase):
    def test_required_added(self):
        new = mod(lambda n: n["required"].append("b"))
        self.assertFalse(cmp(new, "consumer-first")["compatible"])
        self.assertTrue(cmp(new, "producer-first")["compatible"])

    def test_required_removed(self):
        new = mod(lambda n: n.__setitem__("required", []))
        self.assertFalse(cmp(new, "producer-first")["compatible"])
        self.assertTrue(cmp(new, "consumer-first")["compatible"])

    def test_additional_properties_tightened(self):
        new = mod(lambda n: n.__setitem__("additionalProperties", False))
        self.assertFalse(cmp(new, "consumer-first")["compatible"])
        self.assertTrue(cmp(new, "producer-first")["compatible"])

    def test_additional_properties_loosened_hits_closed_old_consumer(self):
        old = dict(OLD, additionalProperties=False)
        res = sc.compare(old, OLD, direction="producer-first", consumer="closed")
        self.assertFalse(res["compatible"])
        self.assertTrue(sc.compare(old, OLD, direction="consumer-first")["compatible"])

    def test_optional_property_added_vs_closed_old_consumer(self):
        old = dict(OLD, additionalProperties=False)
        new = copy.deepcopy(old)
        new["properties"]["d"] = {"type": "string"}
        self.assertFalse(sc.compare(old, new, direction="producer-first")["compatible"])
        self.assertTrue(sc.compare(old, new, direction="consumer-first")["compatible"])
        self.assertTrue(cmp(mod(lambda n: n["properties"].__setitem__("d", {"type": "string"})))["compatible"])

    def test_property_removed(self):
        new = mod(lambda n: n["properties"].pop("b"))
        self.assertFalse(cmp(new, "producer-first")["compatible"])
        self.assertTrue(cmp(new, "consumer-first")["compatible"])

    def test_type_widened_and_narrowed(self):
        wide = mod(lambda n: n["properties"]["b"].__setitem__("type", ["integer", "string"]))
        self.assertFalse(cmp(wide, "producer-first")["compatible"])
        self.assertTrue(cmp(wide, "consumer-first")["compatible"])
        self.assertTrue(cmp(wide, "producer-first", "open")["compatible"])
        narrow = sc.compare(wide, OLD, direction="producer-first")
        self.assertTrue(narrow["compatible"])
        self.assertFalse(sc.compare(wide, OLD, direction="consumer-first")["compatible"])

    def test_incomparable_type_change_incompatible_both_ways(self):
        new = mod(lambda n: n["properties"]["b"].__setitem__("type", "string"))
        for d in ("producer-first", "consumer-first", "both"):
            self.assertFalse(cmp(new, d, "open")["compatible"], d)

    def test_pattern_change_is_undetermined_not_compatible(self):
        new = mod(lambda n: n["properties"]["c"].__setitem__("pattern", "^b+$"))
        res = cmp(new, "producer-first")
        self.assertFalse(res["compatible"])
        self.assertTrue(res["undetermined"])
        self.assertIn("pattern", json.dumps(res["undetermined"]))

    def test_pattern_added_is_tightening_removed_is_loosening(self):
        added = mod(lambda n: n["properties"]["b"].__setitem__("pattern", "^[0-9]+$"))
        self.assertTrue(cmp(added, "producer-first")["compatible"])
        self.assertFalse(cmp(added, "consumer-first")["compatible"])
        removed = mod(lambda n: n["properties"]["c"].pop("pattern"))
        self.assertFalse(cmp(removed, "producer-first")["compatible"])
        self.assertTrue(cmp(removed, "consumer-first")["compatible"])

    def test_min_length_numeric_direction(self):
        up = mod(lambda n: n["properties"]["c"].__setitem__("minLength", 5))
        self.assertTrue(cmp(up, "producer-first")["compatible"])
        self.assertFalse(cmp(up, "consumer-first")["compatible"])
        down = mod(lambda n: n["properties"]["c"].__setitem__("minLength", 1))
        self.assertFalse(cmp(down, "producer-first")["compatible"])

    def test_unknown_keyword_still_breaking(self):
        new = mod(lambda n: n["properties"]["a"].__setitem__("x-novel", 1))
        self.assertFalse(cmp(new, "consumer-first", "open")["compatible"])


class Cli(unittest.TestCase):
    def run_cli(self, new, *flags):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.json", Path(d) / "b.json"
            a.write_text(json.dumps(OLD))
            b.write_text(json.dumps(new))
            return subprocess.run([sys.executable, "-I", str(SK / "scripts" / "schema_compat.py"), str(a), str(b), *flags],
                                  capture_output=True, text=True)

    def test_cli_direction_flags(self):
        self.assertEqual(self.run_cli(ADD, "--direction", "producer-first", "--consumer", "closed").returncode, 1)
        self.assertEqual(self.run_cli(ADD, "--direction", "producer-first", "--consumer", "open").returncode, 0)
        self.assertEqual(self.run_cli(ADD, "--direction", "consumer-first").returncode, 0)
        self.assertEqual(self.run_cli(ADD).returncode, 1)

    def test_cli_bad_flag_value_is_usage_error(self):
        self.assertEqual(self.run_cli(ADD, "--direction", "sideways").returncode, 2)


class DogfoodRegisterSchema(unittest.TestCase):
    def test_continuation_schema_vs_5ce7922c_by_direction(self):
        old = json.loads((SK / "tests" / "fixtures" / "register.schema.5ce7922c.json").read_text())
        new = json.loads((SK / "schema" / "register.schema.json").read_text())
        pf = sc.compare(old, new, direction="producer-first", consumer="closed")
        self.assertFalse(pf["compatible"])  # new registers (no source_identity, UNASSIGNED) reach old validators
        self.assertIn("source_identity", json.dumps(pf["breaking"]))
        cf = sc.compare(old, new, direction="consumer-first", consumer="closed")
        self.assertIn("family", json.dumps(cf["undetermined"]))  # family pattern widened: needs a human


if __name__ == "__main__":
    unittest.main()
