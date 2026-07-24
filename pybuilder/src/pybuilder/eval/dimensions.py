"""The evaluation dimensions and their plugin registry.

Five dimensions, per the TDD-of-LLM-applications article:

- ``exact``  — normalized equality (0 or 1).
- ``fuzzy``  — lexical token-set similarity in [0, 1] (deterministic, no model).
- ``static`` — lint/type/format/length signals folded to [0, 1] from metrics.json.
- ``human``  — a logged grade slot; ``n/a`` until a human fills it.
- ``judge``  — LLM-as-judge; registered by :mod:`pybuilder.judge` when available.

Dimensions are plugins: register a new one with :func:`register` and it shows up
in :func:`evaluate_all` without editing the harness core. A dimension that raises
is recorded as ``dimension_error`` for that row and never aborts the suite.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    OK = "ok"
    NA = "n/a"  # no expected value / not applicable
    DIMENSION_ERROR = "dimension_error"  # the dimension raised
    UNAVAILABLE = "unavailable"  # e.g. judge has no provider/key
    LOW_CONFIDENCE = "low_confidence"  # e.g. judge variance too high


@dataclass(frozen=True)
class DimensionResult:
    """One dimension's verdict on one (expected, actual) pair."""

    name: str
    score: float | None  # in [0, 1] when status is OK, else None
    status: Status = Status.OK
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "status": self.status.value,
            "detail": self.detail,
        }


# A dimension takes (expected, actual, context) and returns a DimensionResult.
# expected may be None (exploratory run with no gold value).
Dimension = Callable[[Any, Any, Mapping[str, Any]], DimensionResult]

_REGISTRY: dict[str, Dimension] = {}


def register(name: str, fn: Dimension) -> None:
    """Register (or replace) a dimension by name."""
    _REGISTRY[name] = fn


def registry() -> dict[str, Dimension]:
    """A copy of the current dimension registry."""
    return dict(_REGISTRY)


def evaluate_all(
    expected: Any,
    actual: Any,
    context: Mapping[str, Any] | None = None,
    *,
    dimensions: list[str] | None = None,
) -> list[DimensionResult]:
    """Run every (or the named) dimension; isolate failures per dimension.

    A dimension that raises becomes a ``dimension_error`` result — the other
    dimensions still run. This is the log-don't-assert contract at the dimension
    level; :class:`~pybuilder.eval.results_bag.ResultsBag` enforces it at the row
    and suite level.
    """
    ctx: Mapping[str, Any] = context or {}
    names = dimensions if dimensions is not None else list(_REGISTRY)
    results: list[DimensionResult] = []
    for name in names:
        fn = _REGISTRY.get(name)
        if fn is None:
            results.append(
                DimensionResult(name, None, Status.UNAVAILABLE, "dimension not registered")
            )
            continue
        try:
            results.append(fn(expected, actual, ctx))
        except Exception as exc:  # noqa: BLE001 — isolating one dimension's failure is the point
            results.append(
                DimensionResult(name, None, Status.DIMENSION_ERROR, f"{type(exc).__name__}: {exc}")
            )
    return results


# --- built-in dimensions ------------------------------------------------------

_WORD = re.compile(r"\w+")


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def exact(expected: Any, actual: Any, context: Mapping[str, Any]) -> DimensionResult:
    """Normalized equality. ``n/a`` when there is no expected value."""
    if expected is None:
        return DimensionResult("exact", None, Status.NA, "no expected value")
    score = 1.0 if _normalize(expected) == _normalize(actual) else 0.0
    return DimensionResult("exact", score)


def fuzzy(expected: Any, actual: Any, context: Mapping[str, Any]) -> DimensionResult:
    """Lexical token-set similarity (Jaccard over word tokens), in [0, 1].

    Deterministic and model-free — a free near-miss signal an exact check throws
    away. (An embedding-based semantic variant is vision OQ-1; this is the v1
    default precisely because it is deterministic and offline.)
    """
    if expected is None:
        return DimensionResult("fuzzy", None, Status.NA, "no expected value")
    a = set(_WORD.findall(_normalize(expected)))
    b = set(_WORD.findall(_normalize(actual)))
    if not a and not b:
        return DimensionResult("fuzzy", 1.0, detail="both empty")
    inter = len(a & b)
    union = len(a | b)
    return DimensionResult("fuzzy", inter / union if union else 0.0)


def static(expected: Any, actual: Any, context: Mapping[str, Any]) -> DimensionResult:
    """Fold static signals from ``context['metrics']`` into a [0, 1] score.

    Reads the same ``metrics.json`` the scaffold's ``run-metrics`` emits, so the
    lint/type/test floor is not recomputed here. Score is the fraction of the
    available static gates that passed.
    """
    metrics = context.get("metrics")
    if not isinstance(metrics, Mapping):
        return DimensionResult("static", None, Status.NA, "no metrics in context")
    gates: list[bool] = []
    if "ruff_errors" in metrics:
        gates.append(int(metrics["ruff_errors"]) == 0)
    if "mypy_errors" in metrics:
        gates.append(int(metrics["mypy_errors"]) == 0)
    if "tests_failing" in metrics:
        gates.append(int(metrics["tests_failing"]) == 0)
    if "coverage_pct" in metrics:
        gates.append(float(metrics["coverage_pct"]) >= float(metrics.get("coverage_min", 0)))
    if not gates:
        return DimensionResult("static", None, Status.NA, "no recognized static metrics")
    return DimensionResult("static", sum(gates) / len(gates))


def human(expected: Any, actual: Any, context: Mapping[str, Any]) -> DimensionResult:
    """Logged human-grade slot. ``n/a`` until a grade is supplied in context."""
    grade = context.get("human_grade")
    if grade is None:
        return DimensionResult("human", None, Status.NA, "awaiting human grade")
    return DimensionResult("human", float(grade))


# Register the four model-free built-ins. `judge` is registered by pybuilder.judge.
register("exact", exact)
register("fuzzy", fuzzy)
register("static", static)
register("human", human)
