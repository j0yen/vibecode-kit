"""Shared receipts layout — the one place pipeline stages write evidence.

Every stage writes a typed :class:`Receipt` under ``<project>/.pybuilder/receipts/``.
The gate (``pybuilder.gate``) reads them and decides ready/blocked. Receipts carry
the git HEAD they were produced against so the gate can reject stale evidence
(autobuilder parity: a receipt older than HEAD is treated as missing).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

RECEIPTS_DIRNAME = ".pybuilder"


class Verdict(StrEnum):
    PASS = "pass"
    CONCERN = "concern"
    BLOCK = "block"
    UNAVAILABLE = "unavailable"


@dataclass
class Receipt:
    """A single piece of gate evidence."""

    name: str
    verdict: Verdict
    detail: str = ""
    # git commit the receipt was produced against; "" when not in a repo.
    commit: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["verdict"] = self.verdict.value
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Receipt:
        return Receipt(
            name=str(d["name"]),
            verdict=Verdict(str(d["verdict"])),
            detail=str(d.get("detail", "")),
            commit=str(d.get("commit", "")),
            data=dict(d.get("data", {})),
        )


def git_head(repo: str | Path) -> str:
    """Return the short HEAD sha of ``repo``, or "" if not a git repo."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def git_is_dirty(repo: str | Path) -> bool:
    """True if the working tree has uncommitted changes (or is not a repo)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return True


class ReceiptStore:
    """Read/write receipts under ``<project>/.pybuilder/receipts/``."""

    def __init__(self, project: str | Path) -> None:
        self.project = Path(project)
        self.root = self.project / RECEIPTS_DIRNAME
        self.receipts_dir = self.root / "receipts"

    def write(self, receipt: Receipt) -> Path:
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        if not receipt.commit:
            receipt.commit = git_head(self.project)
        path = self.receipts_dir / f"{receipt.name}.json"
        path.write_text(json.dumps(receipt.to_dict(), indent=2) + "\n", encoding="utf-8")
        return path

    def read(self, name: str) -> Receipt | None:
        path = self.receipts_dir / f"{name}.json"
        if not path.exists():
            return None
        return Receipt.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def is_stale(self, receipt: Receipt) -> bool:
        """A receipt is stale if produced against a commit other than current HEAD.

        Treated as missing by the gate. A receipt with no commit (not a repo) is
        never stale — there is no HEAD to diverge from.
        """
        head = git_head(self.project)
        if not head or not receipt.commit:
            return False
        return receipt.commit != head
