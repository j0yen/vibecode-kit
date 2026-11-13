"""Repairs for the third independent exact-head review of 4414af68 (DEFECTS 1-12, closed as classes).
Fixtures are synthetic and source-only; they exercise the rules, not production behavior. Credential-shaped
canaries are FAKE, assembled at run time from fragments and never printed: a failure reports a fixed message.
No test depends on the real clock or the host time zone: the reference clock is injected (NOW)."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from test_register import SK, base, rec
from test_review_fixes2 import NOW, check, errs, mut, row, run, wj, sch, H40, H64
import register_validate as rv

sys.path.insert(0, str(SK / "scripts"))
import extract_register as xr  # noqa: E402
import ir_norm  # noqa: E402
import lost_message_check as lm  # noqa: E402
import schema_compat as sc  # noqa: E402

FIX = SK / "tests" / "fixtures"
ZW = "​"
FAKES = {
    "sk-live": "sk" + "_live_" + "Ab12CdEf34GhIj56",
    "sk-test": "sk" + "_test_" + "Zy98XwVu76TsRq54",
    "glpat": "glpat" + "-" + "Ab12Cd34Ef56Gh78Ij90",
    "npm": "npm" + "_" + "Ab12Cd34Ef56" + "Gh78Ij90Kl12Mn34",
    "aws40": "Qw8Er2Ty6Ui0" + "Op4As9Df1Gh5" + "Jk7Lz3Xc6Vb2Nm",
    "zwsp-gh": "gh" + ZW + "p_" + "Q" * 36,
    "zwsp-akia": "AK" + ZW + "IA" + "Z" * 16,
    "hf": "hf" + "_" + "AbCdEfGhIjKlMnOp",
}


def leaked(fake, text):
    core = fake.replace(ZW, "")[-12:]
    return core in text.replace(ZW, "")


def complete_ok(reg):
    return check(reg)["ok"]


# ---- DEFECT 1 ---------------------------------------------------------------------------------------
class TestD1Adoption(unittest.TestCase):
    def adopt(self, ref):
        return mut(lambda r: r.update(installed_state="loaded", adoption_evidence=[{"ref": ref, "observed_at": "2026-11-12T11:00:00Z"}]))

    REFUSED = ("process: UNKNOWN", "pid=", "no process found for ctl", "systemctl list-units process-compose.service loaded active",
               "lsof", "process: n/a", "systemctl status exe.service enabled", "/proc/", "pid not found", "/proc/x/exe",
               "process", "exe", "cmdline", "pid", "pid 0 exe", "pid 4242 not running exe", "pid: tbd exe",
               "ps shows process UNKNOWN", "pgrep", "top", "fuser", "ctl.timer pid 4242 cmdline /usr/bin/ctl",
               "journalctl -u ctl.service pid 4242 exe", "unit ctl.service Active: inactive (dead) pid 4242 exe",
               "pid 4242 exited, exe gone", "lsof -p 4242 found no process", "process none", "pidof ctl: nothing",
               "/proc/4242/ is empty", "pid 4242 (unavailable) exe", "list-unit-files | grep process")

    def test_non_observations_refused_naming_record(self):
        for v in self.REFUSED:
            res = check(self.adopt(v))
            self.assertFalse(res["ok"], "a non-observation was accepted as process adoption")
            self.assertIn("unevidenced-state", errs(res))
            self.assertTrue([f for f in res["findings"] if f["code"] == "unevidenced-state" and f["record"] == "R1"])

    def test_positive_observations_accepted(self):
        for v in ("pid 4242 cmdline /usr/bin/ctl --serve exe sha", "/proc/4242/exe -> /usr/bin/ctl", "pid=4242 exe=/usr/bin/ctl",
                  "lsof -p 4242 shows process ctl-event-wait", "pid: 77 comm ctl", "/proc/9/cmdline names ctl.sh"):
            self.assertTrue(complete_ok(self.adopt(v)), "a positive process observation was refused")

    def test_one_good_ref_among_bad_ones_is_enough_and_all_bad_is_not(self):
        reg = mut(lambda r: r.update(installed_state="loaded", adoption_evidence=[{"ref": "lsof", "observed_at": "2026-11-12T11:00:00Z"}, {"ref": "pid 4242 exe", "observed_at": "2026-11-12T11:00:00Z"}]))
        self.assertTrue(complete_ok(reg))
        reg = mut(lambda r: r.update(installed_state="loaded", adoption_evidence=[{"ref": "lsof", "observed_at": "2026-11-12T11:00:00Z"}, {"ref": "pid=", "observed_at": "2026-11-12T11:00:00Z"}]))
        self.assertFalse(complete_ok(reg))

    def test_skill_md_states_the_rule(self):
        txt = (SK / "SKILL.md").read_text()
        self.assertIn("/proc/<n>", txt)
        self.assertIn("negation", txt)


# ---- DEFECT 2 ---------------------------------------------------------------------------------------
class TestD2Redaction(unittest.TestCase):
    def test_every_class_masked_in_every_validator_path(self):
        for name, v in FAKES.items():
            r1, r2 = rec("R1"), rec("R2", role="consumer", comp="svc-b")
            r1["record_id"] = r2["record_id"] = v                      # duplicate-record path
            r1["family"] = v                                           # unknown-family path (record id too)
            r2["role"] = v                                             # role in counts / unclassified message
            reg = {"schema_version": 1, "coverage": {"declared": "all-interfaces-complete", "declared_counts": {v: 1}},
                   "families": [{"id": "IF001", "registered_callers": [v]}], "records": [r1, r2], v: 1}
            res = check(reg)
            self.assertFalse(leaked(v, json.dumps(res)), f"{name}: leaked through the library result")
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("register_validate.py", wj(d, "r.json", reg), "--now", "2026-11-13T12:00:00Z")
            self.assertFalse(leaked(v, out), f"{name}: leaked through the validator CLI")

    def test_every_class_masked_in_lost_message_check(self):
        for name, v in FAKES.items():
            f = json.loads((FIX / "review" / "lost_consistent.json").read_text())
            f["id"] = v
            f["claim"] = v                                             # unrecognised claim is stated, redacted
            f["trace"]["waiter"]["actor"] = v
            f["trace"]["producer"]["actor"] = v + "x"
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("lost_message_check.py", wj(d, "f.json", f))
            self.assertFalse(leaked(v, out), f"{name}: leaked through lost_message_check")
            f["claim"] = "message-lost"
            f["label"] = v
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("lost_message_check.py", wj(d, "f.json", f))
            self.assertFalse(leaked(v, out), f"{name}: leaked through lost_message_check (label/actor)")

    def test_other_scripts_do_not_echo_the_classes(self):
        for name, v in FAKES.items():
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("extract_register.py", wj(d, "in.jsonl", '{"a": 1, "' + v + '": 1, "' + v + '": 2}\n'), Path(d) / "o")
                self.assertFalse(leaked(v, out + (Path(d) / "o" / "rejected.json").read_text()), f"{name}: extractor")
                rc, out = run("schema_compat.py", wj(d, "a.json", '{"' + v + '": 1, "' + v + '": 2}'), wj(d, "b.json", {}))
                self.assertFalse(leaked(v, out), f"{name}: compat")
                src = wj(d, "s.sh", "X='a'\n")
                rc, out = run("discriminator_check.py", src, "--line", "1", "--names", v)
                self.assertFalse(leaked(v, out), f"{name}: discriminator name")
                rc, out = run("discriminator_check.py", wj(d, "s.sh", "X='" + v + "'\n"), "--line", "1", "--names", "a", "--json")
                self.assertFalse(leaked(v, out), f"{name}: discriminator pattern")

    def test_ordinary_text_is_not_masked(self):
        for t in ("svc-a", "IF001", "record R1", "pid 4242 exe link", "a" * 64, "c" * 40, "x-0123456789abcdef",
                  "stale-evidence evidence[0] observed 2026-11-12T09:00:00+00:00 before source_identity identity 2026-11-12T10:00:00+00:00",
                  "/mnt/ssd/cargo-target/r7-irv-20261112/fix3/x"):
            self.assertEqual(ir_norm.redact(t), t)

    def test_finding_record_field_is_masked(self):
        r1, r2 = rec("R1"), rec("R2", role="consumer", comp="svc-b")
        r1["record_id"] = r2["record_id"] = FAKES["glpat"]
        res = check({"schema_version": 1, "coverage": {"declared": "partial"}, "families": [{"id": "IF001"}], "records": [r1, r2]})
        self.assertFalse(leaked(FAKES["glpat"], json.dumps(res["findings"])))


# ---- DEFECT 3 ---------------------------------------------------------------------------------------
PLACEHOLDER_VARIANTS = ("N.A.", "n.a", "N/A", "N / A", "n-a", "undefined", "Undefined.", "null", "NULL", "nil", "not available",
                        "Not  Available", "not applicable", "unavailable", "unknown", "unknowń", "unknowń", "unknown️",
                        "unk", "tbd", "tba", "TODO", "to do", "to-do", "?", "???", "-", "--", "–", "—", "−",
                        "‐", "‑", "－", "tbd?", "unknown=", "unknown:", "none", "None.", "Ｎ／Ａ",
                        "…", "...", "unspecified", "not known", "​none​", " \tunknown\n", "[none]", "(n/a)",
                        "Ṅ/A", "ünknown", "")


class TestD3Placeholders(unittest.TestCase):
    def test_family_is_unknown_equivalent(self):
        for v in PLACEHOLDER_VARIANTS:
            self.assertTrue(ir_norm.is_unknown(v), f"placeholder {v!r} counted as stated")

    def test_stated_values_stay_stated(self):
        for v in ("svc-a", "ryzen7", "1.0.0", "unknown-service", "none-of-it", "n2", "todo-app", "na-core", "j0yen/x", "a",
                  "not-available-svc", "0"):
            self.assertFalse(ir_norm.is_unknown(v), f"stated value {v!r} counted as placeholder")
        self.assertTrue(ir_norm.is_unknown(5) and ir_norm.is_unknown(None) and ir_norm.is_unknown(["x"]))

    def test_every_field_the_complete_check_reads(self):
        fields = {
            "host": lambda r, v: r.update(host=v),
            "component": lambda r, v: r.update(component=v),
            "role": lambda r, v: r.update(role=v),
            "installed_state": lambda r, v: r.update(installed_state=v),
            "label": lambda r, v: r.update(label=v),
            "repo": lambda r, v: r["source_identity"].update(repo=v),
            "version": lambda r, v: r["source_identity"].update(version=v),
            "evidence": lambda r, v: r.update(evidence=[{"ref": v, "observed_at": "2026-11-12T11:00:00Z"}]),
            "adoption": lambda r, v: r.update(installed_state="loaded", adoption_evidence=[{"ref": "pid 4242 exe " + v}]),
        }
        for fld, fn in fields.items():
            for v in PLACEHOLDER_VARIANTS[:48:3]:
                if fld == "adoption":
                    continue
                if not v:
                    continue
                reg = mut(lambda r: fn(r, v))
                self.assertFalse(complete_ok(reg), f"{fld}={v!r} passed complete")
        for v in ("N.A.", "undefined", "not available", "unknowń", "???", "–", "tbd?", "unknown="):
            reg = mut(lambda r: r.update(installed_state="loaded", adoption_evidence=[{"ref": v}]))
            self.assertFalse(complete_ok(reg), f"adoption ref {v!r} passed complete")

    def test_extractor_treats_the_family_as_not_stated(self):
        for v in ("N.A.", "undefined", "not available", "unknowń", "???", "–", "todo"):
            r = xr.convert([row(component=v, host=v)])["register"]["records"][0]
            self.assertEqual((r["component"], r["host"]), ("UNKNOWN", "UNKNOWN"), f"{v!r}")


# ---- DEFECTS 4, 5, 11 ---------------------------------------------------------------------------------
class TestD4D5D11Timestamps(unittest.TestCase):
    def reg(self, declared="all-interfaces-complete", **kw):
        reg = base(declared)
        r = reg["records"][0]
        r.update(installed_state="loaded", adoption_evidence=[{"ref": "pid 4242 exe", "observed_at": "2026-11-12T11:00:00Z"}])
        for k, v in kw.items():
            if k == "adopt_obs":
                r["adoption_evidence"][0]["observed_at"] = v
        return reg

    def test_adoption_timestamps_follow_the_evidence_rules(self):
        self.assertTrue(complete_ok(self.reg()))
        for v, code in (("garbage", "unparseable-timestamp"), ("2099-01-01T00:00:00Z", "future-timestamp"),
                        ("2026-11-12T10:00:00", "ambiguous-timestamp"), ("", "unparseable-timestamp"),
                        ("N/A", "unparseable-timestamp"), ("2026-11-12T09:00:00Z", "stale-evidence"),
                        ("2026-11-13T12:10:00Z", "future-timestamp")):
            res = check(self.reg(adopt_obs=v))
            self.assertIn(code, errs(res), f"adoption observed_at {v!r}")
            warn = check(self.reg("partial", adopt_obs=v))
            self.assertTrue(warn["ok"])
            self.assertIn(code, {f["code"] for f in warn["findings"] if f["severity"] == "warn"})

    def test_omitted_stamps_refuse_complete(self):
        reg = base()
        reg["records"][0]["source_identity"].pop("captured_at")
        res = check(reg)
        self.assertIn("missing-timestamp", errs(res))
        reg = base()
        reg["records"][0]["evidence"] = [{"ref": "file:x#1"}]
        self.assertIn("missing-timestamp", errs(check(reg)))
        for v in ("", "   ", None):
            reg = base()
            reg["records"][0]["evidence"] = [{"ref": "file:x#1", "observed_at": v}]
            self.assertFalse(check(reg)["ok"], f"observed_at {v!r}")
            reg = base()
            reg["records"][0]["source_identity"]["captured_at"] = v
            self.assertFalse(check(reg)["ok"], f"captured_at {v!r}")

    def test_omitted_stamp_on_each_source_of_a_multi_source_record(self):
        reg = base()
        r = reg["records"][0]
        si = dict(r.pop("source_identity"))
        r["sources"] = [dict(si, path_or_command="a/x"), {k: v for k, v in dict(si, path_or_command="b/x").items() if k != "captured_at"}]
        res = check(reg)
        self.assertTrue([f for f in res["findings"] if f["code"] == "missing-timestamp" and "sources[1]" in f["message"]])
        self.assertFalse([f for f in res["findings"] if f["code"] == "missing-timestamp" and "sources[0]" in f["message"]])

    def test_omitted_stamps_only_warn_on_partial(self):
        reg = base("partial")
        reg["records"][0]["source_identity"].pop("captured_at")
        res = check(reg)
        self.assertTrue(res["ok"])
        self.assertIn("missing-timestamp", {f["code"] for f in res["findings"] if f["severity"] == "warn"})

    def test_lowercase_z_is_a_valid_utc_offset_and_overflow_is_unparseable(self):
        reg = base()
        reg["records"][0]["evidence"] = [{"ref": "file:x#1", "observed_at": "2026-11-12T11:00:00z"}]
        self.assertTrue(check(reg)["ok"])
        reg["records"][0]["evidence"] = [{"ref": "file:x#1", "observed_at": "0001-01-01T00:00:00+23:59"}]
        reg["records"][0]["source_identity"]["captured_at"] = "2026-11-12T10:00:00Z"
        self.assertFalse(check(reg)["ok"])          # not convertible to UTC: unparseable, refused, no traceback

    def test_unstamped_adoption_is_stated_not_silent(self):
        reg = self.reg()
        del reg["records"][0]["adoption_evidence"][0]["observed_at"]
        res = check(reg)
        self.assertFalse(res["ok"])       # repair 4 (D1): an unstamped adoption ref is refused under complete, not warned
        self.assertIn("missing-timestamp", {f["code"] for f in res["findings"] if f["severity"] == "error"})

    def test_naive_now_is_not_replaced_by_the_wall_clock(self):
        reg = base()
        reg["records"][0]["evidence"] = [{"ref": "file:x#1", "observed_at": "2026-11-12T13:00:00Z"}]
        with self.assertRaises(ValueError):
            rv.validate(reg, rv.load_schema(), now=datetime(2026, 11, 12, 12, 0, 0))
        with self.assertRaises(TypeError):
            rv.validate(reg, rv.load_schema(), now="2026-11-12T12:00:00Z")
        aware = rv.validate(reg, rv.load_schema(), now=datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc))
        self.assertIn("future-timestamp", {f["code"] for f in aware["findings"]})
        self.assertTrue(rv.validate(base(), rv.load_schema())["ok"])          # None: the wall clock, stated default

    def test_cli_still_rejects_offsetless_now(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(run("register_validate.py", wj(d, "r.json", base()), "--now", "2026-11-12T12:00:00")[0], 2)


# ---- DEFECTS 6, 7 -------------------------------------------------------------------------------------
class TestD6D7Lost(unittest.TestCase):
    def f(self, **top):
        f = json.loads((FIX / "review" / "lost_consistent.json").read_text())
        f.update(top)
        return f

    def trace(self, actor_p, actor_w, adapters=None, **links):
        f = self.f()
        f["trace"]["adapters"] = adapters if adapters is not None else []
        f["trace"]["adapters_none_evidence"] = "none-found"
        f["trace"]["producer"]["actor"], f["trace"]["waiter"]["actor"] = actor_p, actor_w
        for k, v in links.items():
            a, b = k.split("__")
            f["trace"][a][b] = v
        return f

    def test_actors_compare_by_type_and_value(self):
        for p, w in ((1, True), (True, 1), (1, 1.0), (1, "1"), (0, False), (None, "None"), ("a", "A"), ([1], [True])):
            if p is None:
                continue
            res = lm.classify(self.trace(p, w))
            self.assertFalse(res["ok"], f"actors {p!r} and {w!r} treated as equal")
            self.assertTrue(res["inconsistent_links"])
            self.assertEqual(res["label"], "conditional-risk")
        for same in (1, True, "bld", 1.5, [1, 2], {"a": 1}):
            self.assertTrue(lm.classify(self.trace(same, same))["ok"], f"identical actor {same!r} refused")

    def test_family_interface_message_compare_by_type(self):
        for fld in ("family", "interface", "message"):
            res = lm.classify(self.trace("a", "a", producer__x=1, **{f"producer__{fld}": 1, f"waiter__{fld}": True}))
            self.assertTrue(res["inconsistent_links"], fld)

    def test_adapter_maps_compare_by_type(self):
        ad = [dict(self.f()["trace"]["adapters"][0], maps_from=True, maps_to="b")]
        self.assertTrue(lm.classify(self.trace(1, "b", adapters=ad))["inconsistent_links"])
        ad = [dict(self.f()["trace"]["adapters"][0], maps_from=1, maps_to=True)]
        self.assertTrue(lm.classify(self.trace(1, 1, adapters=ad))["inconsistent_links"])        # waiter 1 != reached True
        ad = [dict(self.f()["trace"]["adapters"][0], maps_from=1, maps_to=True)]
        self.assertEqual(lm.classify(self.trace(1, True, adapters=ad))["inconsistent_links"], [])  # 1 -> True is not a loop

    def test_cli_refuses_the_one_versus_true_trace(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("lost_message_check.py", wj(d, "f.json", self.trace(1, True)))
        self.assertEqual(rc, 1)
        self.assertIn("inconsistent", out)

    CLAIMS = ("messagelost", "message-lost .", "message-dropped", "lost-message", "Message Lost", "MESSAGE_LOST", "messages-lost",
              "message  lost", "msg-lost", "message-loss", "lost messages!", "message​-lost", "MSG_DROPPED", "message missing",
              "dropped-message", "the message was lost", "Ｍessage-lost", "messagesdropped")

    def test_claim_wordings_are_recognised_and_checked(self):
        for c in self.CLAIMS:
            f = self.f(claim=c)
            f["trace"] = {}
            res = lm.classify(f)
            self.assertFalse(res["ok"], f"claim {c!r} bypassed the trace rule")
            self.assertIn("producer", res["missing_links"])
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("lost_message_check.py", wj(d, "f.json", f))
            self.assertEqual(rc, 1, c)

    def test_unrecognised_claim_is_stated_never_silent(self):
        for c in ("latency regression", "event dropped", "message delivered", 5, None, ["message-lost"], "", "lost"):
            f = self.f(claim=c)
            f["trace"] = {}
            res = lm.classify(f)
            self.assertIs(res["claim_recognised"], False, repr(c))
            self.assertEqual(res["consistency"], "not-applicable")
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("lost_message_check.py", wj(d, "f.json", f))
            self.assertEqual(rc, 0, c)
            self.assertIn("NOT-CHECKED", out, f"claim {c!r} passed without a statement")

    def test_recognised_claim_prints_no_not_checked(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("lost_message_check.py", wj(d, "f.json", self.f()))
        self.assertEqual(rc, 0)
        self.assertNotIn("NOT-CHECKED", out)


# ---- DEFECTS 8, 9 -------------------------------------------------------------------------------------
def objs(**props):
    return {"type": "object", "properties": props, "additionalProperties": {"type": "string"}}


class TestD8D9Compat(unittest.TestCase):
    def test_new_property_checked_against_old_additional_properties_schema(self):
        o = objs(a={"type": "string"})
        for newp, pf_ok in (({"type": "integer"}, False), ({"type": "string"}, True), ({"type": "string", "enum": ["x"]}, True),
                            ({}, False), ({"type": ["string", "null"]}, False), ({"type": "string", "pattern": "^a"}, True),
                            ({"type": "boolean"}, False), ({"type": "object"}, False)):
            n = objs(a={"type": "string"}, b=newp)
            r = sc.compare(o, n, "producer-first")
            self.assertEqual(r["compatible"], pf_ok, f"new property {newp}")
            self.assertTrue(sc.compare(o, n, "consumer-first")["compatible"], f"consumer-first {newp}")
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("schema_compat.py", wj(d, "o.json", o), wj(d, "n.json", n), "--direction", "producer-first")
            self.assertEqual(rc, 0 if pf_ok else 1, newp)

    def test_open_consumer_tolerates_it(self):
        o, n = objs(a={"type": "string"}), objs(a={"type": "string"}, b={"type": "integer"})
        self.assertTrue(sc.compare(o, n, "producer-first", "open")["compatible"])
        self.assertFalse(sc.compare(o, n, "producer-first", "closed")["compatible"])

    def test_nested_level_and_open_old_schema(self):
        wrap = lambda inner: {"type": "object", "properties": {"x": inner}}  # noqa: E731
        o, n = wrap(objs()), wrap(objs(b={"type": "integer"}))
        self.assertFalse(sc.compare(o, n, "producer-first")["compatible"])
        plain_o = {"type": "object", "properties": {}}
        plain_n = {"type": "object", "properties": {"b": {"type": "integer"}}}
        self.assertTrue(sc.compare(plain_o, plain_n, "producer-first")["compatible"])        # old additionalProperties open
        closed_o = dict(plain_o, additionalProperties=False)
        self.assertFalse(sc.compare(closed_o, plain_n, "producer-first")["compatible"])

    DEFS = {"a": {"type": "string"}}

    def refd(self, ref):
        return {"definitions": self.DEFS, "type": "object", "properties": {"x": ref}}

    def test_ref_swapped_with_equal_inline_is_a_note_only(self):
        a, b = self.refd({"$ref": "#/definitions/a"}), self.refd({"type": "string"})
        for o, n in ((a, b), (b, a)):
            for d in ("both", "producer-first", "consumer-first"):
                r = sc.compare(o, n, d)
                self.assertTrue(r["compatible"], (d, r["breaking"]))
                self.assertEqual(r["breaking"], [])
            with tempfile.TemporaryDirectory() as t:
                self.assertEqual(run("schema_compat.py", wj(t, "o.json", o), wj(t, "n.json", n))[0], 0)

    def test_ref_swapped_with_different_inline_is_still_caught(self):
        a, b = self.refd({"$ref": "#/definitions/a"}), self.refd({"type": "integer"})
        self.assertFalse(sc.compare(a, b, "both")["compatible"])
        self.assertFalse(sc.compare(b, a, "both")["compatible"])
        c = self.refd({"type": ["string", "null"]})
        self.assertFalse(sc.compare(a, c, "producer-first")["compatible"])
        self.assertTrue(sc.compare(a, c, "consumer-first")["compatible"])

    def test_identical_files_are_compatible_with_any_keyword(self):
        docs = (self.refd({"$ref": "#/definitions/a"}),
                {"type": "string", "format": "date"},
                {"type": "object", "properties": {"a": {"oneOf": [{"type": "string"}, {"type": "integer"}]}}},
                {"type": "object", "properties": {"a": {"not": {"type": "null"}, "type": "string"}}},
                {"type": "string", "default": "x", "examples": ["y"], "$comment": "c"})
        for d in docs:
            for direction in ("both", "producer-first", "consumer-first"):
                self.assertTrue(sc.compare(d, json.loads(json.dumps(d)), direction)["compatible"], d)
            with tempfile.TemporaryDirectory() as t:
                self.assertEqual(run("schema_compat.py", wj(t, "o.json", d), wj(t, "n.json", d))[0], 0)

    def test_changed_or_added_unsupported_keywords_are_still_breaking(self):
        self.assertFalse(sc.compare({"type": "string", "format": "date"}, {"type": "string", "format": "date-time"})["compatible"])
        self.assertFalse(sc.compare({"type": "string"}, {"type": "string", "format": "date"})["compatible"])
        self.assertFalse(sc.compare({"type": "string", "oneOf": [{"type": "string"}]}, {"type": "string"})["compatible"])
        self.assertFalse(sc.compare({"type": "string", "if": {}}, {"type": "string", "if": {"type": "null"}})["compatible"])

    def test_unchanged_applicator_next_to_a_change_is_not_compatible(self):
        one = {"oneOf": [{"type": "string"}, {"type": "integer"}]}
        o = {"type": "object", "properties": {"a": dict(one, type="string")}}
        n = {"type": "object", "properties": {"a": dict(one, type="integer")}}
        self.assertFalse(sc.compare(o, n, "both")["compatible"])
        o = {"type": "object", "properties": {}, **one}
        n = {"type": "object", "properties": {"b": {"type": "integer"}}, **one}
        r = sc.compare(o, n, "consumer-first")
        self.assertFalse(r["compatible"])
        self.assertTrue(r["undetermined"])


# ---- DEFECT 10 ----------------------------------------------------------------------------------------
class TestD10Hex(unittest.TestCase):
    def ident(self, s):
        r = xr.convert([row(source_identity=s, installed_state="source-only")])["register"]["records"][0]["source_identity"]
        return r["available"]

    def test_not_an_identity(self):
        for s in ("path+sha256:/p " + "d" * 64 + "\n", "commit " + "c" * 40 + "\n", "commit " + "c" * 40 + " (dirty, unverified)",
                  "path+sha256:/p " + "d" * 64 + " ", "path+sha256:/p " + "d" * 64 + "\r\n", "commit " + "c" * 40 + " ",
                  "commit " + "c" * 40 + "\t", " commit " + "c" * 40, "commit  " + "c" * 40, "commit " + "c" * 40 + "x",
                  "path+sha256:/p " + "d" * 64 + " extra", "commit " + "c" * 41, "commit " + "c" * 39,
                  "path+sha256:/p " + "d" * 63, "path+sha256:/p " + "D" * 64, "commit " + "C" * 40):
            self.assertFalse(self.ident(s), f"{s[:20]!r}... {s[-12:]!r} accepted as an identity")

    def test_exact_forms_still_parse(self):
        self.assertTrue(self.ident("path+sha256:/p " + "d" * 64))
        self.assertTrue(self.ident("commit " + "c" * 40))

    def test_cli_row_with_a_trailing_newline_in_the_string(self):
        with tempfile.TemporaryDirectory() as d:
            line = json.dumps(row(source_identity="commit " + "c" * 40 + "\n", installed_state="source-only"))
            rc, out = run("extract_register.py", wj(d, "in.jsonl", line + "\n"), Path(d) / "o")
            reg = json.loads((Path(d) / "o" / "register-partial.json").read_text())
        self.assertEqual(reg["records"][0]["source_identity"]["version"], "UNKNOWN")
        self.assertEqual(reg["records"][0]["installed_state"], "UNKNOWN")


# ---- DEFECT 12 ----------------------------------------------------------------------------------------
class TestD12Fusion(unittest.TestCase):
    def recs(self, rows, **kw):
        out = xr.convert(rows, **kw)
        return out["register"]["records"], out["stats"]

    def two(self, p1, p2, r1="r1", r2="r2", i1=None, i2=None):
        return [row(component="recall", source_repo=r1, path_or_command=p1, source_identity=i1 or "commit " + H40),
                row(component="recall", source_repo=r2, path_or_command=p2, source_identity=i2 or "commit " + "c" * 40)]

    def test_same_name_different_repos_and_commits_stay_separate_by_default(self):
        for p1, p2 in (("r1/a.py", "r2/b.py"), ("r1/README.md", "r2/README.md"), ("a.py", "b.py"), ("r1/a.py", "r2/a.py")):
            recs, st = self.recs(self.two(p1, p2))
            self.assertEqual(len(recs), 2, (p1, p2))
            self.assertFalse([r for r in recs if "sources" in r or "fusion_basis" in r])
            self.assertEqual(st.get("fused_multi_source_components", 0), 0)

    def test_same_repo_different_paths_stay_separate(self):
        recs, _ = self.recs(self.two("r1/a.py", "r1/b.py", r2="r1"))
        self.assertEqual(len(recs), 2)

    def test_same_content_sha256_fuses_with_a_named_basis(self):
        recs, st = self.recs(self.two("r1/a.py", "r2/b.py", i1="path+sha256:r1/a.py " + H64, i2="path+sha256:r2/b.py " + H64))
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["fusion_basis"], "same-content-sha256")
        self.assertEqual(len(recs[0]["sources"]), 2)
        self.assertEqual(st["fused_multi_source_components"], 1)

    def test_different_sha256_does_not_fuse(self):
        recs, _ = self.recs(self.two("r1/a.py", "r2/b.py", i1="path+sha256:r1/a.py " + H64, i2="path+sha256:r2/b.py " + "e" * 64))
        self.assertEqual(len(recs), 2)

    def test_same_repo_identity_in_other_spellings_with_one_path_fuses(self):
        same = "commit " + H40         # repair 4 (D8): distinct commits never fuse, so the one-component rows state one commit
        recs, _ = self.recs(self.two("src/a.py", "src/./a.py", r1="github.com/o/r1", r2="https://github.com/O/r1.git/", i1=same, i2=same))
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["fusion_basis"], "same-repo-identity-and-path")
        recs, _ = self.recs(self.two("src/a.py", "src/./a.py", r1="github.com/o/r1", r2="git@github.com:o/r2.git"))
        self.assertEqual(len(recs), 2)
        recs, _ = self.recs(self.two("src/a.py", "src/./a.py", r1="github.com/o/r1", r2="git@github.com:o/r1.git", i1=same, i2=same))
        self.assertEqual(len(recs), 1)

    def test_heuristic_is_opt_in_and_labelled_a_guess(self):
        recs, _ = self.recs(self.two("r1/a.py", "r2/b.py"), heuristic_fusion=True)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["fusion_basis"], "same-name-and-repo-rooted-paths-heuristic")
        txt = (SK / "SKILL.md").read_text().lower()
        self.assertIn("off by default", txt)
        self.assertIn("--heuristic-fusion", txt)

    def test_real_input_fuses_nothing_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("extract_register.py", FIX / "endpoints.jsonl", Path(d) / "o")
            reg = json.loads((Path(d) / "o" / "register-partial.json").read_text())
            vrc, vout = run("register_validate.py", Path(d) / "o" / "register-partial.json")
            crc, cout = run("register_validate.py", Path(d) / "o" / "register-declared-complete.json")
        self.assertEqual(rc, 0)
        self.assertEqual([r for r in reg["records"] if "sources" in r], [])
        self.assertEqual(vrc, 0, vout[-300:])
        self.assertEqual(crc, 1)
        self.assertIn("REFUSED", cout)


if __name__ == "__main__":
    unittest.main()
