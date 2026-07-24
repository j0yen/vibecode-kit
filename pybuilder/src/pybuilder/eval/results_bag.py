"""The log-don't-assert recorder.

A :class:`ResultsBag` records one :class:`Row` per evaluation — its identity
columns plus every dimension's result — *without* failing on a single dimension
miss. Rows aggregate to a CSV (always) and a pandas DataFrame (when pandas is
installed). This is the article's ``results_bag`` / ``module_results_df`` pattern,
implemented in-process so it needs neither pytest nor pytest-harvest to run, but
interoperable with both.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .dimensions import DimensionResult, Status, evaluate_all


@dataclass
class Row:
    """One evaluation: identity + the dimension vector recorded for it."""

    test_id: str
    results: list[DimensionResult]
    dataset_row_id: str = ""
    commit: str = ""  # producing commit, when known (set by the dataset registry)
    meta: dict[str, Any] = field(default_factory=dict)

    def score(self, dimension: str) -> float | None:
        for r in self.results:
            if r.name == dimension:
                return r.score
        return None

    def flat(self) -> dict[str, Any]:
        """Flatten to a single CSV-friendly record."""
        rec: dict[str, Any] = {
            "test_id": self.test_id,
            "dataset_row_id": self.dataset_row_id,
            "commit": self.commit,
        }
        for r in self.results:
            rec[f"{r.name}_score"] = r.score
            rec[f"{r.name}_status"] = r.status.value
        rec.update(self.meta)
        return rec


class ResultsBag:
    """Accumulates rows; never raises on a dimension miss."""

    def __init__(self) -> None:
        self.rows: list[Row] = []

    def record(
        self,
        test_id: str,
        expected: Any,
        actual: Any,
        context: Mapping[str, Any] | None = None,
        *,
        dimensions: list[str] | None = None,
        dataset_row_id: str = "",
        commit: str = "",
        **meta: Any,
    ) -> Row:
        """Evaluate one (expected, actual) pair across dimensions and log it.

        A failing dimension is recorded (``score`` reflects the miss, or a
        non-OK :class:`Status`), never raised.
        """
        results = evaluate_all(expected, actual, context, dimensions=dimensions)
        row = Row(
            test_id=test_id,
            results=results,
            dataset_row_id=dataset_row_id,
            commit=commit,
            meta=dict(meta),
        )
        self.rows.append(row)
        return row

    def add(self, row: Row) -> None:
        self.rows.append(row)

    # --- aggregation ----------------------------------------------------------

    def columns(self) -> list[str]:
        """Stable union of all flattened keys across rows (identity first)."""
        cols: list[str] = ["test_id", "dataset_row_id", "commit"]
        seen = set(cols)
        for row in self.rows:
            for k in row.flat():
                if k not in seen:
                    seen.add(k)
                    cols.append(k)
        return cols

    def to_csv(self, path: str | Path) -> Path:
        """Write rows to CSV. Falls back to a sibling path if the target is locked.

        Never loses the in-memory rows: on a write error, writes to
        ``<path>.fallback.csv`` and returns that path.
        """
        cols = self.columns()
        target = Path(path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            self._write_csv(target, cols)
            return target
        except OSError:
            fallback = target.with_suffix(target.suffix + ".fallback.csv")
            self._write_csv(fallback, cols)
            return fallback

    def _write_csv(self, target: Path, cols: list[str]) -> None:
        with target.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols)
            writer.writeheader()
            for row in self.rows:
                writer.writerow(row.flat())

    def to_dataframe(self) -> Any:
        """Return a pandas DataFrame (the article's ``module_results_df``).

        Raises :class:`RuntimeError` if pandas is not installed — callers that
        only need persistence should use :meth:`to_csv`, which has no dep.
        """
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover - exercised only without pandas
            raise RuntimeError("pandas not installed; `pip install pybuilder[pandas]`") from exc
        return pd.DataFrame([row.flat() for row in self.rows], columns=self.columns())

    def dimension_errors(self) -> list[Row]:
        """Rows where at least one dimension errored — for triage, not abort."""
        return [
            row
            for row in self.rows
            if any(r.status is Status.DIMENSION_ERROR for r in row.results)
        ]
