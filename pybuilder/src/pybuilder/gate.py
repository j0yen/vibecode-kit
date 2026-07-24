"""Risk gate — receipt-based ready/blocked. No self-approval.

Mirrors autobuilder's Stage-4 gate: a project is ``ready`` only when every required
receipt passes. Required receipts depend on the target: deterministic targets
(cli/lib) need intake/scaffold-integrity/proof/audit/reviewer/ci; agent (LLM-bearing)
targets additionally need eval-vector (no regression), stability (not underspecified),
and dataset-provenance. Missing, failed, stale, or — for LLM-bearing artifacts —
unavailable receipts block, with a machine-readable diagnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .receipts import Receipt, ReceiptStore, Verdict

# Receipts every target must satisfy.
DETERMINISTIC_RECEIPTS = ["intake", "scaffold-integrity", "proof", "audit", "reviewer", "ci-checks"]
# Additional receipts for LLM-bearing (agent) targets.
LLM_RECEIPTS = ["eval-vector", "stability", "dataset-provenance"]


def required_receipts(target: str) -> list[str]:
    base = list(DETERMINISTIC_RECEIPTS)
    if target == "agent":
        base += LLM_RECEIPTS
    return base


@dataclass
class GateVerdict:
    ready: bool
    target: str
    failures: list[dict[str, Any]] = field(default_factory=list)
    concerns: list[dict[str, Any]] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)  # receipts skipped via degradation
    checked: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "target": self.target,
            "failures": self.failures,
            "concerns": self.concerns,
            "degraded": self.degraded,
            "checked": self.checked,
        }


def evaluate_gate(
    store: ReceiptStore,
    target: str,
    *,
    allow_degraded: bool = True,
) -> GateVerdict:
    """Decide ready/blocked from the receipts in ``store``.

    - Missing or stale receipt → failure (no passing on stale evidence).
    - ``BLOCK`` verdict → failure. ``CONCERN`` → non-fatal concern the loop must
      address before the next gate (autobuilder parity).
    - ``UNAVAILABLE`` → for a deterministic target with ``allow_degraded`` it is a
      stated degradation (cli/lib may pass without eval packages); for an agent
      target it is a failure (an LLM-bearing artifact must prove its eval dims).
    """
    failures: list[dict[str, Any]] = []
    concerns: list[dict[str, Any]] = []
    degraded: list[str] = []
    required = required_receipts(target)

    for name in required:
        receipt = store.read(name)
        if receipt is None:
            failures.append({"receipt": name, "reason": "missing"})
            continue
        if store.is_stale(receipt):
            failures.append(
                {"receipt": name, "reason": f"stale (commit {receipt.commit} != HEAD)"}
            )
            continue
        _classify(name, receipt, target, allow_degraded, failures, concerns, degraded)

    return GateVerdict(
        ready=not failures,
        target=target,
        failures=failures,
        concerns=concerns,
        degraded=degraded,
        checked=required,
    )


def _classify(
    name: str,
    receipt: Receipt,
    target: str,
    allow_degraded: bool,
    failures: list[dict[str, Any]],
    concerns: list[dict[str, Any]],
    degraded: list[str],
) -> None:
    if receipt.verdict is Verdict.PASS:
        return
    if receipt.verdict is Verdict.CONCERN:
        concerns.append({"receipt": name, "detail": receipt.detail})
        return
    if receipt.verdict is Verdict.UNAVAILABLE:
        is_eval_receipt = name in LLM_RECEIPTS
        if target != "agent" and is_eval_receipt and allow_degraded:
            degraded.append(name)
            return
        failures.append({"receipt": name, "reason": "unavailable", "detail": receipt.detail})
        return
    # BLOCK
    failures.append({"receipt": name, "reason": "block", "detail": receipt.detail})
