"""Repairs for the second independent exact-head review of 0eb2848f (DEFECTS 1-10).
Fixtures are synthetic and source-only; they exercise the rules, not production behavior. Credential-shaped
canaries are built at run time from fragments and are never printed: a failure reports a fixed message.
No test depends on the real clock or the host time zone: the reference clock is injected."""
import copy
import inspect
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from test_register import SK, base, check as _check0, rec
import register_validate as rv

sys.path.insert(0, str(SK / "scripts"))
import extract_register as xr  # noqa: E402
import lost_message_check as lm  # noqa: E402
import schema_compat as sc  # noqa: E402

H40, H64 = "a" * 40, "b" * 64
NOW = datetime(2026, 11, 13, 12, 0, 0, tzinfo=timezone.utc)
GH = "ghp" + "_" + "Q" * 36          # fake canary shapes, assembled so no literal is stored
AK = "AK" + "IA" + "Z" * 16
JW = "ey" + "J" + "Z" * 20


def run(script, *args, env=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run([sys.executable, "-I", str(SK / "scripts" / script), *map(str, args)],
                       capture_output=True, text=True, env=e)
    return p.returncode, p.stdout + p.stderr


def wj(d, name, obj):
    p = Path(d) / name
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj), encoding="utf-8")
    return p


def check(reg, now=NOW):
    kw = {"now": now} if "now" in inspect.signature(rv.validate).parameters else {}
    return rv.validate(reg, rv.load_schema(), **kw)


def errs(res):
    return {f["code"] for f in res["findings"] if f["severity"] == "error"}


def mut(fn):
    reg = base()
    fn(reg["records"][0])
    return reg


def leaks(text):
    return any(c in text for c in (GH, AK, JW, GH[:12], AK[:8]))


def row(**k):
    d = {"family": "IF001", "role": "producer", "host": "h", "component": "c", "interface_kind": "http",
         "source_repo": "r1", "source_identity": "commit " + H40, "installed_state": "source-only",
         "evidence": "side=producer"}
    d.update(k)
    return d


def sch(**p):
    d = {"type": "object", "properties": {}}
    d["properties"].update(p)
    return d


class TestD01TypeRefAdditional(unittest.TestCase):
    def cmp(self, o, n, d, c="closed"):
        return sc.compare(o, n, d, c)

    def test_type_removed_is_loosening(self):
        o, n = sch(a={"type": "string"}), sch(a={})
        self.assertFalse(self.cmp(o, n, "producer-first")["compatible"])
        self.assertTrue(self.cmp(o, n, "consumer-first")["compatible"])
        self.assertTrue(self.cmp(o, n, "producer-first", "open")["compatible"])

    def test_type_added_is_tightening(self):
        o, n = sch(a={}), sch(a={"type": "string"})
        self.assertFalse(self.cmp(o, n, "consumer-first")["compatible"])
        self.assertTrue(self.cmp(o, n, "producer-first")["compatible"])

    def test_top_level_type_removed_or_added(self):
        self.assertFalse(sc.compare({"type": "string"}, {}, "both")["compatible"])
        self.assertFalse(sc.compare({}, {"type": "string"}, "both")["compatible"])

    def test_both_directions_never_compatible_for_type_change_without_finding(self):
        for o, n in (({"type": "string"}, {}), ({}, {"type": "string"})):
            r = sc.compare(o, n, "both")
            self.assertTrue(r["breaking"] or r["undetermined"])

    def schema_with_refs(self, target):
        return {"definitions": {"x": {"type": "string"}, "y": {"type": ["string", "null"]}},
                "type": "object", "properties": {"a": {"$ref": "#/definitions/" + target}}}

    def test_ref_retarget_to_looser_definition(self):
        o, n = self.schema_with_refs("x"), self.schema_with_refs("y")
        self.assertFalse(self.cmp(o, n, "producer-first")["compatible"])
        self.assertTrue(self.cmp(o, n, "consumer-first")["compatible"])

    def test_ref_retarget_to_narrower_definition(self):
        o, n = self.schema_with_refs("y"), self.schema_with_refs("x")
        self.assertFalse(self.cmp(o, n, "consumer-first")["compatible"])
        self.assertTrue(self.cmp(o, n, "producer-first")["compatible"])

    def test_unresolvable_ref_retarget_is_undetermined_never_compatible(self):
        o = {"type": "object", "properties": {"a": {"$ref": "#/definitions/x"}}, "definitions": {"x": {}}}
        n = {"type": "object", "properties": {"a": {"$ref": "http://elsewhere/s.json"}}, "definitions": {"x": {}}}
        r = self.cmp(o, n, "both")
        self.assertFalse(r["compatible"])
        self.assertTrue(r["undetermined"] or r["breaking"])

    def test_ref_to_inline_swap_is_compared(self):
        o = {"definitions": {"x": {"type": "string"}}, "properties": {"a": {"$ref": "#/definitions/x"}}}
        n = {"definitions": {"x": {"type": "string"}}, "properties": {"a": {}}}
        self.assertFalse(self.cmp(o, n, "producer-first")["compatible"])

    def test_equal_ref_still_compatible(self):
        o = self.schema_with_refs("x")
        self.assertTrue(self.cmp(o, copy.deepcopy(o), "both")["compatible"])

    def test_retarget_to_identical_content_is_compatible(self):
        o = {"definitions": {"x": {"type": "string"}, "y": {"type": "string"}}, "properties": {"a": {"$ref": "#/definitions/x"}}}
        n = {"definitions": {"x": {"type": "string"}, "y": {"type": "string"}}, "properties": {"a": {"$ref": "#/definitions/y"}}}
        self.assertTrue(self.cmp(o, n, "both")["compatible"])

    def test_additional_properties_schema_changed(self):
        o = {"type": "object", "additionalProperties": {"type": "string"}}
        n = {"type": "object", "additionalProperties": {"type": "integer"}}
        r = self.cmp(o, n, "both")
        self.assertFalse(r["compatible"])
        self.assertTrue(r["breaking"] or r["undetermined"])

    def test_additional_properties_schema_removed_is_loosening(self):
        o = {"type": "object", "additionalProperties": {"type": "string"}}
        n = {"type": "object"}
        self.assertFalse(self.cmp(o, n, "producer-first")["compatible"])
        self.assertTrue(self.cmp(o, n, "consumer-first")["compatible"])

    def test_additional_properties_schema_added_is_tightening(self):
        o = {"type": "object"}
        n = {"type": "object", "additionalProperties": {"type": "string"}}
        self.assertFalse(self.cmp(o, n, "consumer-first")["compatible"])
        self.assertTrue(self.cmp(o, n, "producer-first")["compatible"])

    def test_cli_rc1_with_finding_for_type_removed(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("schema_compat.py", wj(d, "o.json", {"type": "string"}), wj(d, "n.json", {}))
        self.assertEqual(rc, 1)
        self.assertIn("type", out)


class TestD02UnknownEvidence(unittest.TestCase):
    def ev(self, ref):
        return mut(lambda r: r.update(evidence=[{"ref": ref, "observed_at": "2026-11-12T11:00:00Z"}]))

    def test_unknown_equivalent_evidence_ref_refused_naming_record(self):
        for v in ("UNKNOWN", "unknown", "?", "tbd", "-", "n/a", "UNKNOWN​"):
            res = check(self.ev(v))
            self.assertFalse(res["ok"], "placeholder evidence ref accepted on complete")
            self.assertIn("missing-evidence", errs(res))
            self.assertIn("R1", [f["record"] for f in res["findings"] if f["code"] == "missing-evidence"])

    def test_unknown_evidence_ref_under_partial_is_warning(self):
        reg = self.ev("UNKNOWN")
        reg["coverage"]["declared"] = "partial"
        res = check(reg)
        self.assertTrue(res["ok"])

    def adopt(self, ref):
        return mut(lambda r: r.update(installed_state="loaded", adoption_evidence=[{"ref": ref, "observed_at": "2026-11-12T11:00:00Z"}]))

    def test_unknown_adoption_ref_refused(self):
        for v in ("UNKNOWN", "unknown", "?", "tbd", "UNK"):
            res = check(self.adopt(v))
            self.assertFalse(res["ok"], "placeholder adoption ref accepted")
            self.assertIn("unevidenced-state", errs(res))

    def test_unit_listing_is_not_process_adoption(self):
        for v in ("systemctl list-units ctl.service loaded active running",
                  "unit ctl.service is-enabled enabled", "installed in /etc/systemd/system"):
            res = check(self.adopt(v))
            self.assertFalse(res["ok"], "a unit listing was accepted as process adoption")
            self.assertIn("unevidenced-state", errs(res))

    def test_process_observation_is_adoption(self):
        for v in ("pid 4242 exe link /proc/4242/exe sha256 matches", "pid-1 exe link",
                  "ps -o pid,cmd shows process ctl.sh", "/proc/77/cmdline names ctl-event-wait.sh"):
            self.assertTrue(check(self.adopt(v))["ok"], "process adoption refused")

    def test_adoption_finding_does_not_echo_ref(self):
        res = check(self.adopt("systemctl list-units " + GH))
        self.assertFalse(leaks(json.dumps(res)), "adoption ref echoed")


class TestD10SharedNormalizer(unittest.TestCase):
    VARIANTS = ["UNK", "?", "tbd", "TBD", "-", "N/A", "none", "UNKNOWN.", "UNKNOWN​", " unknown ",
                "​UnKnOwN‍", "unknown ", "\xa0unknown\xa0", "Unknown!", "n/a;"]

    def test_normalizer_is_one_function(self):
        import ir_norm
        for v in self.VARIANTS:
            self.assertTrue(ir_norm.is_unknown(v), "placeholder not unknown")
        for v in ("svc-a", "none-of-the-above-svc", "x", "0"):
            self.assertFalse(ir_norm.is_unknown(v), "real value treated as unknown")
        self.assertTrue(ir_norm.is_unknown(None) and ir_norm.is_unknown(5) and ir_norm.is_unknown(["a"]))

    def test_validator_and_extractor_import_same_normalizer(self):
        self.assertIs(rv.is_unknown, xr.is_unknown)

    def test_component_version_repo_host_role_state_all_use_it(self):
        fields = {
            "component": lambda r, v: r.update(component=v),
            "version": lambda r, v: r["source_identity"].update(version=v),
            "repo": lambda r, v: r["source_identity"].update(repo=v),
            "host": lambda r, v: r.update(host=v),
            "role": lambda r, v: r.update(role=v),
            "installed_state": lambda r, v: r.update(installed_state=v),
            "label": lambda r, v: r.update(label=v),
        }
        for name, setter in fields.items():
            for v in self.VARIANTS:
                res = check(mut(lambda r, s=setter, v=v: s(r, v)))
                self.assertFalse(res["ok"], f"{name} placeholder accepted on complete")

    def test_extractor_does_not_fuse_or_key_on_placeholder_repo(self):
        out = xr.convert([row(component="ctx", source_repo="UNK", path_or_command="UNK/a"),
                          row(component="ctx", source_repo="tbd", path_or_command="tbd/a",
                              source_identity="commit " + "c" * 40)])["register"]["records"]
        self.assertEqual(len(out), 2)

    def test_extractor_component_placeholder_becomes_unknown(self):
        r = xr.convert([row(component="tbd")])["register"]["records"][0]
        self.assertEqual(r["component"], "UNKNOWN")
        res = check({"schema_version": 1, "coverage": {"declared": "all-interfaces-complete"},
                     "families": [{"id": "IF001"}], "records": [r]})
        self.assertFalse(res["ok"])


class TestD03ExtractorShape(unittest.TestCase):
    def test_wrong_typed_fields_do_not_raise(self):
        for fld in ("interface_kind", "role", "installed_state", "host", "component", "path_or_command",
                    "source_repo", "family", "evidence", "observed_at", "captured_at", "source_identity"):
            for bad in (["x"], {}, {"a": 1}, 5, True):
                xr.convert([row(**{fld: bad})])

    def test_cli_wrong_shape_row_rc_not_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            p = wj(d, "in.jsonl", json.dumps(row(interface_kind=["http"])) + "\n")
            rc, out = run("extract_register.py", p, Path(d) / "o")
        self.assertIn(rc, (0, 3))
        self.assertNotIn("Traceback", out)

    def test_deep_row_is_rejected_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            deep = "[" * 200000 + "]" * 200000
            p = wj(d, "in.jsonl", deep + "\n" + json.dumps(row()) + "\n")
            rc, out = run("extract_register.py", p, Path(d) / "o")
            self.assertEqual(rc, 3)
            self.assertNotIn("Traceback", out)
            rej = json.loads((Path(d) / "o" / "rejected.json").read_text())
            self.assertEqual([r["line"] for r in rej], [1])
            reg = json.loads((Path(d) / "o" / "register-partial.json").read_text())
            self.assertEqual(len(reg["records"]), 1)

    def test_deep_row_inside_object_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            line = '{"family":"IF001","evidence":' + "[" * 200000 + "]" * 200000 + "}"
            rc, out = run("extract_register.py", wj(d, "in.jsonl", line + "\n"), Path(d) / "o")
        self.assertEqual(rc, 3)
        self.assertNotIn("Traceback", out)

    def test_validator_wrong_shape_register_rc2_no_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            for reg in ({"records": [{"evidence": 5, "sources": {"a": 1}, "role": ["x"], "family": []}]},
                        {"coverage": [], "records": [[1]], "families": {"a": 1}}):
                rc, out = run("register_validate.py", wj(d, "r.json", reg))
                self.assertIn(rc, (1, 2))
                self.assertNotIn("Traceback", out)
            deep = "[" * 100000 + "]" * 100000
            rc, out = run("register_validate.py", wj(d, "r.json", '{"records": ' + deep + "}"))
            self.assertEqual(rc, 2)
            self.assertNotIn("Traceback", out)


class TestD04CompatShape(unittest.TestCase):
    def cli(self, o, n):
        with tempfile.TemporaryDirectory() as d:
            return run("schema_compat.py", wj(d, "o.json", o), wj(d, "n.json", n))

    def test_list_shaped_sections_rc2(self):
        good = {"type": "object", "properties": {"a": {"type": "string"}}}
        for sec in ("properties", "definitions"):
            for bad in ([1], [], "x", 5, [{"a": 1}]):
                rc, out = self.cli(good, {"type": "object", sec: bad})
                self.assertEqual(rc, 2, f"{sec} {type(bad).__name__}")
                self.assertNotIn("Traceback", out)
                self.assertIn("UNKNOWN", out)
                rc, out = self.cli({"type": "object", sec: bad}, good)
                self.assertEqual(rc, 2)

    def test_other_wrong_shapes_rc2(self):
        good = {"type": "object"}
        for k, bad in (("required", 5), ("required", {"a": 1}), ("enum", 5), ("enum", "ab"),
                       ("items", [1]), ("additionalProperties", [1]), ("minLength", "x"), ("type", {"a": 1}),
                       ("properties", {"a": 5}), ("properties", {"a": [1]})):
            rc, out = self.cli(good, dict(good, **{k: bad}))
            self.assertIn(rc, (1, 2), k)
            self.assertNotIn("Traceback", out, k)
            self.assertNotEqual(rc, 0, k)

    def test_boolean_subschema_change_not_silently_compatible(self):
        rc, out = self.cli({"properties": {"a": True}}, {"properties": {"a": False}})
        self.assertNotEqual(rc, 0)
        self.assertNotIn("Traceback", out)


class TestD05HexTypes(unittest.TestCase):
    def f(self, **over):
        f = json.loads((SK / "tests" / "fixtures" / "review" / "lost_consistent.json").read_text())
        for path, v in over.items():
            a, b = path.split("__")
            f["trace"][a][b] = v
        return f

    def test_trailing_newline_sha_and_commit_refused(self):
        self.assertFalse(lm.classify(self.f(waiter__sha256="a" * 64 + "\n"))["ok"])
        f = self.f()
        del f["trace"]["producer"]["sha256"]
        f["trace"]["producer"]["commit"] = H40 + "\n"
        res = lm.classify(f)
        self.assertFalse(res["ok"])
        self.assertIn("producer", res["missing_links"])

    def test_63_65_space_variants_still_refused_and_exact_accepted(self):
        for v in ("a" * 63, "a" * 65, "a" * 64 + " ", " " + "a" * 64):
            self.assertFalse(lm.classify(self.f(waiter__sha256=v))["ok"])
        self.assertTrue(lm.classify(self.f(waiter__sha256="A" * 64))["ok"])
        self.assertTrue(lm.classify(self.f())["ok"])

    def test_cli_refuses_newline_sha(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("lost_message_check.py", wj(d, "f.json", self.f(waiter__sha256="a" * 64 + "\n")))
        self.assertEqual(rc, 1)


class TestD06Timestamps(unittest.TestCase):
    def reg(self, declared="all-interfaces-complete", obs="2026-11-12T11:00:00Z", cap="2026-11-12T10:00:00Z"):
        reg = base(declared)
        reg["records"][0]["evidence"] = [{"ref": "file:x#1", "observed_at": obs}]
        reg["records"][0]["source_identity"]["captured_at"] = cap
        return reg

    def test_offsetless_observed_refused_on_complete_warn_on_partial(self):
        res = check(self.reg(obs="2026-11-12T10:00:00"))
        self.assertFalse(res["ok"])
        self.assertIn("ambiguous-timestamp", errs(res))
        res = check(self.reg("partial", obs="2026-11-12T10:00:00"))
        self.assertTrue(res["ok"])
        self.assertIn("ambiguous-timestamp", {f["code"] for f in res["findings"] if f["severity"] == "warn"})

    def test_offsetless_captured_refused_on_complete(self):
        res = check(self.reg(cap="2026-11-12T09:00:00"))
        self.assertIn("ambiguous-timestamp", errs(res))

    def test_verdict_independent_of_host_time_zone(self):
        out = {}
        with tempfile.TemporaryDirectory() as d:
            p = wj(d, "r.json", self.reg(obs="2026-11-12T10:00:00"))
            for tz in ("UTC", "Pacific/Auckland", "America/New_York"):
                out[tz] = run("register_validate.py", p, "--now", "2026-11-13T12:00:00Z", env={"TZ": tz})
        self.assertEqual({v[0] for v in out.values()}, {1})
        self.assertEqual(len({v[1] for v in out.values()}), 1)

    def test_both_offsetless_not_silently_passed(self):
        res = check(self.reg(obs="2026-11-12T10:00:00", cap="2026-11-12T09:00:00"))
        self.assertFalse(res["ok"])

    def test_future_timestamp_flagged_beyond_skew(self):
        res = check(self.reg(obs="2099-01-01T00:00:00Z"))
        self.assertFalse(res["ok"])
        self.assertIn("future-timestamp", errs(res))
        res = check(self.reg("partial", obs="2099-01-01T00:00:00Z"))
        self.assertTrue(res["ok"])
        self.assertIn("future-timestamp", {f["code"] for f in res["findings"] if f["severity"] == "warn"})

    def test_future_captured_flagged(self):
        self.assertIn("future-timestamp", errs(check(self.reg(cap="2099-01-01T00:00:00Z"))))

    def test_within_skew_not_flagged_and_injected_clock_decides(self):
        obs = "2026-11-13T12:03:00Z"           # 3 min after NOW, inside the 5 min skew
        self.assertTrue(check(self.reg(obs=obs))["ok"])
        self.assertIn("future-timestamp", errs(check(self.reg(obs="2026-11-13T12:10:00Z"))))
        later = datetime(2026, 11, 14, tzinfo=timezone.utc)
        self.assertTrue(check(self.reg(obs="2026-11-13T12:10:00Z"), now=later)["ok"])

    def test_cli_now_option_and_bad_now_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            p = wj(d, "r.json", self.reg(obs="2026-11-13T12:10:00Z"))
            self.assertEqual(run("register_validate.py", p, "--now", "2026-11-13T12:00:00Z")[0], 1)
            self.assertEqual(run("register_validate.py", p, "--now", "2026-11-14T00:00:00Z")[0], 0)
            self.assertEqual(run("register_validate.py", p, "--now", "yesterday")[0], 2)

    def test_offset_forms_still_parse(self):
        self.assertTrue(check(self.reg(obs="2026-11-12T12:00:00+01:00"))["ok"])
        self.assertTrue(check(self.reg(obs="2026-11-12T11:00:00.250Z"))["ok"])


class TestD07Fusion(unittest.TestCase):
    def recs(self, rows):
        return xr.convert(rows, heuristic_fusion=True)["register"]["records"]

    def pair(self, p1, p2, r1="r1", r2="r2"):
        return self.recs([row(component="recall", source_repo=r1, path_or_command=p1),
                          row(component="recall", source_repo=r2, path_or_command=p2,
                              source_identity="commit " + "c" * 40)])

    def test_dotdot_path_is_normalized_before_rooted_check(self):
        self.assertEqual(len(self.pair("r1/../r2/a.py", "r2/b.py")), 2)
        self.assertEqual(len(self.pair("r1/a/../../r2/a.py", "r2/b.py")), 2)

    def test_dotdot_that_stays_inside_repo_is_rooted(self):
        self.assertEqual(len(self.pair("r1/x/../a.py", "r2/b.py")), 1)

    def test_repo_with_trailing_slash_and_absolute_paths(self):
        self.assertEqual(len(self.pair("r1//a.py", "r2/b.py", r1="r1/")), 2)
        self.assertEqual(len(self.pair("r1//a.py", "r2/b.py")), 2)
        self.assertEqual(len(self.pair("r1/a.py", "r2/b.py", r1="r1/")), 2)
        self.assertEqual(len(self.pair("/r1/a.py", "/r2/b.py")), 2)
        self.assertEqual(len(self.pair("r1/../a.py", "r2/b.py")), 2)

    def test_same_named_components_in_unrelated_repos_without_shared_evidence_stay_separate(self):
        # no tests/fixtures says these are one component: a shared stated identity is required
        a = row(component="recall", source_repo="r1", path_or_command="r1/a.py", evidence="side=producer unrelated-a")
        b = row(component="recall", source_repo="r2", path_or_command="r2/b.py", evidence="side=producer unrelated-b",
                source_identity="commit " + "c" * 40)
        out = self.recs([a, b])
        self.assertTrue(len(out) == 2 or all("fusion_basis" in r for r in out if "sources" in r),
                        "a fused record must state that its basis is a heuristic")

    def test_skill_md_does_not_call_the_rule_positive_evidence(self):
        txt = (SK / "SKILL.md").read_text().lower()
        src = (SK / "scripts" / "extract_register.py").read_text().lower()
        self.assertTrue("positive evidence" not in txt, "SKILL.md still says positive evidence")
        self.assertTrue("positive evidence" not in src, "extractor still says positive evidence")
        self.assertTrue("heuristic" in txt, "SKILL.md does not call the fusion rule a heuristic")

    def test_fused_record_names_its_basis(self):
        out = self.pair("r1/a.py", "r2/b.py")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].get("fusion_basis"), "same-name-and-repo-rooted-paths-heuristic")


class TestD08Redaction(unittest.TestCase):
    def test_credential_shapes_redacted_in_every_validator_message(self):
        for canary in (GH, AK, JW):
            reg = mut(lambda r: r.update(evidence=[{"ref": "e", "observed_at": "2026-11-12T11:00:00Z", canary: 1}]))
            res = check(reg)
            self.assertFalse(leaks(json.dumps(res)), "credential-shaped property key echoed (api)")
            reg = mut(lambda r: r.update(role=canary))
            res = check(reg)
            self.assertFalse(leaks(json.dumps(res)), "credential-shaped role echoed (api)")
            reg = mut(lambda r: r.update(record_id=canary))
            self.assertFalse(leaks(json.dumps(check(reg))), "credential-shaped record id echoed (api)")
        with tempfile.TemporaryDirectory() as d:
            reg = mut(lambda r: r.update(role=GH, evidence=[{"ref": "e", GH: 1}]))
            rc, out = run("register_validate.py", wj(d, "r.json", reg))
            self.assertFalse(leaks(out), "credential-shaped text echoed (cli)")
            rc, out = run("register_validate.py", wj(d, "d.json", '{"a": 1, "' + AK + '": 1, "' + AK + '": 2}'))
            self.assertEqual(rc, 2)
            self.assertFalse(leaks(out), "duplicate key name echoed (cli)")

    def lost(self, **top):
        f = json.loads((SK / "tests" / "fixtures" / "review" / "lost_consistent.json").read_text())
        f.update(top)
        return f

    def test_lost_message_redacts_id_actor_and_labels(self):
        f = self.lost(id=GH)
        f["trace"]["waiter"]["actor"] = AK
        f["label"] = JW
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("lost_message_check.py", wj(d, "f.json", f))
        self.assertFalse(leaks(out), "lost_message_check echoed credential-shaped text")
        f = self.lost()
        f["trace"]["waiter"]["actor"] = AK
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("lost_message_check.py", wj(d, "f.json", f))
        self.assertEqual(rc, 1)
        self.assertFalse(leaks(out), "inconsistent actor echoed")

    def test_lost_message_duplicate_key_name_not_echoed(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("lost_message_check.py", wj(d, "f.json", '{"a": 1, "' + GH + '": 1, "' + GH + '": 2}'))
        self.assertEqual(rc, 2)
        self.assertFalse(leaks(out), "duplicate key name echoed")

    def test_ordinary_text_not_redacted(self):
        import ir_norm
        for t in ("svc-a", "IF001", "record R1", "pid 4242 exe link", "a" * 64):
            self.assertEqual(ir_norm.redact(t), t)

    def test_extractor_and_compat_do_not_echo_credential_keys(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("extract_register.py", wj(d, "in.jsonl", '{"a": 1, "' + GH + '": 1, "' + GH + '": 2}\n'), Path(d) / "o")
            self.assertFalse(leaks(out + (Path(d) / "o" / "rejected.json").read_text()), "extractor echoed key")
            rc, out = run("schema_compat.py", wj(d, "a.json", '{"' + AK + '": 1, "' + AK + '": 2}'), wj(d, "b.json", {}))
            self.assertFalse(leaks(out), "compat echoed key")


class TestD09LostConsistency(unittest.TestCase):
    def f(self):
        return json.loads((SK / "tests" / "fixtures" / "review" / "lost_consistent.json").read_text())

    def test_actor_cycle_is_flagged_and_refused(self):
        f = self.f()
        f["trace"]["adapters"] = [dict(f["trace"]["adapters"][0], maps_from="bld", maps_to="ops"),
                                  dict(f["trace"]["adapters"][0], ref="a2.py:1", maps_from="ops", maps_to="bld")]
        f["trace"]["waiter"]["actor"] = "bld"
        res = lm.classify(f)
        self.assertFalse(res["ok"])
        self.assertEqual(res["label"], "conditional-risk")
        self.assertTrue([x for x in res["inconsistent_links"] if "cycle" in x])

    def test_identity_map_is_not_a_cycle(self):
        f = self.f()
        f["trace"]["adapters"][0]["maps_to"] = "bld"
        f["trace"]["waiter"]["actor"] = "bld"
        res = lm.classify(f)
        self.assertTrue(res["ok"])
        self.assertEqual(res["inconsistent_links"], [])

    def test_fully_stated_trace_is_marked_proven(self):
        res = lm.classify(self.f())
        self.assertEqual(res["consistency"], "proven")
        self.assertEqual(res["unproven"], [])

    def test_trace_stating_nothing_is_marked_unproven(self):
        f = self.f()
        for lnk in [f["trace"]["producer"], f["trace"]["waiter"], *f["trace"]["adapters"]]:
            for k in ("family", "interface", "message", "actor", "maps_from", "maps_to"):
                lnk.pop(k, None)
        res = lm.classify(f)
        self.assertEqual(res["consistency"], "unproven")
        self.assertTrue(res["unproven"])
        self.assertEqual(res["label"], "observed-defect")      # label rule unchanged; the marker is the signal

    def test_waiter_actor_unstated_marked_unproven(self):
        f = self.f()
        del f["trace"]["waiter"]["actor"]
        res = lm.classify(f)
        self.assertEqual(res["consistency"], "unproven")
        self.assertTrue([u for u in res["unproven"] if "actor" in u])

    def test_cli_prints_unproven_line_and_cycle_rc1(self):
        f = self.f()
        del f["trace"]["waiter"]["actor"]
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("lost_message_check.py", wj(d, "f.json", f))
        self.assertEqual(rc, 0)
        self.assertIn("UNPROVEN", out)

    def test_passthrough_claims_untouched(self):
        res = lm.classify({"id": "F", "claim": "other", "label": "hypothesis"})
        self.assertTrue(res["ok"])


class TestD06F8InstalledOnWord(unittest.TestCase):
    """Prior D6 F8: the validator's OK line states which installed states were taken on the declarer's word."""

    def test_ok_line_names_installed_states_without_path_and_sha(self):
        reg = base()
        reg["records"][0]["source_identity"] = {"repo": "j0yen/x", "version": "1.0.0", "available": True,
                                                "captured_at": "2026-11-12T10:00:00Z"}
        res = check(reg)
        self.assertTrue(res["ok"])
        self.assertEqual(res["installed_on_word"], ["R1"])
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("register_validate.py", wj(d, "r.json", reg), "--now", "2026-11-13T12:00:00Z")
        self.assertEqual(rc, 0)
        self.assertIn("on the declarer's word", out.splitlines()[-1])
        self.assertIn("R1", out.splitlines()[-1])

    def test_short_sha_is_on_word(self):
        reg = base()
        reg["records"][0]["source_identity"]["sha256"] = "abc"
        self.assertEqual(check(reg)["installed_on_word"], ["R1"])

    def test_path_and_full_sha_is_not_on_word(self):
        res = check(base())
        self.assertEqual(res["installed_on_word"], [])
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("register_validate.py", wj(d, "r.json", base()), "--now", "2026-11-13T12:00:00Z")
        self.assertNotIn("declarer's word", out)

    def test_partial_register_unchanged(self):
        reg = base("partial")
        reg["records"][0]["source_identity"].pop("sha256")
        self.assertTrue(check(reg)["ok"])


if __name__ == "__main__":
    unittest.main()
