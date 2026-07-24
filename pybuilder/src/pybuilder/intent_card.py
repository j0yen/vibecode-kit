"""Intent card — the structured contract every pipeline stage reads.

A PRD is distilled (via the 5-Whys intake prompt) into an ``IntentCard``: the
root motivation, the target kind, and the acceptance criteria with their
MUST/SHOULD/MAY levels. Scaffold turns MUST-ACs into read-only tests; the gate
checks that every MUST-AC is declared and proven; the judge grades against the
AC English text.

This is ``intent-card.v1``. The schema lives at ``schemas/intent-card.schema.json``;
this module is the in-process loader/validator so other modules never re-declare
the shape.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from . import TARGETS

SCHEMA_VERSION = "intent-card.v1"


class Level(StrEnum):
    """RFC-2119 requirement level for an acceptance criterion."""

    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"


class IntentCardError(ValueError):
    """Raised when an intent card is malformed or fails validation."""


@dataclass(frozen=True)
class AcceptanceCriterion:
    """One testable acceptance criterion lifted from the PRD."""

    id: str
    text: str
    level: Level
    # Some ACs are mechanically testable (an assert); others need a judge
    # (faithfulness, explanation quality). The scaffold routes `judged` ACs to
    # the eval harness rather than a bare assert.
    judged: bool = False

    @staticmethod
    def from_dict(d: dict[str, Any]) -> AcceptanceCriterion:
        try:
            return AcceptanceCriterion(
                id=str(d["id"]),
                text=str(d["text"]),
                level=Level(str(d["level"])),
                judged=bool(d.get("judged", False)),
            )
        except (KeyError, ValueError) as exc:
            raise IntentCardError(f"invalid acceptance criterion {d!r}: {exc}") from exc


@dataclass(frozen=True)
class IntentCard:
    """The distilled intent of a PRD. ``intent-card.v1``."""

    slug: str
    root_motivation: str
    target: str
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def must_acs(self) -> list[AcceptanceCriterion]:
        return [ac for ac in self.acceptance_criteria if ac.level is Level.MUST]

    def validate(self) -> None:
        """Raise :class:`IntentCardError` if the card is not buildable.

        Mirrors autobuilder intake: refuse to proceed when no MUST-AC is
        declared (nothing to prove) or when the target is out of scope.
        """
        if not self.slug or not self.slug.replace("-", "").isalnum():
            raise IntentCardError(f"slug must be kebab-case alphanumeric, got {self.slug!r}")
        if self.target not in TARGETS:
            raise IntentCardError(f"target {self.target!r} not in {TARGETS}")
        if self.schema_version != SCHEMA_VERSION:
            raise IntentCardError(
                f"schema_version {self.schema_version!r} != {SCHEMA_VERSION!r}"
            )
        ids = [ac.id for ac in self.acceptance_criteria]
        if len(ids) != len(set(ids)):
            raise IntentCardError("duplicate acceptance-criterion ids")
        if not self.must_acs():
            raise IntentCardError("no MUST-level acceptance criteria — nothing to prove")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["acceptance_criteria"] = [
            {"id": ac.id, "text": ac.text, "level": ac.level.value, "judged": ac.judged}
            for ac in self.acceptance_criteria
        ]
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> IntentCard:
        try:
            card = IntentCard(
                slug=str(d["slug"]),
                root_motivation=str(d["root_motivation"]),
                target=str(d["target"]),
                acceptance_criteria=[
                    AcceptanceCriterion.from_dict(ac) for ac in d.get("acceptance_criteria", [])
                ],
                schema_version=str(d.get("schema_version", SCHEMA_VERSION)),
            )
        except KeyError as exc:
            raise IntentCardError(f"intent card missing required field: {exc}") from exc
        card.validate()
        return card

    @staticmethod
    def load(path: str | Path) -> IntentCard:
        text = Path(path).read_text(encoding="utf-8")
        return IntentCard.from_dict(json.loads(text))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
