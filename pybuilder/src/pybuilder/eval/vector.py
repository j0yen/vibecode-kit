"""Quality vector — collapse a row's dimensions into the signal the loop reads.

autobuilder advances on a single scalar score. pybuilder advances on a *vector*:
the per-dimension mean plus a configurable weighted aggregate. An LLM-app weights
``judge``/``fuzzy`` high; a deterministic lib weights ``exact``/``static`` high.
The loop's advance rule is "net aggregate improvement AND no MUST-AC regression",
evaluated by :mod:`pybuilder.gate`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from .dimensions import Status
from .results_bag import Row

# Sensible starting weights per target (vision OQ-2 calibrates these in dogfood).
DEFAULT_WEIGHTS: dict[str, dict[str, float]] = {
    "cli": {"exact": 0.4, "static": 0.4, "fuzzy": 0.1, "judge": 0.1},
    "lib": {"exact": 0.35, "static": 0.45, "fuzzy": 0.1, "judge": 0.1},
    "agent": {"judge": 0.4, "fuzzy": 0.3, "exact": 0.1, "static": 0.2},
}


@dataclass(frozen=True)
class QualityVector:
    """Per-dimension means across a set of rows, plus a weighted aggregate."""

    per_dimension: dict[str, float]
    aggregate: float
    # dimensions that contributed no OK score (all n/a / error / unavailable)
    skipped: list[str] = field(default_factory=list)

    def regressed_against(self, baseline: QualityVector, *, tol: float = 1e-9) -> bool:
        """True if the weighted aggregate dropped below ``baseline`` beyond ``tol``."""
        return self.aggregate < baseline.aggregate - tol


def _ok_scores(rows: Sequence[Row], dimension: str) -> list[float]:
    out: list[float] = []
    for row in rows:
        for r in row.results:
            if r.name == dimension and r.status is Status.OK and r.score is not None:
                out.append(r.score)
    return out


def weighted_aggregate(
    rows: Sequence[Row],
    weights: Mapping[str, float],
) -> QualityVector:
    """Compute the quality vector over ``rows`` using ``weights``.

    A dimension with no OK scores is dropped from the weighted mean and reported
    in ``skipped`` (so an absent/unavailable judge neither helps nor silently
    tanks the aggregate). Weights are renormalized over the dimensions that
    actually contributed.
    """
    per_dim: dict[str, float] = {}
    skipped: list[str] = []
    for dim in weights:
        scores = _ok_scores(rows, dim)
        if scores:
            per_dim[dim] = sum(scores) / len(scores)
        else:
            skipped.append(dim)

    contributing = {d: w for d, w in weights.items() if d in per_dim}
    total_w = sum(contributing.values())
    if total_w <= 0:
        aggregate = 0.0
    else:
        aggregate = sum(per_dim[d] * (w / total_w) for d, w in contributing.items())
    return QualityVector(per_dimension=per_dim, aggregate=aggregate, skipped=skipped)
