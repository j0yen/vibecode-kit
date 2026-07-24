"""Stability classification: noise vs underspecified spec."""

from __future__ import annotations

import itertools

from pybuilder.stability import Classification, run_stability


def test_deterministic_artifact_is_stable() -> None:
    report = run_stability(lambda: "always", expected="always", n=5)
    assert report.classification is Classification.STABLE
    assert report.correctness_spread == 0.0


def test_n1_is_unknown() -> None:
    report = run_stability(lambda: "x", expected="x", n=1)
    assert report.classification is Classification.UNKNOWN
    assert report.n_completed == 1


def test_wild_variance_is_underspecified_with_spec_signal() -> None:
    # alternate between exact match and total miss -> correctness spread = 1.0
    flip = itertools.cycle(["hello there", "completely different"])
    report = run_stability(lambda: next(flip), expected="hello there", n=8, band=0.2)
    assert report.classification is Classification.UNDERSPECIFIED
    assert "fix the spec" in report.spec_signal


def test_crash_counts_as_a_sample() -> None:
    calls = {"n": 0}

    def sometimes_crashes() -> str:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom")
        return "ok"

    report = run_stability(sometimes_crashes, expected="ok", n=4)
    # the crash is recorded, not discarded -> instability is detected
    assert report.n_completed == 4
    assert report.classification is not Classification.STABLE


def test_max_runs_yields_partial() -> None:
    report = run_stability(lambda: "x", expected="x", n=10, max_runs=3)
    assert report.partial is True
    assert report.n_completed <= 3
