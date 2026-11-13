"""Regression tests for the eighth independent exact-head review (re-review 7 of ce7acc48): DEF-1, DEF-2, DEF-3, DEF-4.
Design under test (field-aware validated identities, opaque untrusted refs, no expanding denylist):
  * an identity prints only when its field grammar validates it AND its pieces are trusted (a closed vocabulary of
    name words; a random-looking piece is allowed only beside those words), otherwise it is an opaque keyed reference;
  * a key name outside the schema is always an opaque reference;
  * free text keeps its redaction layers, and a value of any `name=value` pair that reads as a key (a random mixed
    alphanumeric) is hidden whatever the name is.
Every legitimate positive is paired with a credential negative of similar shape. Source-only: synthetic envelopes,
canaries assembled at run time from fragments, nothing printed."""
import json
import os
import subprocess
import sys
import unittest

from helpers import FIXTURE_NOW, SKILL, codes

import envelope_validate as ev
import queue_adapter as qa
import recommend as rc
import test_review_fixes3 as t3
from test_review_fixes7 import N, hx, setp, short, uuid
from test_review_fixes7_pairs import build, everything, shown

running, done, one = t3.running, t3.done, t3.one
SCRIPTS = str(SKILL / "scripts")

# credential names with a digit or letters glued on, in every position (DEF-1)
GLUED = ["key9", "key2", "pw9", "api9", "pat9", "sk9", "tok9", "auth9", "pwd9", "pass9", "passwd9", "cred9", "oauth9",
         "mykey3", "apikey9", "privkey9", "tokn", "secretkey1", "sshkey9", "accesskey9", "KEY9", "Key9", "apikeyv2",
         "sec9", "jwt9", "otp9", "sig9", "cookie9", "bearer9", "ak9", "salt9", "pin9", "pass_word9", "key_9"]
SHAPES = ["%s=%s", "%s: %s", "--%s %s", "--%s=%s", '{"%s": "%s"}', '{\\"%s\\":\\"%s\\"}', "export %s=%s run"]

# credential-word families joined to a hex piece in an identity field (DEF-2)
FAMILIES = ["sk", "key", "keys", "creds", "cred", "jwt", "auth", "private", "cookie", "otp", "sig", "kms", "vault", "ssh",
            "login", "webhook", "seed", "mnemonic", "tok", "k", "pw9", "api", "oauth", "signing", "wallet", "pass9",
            "token", "secret", "password", "credential", "pat", "pw", "bearer", "apikey", "privkey", "x"]
TEMPLATES = ["%s/{H}/r.json", "%s-{H}.service", "%s_{H}", "%s{H}", "/retained/%s/{H}.json", "%s={H}", "%s@{H}",
             "x-%s-{H}", "%s-{H}-svc", "%s:{H}"]
ID_FIELDS = ["worker.host", "worker.unit", "worker.child", "worker.session", "worker.invocation", "consumer.named",
             "result.artifact", "result.event", "evidence.0.ref"]


def keyish(i=0):
    """a key-shaped canary (mixed letters and digits, 8 characters) assembled at run time"""
    frags = [("Zq9", "Xk3Lm"), ("Pv4", "Wm8Qz"), ("Hn7", "Tc2Rb"), ("Jd5", "Fs6Gy")]
    return "".join(frags[i % 4])


def adapter_out(rows):
    """stdout of the queue adapter CLI for these rows (in-process, same code path as main)"""
    import contextlib
    import io
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(rows, fh)
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            qa.main([fh.name, "2026-11-13T10:00:00Z"])
        return buf.getvalue()
    finally:
        os.unlink(fh.name)


def _hidden(d, needle):
    return needle not in everything(one(d))


class GluedCredentialNames(unittest.TestCase):
    """DEF-1: a short credential word with a digit or letters glued on hides its value in free text, in every shape."""

    def test_every_glued_name_hides_a_short_and_a_hex_value_in_every_shape(self):
        for V in (keyish(0), hx(32, 9), keyish(1)):
            for n in GLUED:
                for shape in SHAPES:
                    s = shape % ((n, V))
                    self.assertNotIn(V, ev.redact(s), s)

    def test_glued_names_hide_in_every_free_text_output_path(self):
        V = keyish(2)
        for n in GLUED[:12]:
            d = running()
            d["coverage_gaps"] = ["gap %s=%s now" % (n, V)]
            d["next_action"] = "run --%s %s" % (n, V)
            d["source"]["identity"] = "row %s: %s" % (n, V)
            self.assertNotIn(V, everything(one(d)), n)
            d2 = running()
            d2["current_owner"] = "%s=%s" % (n, V)
            self.assertNotIn(V, everything(one(d2)), n)

    def test_adapter_hides_glued_names_in_ids_owner_claim(self):
        V = keyish(3)
        rows = [{"ask_id": "key9=%s" % V, "rev": 1, "owner": "pw9=%s" % V, "claim": "apikey9=%s" % V}]
        out = adapter_out(rows)
        self.assertNotIn(V, out)

    def test_value_shape_layer_hides_a_key_shaped_value_under_any_name(self):
        for n in ("tokn", "zzz9", "foo", "x", "somefield"):
            V = keyish(2)
            self.assertNotIn(V, ev.redact("%s=%s" % (n, V)), n)
            self.assertNotIn(V, ev.redact("--%s %s" % (n, V)), n)

    def test_ordinary_pairs_still_print(self):
        keep = "pid=4242 rc=0 state=RUNNING exit=1 attempt=3 ticket=WF-1663 head=%s unit=wm-build.service ts=20261113T104303Z" % hx(12, 5)
        self.assertEqual(ev.redact(keep), keep)
        for s in ("count=17", "name: hermes", "note=ready", "status=ok-2", "mode=fast"):
            self.assertEqual(ev.redact(s), s)


class CredentialWordIdentities(unittest.TestCase):
    """DEF-2: an identity that holds a piece this tool has no reason to trust is opaque by default, whatever word it is."""

    def test_no_family_prints_its_hex_in_any_identity_field(self):
        H = hx(32, 11)
        for f in ID_FIELDS:
            for w in FAMILIES:
                for t in TEMPLATES:
                    v = (t % w).replace("{H}", H)
                    self.assertTrue(_hidden(build(f, v), H), (f, v))

    def test_uuid_and_long_hex_behind_unknown_words_are_opaque(self):
        U, H40 = uuid(5), hx(40, 8)
        for w in ("creds", "jwt", "cookie", "ssh", "kms", "vault", "auth", "private", "seed"):
            for f in ("worker.unit", "worker.session", "worker.invocation", "consumer.named", "result.artifact"):
                for V in (U, H40):
                    self.assertTrue(_hidden(build(f, "%s-%s" % (w, V)), V), (f, w))
                    self.assertTrue(_hidden(build(f, "%s_%s.service" % (w, V)), V), (f, w))

    def test_credential_word_glued_to_letters_or_a_long_remainder_is_opaque(self):
        L = "qwerty" + "uiopasdfgh"
        for f in ("worker.unit", "worker.host", "worker.child", "consumer.named", "result.artifact"):
            for v in ("key" + L, "tok-%s-svc" % L, "sk_" + L, "token-%s.service" % L, "pw9=" + L, "secret" + L):
                self.assertTrue(_hidden(build(f, v), L), (f, v))

    def test_adapter_and_recommend_queue_ids_hide_every_family(self):
        H = hx(32, 13)
        for w in ("sk", "key", "creds", "jwt", "auth", "private", "cookie", "tok", "pw9="):
            rows = [{"ask_id": ("%s_%s" % (w, H)) if "=" not in w else w + H, "rev": 1, "owner": "o"}]
            out = adapter_out(rows)
            self.assertNotIn(H, out, w)

    def test_legitimate_identities_beside_those_negatives_still_print(self):
        H, H12, U = hx(32, 11), hx(12, 5), uuid(5)
        for f, v in [("worker.unit", "wm-build-%s.service" % H), ("worker.unit", "coder@%s.service" % U),
                     ("worker.unit", "codex-exec-%s.service" % H12), ("worker.child", "run-r%s.scope" % H),
                     ("worker.child", "child-%s" % hx(40, 4)), ("worker.session", "sess-" + U), ("worker.session", U),
                     ("worker.invocation", "inv-%s" % H12), ("consumer.named", "verifier-%s" % H12),
                     ("result.artifact", "/retained/WF-1/result-%s.json" % H), ("result.event", "evt-%s" % H),
                     ("result.artifact", "/retained/%s/review-%s.json" % (U, H12)),
                     ("worker.host", "i-0abc123def4567890"), ("worker.session", "01hzx3k9q2m7v5n8r4t6w1y0ab"),
                     ("worker.session", "01HZX3K9Q2M7V5N8R4T6W1Y0AB"), ("worker.host", "redbaron.tail9z8y7.ts.net")]:
            self.assertIn(v, shown(one(build(f, v))), (f, v))

    def test_vocabulary_never_holds_a_credential_word(self):
        for w in ev._ID_WORDS:
            self.assertNotIn(w, ev._CRED_WORDS, w)
            self.assertFalse(ev._cred_name(w), w)


def _pairs():
    H, H12, H40, U = hx(32, 3), hx(12, 5), hx(40, 4), uuid(7)
    return [
        ("worker.unit", "wm-build-WF1663Impl.service"), ("worker.unit", "claude-r7wfr7review.service"),
        ("worker.unit", "run-r7wfr720261113.scope"), ("worker.unit", "wm-build-%s.service" % H),
        ("worker.unit", "coder@%s.service" % U), ("worker.unit", "w-WF-1663-r7-wfr7.service"),
        ("worker.unit", "codex-exec-%s.service" % H12),
        ("worker.host", "ryzen7build20261113.local"), ("worker.host", "i-0abc123def4567890"),
        ("worker.host", "redbaron.tail9z8y7.ts.net"), ("worker.host", "jsy@ryzen7"), ("worker.host", "10.20.30.40"),
        ("worker.child", "pid:4242"), ("worker.child", "run-r%s.scope" % H), ("worker.child", "child-%s" % H40),
        ("worker.session", U), ("worker.session", H), ("worker.session", "sess-" + U),
        ("worker.session", "01HZX3K9Q2M7V5N8R4T6W1Y0AB"), ("worker.session", "01hzx3k9q2m7v5n8r4t6w1y0ab"),
        ("worker.invocation", H), ("worker.invocation", "inv-20261113T104303Z-0007"), ("worker.invocation", U),
        ("consumer.named", "verifier-%s" % H12), ("consumer.named", "hermes"), ("consumer.named", "ctl-seat-2"),
        ("target.head", H40), ("target.head", H12),
        ("result.artifact", "/mnt/ssd/cargo-target/r7-wfr7-20261113/out/review.md"),
        ("result.artifact", "/retained/WF-1/result-%s.json" % H), ("result.event", "evt-%s" % H),
        ("result.artifact", "/retained/%s/review-%s.json" % (U, H12)),
        ("evidence.0.ref", "/mnt/ssd/cargo-target/r7-wfr7-20261113/out/probes.log"), ("evidence.0.ref", "unit-read"),
        ("worker.account", "acct-a"), ("worker.model", "claude-opus-5-5"),
        ("task_id", "WF-20261113T104303Z-0007"), ("task_id", "task-%s" % H), ("task_id", "WF1663Impl"),
        ("task_id", "01HZX3K9Q2M7V5N8R4T6W1Y0AB"),
    ]


def _negs(V):
    P = json.dumps
    return [("kv", "%s=%s" % (N("tok", "en"), V)), ("flag", "run --api-key %s now" % V), ("flag-eq", "run --password=%s now" % V),
            ("json-esc", '{\\"token\\":\\"%s\\"}' % V), ("u-esc", "{\\u0022token\\u0022: \\u0022%s\\u0022}" % V),
            ("string-json", P({"payload": P({"password": V})})), ("nested", P({"credentials": {"a": [{"b": [V]}]}})),
            ("userinfo", "https://svc:%s@h.example/x" % V), ("quoted", 'password="correct horse %s staple"' % V),
            ("glued", "token2=%s" % V), ("glued2", "apikey9=%s" % V), ("glued3", "secret123: %s" % V),
            ("glued4", "key9=%s" % V), ("glued5", "pw9=%s" % V), ("hdr", "Authorization: Bearer %s" % V),
            ("env", "DB_PASSWORD=%s run" % V), ("fam1", "sk_%s" % V), ("fam2", "creds/%s/r.json" % V), ("fam3", "jwt-%s" % V),
            ("fam4", "tok-%s-svc" % V)]


class IdentityPairTable(unittest.TestCase):
    """The reviewer's 40-pair table: each positive prints, and 20 credential negatives of the same value hide in the same
    field and in coverage_gaps and next_action."""

    def test_forty_pairs(self):
        pairs = _pairs()
        self.assertEqual(len(pairs), 40)
        secrets = [hx(32, 9), "".join("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"[(i * 7 + 3) % 62] for i in range(40)),
                   keyish(0), hx(40, 2), uuid(11)]
        bad = []
        for i, (f, v) in enumerate(pairs):
            d0 = build(f, v)
            if f == "task_id":
                d0["evidence"][0]["task_id"] = v
            r0 = one(d0)
            ok = v in (shown(r0) + "\n" + r0["task_id"])
            V = secrets[i % 5]
            leaks = []
            for name, s in _negs(V):
                for fld in {f, "coverage_gaps.0", "next_action"} - {"task_id"}:
                    d = build(fld, s) if fld not in ("coverage_gaps.0", "next_action") else setp(running(), fld, s)
                    if fld == "coverage_gaps.0":
                        d["coverage_gaps"] = [s]
                    if V in everything(one(d)):
                        leaks.append((name, fld))
            if not ok or leaks:
                bad.append((f, v, ok, leaks[:3]))
        self.assertEqual(bad, [])


class IdentityPositionNegativeTable(unittest.TestCase):
    """The reviewer's identity-position negatives (13 fields x credential templates x value shapes), minus the bare values
    that are identity-shaped by construction (a bare hex or letters-only value is indistinguishable from an id)."""

    TPLS = ["token-%s.service", "apikey-%s", "secret_%s", "pw%s", "admin:%s@10.0.0.5", "%s@ryzen7", "/retained/secret/%s.json",
            "/retained/.aws/%s", "key%s", "k%s", "sk-%s", "ghp_%s", "tok-%s-svc", "Bearer %s", "password:%s", "pw9=%s",
            "x-%s.scope", "creds/%s/r.json"]

    def test_no_template_prints_a_hex_base62_or_key_shaped_value(self):
        b62v = "".join("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"[(i * 11 + 5) % 62] for i in range(40))
        values = [hx(32, 12), b62v, keyish(0), "".join(b62v[:16]), hx(40, 6)]
        fields = ID_FIELDS + ["task_id", "worker.account", "worker.model"]
        for f in fields:
            for t in self.TPLS:
                for V in values:
                    d = build(f, t % V) if f != "task_id" else dict(running(), task_id=t % V)
                    if f == "task_id":
                        d["evidence"][0]["task_id"] = t % V
                    self.assertNotIn(V, everything(one(d)), (f, t))


class UnknownKeysAreOpaque(unittest.TestCase):
    """DEF-3: a key outside the schema is never echoed; a key inside the schema keeps its name."""

    def test_unknown_keys_print_as_opaque_refs_whatever_they_look_like(self):
        for k in ("hunter2", "qwerty" + "uiopasdfgh", "bogus", "extra_field", "zz_note", "Zq9Xk3Lm", "x" + hx(32, 6)):
            d = running()
            d[k] = "v"
            d["worker"][k] = "v"
            d["evidence"][0][k] = "v"
            r = one(d)
            out = everything(r)
            self.assertNotIn(k, out, k)
            findings = ev.validate(d, FIXTURE_NOW)
            for f in findings:
                if f["code"] == "UNKNOWN_KEY":
                    self.assertNotIn(k, f["path"] + f["message"], k)
                    self.assertIn("[opaque key ", f["path"])

    def test_safe_key_is_decided_by_the_schema_alone(self):
        for k in ("task_id", "worker", "evidence", "state", "result"):
            self.assertEqual(ev.safe_key(k), k)
        for k in ("bogus", "hunter2", "note", "a", "worker_x"):
            self.assertTrue(ev.safe_key(k).startswith("[opaque key "), k)

    def test_duplicate_schema_key_keeps_its_name_and_a_duplicate_unknown_key_is_opaque(self):
        txt = '{"schema": "x", "bogus": 1, "bogus": 2}'
        obj = ev.load_json_text(txt)
        out = ev.find_dups(obj)
        self.assertTrue(out and "bogus" not in out[0])


class OpaqueRefProperties(unittest.TestCase):
    """DEF-4: pin the opaque-ref design: the field label is part of the digest, and the key is random per process, so a
    fixed PYTHONHASHSEED cannot make refs deterministic and a guess cannot be confirmed from the output."""

    def _run(self, env_extra, flags=()):
        code = ("import sys;sys.path.insert(0,%r);import envelope_validate as ev;"
                "print(ev.opaque('task','Zq9Xk3Lm'),ev.opaque('repo','Zq9Xk3Lm'))" % SCRIPTS)
        env = {"PATH": os.environ.get("PATH", "")}
        env.update(env_extra)
        return subprocess.run([sys.executable, *flags, "-c", code], env=env, capture_output=True, text=True).stdout.strip()

    def test_label_separates_fields(self):
        a, b = ev.opaque("task", "Zq9Xk3Lm"), ev.opaque("repo", "Zq9Xk3Lm")
        self.assertNotEqual(a.split()[-1], b.split()[-1])
        self.assertIn("task", a)
        self.assertIn("repo", b)

    def test_equal_values_give_equal_refs_and_different_values_differ(self):
        self.assertEqual(ev.opaque("task", "abc"), ev.opaque("task", "abc"))
        self.assertNotEqual(ev.opaque("task", "abc"), ev.opaque("task", "abd"))

    def test_the_key_is_random_per_process(self):
        self.assertEqual(len(ev._OPQ_KEY), 16)
        for env in ({}, {"PYTHONHASHSEED": "0"}):
            self.assertNotEqual(self._run(env), self._run(env), env)
        self.assertNotEqual(self._run({"PYTHONHASHSEED": "0"}, ("-I",)), self._run({"PYTHONHASHSEED": "0"}, ("-I",)))

    def test_label_separation_holds_across_processes_and_never_echoes_the_value(self):
        out = self._run({"PYTHONHASHSEED": "0"})
        refs = out.replace("[opaque ", "").replace("]", "").split()
        self.assertNotEqual(refs[1], refs[3])
        self.assertNotIn("Zq9Xk3Lm", out)


if __name__ == "__main__":
    unittest.main()
