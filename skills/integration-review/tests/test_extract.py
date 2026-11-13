"""extract_register.py: evidence-faithful conversion of endpoints.jsonl rows into register records.

Fixtures are synthetic source-only rows; they prove the conversion rules, not production behavior."""
import json
import sys
import unittest
from pathlib import Path

from test_register import check, codes

SK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SK / "scripts"))
import extract_register as ex  # noqa: E402

SHA = "ab" * 32
COMMIT = "12" * 20


def row(**kw):
    r = {"family": "IF001", "role": "producer", "host": "carbon", "component": "svc",
         "path_or_command": "/p/svc", "interface_kind": "event", "source_repo": "UNKNOWN",
         "source_identity": "UNKNOWN", "installed_state": "UNKNOWN",
         "evidence": "register.json[0]; note.md:5", "classification": "unclassified"}
    r.update(kw)
    return r


def conv(rows, declared="partial"):
    return ex.convert(rows, declared, heuristic_fusion=True)     # the pinned fusion tests run the opt-in heuristic


def one(r):
    out = conv([r])
    return out["register"]["records"][0]


class Identity(unittest.TestCase):
    def test_path_sha_parsed_and_raw_kept(self):
        s = f"path+sha256:/home/x/bin/y {SHA}"
        rec = one(row(source_identity=s, installed_state="installed", source_repo="deploy"))
        si = rec["source_identity"]
        self.assertEqual((si["path"], si["sha256"], si["repo"]), ("/home/x/bin/y", SHA, "deploy"))
        self.assertEqual(si["raw"], s)
        self.assertTrue(si["available"])
        self.assertEqual(rec["installed_state"], "installed")

    def test_commit_parsed(self):
        rec = one(row(source_identity=f"commit {COMMIT}", installed_state="source-only", source_repo="wm-build"))
        self.assertEqual(rec["source_identity"]["commit"], COMMIT)
        self.assertEqual(rec["source_identity"]["version"], COMMIT)
        self.assertEqual(rec["installed_state"], "source-only")

    def test_unstated_identity_is_unknown_not_guessed(self):
        rec = one(row(source_identity="UNKNOWN"))
        si = rec["source_identity"]
        self.assertEqual(si["version"], "UNKNOWN")
        self.assertFalse(si["available"])
        self.assertNotIn("commit", si)
        self.assertNotIn("sha256", si)
        self.assertEqual(si["raw"], "UNKNOWN")

    def test_hex_without_stated_form_not_parsed(self):
        s = f"see {COMMIT} and {SHA} somewhere"
        si = one(row(source_identity=s))["source_identity"]
        self.assertEqual(si["version"], "UNKNOWN")
        self.assertEqual(si["raw"], s)

    def test_nonstring_identity_unknown(self):
        si = one(row(source_identity=12345))["source_identity"]
        self.assertEqual(si["version"], "UNKNOWN")


class Sides(unittest.TestCase):
    def test_mechanical_side_becomes_unknown_claim_kept(self):
        for claimed in ("producer", "consumer", "caller", "adapter"):
            rec = one(row(role=claimed))
            self.assertEqual(rec["role"], "UNKNOWN", claimed)
            self.assertEqual(rec["claimed_roles"], [claimed])

    def test_side_kept_only_when_row_evidence_states_it(self):
        rec = one(row(role="consumer", evidence="reading ctl-event-wait.sh:12 side=consumer"))
        self.assertEqual(rec["role"], "consumer")

    def test_side_marker_for_other_side_not_accepted(self):
        rec = one(row(role="consumer", evidence="side=producer"))
        self.assertEqual(rec["role"], "UNKNOWN")


class Installed(unittest.TestCase):
    def test_loaded_from_unit_listing_never_loaded(self):
        rec = one(row(installed_state="loaded"))
        self.assertEqual(rec["installed_state"], "UNKNOWN")
        self.assertEqual(rec["claimed_installed_states"], ["loaded"])

    def test_loaded_with_path_sha_still_not_loaded(self):
        rec = one(row(installed_state="loaded", source_identity=f"path+sha256:/a/b {SHA}"))
        self.assertNotEqual(rec["installed_state"], "loaded")

    def test_installed_without_path_sha_is_unknown(self):
        rec = one(row(installed_state="installed", source_identity="UNKNOWN"))
        self.assertEqual(rec["installed_state"], "UNKNOWN")
        self.assertEqual(rec["claimed_installed_states"], ["installed"])

    def test_source_only_needs_stated_commit(self):
        self.assertEqual(one(row(installed_state="source-only"))["installed_state"], "UNKNOWN")


class Evidence(unittest.TestCase):
    def test_long_evidence_verbatim_not_truncated(self):
        e = "x; " * 400 + "end"
        rec = one(row(evidence=e))
        self.assertEqual(rec["evidence"], [{"ref": e}])

    def test_missing_evidence_recorded_missing(self):
        for e in (None, "", "   ", []):
            rec = one(row(evidence=e))
            self.assertEqual(rec["evidence"], [], repr(e))
        out = conv([row(evidence=None)])
        self.assertIn("missing-evidence", codes(check(out["register"])))

    def test_list_evidence_each_ref_verbatim(self):
        rec = one(row(evidence=["a ; b", "c"]))
        self.assertEqual([e["ref"] for e in rec["evidence"]], ["a ; b", "c"])

    def test_row_timestamps_passed_through_and_stale_detected(self):
        r = row(source_identity=f"commit {COMMIT}", installed_state="source-only",
                captured_at="2026-11-12T10:00:00Z", observed_at="2026-11-12T09:00:00Z")
        out = conv([r])
        self.assertIn("stale-evidence", codes(check(out["register"])))
        out = conv([r], "all-interfaces-complete")
        self.assertFalse(check(out["register"])["ok"])

    def test_row_has_no_invented_timestamps(self):
        rec = one(row())
        self.assertNotIn("captured_at", rec["source_identity"])
        self.assertNotIn("observed_at", rec["evidence"][0])


class Malformed(unittest.TestCase):
    def test_bad_lines_rejected_not_filled(self):
        lines = [json.dumps(row()), "{not json", json.dumps([1, 2]), "", json.dumps(row(component="b", path_or_command="/b"))]
        out = ex.convert_lines(lines, "partial")
        self.assertEqual(len(out["register"]["records"]), 2)
        self.assertEqual([r["line"] for r in out["rejected"]], [2, 3])
        self.assertTrue(out["rejected"][0]["reason"])

    def test_missing_family_goes_unassigned_not_guessed(self):
        r = row()
        del r["family"]
        rec = one(r)
        self.assertEqual(rec["family"], "UNASSIGNED")

    def test_missing_or_mistyped_fields_unknown(self):
        r = row(host=5, component=None)
        del r["interface_kind"]
        rec = one(r)
        self.assertEqual(rec["host"], "UNKNOWN")
        self.assertEqual(rec["component"], "UNKNOWN")
        self.assertEqual(rec["interface_kind"], "other")
        out = conv([r], "all-interfaces-complete")
        self.assertFalse(check(out["register"])["ok"])

    def test_extractor_never_labels_or_invents_effects(self):
        rec = one(row())
        self.assertEqual(rec["label"], "unclassified")
        self.assertNotIn("effect_state", rec)
        self.assertNotIn("replay", rec)


class MultiSourceAndIdentity(unittest.TestCase):
    def pair(self):
        return [row(component="ctx", role="consumer", source_repo="summa", path_or_command="summa/README.md",
                    source_identity=f"commit {COMMIT}", installed_state="source-only", evidence="e-summa"),
                row(component="ctx", role="consumer", source_repo="recall", path_or_command="recall/README.md",
                    source_identity=f"commit {'34' * 20}", installed_state="source-only", evidence="e-recall")]

    def test_summa_recall_one_component_two_sources_no_qualifier(self):
        recs = conv(self.pair())["register"]["records"]
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertEqual(r["component"], "ctx")
        self.assertNotIn("source_identity", r)
        self.assertEqual([s["repo"] for s in r["sources"]], ["summa", "recall"])
        self.assertEqual([s["path_or_command"] for s in r["sources"]], ["summa/README.md", "recall/README.md"])
        self.assertEqual([s["raw"] for s in r["sources"]], [f"commit {COMMIT}", f"commit {'34' * 20}"])
        self.assertEqual([e["ref"] for e in r["evidence"]], ["e-summa", "e-recall"])
        self.assertNotIn("path_or_command", r)
        self.assertEqual(r["source_rows"], [1, 2])

    def test_same_repo_different_paths_stay_two_endpoints(self):
        rows = [row(component="c", path_or_command="/a", source_repo="deploy"),
                row(component="c", path_or_command="/b", source_repo="deploy")]
        recs = conv(rows)["register"]["records"]
        self.assertEqual(len(recs), 2)
        self.assertEqual({r["path_or_command"] for r in recs}, {"/a", "/b"})
        self.assertNotIn("duplicate-record", codes(check(conv(rows)["register"])))

    def test_unknown_repos_never_merged(self):
        rows = [row(component="c", path_or_command="/a"), row(component="c", path_or_command="/b")]
        self.assertEqual(len(conv(rows)["register"]["records"]), 2)

    def test_true_duplicate_rows_merge_evidence_once(self):
        rows = [row(evidence="e1"), row(evidence="e2"), row(evidence="e1")]
        recs = conv(rows)["register"]["records"]
        self.assertEqual(len(recs), 1)
        self.assertEqual([e["ref"] for e in recs[0]["evidence"]], ["e1", "e2"])
        self.assertEqual(recs[0]["source_rows"], [1, 2, 3])

    def test_differing_states_across_merged_rows_become_unknown(self):
        rows = [row(installed_state="source-only", source_identity=f"commit {COMMIT}"),
                row(installed_state="installed", source_identity=f"path+sha256:/a {SHA}")]
        recs = conv(rows)["register"]["records"]
        self.assertEqual(len(recs), 1)  # same endpoint key, same (unknown) repo, same path
        self.assertEqual(recs[0]["installed_state"], "UNKNOWN")
        self.assertEqual(len(recs[0]["sources"]), 2)


class Unassigned(unittest.TestCase):
    def test_unassigned_rows_kept_and_counted(self):
        rows = [row(), row(family="UNASSIGNED", component="u1", path_or_command="/u1"),
                row(family="UNASSIGNED", component="u2", path_or_command="/u2", role="UNKNOWN")]
        out = conv(rows)
        res = check(out["register"])
        self.assertTrue(res["ok"], res["findings"])
        self.assertEqual(res["counts"]["unassigned"], 2)
        self.assertEqual(res["counts"]["records"], 3)
        self.assertEqual(out["stats"]["unassigned_records"], 2)
        self.assertEqual([f["id"] for f in out["register"]["families"]], ["IF001"])

    def test_complete_declaration_refused_naming_unassigned(self):
        rows = [row(), row(family="UNASSIGNED", component="u1", path_or_command="/u1")]
        res = check(conv(rows, "all-interfaces-complete")["register"])
        self.assertFalse(res["ok"])
        self.assertTrue([f for f in res["findings"] if f["code"] == "unassigned" and f["severity"] == "error"])


if __name__ == "__main__":
    unittest.main()
