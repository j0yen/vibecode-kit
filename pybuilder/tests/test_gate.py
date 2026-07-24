"""Risk gate: receipt-based ready/blocked, no self-approval, no stale passes."""

from __future__ import annotations

from pathlib import Path

from pybuilder.gate import DETERMINISTIC_RECEIPTS, LLM_RECEIPTS, evaluate_gate
from pybuilder.receipts import Receipt, ReceiptStore, Verdict


def _store(tmp_path: Path) -> ReceiptStore:
    return ReceiptStore(tmp_path)


def _pass_all(store: ReceiptStore, names: list[str]) -> None:
    for n in names:
        store.write(Receipt(n, Verdict.PASS))


def test_all_pass_is_ready_for_lib(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _pass_all(store, DETERMINISTIC_RECEIPTS)
    verdict = evaluate_gate(store, "lib")
    assert verdict.ready is True


def test_missing_receipt_blocks(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _pass_all(store, [n for n in DETERMINISTIC_RECEIPTS if n != "reviewer"])
    verdict = evaluate_gate(store, "lib")
    assert verdict.ready is False
    assert any(f["receipt"] == "reviewer" and f["reason"] == "missing" for f in verdict.failures)


def test_block_verdict_blocks(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _pass_all(store, [n for n in DETERMINISTIC_RECEIPTS if n != "audit"])
    store.write(Receipt("audit", Verdict.BLOCK, "bare-except found"))
    verdict = evaluate_gate(store, "lib")
    assert verdict.ready is False


def test_concern_is_non_fatal(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _pass_all(store, [n for n in DETERMINISTIC_RECEIPTS if n != "reviewer"])
    store.write(Receipt("reviewer", Verdict.CONCERN, "naming nit"))
    verdict = evaluate_gate(store, "lib")
    assert verdict.ready is True
    assert verdict.concerns


def test_agent_requires_eval_receipts(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _pass_all(store, DETERMINISTIC_RECEIPTS)  # deterministic ones only
    verdict = evaluate_gate(store, "agent")
    assert verdict.ready is False
    missing = {f["receipt"] for f in verdict.failures}
    assert set(LLM_RECEIPTS) <= missing


def test_lib_degrades_on_unavailable_eval_but_agent_does_not(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _pass_all(store, DETERMINISTIC_RECEIPTS)
    for n in LLM_RECEIPTS:
        store.write(Receipt(n, Verdict.UNAVAILABLE, "eval pkg absent"))
    # lib: eval receipts not even required, so ready and nothing degraded for them
    assert evaluate_gate(store, "lib").ready is True
    # agent: unavailable eval receipts are required -> block
    assert evaluate_gate(store, "agent").ready is False


def test_stale_receipt_is_treated_as_missing(tmp_path: Path) -> None:
    # init a real repo so HEAD exists and we can fake a divergent commit
    import subprocess

    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "--allow-empty", "-q", "-m", "x"],
        check=True,
    )
    store = _store(tmp_path)
    _pass_all(store, [n for n in DETERMINISTIC_RECEIPTS if n != "proof"])
    stale = Receipt("proof", Verdict.PASS, commit="deadbee")  # not current HEAD
    store.write(stale)
    verdict = evaluate_gate(store, "lib")
    assert verdict.ready is False
    assert any(f["receipt"] == "proof" and "stale" in f["reason"] for f in verdict.failures)
