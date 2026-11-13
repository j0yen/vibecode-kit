"""Repairs for the ninth independent exact-head review of 950cafba (DEFECTS D1, D2, closed as classes).
Fixtures are synthetic and source-only (tests/fixtures/review/commit_spellings.json, evidence_prose.json); they
exercise the rules, not production behavior. The reference clock is injected (NOW); no test reads the wall clock
or depends on the host time zone.
D1: a placeholder commit (UNKNOWN, TBD, n/a, empty ...) is an UNSTATED commit; sha:<hex>, "commit <hex>", other
labels and zero-width/format characters around one hex are the SAME commit as the bare hex. Records of one endpoint
that differ only so raise duplicate-record. ONE commit-equality rule (ir_norm.commit_id, used through
register_validate._commit_toks) serves production and the pairwise definition (_same_commit).
D2: a prose evidence ref that only says the fact is unknown, missing, null, nil, unavailable, pending or to be done is
non-evidence (ir_norm.non_evidence): missing-evidence on complete. A ref with a concrete anchor is never judged so."""
import json
import random
import sys
import tempfile
import time
import unittest
from pathlib import Path

from test_register import SK, base
from test_review_fixes2 import NOW, check, errs, run, wj   # noqa: F401  (NOW: injected clock)
from test_review_fixes8 import hand, regs, srcid, vcli

sys.path.insert(0, str(SK / "scripts"))
import ir_norm  # noqa: E402
import register_validate as rv  # noqa: E402

FX = Path(__file__).resolve().parent / "fixtures" / "review"
COMMITS = json.loads((FX / "commit_spellings.json").read_text())
PROSE = json.loads((FX / "evidence_prose.json").read_text())
H, H2 = COMMITS["hex"], COMMITS["other_hex"]


def pair_dup(ca, cb, declared="all-interfaces-complete"):
    a = hand("r1", source_identity=srcid("o/r", ca))
    b = hand("r2", source_identity=srcid("o/r", cb))
    res = check(regs((a, b), declared))
    return "duplicate-record" in errs(res), res


# ---------------------------------------------------------------------------------------------------------
class TestD1PlaceholderAndAlternateCommitSpellings(unittest.TestCase):
    def test_every_same_pair_is_a_duplicate_and_complete_is_refused(self):
        for ca, cb in COMMITS["same_pairs"]:
            hit, res = pair_dup(ca, cb)
            self.assertTrue(hit, (ca, cb))
            self.assertFalse(res["ok"], (ca, cb))

    def test_every_distinct_pair_stays_two_endpoints(self):
        for ca, cb in COMMITS["distinct_pairs"]:
            hit, _ = pair_dup(ca, cb)
            self.assertFalse(hit, (ca, cb))

    def test_six_hex_abbreviation_stays_below_the_prefix_rule(self):
        hit, _ = pair_dup(H[:6], H)
        self.assertFalse(hit)

    def test_cli_refuses_complete_naming_both_records(self):
        for ca, cb in (("UNKNOWN", "TBD"), (H, "UNKNOWN"), ("sha:" + H, H), ("commit " + H, H), ("​" + H, H),
                       ("", "n/a")):
            a = hand("r1", source_identity=srcid("o/r", ca))
            b = hand("r2", source_identity=srcid("o/r", cb))
            rc, out = vcli(regs((a, b)))
            self.assertEqual(rc, 1, (ca, cb))
            self.assertIn("duplicate-record", out)
            self.assertIn("r1", out)
            self.assertIn("r2", out)

    def test_cli_accepts_two_endpoints_with_different_stated_commits(self):
        a = hand("r1", source_identity=srcid("o/r", "sha:" + H))
        b = hand("r2", source_identity=srcid("o/r", "commit " + H2))
        rc, out = vcli(regs((a, b)))
        self.assertEqual(rc, 0, out)

    def test_placeholder_commit_is_unstated_in_the_identity(self):
        for c in ("UNKNOWN", "TBD", "n/a", "", "null", " N/A ", "​-"):
            r = hand("r1", source_identity=srcid("o/r", c))
            self.assertEqual(rv._ident(r)[1], frozenset(), c)

    def test_commit_id_class_rules(self):
        self.assertIsNone(ir_norm.commit_id("UNKNOWN"))
        self.assertIsNone(ir_norm.commit_id(None))
        self.assertIsNone(ir_norm.commit_id(12))
        for c in ("sha:" + H, "commit " + H, "​" + H.upper(), "git:" + H + "."):
            self.assertEqual(ir_norm.commit_id(c), H, c)
        self.assertEqual(ir_norm.commit_id("v1.2.0"), "v1.2.0")
        self.assertEqual(ir_norm.commit_id("Release-7"), "release-7")

    def test_one_commit_rule_serves_production_and_the_pairwise_definition(self):
        real = rv._N.commit_id
        rv._N.commit_id = lambda c: c.lower() if isinstance(c, str) else None      # a mutant: no label/format folding
        try:
            self.assertFalse(rv._same_commit(H, "sha:" + H))
            groups = rv._duplicate_groups([hand("r1", source_identity=srcid("o/r", H)),
                                           hand("r2", source_identity=srcid("o/r", "sha:" + H))])
        finally:
            rv._N.commit_id = real
        self.assertEqual(groups, [])          # both paths read the same rule: a mutant of it breaks both

    def test_same_commit_reads_the_token_rule_not_a_second_copy(self):
        real = rv._commit_toks
        rv._commit_toks = lambda commits: (set(), set())
        try:
            self.assertFalse(rv._same_commit(H, H))
        finally:
            rv._commit_toks = real
        self.assertTrue(rv._same_commit(H, H))

    def test_pairwise_definition_and_keyed_grouping_agree_on_every_fixture_pair(self):
        for ca, cb in COMMITS["same_pairs"] + COMMITS["distinct_pairs"]:
            a = hand("r1", source_identity=srcid("o/r", ca))
            b = hand("r2", source_identity=srcid("o/r", cb))
            keyed = bool(rv._duplicate_groups([a, b]))
            self.assertEqual(keyed, rv._conflict(rv._ident(a), rv._ident(b)), (ca, cb))

    def test_random_registers_equal_the_all_pairs_closure(self):
        rng = random.Random(9)
        spell = [lambda h: h, lambda h: "sha:" + h, lambda h: "commit " + h, lambda h: h.upper(), lambda h: "​" + h,
                 lambda h: h[:9], lambda h: "sha1:" + h[:12], lambda h: "UNKNOWN", lambda h: "TBD", lambda h: "", lambda h: "n/a",
                 lambda h: None]
        hexes = [H, H2, H[:7] + "0" * 33, H[:7] + "1" * 33]
        repos = ["o/r", "O/R", "https://github.com/o/r.git", "p/r", None, "UNKNOWN"]
        bad = 0
        for _ in range(700):
            recs = []
            for i in range(rng.randint(2, 9)):
                si = {"version": "v", "available": True, "captured_at": "2026-11-12T09:00:00Z"}
                repo, c = rng.choice(repos), rng.choice(spell)(rng.choice(hexes))
                if repo:
                    si["repo"] = repo
                if c is not None:
                    si["commit"] = c
                recs.append(hand(f"r{i}", path=rng.choice(["a.py", "b.py", None]), source_identity=si))
            ids = [rv._ident(r) for r in recs]
            par = list(range(len(recs)))

            def f(i):
                while par[i] != i:
                    i = par[i]
                return i
            for i in range(len(recs)):
                for j in range(i):
                    if rv._key(recs[i]) == rv._key(recs[j]) and rv._conflict(ids[i], ids[j]):
                        par[f(i)] = f(j)
            comp = {}
            for i in range(len(recs)):
                comp.setdefault(f(i), set()).add(recs[i]["record_id"])
            want = {frozenset(v) for v in comp.values() if len(v) > 1}
            got = {frozenset(r["record_id"] for r in g) for g in rv._duplicate_groups(recs)}
            bad += want != got
        self.assertEqual(bad, 0)

    def test_grouping_with_spelling_variants_stays_fast(self):
        # "+ 1" below: group 0 was the all-zero sha by arithmetic accident; the null sha is unstated (re-review 11 D1, fixture correction)
        spell = ("%s", "sha:%s", "commit %s", "​%s")
        recs = [hand(f"r{i}", source_identity=srcid("o/r", spell[i % 4] % ("%040x" % (i // 4 + 1)))) for i in range(3000)]
        t = time.time()
        groups = rv._duplicate_groups(recs)
        self.assertLess(time.time() - t, 15)
        self.assertEqual(len(groups), 750)


# ---------------------------------------------------------------------------------------------------------
class TestD2PlaceholderProseIsNeverEvidence(unittest.TestCase):
    def verdict(self, ref, declared="all-interfaces-complete"):
        reg = base(declared)
        reg["records"][1]["evidence"] = [{"ref": ref, "observed_at": "2026-11-12T11:00:00Z"}]
        res = check(reg)
        return res["ok"], "missing-evidence" in {f["code"] for f in res["findings"]}

    def test_every_non_evidence_ref_is_missing_evidence_on_complete(self):
        for ref in PROSE["non_evidence"]:
            ok, missing = self.verdict(ref)
            self.assertTrue(missing and not ok, f"counts as evidence: {ref!r}")

    def test_genuine_refs_are_not_refused(self):
        for ref in PROSE["evidence"]:
            ok, missing = self.verdict(ref)
            self.assertTrue(ok and not missing, f"refused: {ref!r}")

    def test_non_evidence_is_a_class_not_a_word_list(self):
        for ref in ("the status reads unknown", "reviewer says value is nil", "currently pending", "source still unavailable",
                    "answer: null", "n/a for now", "to follow", "it is empty", "result still unknown to us"):
            self.assertTrue(ir_norm.non_evidence(ref), ref)
        for ref in ("a.py:12", "status 200", "tests: 0 failed, 12 passed", "https://example.invalid/x", "src/unknown/x.py",
                    "pid 77 exe /bin/svc"):
            self.assertFalse(ir_norm.non_evidence(ref), ref)

    def test_a_placeholder_word_inside_a_longer_concrete_statement_still_counts(self):
        for ref in ("the handler writes null to the topic when the retry budget 3 is spent, shown at a.py:44",
                    "test_unknown_field passes: 1 passed"):
            ok, missing = self.verdict(ref)
            self.assertTrue(ok and not missing, ref)

    def test_cli_refuses_complete_naming_the_record(self):
        reg = base()
        reg["records"][1]["evidence"] = [{"ref": "status: unknown", "observed_at": "2026-11-12T11:00:00Z"}]
        rc, out = vcli(reg)
        self.assertEqual(rc, 1)
        self.assertIn("missing-evidence", out)

    def test_one_genuine_ref_beside_a_placeholder_one_is_enough(self):
        reg = base()
        reg["records"][1]["evidence"] = [{"ref": "evidence: null", "observed_at": "2026-11-12T11:00:00Z"},
                                         {"ref": "tests: 0 failed, 12 passed", "observed_at": "2026-11-12T11:00:00Z"}]
        self.assertTrue(check(reg)["ok"])

    def test_partial_register_only_warns(self):
        ok, missing = self.verdict("value is nil", "partial")
        self.assertTrue(ok and missing)

    def test_skill_states_both_rules_as_classes(self):
        text = (SK / "SKILL.md").read_text()
        self.assertIn("placeholder commit", text)
        self.assertIn("non-evidence", text)


if __name__ == "__main__":
    unittest.main()
