"""LLM-as-judge dimension — calibrated, always-Opus, stability-guarded.

The fifth dimension: grade an artifact against a declarative rubric using the
strongest model (Opus), independent of whatever produced the artifact (autobuilder's
"independent verification is where you spend the strongest model").

Safeguards, so the judge is not itself a source of confident-wrong scores:
- Rubrics forbid length/style-as-quality criteria (:func:`validate_rubric`).
- The judge self-marks ``low_confidence`` when repeat judgments diverge.
- Without the ``anthropic`` package or an API key, the dimension records
  ``unavailable`` rather than a fabricated number — and the gate refuses to
  weight an unavailable/uncalibrated judge.

Calibration against a human-graded reference set lives in :func:`calibration_agreement`;
the gate will not weight ``judge`` until agreement clears the project threshold.
"""

from __future__ import annotations

import os
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from .eval.dimensions import DimensionResult, Status, register
from .models import REVIEW_MODEL
_FORBIDDEN_RUBRIC_TERMS = ("length", "longer", "word count", "verbose", "style")


class RubricError(ValueError):
    """Raised when a rubric includes a forbidden criterion."""


def validate_rubric(rubric: Sequence[str]) -> None:
    """Reject rubrics that grade on length/style (judges anchor on these)."""
    for item in rubric:
        low = item.lower()
        for term in _FORBIDDEN_RUBRIC_TERMS:
            if term in low:
                raise RubricError(f"rubric item grades on forbidden criterion {term!r}: {item!r}")


class JudgeBackend(Protocol):
    """A scorer that returns a [0, 1] score for one (rubric, artifact) pair."""

    def score(self, rubric: Sequence[str], artifact: str) -> float: ...


@dataclass
class AnthropicJudge:
    """Opus-backed judge. Constructing it does not require the network; scoring does."""

    model: str = REVIEW_MODEL

    def score(self, rubric: Sequence[str], artifact: str) -> float:  # pragma: no cover - network
        import anthropic  # imported lazily; optional dep

        client = anthropic.Anthropic()
        rubric_text = "\n".join(f"- {item}" for item in rubric)
        prompt = (
            "Grade the ARTIFACT against the RUBRIC. Return only a number in [0,1]."
            " Do not reward length or style.\n\n"
            f"RUBRIC:\n{rubric_text}\n\nARTIFACT:\n{artifact}\n"
        )
        msg = client.messages.create(
            model=self.model,
            max_tokens=16,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in msg.content if block.type == "text")
        return _parse_score(text)


def _parse_score(text: str) -> float:
    """Parse a bare [0,1] score; raise ValueError on anything unparseable."""
    value = float(text.strip().split()[0])
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"judge score out of range: {value}")
    return value


def _default_backend() -> JudgeBackend | None:
    """An Opus judge if anthropic + a key are present, else None (→ unavailable)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return None
    return AnthropicJudge()


def judge_dimension(
    *,
    backend: JudgeBackend | None = None,
    repeats: int = 1,
    variance_tol: float = 0.15,
    calibrated: bool = False,
) -> Any:
    """Build a ``judge`` dimension callable for the eval registry.

    The artifact is taken from ``actual``; the rubric from ``context['rubric']``.
    With ``repeats > 1`` the judge scores K times and self-marks ``low_confidence``
    when the spread exceeds ``variance_tol``. Until ``calibrated`` is True the
    score is still recorded, but the gate treats it as non-advancing evidence.
    """
    chosen = backend if backend is not None else _default_backend()

    def _judge(expected: Any, actual: Any, context: Mapping[str, Any]) -> DimensionResult:
        rubric = context.get("rubric")
        if not rubric:
            return DimensionResult("judge", None, Status.NA, "no rubric declared")
        validate_rubric(list(rubric))
        if chosen is None:
            return DimensionResult(
                "judge", None, Status.UNAVAILABLE, "no anthropic backend / API key"
            )
        scores = [chosen.score(list(rubric), str(actual)) for _ in range(max(1, repeats))]
        mean = statistics.fmean(scores)
        spread = (max(scores) - min(scores)) if len(scores) > 1 else 0.0
        if spread > variance_tol:
            return DimensionResult(
                "judge", mean, Status.LOW_CONFIDENCE, f"spread {spread:.3f} > {variance_tol}"
            )
        detail = "" if calibrated else "uncalibrated (gate will not weight)"
        return DimensionResult("judge", mean, Status.OK, detail)

    return _judge


def calibration_agreement(judge_scores: Sequence[float], human_scores: Sequence[float]) -> float:
    """Pearson correlation between judge and human grades over a reference set.

    The gate refuses to weight ``judge`` until this clears the project threshold
    (vision OQ-1 fixes the metric + value). Returns 0.0 for degenerate input
    (n < 2 or zero variance) rather than raising.
    """
    if len(judge_scores) != len(human_scores):
        raise ValueError("judge and human score lists must be the same length")
    if len(judge_scores) < 2:
        return 0.0
    try:
        return statistics.correlation(judge_scores, human_scores)
    except statistics.StatisticsError:
        return 0.0


def install_default_judge() -> bool:
    """Register the default judge dimension. Returns True if a backend is live."""
    backend = _default_backend()
    register("judge", judge_dimension(backend=backend))
    return backend is not None
