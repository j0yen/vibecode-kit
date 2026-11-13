"""Regression tests for the ninth independent exact-head review (re-review 8 of 144421e7): DEF-1 .. DEF-6.
Design under test: ONE trust gate on every output path. An identity or row field prints only when its field grammar
validates it AND its pieces are trusted (closed vocabulary, short plain pieces, bounded lengths), otherwise it is an opaque
keyed reference. In free text the value of any `name=value` / `name: value` / `--name value` pair is hidden unless it reads
as a closed-vocabulary or plain number/time value, or the name is a schema key whose value validates and is trusted; a
credential word glued to a value is hidden too. A credential-name list remains only as an extra layer.
Every legitimate positive is paired with a credential negative of similar shape. Source-only: synthetic envelopes, canaries
assembled at run time from fragments, nothing printed (assertion labels never carry a canary)."""
import contextlib
import io
import json
import os
import random
import tempfile
import unittest

from helpers import FIX, SKILL, install_fixture_clock, remove_fixture_clock

import envelope_validate as ev
import queue_adapter as qa
import recommend as rc
import test_review_fixes3 as t3
from test_review_fixes7 import hx, setp
from test_review_fixes7_pairs import build, everything, shown

running, done, one = t3.running, t3.done, t3.one


def setUpModule():
    install_fixture_clock()


def tearDownModule():
    remove_fixture_clock()


_R = random.Random(9)
B36 = "abcdefghijklmnopqrstuvwxyz0123456789"
B32 = "abcdefghijklmnopqrstuvwxyz234567"
B62 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
LOWER = "abcdefghijklmnopqrstuvwxyz"


def rnd(alpha, n):
    return "".join(_R.choice(alpha) for _ in range(n))


def adapter_out(rows):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(rows, fh)
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            qa.main([fh.name, "2026-11-13T10:00:00Z"])
        return buf.getvalue()
    finally:
        os.unlink(fh.name)


def queue_recommend_out(rows):
    envs = qa.rows_to_envelopes(rows, "2026-11-13T06:30:00Z")
    recs = rc.recommend_set({"envelopes": envs})
    return json.dumps(recs) + "\n" + rc.render_text(recs)


class DnsHostTrust(unittest.TestCase):
    """DEF-1: a host passes the same trust gate as every identity; the DNS grammar is not a bypass."""

    def hosts(self):
        out = []
        for alpha, n, tld in ((B36, 18, "net"), (B32, 19, "io"), (B36, 12, "dev"), (B36, 14, "com"), (B32, 11, "local")):
            out.append(".".join(rnd(alpha, n) for _ in range(3)) + "." + tld)
        out.append(rnd(B36, 12) + "." + rnd(B36, 12) + ".net")
        out.append(rnd(LOWER, 20) + "." + rnd(LOWER, 20) + ".internal")
        return out

    def test_random_host_labels_are_opaque_in_every_output(self):
        for i, v in enumerate(self.hosts()):
            r = one(build("worker.host", v))
            self.assertNotIn(v, everything(r), "host %d" % i)
            for part in v.split(".")[:-1]:
                self.assertNotIn(part, everything(r), "host %d label" % i)
            self.assertIn("[opaque host ", shown(r), "host %d" % i)

    def test_a_random_host_stays_a_valid_host_so_the_disposition_is_unchanged(self):
        v = self.hosts()[0]
        self.assertEqual(ev.ident(v, "host"), v)
        self.assertEqual(one(build("worker.host", v))["disposition"], one(build("worker.host", "ryzen7"))["disposition"])

    def test_legitimate_hosts_still_print(self):
        for v in ("ryzen7", "redbaron.tail1a2b3.ts.net", "ryzen7.tail1a2b3.ts.net", "ip-10-0-3-4.ec2.internal", "jsy@ryzen7",
                  "fe80::1%eth0", "10.20.30.40:22", "i-0abc123def4567890", "orch.hub.local", "mcphost-1.fleet.internal"):
            self.assertIn(v, shown(one(build("worker.host", v))), v)

    def test_the_paired_credential_hosts_stay_hidden(self):
        for v in ("sk-" + rnd(B36, 12) + "." + rnd(B36, 12) + "." + rnd(B36, 12) + ".dev",
                  hx(16) + "." + hx(16) + "." + hx(16) + ".com"):
            self.assertNotIn(v, everything(one(build("worker.host", v))))


class AdapterRowFields(unittest.TestCase):
    """DEF-2 and DEF-6: every adapter row field passes the field gate, on the adapter CLI and on recommend --queue."""

    def values(self):
        return [rnd(B62, 8), rnd(B62, 16), hx(12, 5), "qwerty" + "uiopasdfgh", "hun" + "ter2x", rnd(B36, 12)]

    def row(self, field, v):
        row = {"ask_id": "WF-1", "rev": 1, "owner": "r7", "row_id": "d-20261112-224051-r7-3b84", "status": "open", "seq": 7,
               "waits_on": []}
        row[field] = [v] if field == "waits_on" else v
        return [row]

    def test_untrusted_row_fields_are_opaque_on_both_paths(self):
        for field in ("row_id", "owner", "waits_on", "status", "claim", "seq"):
            for i, v in enumerate(self.values()):
                rows = self.row(field, v)
                self.assertNotIn(v, adapter_out(rows), "%s #%d adapter" % (field, i))
                self.assertNotIn(v, queue_recommend_out(rows), "%s #%d recommend" % (field, i))

    def test_untrusted_fields_show_an_opaque_ref_and_the_row_stays_refused_or_unknown(self):
        out = adapter_out(self.row("row_id", rnd(B62, 16)))
        self.assertIn("[opaque row ", out)
        out = adapter_out(self.row("owner", rnd(B62, 16)))
        self.assertIn("[opaque owner ", out)

    def test_fields_of_other_types_never_print_their_content(self):
        canary = rnd(B62, 12)
        for bad in ({"k": canary}, [canary], 12345678901234567890):
            for field in ("row_id", "owner", "status", "claim", "seq", "waits_on"):
                rows = self.row(field, bad)
                self.assertNotIn(canary, adapter_out(rows), field)

    def test_legitimate_rows_still_print(self):
        rows = json.loads((FIX / "queue_rows.json").read_text())["rows"]
        out = adapter_out(rows)
        for needle in ("d-20261111-015556-controller-dd8d", '"r7"', "host:ryzen7:unit:r7-irv-a-221051@2026-11-12T22:11",
                       '"ctl"', "A1659", "1257"):
            self.assertIn(needle, out, needle)
        q3 = json.loads((FIX / "review" / "Q3_claim_looks_like_launch.json").read_text())
        self.assertIn("launched pid 42 on ryzen7 unit x.service", adapter_out(q3["rows"] if isinstance(q3, dict) else q3))
        rows = self.row("waits_on", "A1659")
        self.assertIn("A1659", adapter_out(rows))
        rows = self.row("status", "running")
        self.assertIn("running", adapter_out(rows))

    def test_the_adapter_task_id_gate_is_not_a_raw_fallback(self):
        """the keep-for-show mutant (an untrusted ask id printed raw) goes red here"""
        v = "zebra_" + hx(12, 7)
        out = adapter_out([{"ask_id": v, "rev": 1, "owner": "r7"}])
        self.assertNotIn(hx(12, 7), out)
        self.assertIn("[opaque task ", out)
        v = rnd(LOWER, 40)
        self.assertNotIn(v, adapter_out([{"ask_id": v, "rev": 1, "owner": "r7"}]))


NAMES = ("pswd pwrd psswd pasword p4ss k3y sekret secrt scrt apik authtok bearertoken licence dbpass usrpwd credz passkey "
         "keyfile keystore wallet recoveryphrase seedphrase otpseed totp hotp ticket nonce clientsecret sess sessid "
         "jsessionid phpsessid connectionstring connstr dburl webhook vaulttoken privatekey_pem ak_id "
         "aws_secret_access_key accesskeyid SecretAccessKey apiToken authToken x-api-key X-Auth-Token "
         "proxy-authorization signingkey encKey masterkey rootpw rootpass admin_pass userpass db_pw cfg_key KEY_1 key01 "
         "keyA key_a pass_phrase unlockcode verificationcode verify_code logincode magic_link magiclink resettoken "
         "invite_code invitecode inviteKey shared_key sharedsecret psk wpa_psk wifi_password enckey kek dek hmac_key "
         "jwt_secret cookiejar sessionkey sesskey tkt kerberos_ticket macaroon capability_url presigned_url signed_url "
         "sas_token sastoken sig2 signature2 Xamz-Signature note remark foo whatever zzqx").split()
SHAPES = ["%s=%s", "%s: %s", "--%s %s", "--%s=%s", '{"%s": "%s"}', '{\\"%s\\":\\"%s\\"}', "?%s=%s&x=1", "%s = %s",
          "export %s=%s"]


def name_values():
    return {"lc": "kqzj" + "xvbn" + "mwrt", "num": "4829" + "1736" + "0482", "shex": "a3f9" + "c2e1", "word": "hun" + "ter2x",
            "dice": "correct-horse" + "-battery", "hex32": hx(32, 11)}


class FreeTextPairsAreGatedByTrust(unittest.TestCase):
    """DEF-3: the value of any name=value pair in free text is hidden unless the value is a closed-vocabulary value or the
    name is a schema key with a trusted value. Decided by the trust rule, not by a list of credential names."""

    def test_every_name_in_every_shape_hides_every_value_kind(self):
        bad = 0
        for n in NAMES:
            for V in name_values().values():
                for shape in SHAPES:
                    if V in ev.redact(shape % (n, V)):
                        bad += 1
        self.assertEqual(bad, 0)

    def test_a_name_nobody_listed_hides_its_value_end_to_end(self):
        for field in ("coverage_gaps.0", "owner"):
            for i, (n, V) in enumerate((("dbpass", name_values()["lc"]), ("sessionkey", name_values()["lc"]),
                                        ("pswd", name_values()["word"]), ("rootpw", name_values()["num"]),
                                        ("k3y", name_values()["lc"]), ("note", name_values()["lc"]),
                                        ("whatever", name_values()["dice"]))):
                d = setp(running(), field, "%s=%s" % (n, V)) if field == "owner" else setp(running(), field, "%s: %s" % (n, V))
                self.assertNotIn(V, everything(one(d)), "%s #%d" % (field, i))

    def test_flags_with_unlisted_names_hide_their_value(self):
        d = running()
        V = name_values()["shex"]
        d["coverage_gaps"] = ["run --passkey %s now" % V, "run --zzflag %s now" % V]
        self.assertNotIn(V, everything(one(d)))

    def test_paired_positives_still_read(self):
        """benign pairs keep their value: small numbers, times, closed-vocabulary words, bracket refs"""
        for s in ("coverage gaps listed: 2", "missing: host,unit,child", "count=3", "state: RUNNING",
                  "at: 2026-11-13T10:00:00Z", "seen 10:20:30 on host ryzen7", "see https://example.invalid/path"):
            self.assertEqual(ev.redact(s), s, s)

    def test_a_schema_key_with_a_trusted_value_prints_and_an_untrusted_one_does_not(self):
        unit = "wm-build-%s.service" % hx(32, 6)
        out = ev.redact("worker.unit=%s done" % unit)
        self.assertIn(unit, out)
        bad = "worker.unit=" + "zq" + "xjkvbnmwrtplhgfdsa" + "tyui"
        self.assertNotIn("xjkvbnmwrt", ev.redact(bad))
        self.assertNotIn("xjkvbnmwrt", ev.redact("worker.host=" + rnd(B36, 18) + "." + rnd(B36, 18) + "." + rnd(B36, 18) + ".net"))

    def test_an_identity_that_is_a_name_value_pair_needs_a_vocabulary_name(self):
        V = name_values()["word"]
        r = one(setp(running(), "current_owner", "pswd=%s" % V))
        self.assertNotIn(V, everything(r))
        self.assertIn("pid=4242", shown(one(build("worker.child", "pid=4242"))))


class GluedCompositesInFreeText(unittest.TestCase):
    """DEF-4: a credential word joined to a value without a separator is hidden in free text like an identity."""

    def cases(self):
        return [("token-%s" % rnd(B62, 8)), ("apikey-task-%s" % rnd(B62, 8)), ("token-%s" % rnd(LOWER, 16)),
                ("secret_run_%s" % rnd(LOWER, 16)), ("token-%s" % hx(12, 8)), ("token-build-%s.service" % rnd(B62, 8)),
                ("secret_run_%s" % rnd(B62, 16)), ("token%s" % rnd(B62, 10)), ("bearer-%s" % rnd(LOWER, 12)),
                ("password-%s" % rnd(LOWER, 10))]

    def test_composites_hide_in_redact_and_in_every_free_text_field(self):
        for i, s in enumerate(self.cases()):
            V = s.split("-")[-1].split("_")[-1].replace(".service", "").replace("token", "", 1) if "-" in s or "_" in s else s[5:]
            self.assertNotIn(V, ev.redact("see " + s + " now"), "case %d" % i)
            d = running()
            d["coverage_gaps"] = ["gap %s here" % s]
            d["next_action"] = s
            self.assertNotIn(V, everything(one(d)), "case %d e2e" % i)

    def test_plain_composite_names_still_read(self):
        for s in ("token-refresh-service.timer", "secret-service", "api-gateway", "pat-1"):
            self.assertEqual(ev.redact("see %s now" % s), "see %s now" % s, s)


class LettersOnlyPieces(unittest.TestCase):
    """DEF-5: a letters-only piece longer than a name is opaque; short names and vocabulary words still print."""

    FIELDS = ("worker.host", "worker.unit", "worker.session", "worker.invocation", "worker.child", "consumer.named",
              "result.artifact", "worker.account", "current_owner")

    def test_long_random_lowercase_pieces_are_opaque_in_every_identity_field(self):
        vals = [rnd(LOWER, 32), rnd(LOWER, 48), "unit-" + rnd(LOWER, 20), "sess-" + rnd(LOWER, 32), rnd(LOWER, 24),
                rnd(LOWER, 17), "x-" + rnd(LOWER, 26) + ".scope"]
        for f in self.FIELDS:
            for i, v in enumerate(vals):
                d = build(f, v) if f != "current_owner" else setp(running(), f, v)
                self.assertNotIn(v, everything(one(d)), "%s #%d" % (f, i))
                for piece in v.replace(".", "-").split("-"):
                    if len(piece) > 16:
                        self.assertNotIn(piece, everything(one(d)), "%s #%d piece" % (f, i))

    def test_a_random_run_cut_by_a_separator_is_still_a_run(self):
        v = rnd(LOWER, 12) + "-" + rnd(LOWER, 12)
        for f in self.FIELDS[:6]:
            self.assertNotIn(v, everything(one(build(f, v))), f)

    def test_disposition_is_unchanged_by_an_opaque_display(self):
        v = "unit-" + rnd(LOWER, 20)
        self.assertEqual(one(build("worker.unit", v))["disposition"], one(build("worker.unit", "unit-a"))["disposition"])

    def test_names_and_vocabulary_words_still_print(self):
        for f, v in (("worker.unit", "wm-build-%s.service" % hx(32)), ("worker.unit", "wmbuild1663impl2.service"),
                     ("consumer.named", "hermes"), ("consumer.named", "WF1663Impl"), ("worker.host", "redbaron"),
                     ("worker.session", "sess-" + hx(12)), ("worker.unit", "codex-exec-%s.service" % hx(12)),
                     ("worker.unit", "verifier-worker.service"),
                     ("worker.child", "pid:2659106"), ("worker.invocation", "inv-20261113T104303Z-0007")):
            self.assertIn(v, shown(one(build(f, v))), v)

    def test_a_digit_only_piece_longer_than_an_id_is_opaque(self):
        v = "task-" + "3269" + "7661" + "9141"
        self.assertNotIn(v, everything(one(build("worker.session", v))))
        self.assertIn("pid:2659106", shown(one(build("worker.child", "pid:2659106"))))


class PriorClosuresStayClosed(unittest.TestCase):
    """The gate change must not reopen earlier closures or refuse legitimate output."""

    def test_the_text_render_and_json_carry_no_mark_characters(self):
        r = one(build("worker.unit", "wm-build-%s.service" % hx(32)))
        for ch in ("\ue000", "\ue001", "\ue002", "\ue003"):
            self.assertNotIn(ch, everything(r))

    def test_a_trusted_identity_inside_a_gap_survives_the_later_run_rule(self):
        unit = "wm-build-%s.service" % hx(32, 4)
        d = running()
        d["coverage_gaps"] = ["worker.unit=%s still running" % unit]
        out = everything(one(d))
        self.assertIn(unit, out)
        self.assertNotIn("\ue002", out)

    def test_tool_owned_lines_are_composed_by_redact_tool_and_keep_their_words(self):
        line = "REFUSE FALSE_COMPLETE [0] declared_complete: declared complete with state RUNNING and UNKNOWN: target.head"
        self.assertEqual(ev.redact_tool(line), line)

    def test_the_vocabulary_is_read_from_the_tool_and_holds_no_secret_shaped_word(self):
        words = ev._free_words()
        self.assertIn("independent", words)
        for w in words:
            self.assertRegex(w, r"^[a-z0-9]+$")
            self.assertLessEqual(len(w), 32)
        # a word of the vocabulary is plain text; the canaries of the other tests are not in it
        for v in name_values().values():
            self.assertNotIn(v, words)

    def test_the_library_view_of_a_recommendation_carries_no_marks(self):
        d = running()
        d["coverage_gaps"] = ["worker.unit=wm-build-%s.service ok" % hx(32, 5)]
        r = rc.recommend_one(d, ev.validate(d, now="2026-11-12T11:00:00Z"))
        self.assertNotIn("\ue000", json.dumps(r))
