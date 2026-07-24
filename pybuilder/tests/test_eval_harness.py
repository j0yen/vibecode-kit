"""The centerpiece: multi-dimensional, log-don't-assert evaluation."""

from __future__ import annotations

from pathlib import Path

from pybuilder.eval.dimensions import (
    DimensionResult,
    Status,
    evaluate_all,
    register,
)
from pybuilder.eval.results_bag import ResultsBag
from pybuilder.eval.vector import weighted_aggregate


def test_log_dont_assert_keeps_all_dimensions_on_partial_failure() -> None:
    bag = ResultsBag()
    row = bag.record("t1", expected="hello world", actual="hello there", dimensions=["exact", "fuzzy"])
    # exact misses (0) but fuzzy still records a partial score — and nothing raised.
    assert row.score("exact") == 0.0
    assert row.score("fuzzy") is not None and 0.0 < row.score("fuzzy") < 1.0  # type: ignore[operator]
    assert len(bag.rows) == 1


def test_dimension_error_is_isolated_not_raised() -> None:
    def boom(expected: object, actual: object, ctx: object) -> DimensionResult:
        raise ValueError("kaboom")

    register("boom", boom)
    results = evaluate_all("x", "x", {}, dimensions=["exact", "boom"])
    by_name = {r.name: r for r in results}
    assert by_name["exact"].score == 1.0
    assert by_name["boom"].status is Status.DIMENSION_ERROR
    assert "kaboom" in by_name["boom"].detail


def test_no_expected_value_is_na_not_failure() -> None:
    results = evaluate_all(None, "anything", {}, dimensions=["exact", "fuzzy"])
    assert all(r.status is Status.NA for r in results)


def test_static_dimension_reads_metrics() -> None:
    ctx = {"metrics": {"ruff_errors": 0, "mypy_errors": 0, "tests_failing": 0}}
    results = evaluate_all("x", "x", ctx, dimensions=["static"])
    assert results[0].score == 1.0
    ctx_bad = {"metrics": {"ruff_errors": 3, "mypy_errors": 0, "tests_failing": 1}}
    results_bad = evaluate_all("x", "x", ctx_bad, dimensions=["static"])
    assert results_bad[0].score is not None and results_bad[0].score < 1.0


def test_csv_export_has_one_row_per_record(tmp_path: Path) -> None:
    bag = ResultsBag()
    bag.record("a", "x", "x", dimensions=["exact"])
    bag.record("b", "x", "y", dimensions=["exact"])
    out = bag.to_csv(tmp_path / "results.csv")
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3  # header + 2 rows
    assert "exact_score" in lines[0]


def test_quality_vector_skips_dimensions_with_no_ok_scores() -> None:
    bag = ResultsBag()
    bag.record("t", expected="hi", actual="hi", dimensions=["exact", "fuzzy"])
    # judge is not registered by default in this offline test -> unavailable -> skipped
    vec = weighted_aggregate(bag.rows, {"exact": 0.5, "fuzzy": 0.3, "judge": 0.2})
    assert "judge" in vec.skipped
    # aggregate renormalizes over contributing dims (exact=1, fuzzy=1) -> 1.0
    assert abs(vec.aggregate - 1.0) < 1e-9


def test_locked_csv_falls_back_without_losing_data(tmp_path: Path) -> None:
    bag = ResultsBag()
    bag.record("a", "x", "x", dimensions=["exact"])
    # point at a directory path to force an OSError on open()
    target = tmp_path / "adir"
    target.mkdir()
    out = bag.to_csv(target)
    assert out.exists() and out != target
