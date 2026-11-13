"""Repairs for the independent exact-head review of 0b257093 (defects D1-D12).
Fixtures are synthetic and source-only; they exercise the rules, not production behavior.
A test never prints a credential-shaped canary: failures report a fixed message."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_register import SK, base, check, rec

sys.path.insert(0, str(SK / "scripts"))
import extract_register as xr  # noqa: E402
import lost_message_check as lm  # noqa: E402
import schema_compat as sc  # noqa: E402

FX = SK / "tests" / "fixtures" / "review"
H64, H40 = "b" * 64, "a" * 40
CANARY = "password=CANARY123"


def run(script, *args):
    p = subprocess.run([sys.executable, "-I", str(SK / "scripts" / script), *map(str, args)],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def wj(d, name, obj):
    p = Path(d) / name
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj), encoding="utf-8")
    return p


def codes(res, sev="error"):
    return {f["code"] for f in res["findings"] if f["severity"] == sev}


def row(**k):
    d = {"family": "IF001", "role": "producer", "host": "h", "component": "c", "interface_kind": "http",
         "source_repo": "r1", "source_identity": "commit " + H40, "installed_state": "source-only",
         "evidence": "side=producer"}
    d.update(k)
    return d


def lost(**over):
    f = json.loads((FX / "lost_consistent.json").read_text())
    for k, v in over.items():
        f[k] = v
    return f


class TestD01ZeroRecords(unittest.TestCase):
    def reg(self, declared):
        return {"schema_version": 1, "coverage": {"declared": declared}, "families": [], "records": []}

    def test_complete_with_zero_records_refused(self):
        res = check(self.reg("all-interfaces-complete"))
        self.assertFalse(res["ok"])
        self.assertIn("no-records", codes(res))

    def test_complete_cli_rc1(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("register_validate.py", wj(d, "r.json", self.reg("all-interfaces-complete")))
        self.assertEqual(rc, 1)
        self.assertIn("REFUSED", out)

    def test_partial_with_zero_records_still_ok(self):
        self.assertTrue(check(self.reg("partial"))["ok"])

    def test_empty_extraction_declared_complete_refused(self):
        with tempfile.TemporaryDirectory() as d:
            src = wj(d, "e.jsonl", "")
            rc, _ = run("extract_register.py", src, Path(d) / "o")
            self.assertEqual(rc, 0)
            rc, out = run("register_validate.py", Path(d) / "o" / "register-declared-complete.json")
        self.assertEqual(rc, 1)


class TestD02UnknownEquivalents(unittest.TestCase):
    def go(self, mutate):
        reg = base()
        mutate(reg)
        return check(reg)

    def test_component_unknown_variants_refused(self):
        for v in ("unknown", " Unknown ", "UnKnown\t", "   "):
            res = self.go(lambda g, v=v: g["records"][0].update(component=v))
            self.assertFalse(res["ok"], repr(v))
            self.assertIn("missing-endpoint", codes(res), repr(v))

    def test_version_unknown_variants_refused(self):
        for v in ("unknown", " UNKNOWN ", "  ", "\n"):
            res = self.go(lambda g, v=v: g["records"][0]["source_identity"].update(version=v))
            self.assertFalse(res["ok"], repr(v))
            self.assertIn("unknown-field", codes(res), repr(v))

    def test_unknown_component_does_not_satisfy_family_endpoint(self):
        res = self.go(lambda g: g["records"][0].update(component="unknown"))
        msgs = " ".join(f["message"] for f in res["findings"])
        self.assertIn("no producer endpoint", msgs)

    def test_unclassified_variants_refused(self):
        res = self.go(lambda g: g["records"][0].update(label=" Unclassified "))
        self.assertFalse(res["ok"])

    def test_blank_evidence_ref_is_missing_evidence(self):
        res = self.go(lambda g: g["records"][0].update(evidence=[{"ref": "  "}]))
        self.assertIn("missing-evidence", codes(res))

    def test_sources_list_version_unknown_variants(self):
        def m(g):
            r = g["records"][0]
            si = r.pop("source_identity")
            r["sources"] = [dict(si), dict(si, version="unknown")]
        self.assertFalse(self.go(m)["ok"])


class TestD03LostMessageConsistency(unittest.TestCase):
    def test_consistent_alias_chain_is_observed_defect(self):
        res = lm.classify(lost())
        self.assertEqual(res["label"], "observed-defect")
        self.assertTrue(res["ok"])
        self.assertEqual(res["inconsistent_links"], [])

    def test_different_families_conditional_risk_names_link(self):
        f = lost()
        f["trace"]["adapters"][0]["family"] = "IF002"
        f["trace"]["waiter"]["family"] = "IF003"
        res = lm.classify(f)
        self.assertEqual(res["label"], "conditional-risk")
        self.assertFalse(res["ok"])
        self.assertTrue(any(x.startswith("adapters[0]") for x in res["inconsistent_links"]))
        self.assertTrue(any(x.startswith("waiter") for x in res["inconsistent_links"]))

    def test_different_interface_conditional_risk(self):
        f = lost()
        f["trace"]["waiter"]["interface"] = "cli"
        res = lm.classify(f)
        self.assertEqual(res["label"], "conditional-risk")
        self.assertTrue(any(x.startswith("waiter") for x in res["inconsistent_links"]))

    def test_different_message_path_conditional_risk(self):
        f = lost()
        f["trace"]["producer"]["message"] = "m1"
        f["trace"]["waiter"]["message"] = "m2"
        self.assertEqual(lm.classify(f)["label"], "conditional-risk")

    def test_waiter_actor_differs_from_producer_actor(self):
        f = lost()
        f["trace"]["adapters"] = [dict(f["trace"]["adapters"][0])]
        del f["trace"]["adapters"][0]["maps_from"], f["trace"]["adapters"][0]["maps_to"]
        f["trace"]["producer"]["actor"] = "alice"
        f["trace"]["waiter"]["actor"] = "bob"
        res = lm.classify(f)
        self.assertEqual(res["label"], "conditional-risk")
        self.assertIn("waiter: actor 'bob' is not the actor reaching it ('alice')", res["inconsistent_links"])

    def test_adapter_maps_from_other_actor(self):
        f = lost()
        f["trace"]["adapters"][0]["maps_from"] = "someone-else"
        res = lm.classify(f)
        self.assertEqual(res["label"], "conditional-risk")
        self.assertTrue(any(x.startswith("adapters[0]") for x in res["inconsistent_links"]))

    def test_cli_names_inconsistent_link(self):
        f = lost()
        f["trace"]["waiter"]["family"] = "IF009"
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("lost_message_check.py", wj(d, "f.json", f))
        self.assertEqual(rc, 1)
        self.assertIn("waiter", out.split("REFUSED")[-1])


class TestD04NoEvidenceEcho(unittest.TestCase):
    def stale(self, declared):
        reg = base(declared)
        reg["records"][0]["evidence"] = [{"ref": CANARY, "observed_at": "2020-01-01T00:00:00Z"}]
        return reg

    def test_stale_partial_does_not_print_ref(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("register_validate.py", wj(d, "r.json", self.stale("partial")))
        self.assertEqual(rc, 0)
        self.assertTrue("CANARY123" not in out, "evidence ref echoed")
        self.assertIn("stale-evidence", out)
        self.assertIn("evidence[0]", out)

    def test_stale_complete_does_not_print_ref(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("register_validate.py", wj(d, "r.json", self.stale("all-interfaces-complete")))
        self.assertEqual(rc, 1)
        self.assertTrue("CANARY123" not in out, "evidence ref echoed")

    def test_credential_shaped_value_in_schema_error_is_redacted(self):
        reg = base("partial")
        reg["records"][0]["label"] = CANARY
        reg["records"][0]["evidence"] = [{"ref": CANARY, "extra": CANARY}]
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("register_validate.py", wj(d, "r.json", reg))
        self.assertEqual(rc, 1)
        self.assertTrue("CANARY123" not in out, "credential-shaped text echoed")

    def test_validate_messages_never_hold_ref(self):
        res = check(self.stale("all-interfaces-complete"))
        self.assertTrue("CANARY123" not in json.dumps(res), "evidence ref in findings")


class TestD05CompatKeywordsAndItems(unittest.TestCase):
    def cmp(self, old, new, d="both", c="closed"):
        return sc.compare(old, new, d, c)

    def test_unsupported_keyword_removed_not_compatible(self):
        res = self.cmp({"type": "integer", "maximum": 5}, {"type": "integer"})
        self.assertFalse(res["compatible"])
        self.assertTrue(any("maximum" in b for b in res["breaking"]))

    def test_unsupported_keyword_oneof_removed_not_compatible(self):
        res = self.cmp({"type": "string", "oneOf": [{"pattern": "^a"}]}, {"type": "string"})
        self.assertFalse(res["compatible"])

    def test_unsupported_keyword_in_both_not_compatible(self):
        self.assertFalse(self.cmp({"maximum": 5}, {"maximum": 9})["compatible"])

    def test_items_constraint_removed_loosens(self):
        old = {"type": "array", "items": {"enum": ["a"]}}
        new = {"type": "array"}
        self.assertFalse(self.cmp(old, new, "producer-first")["compatible"])
        self.assertTrue(self.cmp(old, new, "consumer-first")["compatible"])

    def test_items_constraint_added_tightens(self):
        old = {"type": "array"}
        new = {"type": "array", "items": {"enum": ["a"]}}
        self.assertFalse(self.cmp(old, new, "consumer-first")["compatible"])
        self.assertTrue(self.cmp(old, new, "producer-first")["compatible"])

    def test_items_open_consumer_tolerates(self):
        old = {"type": "array"}
        new = {"type": "array", "items": {"enum": ["a"]}}
        self.assertTrue(self.cmp(old, new, "consumer-first", "open")["compatible"])

    def test_items_empty_schema_is_no_constraint(self):
        self.assertTrue(self.cmp({"type": "array"}, {"type": "array", "items": {}})["compatible"])

    def test_items_form_change_not_compatible(self):
        res = self.cmp({"items": {"type": "string"}}, {"items": [{"type": "string"}]})
        self.assertFalse(res["compatible"])


class TestD06StateEvidence(unittest.TestCase):
    """loaded needs adoption evidence in the validator; installed's path+sha256 rule is scoped to the
    extractor (SKILL.md), because hand registers state installed on the reviewer's word."""

    def mk(self, declared="all-interfaces-complete", **si):
        reg = base(declared)
        r = reg["records"][0]
        for k in ("path", "sha256"):
            r["source_identity"].pop(k, None)
        r["source_identity"].update(si)
        return reg

    def loaded(self, declared="all-interfaces-complete"):
        reg = self.mk(declared)
        reg["records"][0]["installed_state"] = "loaded"
        return reg

    def test_loaded_without_adoption_evidence_refused_on_complete(self):
        res = check(self.loaded())
        self.assertFalse(res["ok"])
        self.assertIn("unevidenced-state", codes(res))

    def test_loaded_with_adoption_evidence_accepted(self):
        reg = self.loaded()
        reg["records"][0]["adoption_evidence"] = [{"ref": "pid-1 exe link", "observed_at": "2026-11-12T11:00:00Z"}]
        self.assertTrue(check(reg)["ok"])

    def test_loaded_with_blank_adoption_evidence_refused(self):
        reg = self.loaded()
        reg["records"][0]["adoption_evidence"] = [{"ref": "  "}]
        self.assertFalse(check(reg)["ok"])

    def test_loaded_unevidenced_is_warning_on_partial(self):
        res = check(self.loaded("partial"))
        self.assertTrue(res["ok"])
        self.assertIn("unevidenced-state", codes(res, "warn"))

    def test_installed_rule_is_scoped_to_extractor_refusal_path_tested(self):
        # extractor: installed without path+sha256 is UNKNOWN, claim kept; complete is then refused
        out = xr.convert([row(installed_state="installed", source_identity="path+sha256:/p")])
        r = out["register"]["records"][0]
        self.assertEqual(r["installed_state"], "UNKNOWN")
        self.assertEqual(r["claimed_installed_states"], ["installed"])
        reg = dict(out["register"], coverage={"declared": "all-interfaces-complete"})
        self.assertFalse(check(reg)["ok"])
        # validator: a hand register's installed is accepted (scope stated in SKILL.md)
        self.assertTrue(check(self.mk())["ok"])

    def test_source_only_needs_no_path(self):
        reg = self.mk(commit=H40)
        reg["records"][0]["installed_state"] = "source-only"
        self.assertTrue(check(reg)["ok"])


class TestD07Timestamps(unittest.TestCase):
    def mk(self, declared, cap=None, obs=None):
        reg = base(declared)
        r = reg["records"][0]
        if cap is not None:
            r["source_identity"]["captured_at"] = cap
        if obs is not None:
            r["evidence"] = [{"ref": "file:x#1", "observed_at": obs}]
        return reg

    def test_unparseable_observed_at_refused_on_complete(self):
        res = check(self.mk("all-interfaces-complete", obs="yesterday"))
        self.assertFalse(res["ok"])
        self.assertIn("unparseable-timestamp", codes(res))

    def test_unparseable_captured_at_refused_on_complete(self):
        res = check(self.mk("all-interfaces-complete", cap="not-a-date"))
        self.assertIn("unparseable-timestamp", codes(res))

    def test_unparseable_is_warning_on_partial(self):
        res = check(self.mk("partial", obs="yesterday"))
        self.assertTrue(res["ok"])
        self.assertIn("unparseable-timestamp", codes(res, "warn"))

    def test_non_string_timestamp_flagged(self):
        res = check(dict(self.mk("all-interfaces-complete"), records=[
            dict(rec("R1"), evidence=[{"ref": "e", "observed_at": 5}])] + base()["records"][1:]))
        self.assertFalse(res["ok"])

    def test_message_does_not_echo_timestamp_text(self):
        res = check(self.mk("all-interfaces-complete", obs=CANARY))
        self.assertTrue("CANARY123" not in json.dumps(res), "timestamp text echoed")

    def test_valid_timestamps_unchanged(self):
        self.assertTrue(check(base())["ok"])


class TestD08Fusion(unittest.TestCase):
    def recs(self, rows):
        return xr.convert(rows, heuristic_fusion=True)["register"]["records"]

    def test_same_name_different_repos_unrooted_paths_not_fused(self):
        out = self.recs([row(component="recall", source_repo="summa", path_or_command="/s/recall.py", interface_kind="cli"),
                         row(component="recall", source_repo="recall-svc", path_or_command="/r/recall.py", interface_kind="cli")])
        self.assertEqual(len(out), 2)
        self.assertFalse([r for r in out if "sources" in r])

    def test_rooted_paths_with_distinct_identities_fuse(self):
        out = self.recs([row(component="ctx", source_repo="summa", path_or_command="summa/README.md"),
                         row(component="ctx", source_repo="recall", path_or_command="recall/README.md",
                             source_identity="commit " + "c" * 40)])
        self.assertEqual(len(out), 1)
        self.assertEqual(len(out[0]["sources"]), 2)

    def test_rooted_paths_with_identical_identity_not_fused(self):
        out = self.recs([row(component="ctx", source_repo="summa", path_or_command="summa/README.md"),
                         row(component="ctx", source_repo="recall", path_or_command="recall/README.md")])
        self.assertEqual(len(out), 2)

    def test_unknown_identity_not_fused(self):
        out = self.recs([row(component="ctx", source_repo="summa", path_or_command="summa/README.md",
                             source_identity="garbled"),
                         row(component="ctx", source_repo="recall", path_or_command="recall/README.md",
                             source_identity="commit " + "c" * 40)])
        self.assertEqual(len(out), 2)


class TestD09ContradictorySides(unittest.TestCase):
    def one(self, **k):
        return xr.convert([row(**k)])["register"]["records"][0]

    def test_contradictory_marks_unknown_and_claim_kept(self):
        r = self.one(evidence="side=consumer; side=producer")
        self.assertEqual(r["role"], "UNKNOWN")
        self.assertEqual(r["claimed_roles"], ["producer"])

    def test_contradictory_marks_across_evidence_items(self):
        r = self.one(evidence=["side=producer", "side=adapter"])
        self.assertEqual(r["role"], "UNKNOWN")

    def test_repeated_same_mark_is_fine(self):
        r = self.one(evidence=["side=producer a", "side=producer b"])
        self.assertEqual(r["role"], "producer")


class TestD10LostMessageTyping(unittest.TestCase):
    def mod(self, fn):
        f = lost()
        fn(f)
        return lm.classify(f)

    def test_sha256_must_be_64_hex(self):
        for bad in ("x", True, 5, "a" * 63, "g" * 64, ["a" * 64]):
            res = self.mod(lambda f, bad=bad: f["trace"]["waiter"].update(sha256=bad))
            self.assertFalse(res["ok"], repr(bad))
            self.assertIn("waiter-installed", res["missing_links"], repr(bad))

    def test_uppercase_hex_accepted(self):
        res = self.mod(lambda f: f["trace"]["producer"].update(sha256="A" * 64))
        self.assertTrue(res["ok"])

    def test_commit_must_be_40_hex(self):
        def m(f):
            del f["trace"]["producer"]["sha256"]
            f["trace"]["producer"]["commit"] = "abc"
        self.assertIn("producer", self.mod(m)["missing_links"])
        def m2(f):
            del f["trace"]["producer"]["sha256"]
            f["trace"]["producer"]["commit"] = H40
        self.assertTrue(self.mod(m2)["ok"])

    def test_ref_must_be_nonblank_string(self):
        for bad in (True, 5, "  "):
            res = self.mod(lambda f, bad=bad: f["trace"]["producer"].update(ref=bad))
            self.assertIn("producer", res["missing_links"], repr(bad))

    def test_adapters_none_evidence_needs_ref(self):
        for bad in (True, 1, "", "  ", []):
            def m(f, bad=bad):
                f["trace"]["adapters"] = []
                f["trace"]["adapters_none_evidence"] = bad
            self.assertIn("adapter", self.mod(m)["missing_links"], repr(bad))

        def ok(f):
            f["trace"]["adapters"] = []
            f["trace"]["adapters_none_evidence"] = "launcher.sh:3 publishes the actor unchanged"
        self.assertEqual(self.mod(ok)["missing_links"], [])

    def test_claim_spelling_variants_normalized(self):
        for c in ("Message Lost", "message_lost", " MESSAGE-LOST ", "Message-Lost"):
            f = lost(claim=c)
            del f["trace"]
            res = lm.classify(f)
            self.assertFalse(res["ok"], c)
            self.assertEqual(res["label"], "conditional-risk", c)

    def test_label_spelling_variant_normalized(self):
        f = lost(label=" Observed-Defect ")
        del f["trace"]
        self.assertFalse(lm.classify(f)["ok"])

    def test_accept_vs_defect_refusal_is_intelligible(self):
        f = lost()
        f["trace"]["waiter"]["verdict_for_actor"] = "accept"
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("lost_message_check.py", wj(d, "f.json", f))
        self.assertEqual(rc, 1)
        last = out.strip().splitlines()[-1]
        self.assertTrue(last.startswith("REFUSED"))
        self.assertFalse(last.rstrip().endswith(":"))
        self.assertIn("accept", last)

    def test_missing_link_refusal_still_names_links(self):
        f = {"id": "F1", "claim": "message-lost", "label": "observed-defect"}
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("lost_message_check.py", wj(d, "f.json", f))
        self.assertIn("producer", out.strip().splitlines()[-1])


class TestD11UnreadableRc2(unittest.TestCase):
    def test_schema_compat_missing_file_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("schema_compat.py", Path(d) / "none.json", Path(d) / "none2.json")
        self.assertEqual(rc, 2)
        self.assertNotIn("Traceback", out)

    def test_schema_compat_invalid_json_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("schema_compat.py", wj(d, "a.json", "{"), wj(d, "b.json", "{}"))
        self.assertEqual(rc, 2)
        self.assertNotIn("Traceback", out)

    def test_schema_compat_wrong_shape_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            for top in ("[]", '"s"', "3", "null"):
                rc, out = run("schema_compat.py", wj(d, "a.json", top), wj(d, "b.json", "{}"))
                self.assertEqual(rc, 2, top)
                self.assertNotIn("Traceback", out)

    def test_schema_compat_nested_wrong_shape_rc2_not_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("schema_compat.py", wj(d, "a.json", {"properties": [1]}),
                          wj(d, "b.json", {"properties": {"a": {}}}))
        self.assertIn(rc, (1, 2))
        self.assertNotIn("Traceback", out)

    def test_schema_compat_non_utf8_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("schema_compat.py", FX / "nonutf8.jsonl", wj(d, "b.json", "{}"))
        self.assertEqual(rc, 2)

    def test_lost_message_non_object_rc2(self):
        for name in ("array_top.json",):
            rc, out = run("lost_message_check.py", FX / name)
            self.assertEqual(rc, 2)
            self.assertNotIn("Traceback", out)

    def test_lost_message_non_utf8_rc2(self):
        rc, out = run("lost_message_check.py", FX / "nonutf8.jsonl")
        self.assertEqual(rc, 2)
        self.assertNotIn("Traceback", out)

    def test_extractor_non_utf8_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("extract_register.py", FX / "nonutf8.jsonl", Path(d) / "o")
        self.assertEqual(rc, 2)
        self.assertNotIn("Traceback", out)

    def test_extractor_missing_input_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("extract_register.py", Path(d) / "nope", Path(d) / "o")
        self.assertEqual(rc, 2)

    def test_extractor_uncreatable_outdir_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            f = wj(d, "blocker", "x")
            rc, out = run("extract_register.py", wj(d, "e.jsonl", ""), f / "sub")
        self.assertEqual(rc, 2)
        self.assertNotIn("Traceback", out)

    def test_validator_wrong_shape_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            for top in ("[]", '"s"', "null"):
                rc, out = run("register_validate.py", wj(d, "r.json", top))
                self.assertEqual(rc, 2, top)
                self.assertNotIn("Traceback", out)

    def test_validator_odd_nested_shapes_no_traceback(self):
        odd = [{"family": ["IF001"]}, {"record_id": {"a": 1}}, {"component": ["x"], "role": {"r": 1}},
               {"evidence": {"ref": "x"}}, {"sources": 5}, {"source_identity": [1]}, {"label": ["x"]}]
        with tempfile.TemporaryDirectory() as d:
            for o in odd:
                reg = base("all-interfaces-complete")
                reg["records"].append(o)
                rc, out = run("register_validate.py", wj(d, "r.json", reg))
                self.assertIn(rc, (1, 2), repr(o))
                self.assertNotIn("Traceback", out, repr(o))

    def test_validator_families_odd_shapes_no_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            for fam in ([["x"]], [{"id": ["x"]}], {"id": "IF001"}, [{"id": "IF001", "registered_callers": [["a"]]}]):
                reg = base("all-interfaces-complete")
                reg["families"] = fam
                rc, out = run("register_validate.py", wj(d, "r.json", reg))
                self.assertIn(rc, (1, 2), repr(fam))
                self.assertNotIn("Traceback", out, repr(fam))


class TestD12Parsing(unittest.TestCase):
    def extract(self, src):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("extract_register.py", src, Path(d) / "o")
            p = Path(d) / "o" / "register-partial.json"
            reg = json.loads(p.read_text()) if p.exists() else None
            rej = json.loads((Path(d) / "o" / "rejected.json").read_text()) if p.exists() else None
        return rc, reg, rej, out

    def test_raw_u2028_and_u0085_inside_valid_row_accepted(self):
        rc, reg, rej, out = self.extract(FX / "u2028.jsonl")
        self.assertEqual(rc, 0, out)
        self.assertEqual(rej, [])
        self.assertEqual(sorted(r["component"] for r in reg["records"]), ["a b", "n\u0085l"])

    def test_crlf_lines_still_parse(self):
        with tempfile.TemporaryDirectory() as d:
            rc, reg, rej, out = self.extract(wj(d, "c.jsonl", json.dumps(row()) + "\r\n" + json.dumps(row(component="z")) + "\r\n"))
        self.assertEqual(rc, 0)
        self.assertEqual(len(reg["records"]), 2)

    def test_duplicate_keys_in_row_rejected(self):
        rc, reg, rej, out = self.extract(FX / "dup_keys.jsonl")
        self.assertEqual(rc, 3)
        self.assertEqual(len(reg["records"]), 0)
        self.assertIn("duplicate", rej[0]["reason"])

    def test_convert_lines_rejects_duplicate_keys(self):
        out = xr.convert_lines(['{"a":1,"a":2}'])
        self.assertEqual(len(out["rejected"]), 1)

    def test_validator_refuses_duplicate_keys_rc2(self):
        rc, out = run("register_validate.py", FX / "dup_declared_register.json")
        self.assertEqual(rc, 2)
        self.assertIn("duplicate", out)

    def test_schema_compat_refuses_duplicate_keys_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("schema_compat.py", FX / "dup_schema.json", wj(d, "b.json", "{}"))
        self.assertEqual(rc, 2)

    def test_lost_message_refuses_duplicate_keys_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("lost_message_check.py", wj(d, "f.json", '{"claim":"a","claim":"message-lost"}'))
        self.assertEqual(rc, 2)

    def test_enum_one_vs_true_is_a_change(self):
        res = sc.compare({"enum": [1]}, {"enum": [True]})
        self.assertFalse(res["compatible"])
        self.assertEqual(len(res["classified"]), 2)

    def test_enum_zero_vs_false_and_int_vs_float(self):
        self.assertFalse(sc.compare({"enum": [0]}, {"enum": [False]})["compatible"])
        self.assertTrue(sc.compare({"enum": [1]}, {"enum": [1.0]})["compatible"])

    def test_enum_cli_rc1(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("schema_compat.py", wj(d, "a.json", {"enum": [1]}), wj(d, "b.json", {"enum": [True]}))
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
