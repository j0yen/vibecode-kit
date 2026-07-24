"""Version-pinned datasets: provenance, append/version, fail-loud reproduce."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pybuilder.dataset import (
    Dataset,
    DatasetRow,
    ReproduceError,
    capture_row,
    diff_versions,
    reproduce,
)


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "--allow-empty", "-q", "-m", "init"],
        check=True,
    )
    return tmp_path


def test_capture_pins_commit(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    ds = Dataset("d")
    row = capture_row(dataset=ds, row_id="r1", input="q", expected="a", repo=repo, prompt="p")
    assert row.commit  # pinned
    assert row.prompt_hash


def test_add_version_never_overwrites(tmp_path: Path) -> None:
    ds = Dataset("d")
    ds.add_version(DatasetRow("r1", "q", "a", commit="aaa"))
    ds.add_version(DatasetRow("r1", "q", "a2", commit="bbb"))
    assert len(ds.rows) == 2
    assert ds.latest("r1").version == 2  # type: ignore[union-attr]
    assert ds.latest("r1").expected == "a2"  # type: ignore[union-attr]


def test_reproduce_fails_loud_on_unreachable_commit(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    row = DatasetRow("r1", "q", "a", commit="deadbeef")  # not in history
    with pytest.raises(ReproduceError, match="unreachable"):
        reproduce(repo, row)


def test_reproduce_rejects_unpinned_row(tmp_path: Path) -> None:
    row = DatasetRow("r1", "q", "a", commit="", unpinned=True)
    with pytest.raises(ReproduceError, match="unpinned"):
        reproduce(tmp_path, row)


def test_diff_attributes_prompt_only_change() -> None:
    old = DatasetRow("r1", "q", "a", commit="aaa", prompt_hash="p1")
    new = DatasetRow("r1", "q", "a", commit="aaa", prompt_hash="p2")
    d = diff_versions(old, new)
    assert d["prompt_changed"] is True
    assert d["code_changed"] is False
    assert d["expected_changed"] is False


def test_save_load_round_trip(tmp_path: Path) -> None:
    ds = Dataset("d")
    ds.add_version(DatasetRow("r1", "q", "a", commit="aaa"))
    ds.save(tmp_path / "ds.json")
    loaded = Dataset.load(tmp_path / "ds.json")
    assert loaded.name == "d"
    assert loaded.rows[0].row_id == "r1"
