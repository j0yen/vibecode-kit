"""LLM-judge: rubric guards, offline degradation, calibration, stability self-guard."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from pybuilder.eval.dimensions import Status
from pybuilder.judge import (
    RubricError,
    calibration_agreement,
    judge_dimension,
    validate_rubric,
)


def test_rubric_rejects_length_criterion() -> None:
    with pytest.raises(RubricError, match="forbidden criterion"):
        validate_rubric(["answer is faithful", "answer is longer than 3 sentences"])


def test_judge_unavailable_without_backend_is_not_a_fake_score() -> None:
    dim = judge_dimension(backend=None)
    res = dim("expected", "actual", {"rubric": ["faithful to context"]})
    assert res.status is Status.UNAVAILABLE
    assert res.score is None  # never fabricates a number


def test_judge_na_without_rubric() -> None:
    dim = judge_dimension(backend=None)
    res = dim("e", "a", {})
    assert res.status is Status.NA


def test_judge_low_confidence_on_high_variance() -> None:
    class FlakyBackend:
        def __init__(self) -> None:
            self.calls = 0

        def score(self, rubric: Sequence[str], artifact: str) -> float:
            self.calls += 1
            return 0.1 if self.calls % 2 else 0.9  # wild swing

    dim = judge_dimension(backend=FlakyBackend(), repeats=4, variance_tol=0.15)
    res = dim("e", "a", {"rubric": ["faithful"]})
    assert res.status is Status.LOW_CONFIDENCE


def test_judge_uncalibrated_note_when_not_calibrated() -> None:
    class Steady:
        def score(self, rubric: Sequence[str], artifact: str) -> float:
            return 0.8

    dim = judge_dimension(backend=Steady(), calibrated=False)
    res = dim("e", "a", {"rubric": ["faithful"]})
    assert res.status is Status.OK
    assert "uncalibrated" in res.detail


def test_calibration_agreement_perfect_correlation() -> None:
    rho = calibration_agreement([0.1, 0.5, 0.9], [0.2, 0.6, 1.0])
    assert rho > 0.99


def test_calibration_degenerate_returns_zero() -> None:
    assert calibration_agreement([0.5], [0.5]) == 0.0
    assert calibration_agreement([0.5, 0.5], [0.5, 0.5]) == 0.0


def _ignore_unused(*_a: Any, **_k: Mapping[str, Any]) -> None:  # keep imports honest
    pass
