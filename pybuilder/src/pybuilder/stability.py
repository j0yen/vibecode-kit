"""Stability runner — turn "flaky" into a spec signal.

Run an artifact N times on the *same* input, score each run through the eval
harness, and classify the variance. The article's key insight: high variance is
often an *underspecified prompt* (a spec bug you fix) rather than acceptable LLM
noise (a property you accept) — and you cannot tell which from a single run.

Classification (against a configurable band on a chosen correctness dimension):
- ``UNKNOWN``         — N < 2; variance undefined, stability unmeasured.
- ``STABLE``          — spread within band (incl. deterministic artifacts).
- ``ACCEPTABLE_NOISE``— spread modest and not concentrated in correctness.
- ``UNDERSPECIFIED``  — correctness dimension swings widely → fix the spec/prompt,
  do not retry the test.
"""

from __future__ import annotations

import statistics
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .eval.dimensions import Status
from .eval.results_bag import ResultsBag, Row


class Classification(StrEnum):
    UNKNOWN = "unknown"
    STABLE = "stable"
    ACCEPTABLE_NOISE = "acceptable-noise"
    UNDERSPECIFIED = "underspecified"


@dataclass
class StabilityReport:
    classification: Classification
    n_requested: int
    n_completed: int
    correctness_dimension: str
    correctness_spread: float
    scores: list[float | None]
    partial: bool = False
    spec_signal: str = ""  # non-empty when UNDERSPECIFIED — points at the prompt/card
    rows: list[Row] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification.value,
            "n_requested": self.n_requested,
            "n_completed": self.n_completed,
            "correctness_dimension": self.correctness_dimension,
            "correctness_spread": self.correctness_spread,
            "scores": self.scores,
            "partial": self.partial,
            "spec_signal": self.spec_signal,
        }


def run_stability(
    artifact: Callable[[], Any],
    expected: Any,
    *,
    n: int = 10,
    context: Mapping[str, Any] | None = None,
    correctness_dimension: str = "exact",
    band: float = 0.2,
    max_runs: int | None = None,
    test_id: str = "stability",
) -> StabilityReport:
    """Execute ``artifact`` up to ``n`` times and classify the output variance.

    ``artifact`` is a zero-arg callable returning the output to evaluate. A run
    that raises is recorded as a failed sample (it counts toward variance — a
    1-in-N crash is exactly the signal), not discarded. ``max_runs`` caps the
    sweep; hitting it yields a ``partial`` report classified on what was gathered.
    """
    bag = ResultsBag()
    ctx = context or {}
    ceiling = n if max_runs is None else min(n, max_runs)
    deterministic_short_circuit = False
    seen_outputs: set[str] = set()

    completed = 0
    for i in range(ceiling):
        try:
            out: Any = artifact()
            seen_outputs.add(repr(out))
        except Exception as exc:  # noqa: BLE001 — a crash is a sample, not an abort
            bag.record(
                f"{test_id}#{i}",
                expected,
                None,
                {**ctx, "crashed": f"{type(exc).__name__}: {exc}"},
                dimensions=[correctness_dimension],
            )
            completed += 1
            continue
        bag.record(f"{test_id}#{i}", expected, out, ctx, dimensions=[correctness_dimension])
        completed += 1
        # Deterministic short-circuit: if the first 2 runs are byte-identical and
        # the context declares no nondeterministic call, stop early as STABLE.
        if i == 1 and len(seen_outputs) == 1 and not ctx.get("nondeterministic", True):
            deterministic_short_circuit = True
            break

    scores = [row.score(correctness_dimension) for row in bag.rows]
    ok_scores = [s for s in scores if s is not None]

    if completed < 2:
        return StabilityReport(
            Classification.UNKNOWN, n, completed, correctness_dimension, 0.0, scores,
            rows=bag.rows,
        )

    spread = (max(ok_scores) - min(ok_scores)) if len(ok_scores) >= 2 else 0.0
    # any crash counts as instability even if the OK scores agree
    crashed = any(
        r.status is not Status.OK and r.status is not Status.NA
        for row in bag.rows
        for r in row.results
    )

    if deterministic_short_circuit or (spread == 0.0 and not crashed):
        classification = Classification.STABLE
        spec_signal = ""
    elif spread > band:
        classification = Classification.UNDERSPECIFIED
        spec_signal = (
            f"correctness dimension {correctness_dimension!r} spread {spread:.3f} > band {band}: "
            "the prompt/intent-card under-constrains the output — fix the spec, do not retry."
        )
    else:
        classification = Classification.ACCEPTABLE_NOISE
        spec_signal = ""

    return StabilityReport(
        classification=classification,
        n_requested=n,
        n_completed=completed,
        correctness_dimension=correctness_dimension,
        correctness_spread=spread,
        scores=scores,
        partial=ceiling < n,
        spec_signal=spec_signal,
        rows=bag.rows,
    )


def variance(scores: Sequence[float]) -> float:
    """Population variance helper (0.0 for n < 2)."""
    return statistics.pvariance(scores) if len(scores) >= 2 else 0.0
