"""Regression tests for the seventh independent exact-head review (re-review 6 of 17ca50a7): DEF-A, DEF-B, DEF-C,
DEF-D, DEF-E, DEF-F, DEF-G, DEF-H. Each class closes its defect as a class.
Design under test: field-aware validated identities and opaque untrusted refs. An identity field prints only when its own
grammar validates it and nothing marks it as a credential; every other value of an identity field, and every value a
mismatch finding would echo, is an opaque keyed reference (never the raw value). Every identity positive is paired with
a credential negative of similar shape. Source-only: synthetic envelopes; clocks are injected; canaries are assembled
at run time from fragments and never printed."""
import copy
import json
import random
import time
import unittest

from helpers import FIXTURE_NOW, SKILL, codes

import envelope_validate as ev
import queue_adapter as qa
import recommend as rc
import test_review_fixes3 as t3

running, done, one, cli, rec = t3.running, t3.done, t3.one, t3.cli, t3.rec
VALIDATE = str(SKILL / "scripts" / "envelope_validate.py")

_RND = random.Random(1663)


def hx(n, seed=3):
    return "".join("0123456789abcdef"[(i * 5 + seed) % 16] for i in range(n))


def uuid(seed=7):
    h = hx(32, seed)
    return "%s-%s-%s-%s-%s" % (h[:8], h[8:12], h[12:16], h[16:20], h[20:])


def b62(n):
    alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(_RND.choice(alpha) for _ in range(n))


def short(seed=2):
    """an 8-character mixed canary no run rule would hide"""
    alpha = "QzXkLmPq9R3vWb7"
    return "".join(alpha[(i * 5 + seed) % len(alpha)] for i in range(8))


def N(*parts):
    """a credential word assembled at run time"""
    return "".join(parts)


NAMES = [N("tok", "en"), N("pass", "word"), N("api_", "key"), N("sec", "ret"), N("client_", "secret")]


def setp(d, path, v):
    d = copy.deepcopy(d)
    t = d
    ps = path.split(".")
    for p in ps[:-1]:
        t = t[int(p)] if isinstance(t, list) else t[p]
    if isinstance(t, list):
        t[int(ps[-1])] = v
    else:
        t[ps[-1]] = v
    return d


def everything(r):
    """every output path of one recommendation: JSON and text"""
    return json.dumps(r) + "\n" + rc.render_text([r])


def uesc(s):
    return "".join("\\u%04x" % ord(c) for c in s)


class DefA_JsonEscapedPairs(unittest.TestCase):
    def forms(self, name, v):
        inner = json.dumps({name: v})
        return {
            "escaped-compact": '{\\"%s\\":\\"%s\\"}' % (name, v),
            "escaped-spaced": '{\\"%s\\": \\"%s\\"}' % (name, v),
            "escaped-assign": '%s=\\"%s\\"' % (name, v),
            "double-escaped": '{\\\\\\"%s\\\\\\":\\\\\\"%s\\\\\\"}' % (name, v),
            "u-escaped-name": '{"%s": "%s"}' % (uesc(name[:2]) + name[2:], v),
            "u-escaped-value": '{"%s": "%s"}' % (name, uesc(v)),
            "u-escaped-both": '{\\"%s\\":\\"%s\\"}' % (uesc(name), uesc(v)),
            "nested-string-json": json.dumps({"payload": inner}),
            "nested-twice": json.dumps({"outer": json.dumps({"payload": inner})}),
            "nested-in-text": "note " + json.dumps(inner) + " end",
        }

    def test_every_escape_form_is_hidden_for_every_credential_name(self):
        for name in NAMES:
            for v in (short(), short(5) + "x", hx(10), "hunter2"):
                for label, text in self.forms(name, v).items():
                    out = ev.redact(text)
                    self.assertNotIn(v, out, (name, label))

    def test_escape_forms_are_hidden_end_to_end(self):
        v = short(4)
        for label, text in self.forms(NAMES[0], v).items():
            for field in ("coverage_gaps.0", "evidence.0.ref", "next_action"):
                d = setp(running(), field, text) if field != "coverage_gaps.0" else dict(running(), coverage_gaps=[text])
                self.assertNotIn(v, everything(one(d)), (label, field))
        # the validator CLI line path
        d = dict(running(), coverage_gaps=[self.forms(NAMES[1], v)["escaped-compact"]])
        d["declared_complete"] = True
        out = ev.redact("%s" % [f["message"] for f in ev.validate(d, now=FIXTURE_NOW)])
        self.assertNotIn(v, out)

    def test_escaped_text_without_a_credential_is_unchanged(self):
        for text in ('{\\"unit\\":\\"wm-build-1\\"}', 'path C:\\\\temp\\\\x', 'say \\"hello\\" twice', '{"a": "b\\nc"}',
                     "tmux pane %12 and fe80::1%eth0"):
            self.assertEqual(ev.redact(text), text, text)

    def test_unescaped_forms_stay_hidden(self):
        v = short(6)
        for name in NAMES:
            for text in ('{"%s": "%s"}' % (name, v), "%s=%s" % (name, v), "%s: %s" % (name, v)):
                self.assertNotIn(v, ev.redact(text))


class DefB_HeadNeverLiftedFromFreeText(unittest.TestCase):
    def hexes(self):
        return [("password=" + hx(10), hx(10)), ("api_key: " + hx(18), hx(18)), ("secret=" + hx(40, 4), hx(40, 4)),
                ("sig=" + hx(64, 9), hx(64, 9)), ("Authorization: Bearer " + hx(40, 6), hx(40, 6)),
                ("--token " + hx(20, 8), hx(20, 8)), ('{"secret": "' + hx(40, 11) + '"}', hx(40, 11)),
                ('{\\"password\\":\\"' + hx(12, 2) + '\\"}', hx(12, 2))]

    def test_credential_named_hex_is_never_a_head_and_never_printed(self):
        for ref, secret in self.hexes():
            d = setp(running(), "evidence.0.ref", ref)
            findings = ev.validate(d, now=FIXTURE_NOW)
            self.assertNotIn("WRONG_TASK", codes(findings), ref)
            self.assertNotIn(secret, json.dumps(findings), ref)
            r = one(d)
            self.assertNotIn(secret, everything(r), ref)

    def test_a_real_head_mismatch_reports_field_names_and_opaque_refs(self):
        other = hx(40, 5)
        d = setp(running(), "evidence.0.ref", "read at head " + other)
        r = one(d)
        self.assertTrue(r["refused"])
        text = " ".join(r["reasons"])
        self.assertIn("WRONG_TASK evidence[0].head", text)
        self.assertIn("target.head", text)
        self.assertIn("[opaque head ", text)
        self.assertNotIn(other, everything(r))
        self.assertNotIn(d["target"]["head"], everything(r))

    def test_matching_head_in_ref_is_no_finding(self):
        d = running()
        d = setp(d, "evidence.0.ref", "read at head " + d["target"]["head"])
        self.assertNotIn("WRONG_TASK", codes(ev.validate(d, now=FIXTURE_NOW)))

    def test_head_field_mismatch_is_opaque_too(self):
        other = short(3)
        d = running()
        d["evidence"][0]["head"] = other
        r = one(d)
        self.assertIn("WRONG_TASK", r["reason_codes"])
        self.assertNotIn(other, everything(r))


# (field, identity positive, credential negative of similar shape)
def _pairs():
    H, H40, U = hx(32), hx(40, 4), uuid()
    return [
        ("worker.host", "jsy@ryzen7", "bob:" + short() + "@ryzen7"),
        ("worker.host", "ryzen7.tail" + hx(5) + ".ts.net", "admin:" + H + "@10.0.0.5"),
        ("worker.host", "10.0.0.5", H40 + "@ryzen7"),
        ("worker.unit", "wm-build-" + H + ".service", "token-" + H + ".service"),
        ("worker.unit", "coder@" + U + ".service", "secret@" + U + ".service"),
        ("worker.unit", "wm-build-" + hx(12) + ".service", N("pass", "word") + "-" + hx(12) + ".service"),
        ("worker.child", "run-r" + H + ".scope", "bearer-" + H + ".scope"),
        ("worker.session", U, N("Bear", "er-") + H),
        ("worker.session", "sess-" + U, N("pa", "t_") + H),
        ("worker.session", H, N("api", "key") + H),
        ("worker.invocation", "inv-" + H, N("pa", "t_") + H),
        ("worker.invocation", "inv-20261113T104303Z-0007", N("tok", "en") + "-" + H40),
    ]


def _printed_for(field, value):
    d = setp(running(), field, value)
    r = one(d)
    return r, everything(r), d


class DefD_CredentialShapedIdentitiesAreOpaque(unittest.TestCase):
    def test_pairs_positive_prints_negative_is_not_printed(self):
        for field, pos, neg in _pairs():
            r, out, _ = _printed_for(field, pos)
            self.assertIn(pos, out, (field, "positive must print"))
            self.assertEqual(r["disposition"], "reuse-active-worker", (field, pos))
            r2, out2, _ = _printed_for(field, neg)
            for piece in (neg, neg.split("@")[0], neg.split(":")[-1].split("@")[0]):
                if len(piece) >= 8:
                    self.assertNotIn(piece, out2, (field, neg))

    def test_untrusted_identity_that_is_not_required_prints_an_opaque_ref(self):
        for field, label in (("worker.session", "sess-id"), ("worker.invocation", "invocation"), ("worker.account", "account")):
            neg = N("Bear", "er-") + hx(32)
            r, out, _ = _printed_for(field, neg)
            self.assertNotIn(neg, out)
            self.assertTrue(any(l.startswith("worker.%s=[opaque %s " % (label, label)) for l in r["evidence_used"]),
                            r["evidence_used"])

    def test_required_identity_that_is_credential_shaped_is_unknown_not_reused(self):
        for field in ("worker.host", "worker.unit", "worker.child"):
            neg = "token-" + hx(32) if field != "worker.host" else "admin:" + hx(32) + "@10.0.0.5"
            r, out, _ = _printed_for(field, neg)
            self.assertNotEqual(r["disposition"], "reuse-active-worker", field)
            self.assertNotIn(hx(32), out, field)

    def test_ident_rejects_credential_grammar(self):
        H = hx(32)
        for v in ("admin:" + H + "@10.0.0.5", hx(40) + "@ryzen7", "bob:" + short() + "@h", "token-" + H, "secret@" + uuid(),
                  N("Bear", "er-") + H, N("pa", "t_") + H, N("pass", "word") + "-" + short(), "tok" + "en" + H[:12]):
            self.assertIsNone(ev.ident(v), v)
        for v in ("ryzen7", "jsy@ryzen7", "r7@ryzen7", "wm-build@x.service", "tmux:%12", "fe80::1%eth0", "10.0.0.5:22",
                  "token-service", "tokenizer-1", "pid:77"):
            self.assertEqual(ev.ident(v), v, v)

    def test_path_ident_rejects_credential_named_directory_with_random_piece(self):
        H = hx(32)
        self.assertIsNone(ev.path_ident("/retained/" + N("sec", "ret") + "/" + H + ".json"))
        self.assertEqual(ev.path_ident("/retained/WF-1/result-" + H + ".json"), "/retained/WF-1/result-" + H + ".json")

    def test_artifact_and_evidence_ref_pairs(self):
        H, H40 = hx(32), hx(40, 4)
        d = done()
        d["result"]["artifact"] = "/retained/" + N("sec", "ret") + "/" + H + ".json"
        self.assertNotIn(H, everything(one(d)))
        d["result"]["artifact"] = "/retained/WF-1/result-" + H + ".json"
        self.assertIn(H, everything(one(d)))
        d = setp(running(), "evidence.0.ref", N("tok", "en") + "=" + H40)
        self.assertNotIn(H40, everything(one(d)))
        d = setp(running(), "evidence.0.ref", "journal-" + H)
        self.assertIn("journal-" + H, everything(one(d)))

    def test_heroku_shape_is_hidden_in_free_text(self):
        v = "HR" + "KU-" + uuid()
        self.assertNotIn(uuid(), ev.redact("note " + v + " end"))

    def test_userinfo_in_host_is_not_a_host(self):
        for v in ("bob:pw@host", "a:b:c@host"):
            self.assertIsNone(ev.ident(v, "host"), v)


class DefC_MismatchEchoesAreOpaque(unittest.TestCase):
    def test_no_mismatch_message_carries_a_raw_value(self):
        v = short(1)
        cases = [("evidence.0.task_id", v), ("evidence.0.repo", v), ("evidence.0.branch", v)]
        for field, val in cases:
            d = setp(running(), field, val)
            r = one(d)
            self.assertTrue(r["refused"], field)
            self.assertNotIn(val, everything(r), field)
            self.assertTrue(any("[opaque " in x for x in r["reasons"]), (field, r["reasons"]))
            self.assertIn(field.replace(".0.", "[0]."), " ".join(r["reasons"]))
        d = done()
        d["result"]["task_id"] = v
        r = one(d)
        self.assertNotIn(v, everything(r))
        self.assertIn("WRONG_TASK result.task_id", " ".join(r["reasons"]))

    def test_legitimate_task_id_in_a_mismatch_is_also_opaque(self):
        d = setp(running(), "evidence.0.task_id", "WF-20261113T104303Z-0007")
        self.assertNotIn("WF-20261113T104303Z-0007", everything(one(d)))

    def test_set_findings_do_not_echo_raw_values(self):
        v = short(2)
        a, b = running(v, "synthetic/r", "syn/b"), running(v, "synthetic/r", "syn/b")
        res = ev.validate_set({"envelopes": [a, b]}, now=FIXTURE_NOW)
        msgs = " ".join(f["message"] for f in res["set_findings"])
        self.assertNotIn(v, msgs)
        c = running(short(3), "synthetic/r", "syn/b")
        res = ev.validate_set({"envelopes": [a, c]}, now=FIXTURE_NOW)
        msgs = " ".join(f["message"] for f in res["set_findings"])
        self.assertNotIn("synthetic/r", msgs)
        self.assertIn("CONFLICTING_TARGET", " ".join(f["code"] for f in res["set_findings"]))
        res = ev.validate_set({"envelopes": [a], "declared_total": v}, now=FIXTURE_NOW)
        self.assertNotIn(v, " ".join(f["message"] for f in res["set_findings"]))

    def test_unknown_key_names_are_not_echoed_raw(self):
        key = N("tok", "en") + "_" + hx(20)
        d = running()
        d[key] = 1
        d["worker"][short(4) + b62(12)] = 1
        out = json.dumps(ev.validate(d, now=FIXTURE_NOW))
        self.assertNotIn(hx(20), out)
        self.assertNotIn(short(4), out)
        self.assertIn("UNKNOWN_KEY", out)
        ok = running()
        ok["extra_note"] = 1
        # re-review 7 DEF-3: the schema is known, so an unknown key is an opaque ref even when it is an ordinary word
        out_ok = json.dumps(ev.validate(ok, now=FIXTURE_NOW))
        self.assertNotIn("extra_note", out_ok)
        self.assertIn("[opaque key ", out_ok)

    def test_duplicate_key_path_does_not_echo_a_random_key(self):
        k = b62(24)
        txt = '{"a": {"%s": 1, "%s": 2}}' % (k, k)
        obj = ev.load_json_text(txt)
        out = json.dumps(ev.validate(obj, now=FIXTURE_NOW))
        self.assertNotIn(k, out)
        self.assertIn("DUPLICATE_KEY", out)

    def test_cli_validator_lines_carry_no_raw_values(self):
        v = short(6)
        d = setp(running(), "evidence.0.task_id", v)
        p = t3.tmp_json(d)
        out = cli(VALIDATE, "--now", FIXTURE_NOW, p)
        self.assertNotIn(v, out.stdout)
        self.assertIn("WRONG_TASK", out.stdout)


class DefF_TaskAndOwnerIdsPrint(unittest.TestCase):
    IDS = ["WF-20261113T104303Z-0007", "task-" + hx(32), "01HZX3K9Q2M7V5N8R4T6W1Y0AB", "A-1663", "task-" + uuid(), "wm-asks:A-1663"]

    def test_task_id_prints_in_record_and_evidence_line(self):
        for tid in self.IDS:
            d = running(tid)
            r = one(d)
            self.assertEqual(r["task_id"], tid)
            self.assertEqual(r["disposition"], "reuse-active-worker", tid)
            self.assertTrue(any(tid in l for l in r["evidence_used"]), tid)
            self.assertIn(tid, rc.render_text([r]))

    def test_task_id_in_a_refused_record_prints_when_valid(self):
        d = running("task-" + hx(32))
        d["evidence"][0]["revision"] = 99
        r = one(d)
        self.assertTrue(r["refused"])
        self.assertEqual(r["task_id"], "task-" + hx(32))

    def test_owner_account_branch_and_ref_ids_print(self):
        d = running()
        d["current_owner"] = "r7-" + hx(12)
        d["worker"]["account"] = "acct-" + uuid()
        d["target"]["branch"] = "r7/feat-" + hx(32)
        d["evidence"][0]["ref"] = "journal-" + hx(32)
        r = one(d)
        used = "\n".join(r["evidence_used"])
        for v in ("owner=r7-" + hx(12), "worker.account=acct-" + uuid(), "@r7/feat-" + hx(32), "evidence journal-" + hx(32)):
            self.assertIn(v, used)

    def test_credential_task_id_pairs_are_opaque(self):
        for bad in (N("tok", "en") + "=" + hx(32), N("Bear", "er-") + hx(32), "token-" + hx(32), "A" + b62(30)):
            d = running(bad)
            r = one(d)
            self.assertNotIn(hx(32), everything(r), bad)
            self.assertNotIn(bad, everything(r), bad)
            self.assertTrue(r["task_id"].startswith("[opaque task ") or r["task_id"] == "[REDACTED]", r["task_id"])

    def test_adapter_ask_id_with_id_pieces_prints(self):
        rows = [{"ask_id": "task-" + hx(32), "rev": 3, "owner": "r7", "row_id": "row-1", "status": "open"},
                {"ask_id": N("tok", "en") + "=" + hx(32), "rev": 3, "owner": "r7", "row_id": "row-2", "status": "open"}]
        out = cli(str(__import__("helpers").SKILL / "scripts" / "queue_adapter.py"), t3.tmp_json(rows)).stdout
        envs = json.loads(out)["envelopes"]
        self.assertEqual(envs[0]["task_id"], "task-" + hx(32))
        self.assertEqual(envs[0]["evidence"][0]["task_id"], "task-" + hx(32))
        self.assertNotIn(hx(32) + '"', json.dumps(envs[1]))
        self.assertEqual(envs[1]["worker"]["session"], "UNKNOWN")


class DefH_OrdinaryMixedAlnumIdsAreIdentities(unittest.TestCase):
    GOOD = [("worker.unit", "wm-build-WF1663Impl.service"), ("worker.unit", "claude-r7wfr6review.service"),
            ("worker.unit", "codex-r7wfitfix2.service"), ("worker.unit", "wm-build-w1663impl-r7.service"),
            ("worker.unit", "wfr6review20261113.service"), ("worker.unit", "wmbuild1663impl2.service"),
            ("worker.child", "run-r7wfr620261113.scope"), ("worker.host", "ryzen7build20261113.local"),
            ("worker.host", "ip-10-0-1-5.us-west-2.compute.internal")]

    def test_ordinary_mixed_alnum_ids_are_reused_and_printed(self):
        for field, v in self.GOOD:
            r, out, _ = _printed_for(field, v)
            self.assertEqual(r["disposition"], "reuse-active-worker", v)
            self.assertIn(v, out, v)

    def test_random_keys_of_similar_shape_are_not_identities(self):
        rnd = random.Random(99)
        alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        accepted = 0
        trials = 600
        for i in range(trials):
            v = "".join(rnd.choice(alpha) for _ in range(rnd.randint(14, 32)))
            if ev.ident("wm-build-" + v + ".service") is not None:
                accepted += 1
        self.assertLessEqual(accepted, trials // 50, accepted)
        for field in ("worker.unit", "worker.child", "worker.host"):
            v = "wm-build-" + b62(19) + ".service"
            r, out, _ = _printed_for(field, v)
            self.assertNotEqual(r["disposition"], "reuse-active-worker", field)
            self.assertNotIn(v, out)

    def test_lowercase_base36_keys_are_not_identities(self):
        rnd = random.Random(5)
        alpha = "abcdefghijklmnopqrstuvwxyz0123456789"
        accepted = sum(ev.ident("svc-" + "".join(rnd.choice(alpha) for _ in range(rnd.randint(18, 30))) + ".service") is not None
                       for _ in range(600))
        self.assertLessEqual(accepted, 600 // 20, accepted)


class DefE_UnknownIsPreserved(unittest.TestCase):
    def test_adapter_output_keeps_unknown_session(self):
        env = qa.row_to_envelope({"ask_id": "A-1663", "rev": 3, "owner": "r7", "row_id": "row-1"})
        out = ev.scrub({"envelopes": [env]})["envelopes"][0]
        self.assertEqual(out["worker"]["session"], "UNKNOWN")
        for k in ("host", "unit", "invocation", "child", "account", "model", "effort"):
            self.assertEqual(out["worker"][k], "UNKNOWN", k)
        self.assertTrue(ev.is_unknown(out["worker"]["session"]))

    def test_credential_named_key_with_a_real_value_is_still_hidden(self):
        v = short(3)
        for name in NAMES:
            self.assertEqual(ev.scrub({name: v})[name], "[REDACTED]")
            self.assertEqual(ev.scrub({name: [v, v]})[name], "[REDACTED]")
            self.assertEqual(ev.scrub({name: "unknown"})[name], "unknown")
            self.assertEqual(ev.scrub({name: {"k": v}})[name], "[REDACTED]")
        self.assertEqual(ev.scrub({N("pass", "word"): "N/A"})[N("pass", "word")], "N/A")

    def test_recommendation_keeps_unknown_fields_as_unknown(self):
        d = running()
        d["worker"]["session"] = "UNKNOWN"
        r = one(d)
        self.assertIn("worker.sess-id=UNKNOWN", r["evidence_used"])


class DefG_CommandMatchingIsLinear(unittest.TestCase):
    def timed(self, text):
        t0 = time.perf_counter()
        ev.redact(text)
        return time.perf_counter() - t0

    def test_repeated_command_words_scale_linearly(self):
        for cmd in ("mysql -u r ", "mariadb x ", "unzip a ", "7z a ", "mysqldump -u r "):
            small, big = self.timed(cmd * 3000), self.timed(cmd * 12000)
            self.assertLess(big, 3.0, (cmd, big))
            self.assertLess(big, max(small, 0.02) * 12, (cmd, small, big))

    def test_command_password_flags_still_hidden(self):
        v = short(7)
        for text in ("sshpass -p %s ssh h" % v, "mysql -u root -p%s db" % v, "mysql -u root -p %s db" % v,
                     "mysqldump -u r -p%s x" % v, "mariadb -p%s" % v, "unzip -P %s a.zip" % v, "7z a -p%s x.7z" % v,
                     "echo mysql | tr x y; mysql -u r -p%s" % v, "mysql -u r\nmysql -u s -p%s" % v):
            self.assertNotIn(v, ev.redact(text), text)
        for text in ("mysql -u root db", "ssh -p 22 host", "mkdir -p /tmp/x", "unzip a.zip", "mysql ; ls -p x"):
            self.assertEqual(ev.redact(text), text, text)

    def test_end_to_end_cost_is_bounded(self):
        d = dict(running(), coverage_gaps=["mysql -u r " * 8000])
        t0 = time.perf_counter()
        one(d)
        self.assertLess(time.perf_counter() - t0, 4.0)


class Def_ShortKeyShapedPiecesAndCompoundNames(unittest.TestCase):
    def test_short_key_shaped_piece_is_not_an_identity_but_short_names_are(self):
        self.assertIsNone(ev.ident("svc:" + short()))
        self.assertIsNone(ev.ident("wm-build-" + short(5) + ".service"))
        for v in ("svc:r7wfr6", "wm-build-WF1663.service", "pod-x7k2p", "w-8d7a81e3", "svc:a1b2c3", "job-20261113"):
            self.assertEqual(ev.ident(v), v, v)

    def test_compound_credential_names_hide_their_value(self):
        v = short(2)
        for name in ("recovery_code", "oauth_verifier", "code_verifier", "backup_codes", "sas"):
            self.assertNotIn(v, ev.redact("%s=%s" % (name, v)), name)
            self.assertNotIn(v, ev.redact('{"%s": "%s"}' % (name, v)), name)
        for text in ("code=%s" % v, "verifier: hermes", "recovery of the unit"):
            self.assertEqual(ev.redact(text), text, text)


class OpaqueRefDesign(unittest.TestCase):
    def test_opaque_is_keyed_field_scoped_and_hides_the_value(self):
        v = short(1)
        a = ev.opaque("host", v)
        self.assertEqual(a, ev.opaque("host", v))
        self.assertNotEqual(a, ev.opaque("unit", v))
        self.assertNotEqual(a, ev.opaque("host", short(2)))
        self.assertNotIn(v, a)
        self.assertTrue(a.startswith("[opaque host ") and a.endswith("]"))
        self.assertEqual(ev.redact(a), a)
        self.assertEqual(ev.scrub({"x": a})["x"], a)

    def test_show_validated_unknown_and_untrusted(self):
        self.assertEqual(ev.scrub({"x": ev.show("unit", "wm-build-1.service")})["x"], "wm-build-1.service")
        self.assertEqual(ev.scrub({"x": ev.show("unit", "UNKNOWN")})["x"], "UNKNOWN")
        bad = "token-" + hx(32)
        self.assertEqual(ev.scrub({"x": ev.show("unit", bad)})["x"], ev.opaque("unit", bad))
        self.assertEqual(ev.show("unit", 7), 7)

    def test_recommend_one_returns_no_private_marks(self):
        d = running()
        r = rc.recommend_one(d, [])
        text = json.dumps(r, ensure_ascii=False)
        self.assertFalse(any(0xE000 <= ord(c) <= 0xE003 for c in text))

    def test_forged_opaque_text_is_just_text(self):
        v = short(2)
        d = running()
        d["worker"]["session"] = "[opaque sess-id 00000000]"
        r = one(d)
        self.assertNotEqual(r["disposition"], "")
        self.assertNotIn(v, everything(r))


if __name__ == "__main__":
    unittest.main()
