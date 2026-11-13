"""Repairs for the eighth independent exact-head review of 20619145 (DEFECTS D1-D6, closed as classes).
Fixtures are synthetic and source-only; they exercise the rules, not production behavior. Credential-shaped
canaries are FAKE, assembled at run time from fragments and never printed: a failure reports a fixed message.
No test depends on the real clock or the host time zone: the reference clock is injected (NOW).
D1: the validator's duplicate grouping is keyed (near-linear) and equals the all-pairs closure of _conflict.
D2: version pins (svc@1.2.3) are not credential-shaped and print as written; two distinct record ids never print
as the same text (a redacted id carries its record position). D3: quoted-local, @localhost and IP-literal e-mail
forms and URL credentials with a raw "/" are redacted on every output path. D4: a negation anywhere before or
after a side mark in its clause, or a doubt wording, leaves the role UNKNOWN. D5: unchecked/skipped/pending/TBD/
waived/disproved/invalid never count as evidence; "0 failed, 12 passed" does. D6: one commit written in another
case or as a prefix is the same commit, so duplicate-record is raised."""
import json
import random
import sys
import tempfile
import time
import unittest
from pathlib import Path

from test_register import SK, base, rec
from test_review_fixes2 import NOW, check, errs, row, run, wj   # noqa: F401  (NOW: injected clock)

sys.path.insert(0, str(SK / "scripts"))
import extract_register as xr  # noqa: E402
import ir_norm  # noqa: E402
import register_validate as rv  # noqa: E402

REAL = Path(__file__).resolve().parent / "fixtures" / "endpoints.jsonl"
NOWS = "2026-11-13T12:00:00Z"


def join(*p):
    return "".join(p)


# FAKE canaries, assembled at run time, never printed
QL = join("mal", "lory")                       # local part of a fake e-mail
PW8 = join("Hq7Rt2Vx9", "Lp4")                 # fake URL password
NEEDLES8 = (QL, "Hq7Rt2Vx9")
GHA = join("gh", "p_", "Q" * 36)
GHB = join("gh", "p_", "R" * 36)


def leaked8(out):
    flat = out.replace("\n", "")
    return any(n in flat for n in NEEDLES8)


EMAIL_FORMS = (
    join(QL, "@", "example", ".com"),
    join('"', QL, " smith", '"', "@", "example", ".com"),
    join(QL, "@", "localhost"),
    join(QL, "@[", "192.0.2.", "7]"),
    join(QL, "@", "192.0.2.", "7"),
    join(QL, "@[IPv6:", "2001:db8::1]"),
    join('"', QL, '"', "@", "localhost"),
)
URL_FORMS = (
    join("https://", QL, ":", PW8, "/x@localhost/a"),
    join("https://", QL, ":", PW8, "/x/y@h.example/z"),
    join("ssh://", QL, ":", "ab/", PW8, "@h.example"),
    join("https://", QL, ":", PW8, "@h.example/z"),          # the listed form stays masked
)
VERSION_PINS = ("svc@1.2.3", "svc@2.0.0", "pkg@1.2.3-beta", "pkg@2.0.0-rc.1", "lib@v1.2.3", "lib@2.0.0+build.5", "x@10.20")


def cm(c):
    return "commit " + c * 40


def srcid(repo=None, commit=None, **kw):
    d = {"version": commit or "v1", "available": True, "captured_at": "2026-11-12T09:00:00Z"}
    if repo:
        d["repo"] = repo
    if commit:
        d["commit"] = commit
        d["raw"] = "commit " + commit
    d.update(kw)
    return d


def hand(rid, path="a.py", **kw):
    r = rec(rid, comp="svc-a", installed_state="source-only")
    r.pop("source_identity", None)
    if path:
        r["path_or_command"] = path
    r.update(kw)
    return r


def regs(pair, declared="all-interfaces-complete"):
    reg = base(declared)
    reg["records"] = list(pair) + reg["records"][1:]
    return reg


def vcli(reg):
    with tempfile.TemporaryDirectory() as d:
        return run("register_validate.py", wj(d, "r.json", reg), "--now", NOWS)


A, B = "a" * 40, "b" * 40


# ---------------------------------------------------------------------------------------------------------
class TestD1ValidatorDuplicateGroupingIsKeyedAndEqualsTheAllPairsClosure(unittest.TestCase):
    def naive(self, recs):
        n = len(recs)
        par = list(range(n))

        def f(i):
            while par[i] != i:
                par[i] = par[par[i]]
                i = par[i]
            return i
        ids = [rv._ident(r) for r in recs]
        keys = [rv._key(r) for r in recs]
        for i in range(n):
            for j in range(i):
                if keys[i] == keys[j] and rv._conflict(ids[i], ids[j]):
                    par[f(i)] = f(j)
        comp = {}
        for i in range(n):
            comp.setdefault(f(i), []).append(recs[i]["record_id"])
        return {frozenset(c) for c in comp.values() if len(c) > 1}

    def test_random_registers_group_exactly_like_the_all_pairs_closure(self):
        rnd = random.Random(21)
        repos = ["o1/r", "o2/r", "https://github.com/o1/r.git", "git@github.com:o2/r", None, "UNKNOWN", "N/A"]
        commits = ["a" * 40, "b" * 40, None, None, "A" * 40, "a" * 7, "ab" + "c" * 5, "b" * 12, "zz"]

        def src():
            si = {"version": "v", "available": True, "captured_at": "2026-11-12T09:00:00Z"}
            r, c = rnd.choice(repos), rnd.choice(commits)
            if r:
                si["repo"] = r
            if c:
                si["commit"] = c
            return si

        def mk(i):
            d = {"record_id": f"r{i}", "family": "IF001", "role": "producer", "host": "h",
                 "component": rnd.choice(["c", "c", "d"]), "interface_kind": "http",
                 "installed_state": "source-only", "path_or_command": rnd.choice(["a.py", "b.py", None])}
            d = {k: v for k, v in d.items() if v is not None}
            if rnd.random() < 0.25:
                d["sources"] = [dict(src(), path_or_command=rnd.choice(["a.py", "b.py", "c.py"])) if rnd.random() < .3 else src()
                                for _ in range(rnd.randint(1, 3))]
            else:
                d["source_identity"] = src()
            return d
        for _ in range(900):
            recs = [mk(i) for i in range(rnd.randint(2, 11))]
            got = {frozenset(r["record_id"] for r in g) for g in rv._duplicate_groups(recs)}
            self.assertEqual(got, self.naive(recs))

    def test_grouping_does_not_compare_every_pair(self):
        n = 1500
        shapes = {
            "distinct-repo-no-commit": [hand(f"r{i}", source_identity=srcid(f"o{i}/r")) for i in range(n)],
            "same-repo-distinct-commit": [hand(f"r{i}", source_identity=srcid("o/r", "%040x" % i)) for i in range(n)],
            "no-repo-distinct-commit": [hand(f"r{i}", source_identity=srcid(None, "%040x" % i)) for i in range(n)],
            "distinct-repo-distinct-commit": [hand(f"r{i}", source_identity=srcid(f"o{i}/r", "%040x" % i)) for i in range(n)],
            "alternating": [hand(f"r{i}", source_identity=srcid(f"o{i}/r" if i % 2 else None, "%040x" % i if i % 3 else None)) for i in range(n)],
        }
        calls = [0]
        real = rv._conflict

        def counting(a, b):
            calls[0] += 1
            return real(a, b)
        rv._conflict = counting
        try:
            for name, recs in shapes.items():
                calls[0] = 0
                t = time.time()
                rv._duplicate_groups(recs)
                self.assertLess(calls[0], 8 * n, name)
                self.assertLess(time.time() - t, 8.0, name)       # generous: the all-pairs scan took 5-20 s at 4000
        finally:
            rv._conflict = real

    def test_validator_cli_on_extractor_output_of_the_slow_shapes_is_fast(self):
        n = 1500
        rows = [row(source_repo=f"o{i}/r", source_identity="path+sha256:/p/x.py " + ("%064x" % i), path_or_command="a.py")
                for i in range(n)]
        out = xr.convert(rows, "partial")["register"]
        with tempfile.TemporaryDirectory() as d:
            t = time.time()
            rc, text = run("register_validate.py", wj(d, "r.json", out), "--now", NOWS)
            self.assertLess(time.time() - t, 12.0)
        self.assertEqual(rc, 0, "partial register of distinct endpoints validates")

    def test_a_duplicate_pair_is_still_found_inside_a_large_register(self):
        recs = [hand(f"r{i}", source_identity=srcid(f"o{i}/r", "%040x" % i)) for i in range(400)]
        recs.append(hand("dupe", source_identity=srcid("o7/r")))
        got = [sorted(r["record_id"] for r in g) for g in rv._duplicate_groups(recs)]
        self.assertEqual(got, [["dupe", "r7"]])

    def test_chain_through_an_unstated_commit_record_joins_three_records(self):
        recs = [hand("r1", source_identity=srcid("o/r", A)), hand("r2", source_identity=srcid("o/r", B)),
                hand("r3", source_identity=srcid("o/r"))]
        got = [sorted(r["record_id"] for r in g) for g in rv._duplicate_groups(recs)]
        self.assertEqual(got, [["r1", "r2", "r3"]])

    def test_distinct_endpoints_of_one_key_stay_distinct(self):
        recs = [hand("r1", source_identity=srcid("o/r", A)), hand("r2", source_identity=srcid("o/r", B)),
                hand("r3", source_identity=srcid("o2/r", A))]
        self.assertEqual(rv._duplicate_groups(recs), [])


# ---------------------------------------------------------------------------------------------------------
class TestD2VersionPinsPrintAsWrittenAndIdsNeverCollapse(unittest.TestCase):
    def test_version_pins_are_not_credential_shaped(self):
        for t in VERSION_PINS:
            self.assertEqual(ir_norm.redact(t), t, "a version pin is redacted")

    def test_real_email_shapes_stay_redacted_beside_version_pins(self):
        for t in ("alice@example.com", "a.b+c@mail.example.org", "x@1.example.com", "x@123.com"):
            self.assertEqual(ir_norm.redact(t), ir_norm.REDACTED, t)

    def test_refused_line_names_two_version_pinned_ids_separately(self):
        g = [rec("p"), rec("svc@1.2.3", role="consumer", comp="c2", path_or_command="a.py"),
             rec("svc@2.0.0", role="consumer", comp="c3", path_or_command="b.py")]
        for r in g[1:]:
            r["evidence"] = []
        reg = base()
        reg["records"] = g
        rc, out = vcli(reg)
        self.assertEqual(rc, 1)
        refused = [ln for ln in out.splitlines() if ln.startswith("REFUSED")][0]
        self.assertIn("svc@1.2.3:missing-evidence", refused)
        self.assertIn("svc@2.0.0:missing-evidence", refused)

    def test_two_ids_that_must_be_redacted_print_distinguishably_and_never_leak(self):
        g = [rec("p"), rec(GHA, role="consumer", comp="c2", path_or_command="a.py"),
             rec(GHB, role="consumer", comp="c3", path_or_command="b.py")]
        for r in g[1:]:
            r["evidence"] = []
        reg = base()
        reg["records"] = g
        rc, out = vcli(reg)
        self.assertEqual(rc, 1)
        self.assertNotIn("Q" * 12, out)
        self.assertNotIn("R" * 12, out)
        refused = [ln for ln in out.splitlines() if ln.startswith("REFUSED")][0]
        items = [x.strip() for x in refused.split("gaps remain in:")[1].split(",")]
        mine = [x for x in items if x.endswith(":missing-evidence")]
        self.assertEqual(len(mine), len(set(mine)), "two distinct ids collapsed to one printed text")
        self.assertEqual(len(mine), 2)

    def test_the_distinguishing_mark_is_stable_between_runs(self):
        g = [rec("p"), rec(GHA, role="consumer", comp="c2", path_or_command="a.py")]
        g[1]["evidence"] = []
        reg = base()
        reg["records"] = g
        self.assertEqual(vcli(reg), vcli(reg))

    def test_duplicate_credential_ids_are_told_apart_by_position(self):
        g = [rec("p"), rec(GHA, role="consumer", comp="c2"), rec(GHA, role="consumer", comp="c2")]
        reg = base()
        reg["records"] = g
        rc, out = vcli(reg)
        self.assertNotIn("Q" * 12, out)
        self.assertIn("duplicate-record", out)

    def test_ordinary_ids_print_exactly_as_written(self):
        reg = base()
        reg["records"][1]["evidence"] = []
        rc, out = vcli(reg)
        self.assertIn("R2:missing-evidence", out)


# ---------------------------------------------------------------------------------------------------------
class TestD3EmailAndUrlCredentialFormsRedactOnEveryPath(unittest.TestCase):
    def test_every_form_redacts_in_the_shared_net(self):
        for t in EMAIL_FORMS + URL_FORMS:
            self.assertEqual(ir_norm.redact(t), ir_norm.REDACTED, "a credential or e-mail form is printed")
            self.assertEqual(ir_norm.redact("see " + t + " end"), ir_norm.REDACTED)

    def test_urls_with_a_port_and_a_scoped_path_are_not_masked(self):
        for t in ("https://registry.example:8080/@scope/pkg", "https://host:5000/pkg@sha256", "https://h.example/a/b@v2",
                  "svc@latest"):
            self.assertEqual(ir_norm.redact(t), t, t)

    def test_validator_stdout_and_stderr_paths(self):
        for t in EMAIL_FORMS + URL_FORMS:
            reg = base()
            reg["records"][0]["record_id"] = t
            reg["records"][0]["component"] = "UNKNOWN"
            reg["records"][1]["role"] = t                 # by_role counts, the 'unclassified' message
            reg["records"][1]["label"] = "unclassified"
            reg["families"][0]["registered_callers"] = [t]
            reg["records"][2]["component"] = t
            rc, out = vcli(reg)
            self.assertFalse(leaked8(out), "validator stdout (findings, REFUSED, counts)")
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("register_validate.py", Path(d) / (t.replace("/", "_") + ".json"))
            self.assertFalse(leaked8(out), "validator stderr unreadable")

    def test_schema_compat_paths(self):
        for t in EMAIL_FORMS + URL_FORMS:
            with tempfile.TemporaryDirectory() as d:
                a = wj(d, "o.json", {"type": "object", "properties": {t: {"type": "string", "enum": [t, "x"]}}, "required": [t]})
                b = wj(d, "n.json", {"type": "object", "properties": {}})
                rc, out = run("schema_compat.py", a, b)
                self.assertFalse(leaked8(out), "schema_compat stdout")
                rc, out = run("schema_compat.py", a, Path(d) / (t.replace("/", "_") + ".json"))
                self.assertFalse(leaked8(out), "schema_compat stderr")

    def test_lost_message_and_discriminator_paths(self):
        for t in EMAIL_FORMS + URL_FORMS:
            nm = t.replace("/", "_")
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("lost_message_check.py", Path(d) / (nm + ".json"))
                self.assertFalse(leaked8(out), "lost_message_check stderr")
                f = wj(d, "f.json", {"id": t, "claim": "message lost " + t, "label": "observed-defect", "trace": {"producer": {"ref": t, "actor": t}}})
                rc, out = run("lost_message_check.py", f)
                self.assertFalse(leaked8(out), "lost_message_check stdout")
                rc, out = run("discriminator_check.py", Path(d) / (nm + ".sh"), "--line", "1", "--names", "a")
                self.assertFalse(leaked8(out), "discriminator_check stderr")
                src = Path(d) / "s.sh"
                src.write_text("X='^a$'\n", encoding="utf-8")
                rc, out = run("discriminator_check.py", src, "--line", t, "--names", "a")
                self.assertFalse(leaked8(out), "discriminator_check argparse echo")

    def test_extractor_paths(self):
        for t in EMAIL_FORMS + URL_FORMS:
            with tempfile.TemporaryDirectory() as d:
                rc, out = run("extract_register.py", Path(d) / (t.replace("/", "_") + ".jsonl"), Path(d) / "o")
                self.assertFalse(leaked8(out), "extractor stderr unreadable input")
                src = Path(d) / "in.jsonl"
                src.write_text("not json " + t + "\n" + json.dumps(row()) + "\n", encoding="utf-8")
                rc, out = run("extract_register.py", src, Path(d) / "o")
                self.assertFalse(leaked8(out), "extractor stdout")
                for f in (Path(d) / "o").glob("*.json"):
                    self.assertFalse(leaked8(f.read_text(encoding="utf-8")), "extractor report file " + f.name)


# ---------------------------------------------------------------------------------------------------------
class TestD4NegationOfASideMarkIsAClassNotAWordList(unittest.TestCase):
    def role(self, ev, claimed="producer"):
        return xr.norm_role({"role": claimed}, xr.evidence_text({"evidence": ev}))[0]

    def test_negation_any_distance_before_the_mark_in_its_clause(self):
        for ev in ("no evidence that side=producer", "not verified that side=producer",
                   "has not been confirmed as side=producer", "never really established that side=producer",
                   "there is no way anyone has yet shown that side=producer", "we could not at any point establish that side=producer",
                   "it is not the case that side=producer", "nothing in the handler shows that side=producer"):
            self.assertEqual(self.role(ev), "UNKNOWN", ev)

    def test_doubt_and_falsity_wordings_after_the_mark(self):
        for ev in ("side=producer is false", "side=producer was refuted", "side=producer: untrue", "side=producer is incorrect",
                   "side=producer disproved by test", "side=producer rejected", "side=producer is unproven", "side=producer unclear"):
            self.assertEqual(self.role(ev), "UNKNOWN", ev)

    def test_doubt_words_before_the_mark(self):
        for ev in ("unverified: side=producer", "claim is false: side=producer", "disputed that side=producer",
                   "pending review of side=producer", "TBD whether side=producer"):
            self.assertEqual(self.role(ev), "UNKNOWN", ev)

    def test_positive_marks_still_count(self):
        for ev in ("side=producer", "side=producer observed in handler", "reads the topic; side=producer",
                   "no tests exist for x; side=producer", "handler publishes the event. side=producer",
                   "publish call at a.py:10 confirms side=producer", "side=producer; not side=consumer",
                   "side=producer\nnot verified elsewhere"):
            self.assertEqual(self.role(ev), "producer", ev)

    def test_a_negated_mark_beside_a_positive_one_keeps_only_the_positive(self):
        self.assertEqual(self.role("side=consumer, not side=producer", "consumer"), "consumer")
        self.assertEqual(self.role("not verified that side=consumer; side=producer", "producer"), "producer")

    def test_words_that_merely_contain_a_negation_stem_do_not_negate(self):
        for ev in ("notifier publishes; side=producer", "side=producer united with the bus", "side=producer unified handler"):
            self.assertEqual(self.role(ev), "producer", ev)

    def test_extractor_end_to_end_unknown_role(self):
        o = xr.convert([row(evidence="no evidence that side=producer")], "partial")["register"]
        self.assertEqual(o["records"][0]["role"], "UNKNOWN")


# ---------------------------------------------------------------------------------------------------------
class TestD5NonEvidenceProseIsNeverEvidence(unittest.TestCase):
    def verdict(self, ref):
        reg = base()
        reg["records"][1]["evidence"] = [{"ref": ref, "observed_at": "2026-11-12T11:00:00Z"}]
        res = check(reg)
        return res["ok"], "missing-evidence" in errs(res)

    def test_non_evidence_refs_do_not_count(self):
        for ref in ("verification unchecked", "skipped", "pending review", "TBD fill in later", "check was waived",
                    "claim disproved", "evidence is invalid", "Pending", "waived", "unreviewed", "check skipped",
                    "result invalid", "disproven by the second test", "test is unrun", "unconfirmed", "to do: check",
                    "assertion is false", "retracted"):
            ok, missing = self.verdict(ref)
            self.assertTrue(missing and not ok, f"counts as evidence: {ref!r}")

    def test_zero_failures_with_passes_is_positive_evidence(self):
        for ref in ("tests: 0 failed, 12 passed", "0 errors, 3 passed", "zero failures; 4 passed", "tests: 0 failed",
                    "0 failed, 0 skipped, 12 passed"):
            ok, missing = self.verdict(ref)
            self.assertTrue(ok and not missing, f"refused: {ref!r}")

    def test_failures_and_empty_passes_still_do_not_count(self):
        for ref in ("tests: 5 failed, 0 passed", "0 passed", "12 skipped, 0 failed", "tests: 1 failed, 11 passed",
                    "0 failed, 3 skipped"):
            ok, missing = self.verdict(ref)
            self.assertTrue(missing, ref)

    def test_path_like_refs_are_not_judged_as_prose(self):
        for ref in ("docs/skipped-cases.md#pending", "file:x#1", "tests/failed/run.log", "a.py:12"):
            ok, missing = self.verdict(ref)
            self.assertFalse(missing, ref)

    def test_one_positive_ref_beside_a_non_evidence_one_is_enough(self):
        reg = base()
        reg["records"][1]["evidence"] = [{"ref": "pending review", "observed_at": "2026-11-12T11:00:00Z"},
                                         {"ref": "tests: 0 failed, 12 passed", "observed_at": "2026-11-12T11:00:00Z"}]
        self.assertTrue(check(reg)["ok"])

    def test_partial_register_only_warns(self):
        reg = base("partial")
        reg["records"][1]["evidence"] = [{"ref": "skipped", "observed_at": "2026-11-12T11:00:00Z"}]
        res = check(reg)
        self.assertTrue(res["ok"])
        self.assertIn("missing-evidence", {f["code"] for f in res["findings"]})


# ---------------------------------------------------------------------------------------------------------
class TestD6OneCommitWrittenTwoWaysIsOneCommit(unittest.TestCase):
    def dup(self, ca, cb, complete=True):
        a = hand("r1", source_identity=srcid("o/r", ca))
        b = hand("r2", source_identity=srcid("o/r", cb))
        res = check(regs((a, b), "all-interfaces-complete" if complete else "partial"))
        return "duplicate-record" in errs(res), res

    def test_commit_differing_only_by_case_is_a_duplicate_and_complete_is_refused(self):
        hit, res = self.dup("a" * 40, "A" * 40)
        self.assertTrue(hit)
        self.assertFalse(res["ok"])

    def test_seven_character_prefix_of_the_same_commit_is_a_duplicate(self):
        for short in ("a" * 7, "a" * 12, "A" * 9):
            hit, _ = self.dup("a" * 40, short)
            self.assertTrue(hit, short)

    def test_cli_refuses_complete_naming_both_records(self):
        a = hand("r1", source_identity=srcid("o/r", "a" * 40))
        b = hand("r2", source_identity=srcid("o/r", "A" * 40))
        rc, out = vcli(regs((a, b)))
        self.assertEqual(rc, 1)
        self.assertIn("r1", out)
        self.assertIn("r2", out)
        self.assertIn("duplicate-record", out)

    def test_different_commits_stay_two_endpoints(self):
        for ca, cb in (("a" * 40, "b" * 40), ("a" * 40, "a" * 6 + "b" + "a" * 33), ("a" * 40, "a" * 6), ("a" * 7, "a" * 6 + "b"),
                       ("abcdef0" + "1" * 33, "abcdef0" + "2" * 33)):
            hit, _ = self.dup(ca, cb)
            self.assertFalse(hit, (ca, cb))

    def test_prefix_equivalence_in_the_keyed_grouping(self):
        recs = [hand("r1", source_identity=srcid("o/r", "a" * 40)), hand("r2", source_identity=srcid("o/r", "a" * 8)),
                hand("r3", source_identity=srcid("o/r", "b" * 40))]
        got = [sorted(r["record_id"] for r in g) for g in rv._duplicate_groups(recs)]
        self.assertEqual(got, [["r1", "r2"]])

    def test_extractor_output_still_passes_the_duplicate_check(self):
        rows = [row(source_identity="commit " + "a" * 40), row(source_identity="commit " + "b" * 40, path_or_command="b.py")]
        o = xr.convert(rows, "partial")["register"]
        self.assertNotIn("duplicate-record", {f["code"] for f in check(o)["findings"]})


# ---------------------------------------------------------------------------------------------------------
class TestRedactFastPathEqualsTheFullNormalization(unittest.TestCase):
    """redact() judges printable ASCII without a backslash or percent sign on one view and caches per string; the
    result must equal the full multi-view normalization on every such text."""

    def test_random_printable_ascii_texts_give_the_same_answer_both_ways(self):
        rnd = random.Random(8)
        frag = ["svc@1.2.3", "alice@example.com", "token", "x", " ", "a.b", ":", "//", "https://u:p/x@h.example/a", "ghp_" + "Q" * 20,
                "AKIA" + "Z" * 10, "pkg@2.0.0-rc.1", "[", "]", ",", "REFUSED:", "R2:missing-evidence", "-", "_", "@", "9", "secret=", "k" * 33,
                "Zq9Xw3Lm5Nb7Vc1K4JF2Ew8", "tbd", "bearer", '"', "@localhost", "@[10.0.0.1]"]
        for _ in range(3000):
            t = "".join(rnd.choice(frag) if rnd.random() < .6 else chr(rnd.randint(32, 126)) for _ in range(rnd.randint(1, 8)))
            if "\\" in t or "%" in t:
                continue
            self.assertEqual(ir_norm._redact(t), ir_norm._redact_full(t))

    def test_non_ascii_and_escaped_texts_still_take_the_full_path(self):
        for t in ("alice\uff20example.com", "a%40example.com", "alice\u200b@example.com", "x\ty"):
            self.assertEqual(ir_norm.redact(t), ir_norm._redact_full(t))

    def test_adversarial_long_texts_redact_in_bounded_time(self):
        for t in ("://a:" * 12000, "x@" + "a." * 12000, "a:" * 20000 + "@", '"' + "a" * 60 + '"' + "@" * 3000):
            t0 = time.time()
            ir_norm.redact(t)
            self.assertLess(time.time() - t0, 6.0)

    def test_is_unknown_cache_keeps_the_rule(self):
        for v, exp in (("N/A", True), ("none", True), ("", True), (None, True), (5, True), ("svc", False), ("tbd", True)):
            self.assertEqual(ir_norm.is_unknown(v), exp)


class TestFixtureFiles(unittest.TestCase):
    FIX = Path(__file__).resolve().parent / "fixtures" / "review"

    def test_commit_case_register_fixture_refuses_complete_naming_both_records(self):
        rc, out = run("register_validate.py", self.FIX / "dup_commit_case_register.json", "--now", NOWS)
        self.assertEqual(rc, 1)
        self.assertIn("duplicate-record", out)
        self.assertIn("r1", out)
        self.assertIn("r2", out)

    def test_negated_far_evidence_fixture_gives_no_positive_role(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("extract_register.py", self.FIX / "negated_far_evidence.jsonl", d)
            self.assertEqual(rc, 0)
            recs = json.loads((Path(d) / "register-partial.json").read_text(encoding="utf-8"))["records"]
        self.assertEqual(len(recs), 6)
        self.assertEqual({r["role"] for r in recs}, {"UNKNOWN"})


class TestRealInputUnchanged(unittest.TestCase):
    def test_real_input_extracts_and_complete_is_refused_naming_records(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("extract_register.py", REAL, d)
            self.assertEqual(rc, 0)
            self.assertIn("records: 507", out)
            rc, out = run("register_validate.py", Path(d) / "register-partial.json", "--now", NOWS)
            self.assertEqual(rc, 0, out[-300:])
            rc, out = run("register_validate.py", Path(d) / "register-declared-complete.json", "--now", NOWS)
            self.assertEqual(rc, 1)
            self.assertIn("REFUSED: declared all-interfaces-complete but gaps remain in:", out)


if __name__ == "__main__":
    unittest.main()
