"""Multi-dimensional, log-don't-assert evaluation.

The centerpiece. Instead of a single ``assert expected == actual`` that aborts on
first miss, evaluation records a *vector* of dimension scores per run and keeps
every dimension's evidence even when one fails:

- :mod:`pybuilder.eval.dimensions` — the five dimensions and their registry.
- :mod:`pybuilder.eval.results_bag` — the log-don't-assert recorder + CSV/DataFrame.
- :mod:`pybuilder.eval.vector` — collapse a row's dimensions to a quality vector.
"""

from .dimensions import (
    DimensionResult,
    Status,
    evaluate_all,
    exact,
    fuzzy,
    register,
    registry,
    static,
)
from .results_bag import ResultsBag, Row
from .vector import QualityVector, weighted_aggregate

__all__ = [
    "DimensionResult",
    "QualityVector",
    "ResultsBag",
    "Row",
    "Status",
    "evaluate_all",
    "exact",
    "fuzzy",
    "register",
    "registry",
    "static",
    "weighted_aggregate",
]
