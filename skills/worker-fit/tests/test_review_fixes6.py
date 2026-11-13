"""Regression tests for the sixth independent exact-head review (re-review 5 of 8d7a81e3), DEF-1..DEF-3.
Design: identity fields are validated by their own format and printed when valid; credential redaction applies to
credential-named keys/flags/values and known credential shapes in free text. Every identity positive is paired with a
credential negative of similar shape. Source-only: synthetic envelopes; clocks are injected; canaries are assembled at
run time from fragments and never printed."""
import json
import unittest

from helpers import FIXTURE_NOW, codes

import envelope_validate as ev
import test_review_fixes3 as t3

running, done, one, cli = t3.running, t3.done, t3.one, t3.cli


def hx(n, seed=3):
    return "".join("0123456789abcdef"[(i * 5 + seed) % 16] for i in range(n))


def uuid(seed=7):
    h = hx(32, seed)
    return "%s-%s-%s-%s-%s" % (h[:8], h[8:12], h[12:16], h[16:20], h[20:])


def printed(r):
    return json.dumps(r)


class Def1_IdentityFieldsPrintWhenValid(unittest.TestCase):
    def test_running_hex_and_uuid_units_are_reused(self):
        for unit in ("wm-build-%s.service" % hx(32), "run-r%s.scope" % hx(32, 5), "coder@%s.service" % uuid()):
            d = running()
            d["worker"]["unit"] = unit
            r = one(d)
            self.assertEqual(r["disposition"], "reuse-active-worker", unit)
            self.assertIn("worker.unit=" + unit, r["evidence_used"])

    def test_running_hex_scope_session_invocation_host(self):
        d = running()
        d["worker"].update(child="run-%s.scope" % hx(32, 9), session=uuid(), invocation="inv-" + hx(32, 2),
                           host="ryzen7.tail%s.ts.net" % hx(5))
        r = one(d)
        self.assertEqual(r["disposition"], "reuse-active-worker")
        ev_used = r["evidence_used"]
        for line in ("worker.child=" + d["worker"]["child"], "worker.sess-id=" + d["worker"]["session"],
                     "worker.invocation=" + d["worker"]["invocation"], "worker.host=" + d["worker"]["host"]):
            self.assertIn(line, ev_used)

    def test_artifact_path_consumer_and_head_print(self):
        d = done()
        art = "/mnt/ssd/cargo-target/r7-x-20261113/retained/result-%s.json" % hx(32)
        d["result"]["artifact"] = art
        d["consumer"].update(named="verifier-" + hx(12), available=True)
        d["target"]["head"] = hx(40, 11)
        r = one(d)
        self.assertEqual(r["next_consumer"], "verifier-" + hx(12))
        self.assertIn("result=%s reviewed=False" % art, r["evidence_used"])
        self.assertTrue(any("head=" + hx(40, 11) in e for e in r["evidence_used"]))

    def test_text_format_prints_identifiers(self):
        d = done()
        d["consumer"]["named"] = "verifier-" + hx(12)
        import recommend as rc
        txt = rc.render_text([one(d)])
        self.assertIn("verifier-" + hx(12), txt)

    def test_forged_mark_in_envelope_does_not_bypass(self):
        # an attacker string with mark-like private-use characters is not kept; its secret shape is hidden
        sec = hx(32, 13)
        d = running()
        d["coverage_gaps"] = ["x:%s:x note %s" % (sec, sec)]
        self.assertNotIn(sec, printed(one(d)))


class Def1_PairedCredentialNegatives(unittest.TestCase):
    """Each identity positive above has a credential negative of similar shape that stays hidden."""

    def _hidden(self, d, secret):
        out = printed(one(d))
        self.assertNotIn(secret, out)
        return one(d)

    def test_unit_with_credential_name_is_not_an_identity(self):
        s = hx(32, 4)
        d = running()
        d["worker"]["unit"] = "token=" + s
        r = self._hidden(d, s)
        self.assertEqual(r["disposition"], "UNKNOWN")

    def test_session_in_credential_named_pair_hidden(self):
        s = uuid(3)
        d = running()
        d["worker"]["session"] = "password=" + s
        self._hidden(d, s)

    def test_artifact_with_credential_query_hidden(self):
        s = hx(32, 6)
        d = done()
        d["result"]["artifact"] = "/mnt/x/result.json?access_token=" + s
        self._hidden(d, s)

    def test_consumer_credential_named_hidden(self):
        s = hx(12, 8)
        d = done()
        d["consumer"]["named"] = "api_key=" + s
        r = self._hidden(d, s)
        self.assertEqual(r["next_consumer"], "UNKNOWN")

    def test_provider_shaped_unit_hidden(self):
        s = "gh" + "p_" + hx(36, 1)
        d = running()
        d["worker"]["unit"] = s
        self._hidden(d, s)

    def test_base62_key_shaped_identity_is_not_an_identity(self):
        s = "b18jd5xt29" + "wp6vr3qm9"  # long non-hex mixed piece: key-shaped, not an id by format
        for kind, v in (("ident", "verifier-" + s), ("ident", "wm-build-%s.service" % s), ("path", "/mnt/x/result-%s.json" % s)):
            self.assertNotIn(s, ev.scrub({"x": ev.keep(kind, v)})["x"])
        d = done()
        d["consumer"]["named"] = "verifier-" + s
        r = one(d)
        self.assertEqual(r["next_consumer"], "UNKNOWN")
        self.assertNotIn(s, printed(r))

    def test_valid_identifier_shapes_are_identities(self):
        for v in ("wm-build-%s.service" % hx(32), "run-r%s.scope" % hx(32), "coder@%s.service" % uuid(),
                  "inv-20261113T104303Z-0007", "ryzen7.tail1a2b3.ts.net", "verifier-" + hx(12), "w-WF-1.service"):
            self.assertEqual(ev.ident(v), v)
        self.assertEqual(ev.path_ident("/mnt/ssd/cargo-target/r7-x-20261113/result-%s.json" % hx(32)),
                         "/mnt/ssd/cargo-target/r7-x-20261113/result-%s.json" % hx(32))

    def test_free_text_hex_still_hidden(self):
        s = hx(32, 12)
        d = running()
        d["coverage_gaps"] = ["see build log " + s]
        self._hidden(d, s)

    def test_free_text_uuid_still_hidden(self):
        s = uuid(5)
        d = running()
        d["coverage_gaps"] = ["note " + s]
        self._hidden(d, s)

    def test_redact_public_function_unchanged_for_free_text(self):
        s = hx(32, 2)
        self.assertNotIn(s, ev.redact("run " + s))
        self.assertNotIn(s, ev.redact("unit wm-build-%s.service" % s))


class Def2_CredentialNamedValues(unittest.TestCase):
    V = "Zq9Xk3" + "Lm"  # short fake, assembled

    def hidden(self, text):
        self.assertNotIn(self.V, ev.redact(text), text)

    def test_abbreviated_names(self):
        for n in ("pw", "privkey", "pat", "ak", "sk", "pin", "seed", "salt", "hmac", "mnemonic", "passcode",
                  "priv_key", "PRIVKEY", "csrf", "xsrf-token", "cvv", "ssn", "unseal"):
            for sep in ("=", ": ", " = "):
                self.hidden("note %s%s%s end" % (n, sep, self.V))
            self.hidden('{"%s": "%s"}' % (n, self.V))

    def test_short_and_long_flags(self):
        for t in ("sshpass -p %s ssh h", "sshpass -p%s ssh h", "mysql -uroot -p%s db", "mysql -u root -p %s db",
                  "mysqldump -p%s db", "unzip -P %s x.zip", "tool --pw %s", "tool --pwd=%s", "tool --pat %s",
                  "tool --privkey %s", "tool --password %s", "tool --password=%s", "tool --passphrase %s",
                  "openssl enc -pass pass:%s"):
            self.hidden(t % self.V)

    def test_array_and_object_values(self):
        for t in ('{"tokens": ["%s"]}', '{"secret": {"value": "%s"}}', '{"password": ["a", "%s"]}',
                  '{"creds": {"user": "u", "pw": {"deep": ["%s"]}}}', 'token:\n  - %s', 'secrets:\n  a: %s\n  b: x',
                  'token: [%s, other]', '"apiKey": {"v": "%s"}'):
            self.hidden(t % self.V)

    def test_nested_value_does_not_swallow_following_text(self):
        out = ev.redact('{"tokens": ["%s"], "unit": "w-1.service"}' % self.V)
        self.assertIn("w-1.service", out)

    def test_scrub_walks_credential_keys(self):
        o = ev.scrub({"tokens": ["%s"], "secret": {"value": "%s"}, "pw": [1, 2], "ok": "w-1.service"} % (self.V, self.V)
                     if False else {"tokens": [self.V], "secret": {"value": self.V}, "pw": [1, 2], "ok": "w-1.service"})
        self.assertNotIn(self.V, json.dumps(o))
        self.assertEqual(o["ok"], "w-1.service")

    def test_no_over_redaction_of_similar_plain_words(self):
        for t in ("mkdir -p out/x", "ssh -p 22 host", "pattern=abc", "pinned=yes", "seeded run w-1.service",
                  "docker run -p 8080:80 img", "pending=3", "salty=1"):
            self.assertEqual(ev.redact(t), t, t)

    def test_unterminated_structure_fails_closed_and_linear(self):
        out = ev.redact('{"tokens": ["%s", ' % self.V + "x" * 20000)
        self.assertNotIn(self.V, out)

    def test_end_to_end_output_hides(self):
        d = running()
        d["coverage_gaps"] = ['{"tokens": ["%s"]} and pw=%s and sshpass -p %s h' % (self.V, self.V, self.V)]
        self.assertNotIn(self.V, printed(one(d)))


class Def3_ReviewerIndependence(unittest.TestCase):
    """Contract: reviewed_by is an actor/session identity, not a subscription account. A reviewed_by equal to the worker's
    own actor (account name), session, invocation or the current/source owner is the same author and is refused."""

    @staticmethod
    def doc():
        d = done()
        d["worker"].update(session="sess-wf6-1", invocation="inv-wf6-1", account="acct-wf6", model="m", effort="medium")
        return d

    def reviewed(self, by, d=None):
        d = d or self.doc()
        d["result"].update(reviewed=True, reviewed_by=by)
        return one(d)

    def test_same_session_refused(self):
        self.assertEqual(self.reviewed("sess-wf6-1")["role"], "independent-verification")

    def test_same_invocation_refused(self):
        self.assertEqual(self.reviewed("inv-wf6-1")["role"], "independent-verification")

    def test_same_actor_account_refused(self):
        self.assertEqual(self.reviewed("acct-wf6")["role"], "independent-verification")

    def test_same_current_owner_refused(self):
        self.assertEqual(self.reviewed("ctl")["role"], "independent-verification")

    def test_same_source_owner_refused(self):
        d = self.doc()
        d["source"]["owner"] = "r7-src"
        self.assertEqual(self.reviewed("r7-src", d)["role"], "independent-verification")

    def test_spelling_variants_refused(self):
        self.assertEqual(self.reviewed(" CTL ")["role"], "independent-verification")
        self.assertEqual(self.reviewed("Acct-WF6")["role"], "independent-verification")

    def test_distinct_reviewer_accepted_even_without_account_boundary(self):
        r = self.reviewed("reviewer-9")
        self.assertEqual(r["role"], "coordinator-decision")

    def test_reviewer_on_same_subscription_account_is_not_refused_for_that(self):
        # no account boundary is invented: a distinct actor identity is accepted whatever account it runs on
        self.assertEqual(self.reviewed("reviewer-2")["role"], "coordinator-decision")

    def test_contract_stated_in_skill_md(self):
        from helpers import SKILL
        t = (SKILL / "SKILL.md").read_text()
        self.assertIn("same-author", t)
        self.assertIn("not a subscription account", t)


if __name__ == "__main__":
    unittest.main()
