"""Version-pinned eval datasets — provenance for every score.

The article's version-control pillar: every eval row carries the git commit hash
(and prompt/rubric hashes) of what produced its expected output, so a score always
answers "against which version?". Datasets are plain JSON (git-diffable,
Sheets/Jupyter-loadable) and append/version — a corrected expected output adds a new
row version; prior versions are retained (autobuilder "never delete" parity).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .receipts import git_head, git_is_dirty


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class DatasetRow:
    """One pinned eval example."""

    row_id: str
    input: Any
    expected: Any  # a single value, or a {"tolerance": ...} / {"distribution": ...} shape
    commit: str  # producing code commit; "" only for explicitly legacy/unpinned rows
    prompt_hash: str = ""
    rubric_hash: str = ""
    version: int = 1
    dirty: bool = False  # working tree was dirty when captured
    dirty_digest: str = ""  # digest of the dirty diff, when dirty
    unpinned: bool = False  # imported legacy row with no real provenance

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> DatasetRow:
        return DatasetRow(**d)


@dataclass
class Dataset:
    """An append/versioned collection of pinned rows."""

    name: str
    rows: list[DatasetRow] = field(default_factory=list)

    def latest(self, row_id: str) -> DatasetRow | None:
        candidates = [r for r in self.rows if r.row_id == row_id]
        return max(candidates, key=lambda r: r.version) if candidates else None

    def add_version(self, row: DatasetRow) -> DatasetRow:
        """Append ``row`` as the next version of its id (never overwrites)."""
        prev = self.latest(row.row_id)
        row.version = (prev.version + 1) if prev else 1
        self.rows.append(row)
        return row

    def save(self, path: str | Path) -> None:
        payload = {"name": self.name, "rows": [r.to_dict() for r in self.rows]}
        Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def load(path: str | Path) -> Dataset:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return Dataset(name=d["name"], rows=[DatasetRow.from_dict(r) for r in d.get("rows", [])])


def capture_row(
    *,
    dataset: Dataset,
    row_id: str,
    input: Any,
    expected: Any,
    repo: str | Path,
    prompt: str = "",
    rubric: str = "",
) -> DatasetRow:
    """Capture a row pinned to ``repo``'s current commit.

    Records a ``dirty`` flag + diff digest when the working tree is not clean —
    never pretends a dirty tree is a clean commit.
    """
    commit = git_head(repo)
    dirty = git_is_dirty(repo)
    row = DatasetRow(
        row_id=row_id,
        input=input,
        expected=expected,
        commit=commit,
        prompt_hash=_hash(prompt) if prompt else "",
        rubric_hash=_hash(rubric) if rubric else "",
        dirty=dirty,
        dirty_digest=_hash(repr(input) + repr(expected)) if dirty else "",
    )
    return dataset.add_version(row)


def commit_reachable(repo: str | Path, commit: str) -> bool:
    """True if ``commit`` exists in ``repo``'s history."""
    import subprocess

    if not commit:
        return False
    try:
        subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


class ReproduceError(RuntimeError):
    """Raised when a row cannot be reproduced (e.g. its commit is unreachable)."""


def reproduce(repo: str | Path, row: DatasetRow) -> None:
    """Assert a row's pinned commit is reachable; fail loud if not.

    The actual re-run is the caller's (it needs the artifact under test); this
    guard guarantees we never silently reproduce against the wrong — current —
    version when the pinned commit has been rebased/gc'd away.
    """
    if row.unpinned or not row.commit:
        raise ReproduceError(f"row {row.row_id!r} is unpinned — no commit to reproduce against")
    if not commit_reachable(repo, row.commit):
        raise ReproduceError(
            f"row {row.row_id!r} pinned to {row.commit!r}, which is unreachable in {repo}"
        )


def diff_versions(old: DatasetRow, new: DatasetRow) -> dict[str, bool]:
    """Attribute a delta between two row versions to code vs prompt vs expected."""
    return {
        "code_changed": old.commit != new.commit,
        "prompt_changed": old.prompt_hash != new.prompt_hash,
        "rubric_changed": old.rubric_hash != new.rubric_hash,
        "expected_changed": repr(old.expected) != repr(new.expected),
    }
