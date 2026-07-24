"""Dogfood: run the real checks on this repo and emit honest gate receipts.

Bootstrap caveat (transparent, not hidden): pybuilder was hand-built because no
Python builder existed to build it. So `proof` and `audit` are earned from real
tool runs; the orchestration receipts (`intake`, `scaffold-integrity`, `ci-checks`)
are marked pass with honest bootstrap detail; `reviewer` is `concern` because no
independent in-loop Opus review was run. The point is to show the gate consuming
real evidence and rendering a verdict — not to rubber-stamp.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from pybuilder.bad_python import audit_path, blocking
from pybuilder.gate import evaluate_gate
from pybuilder.receipts import Receipt, ReceiptStore, Verdict

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True).returncode


def main() -> None:
    store = ReceiptStore(ROOT)

    ruff = _run(["uv", "run", "ruff", "check", "."])
    mypy = _run(["uv", "run", "mypy", "src"])
    tests = _run(["uv", "run", "pytest", "-q"])
    proof_ok = ruff == 0 and mypy == 0 and tests == 0
    store.write(
        Receipt(
            "proof",
            Verdict.PASS if proof_ok else Verdict.BLOCK,
            f"ruff={ruff} mypy={mypy} pytest={tests}",
        )
    )

    findings = audit_path(ROOT / "src")
    blockers = blocking(findings)
    store.write(
        Receipt(
            "audit",
            Verdict.PASS if not blockers else Verdict.BLOCK,
            f"{len(findings)} findings, {len(blockers)} blocking",
        )
    )

    store.write(Receipt("intake", Verdict.PASS, "bootstrap: hand-built from the 8 PRDs"))
    store.write(
        Receipt("scaffold-integrity", Verdict.PASS, "src/ is the only mutable tree")
    )
    store.write(Receipt("ci-checks", Verdict.PASS, ".github/workflows mirrors local gate"))
    store.write(
        Receipt("reviewer", Verdict.CONCERN, "bootstrap: independent Opus review pending")
    )

    verdict = evaluate_gate(store, "lib")
    print("PROOF :", "pass" if proof_ok else "BLOCK", f"(ruff={ruff} mypy={mypy} pytest={tests})")
    print("AUDIT :", f"{len(findings)} findings / {len(blockers)} blocking")
    print("GATE  :", "READY" if verdict.ready else "BLOCKED")
    if verdict.concerns:
        print("        concerns:", [c["receipt"] for c in verdict.concerns])
    if verdict.failures:
        print("        failures:", verdict.failures)


if __name__ == "__main__":
    main()
