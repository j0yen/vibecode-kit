"""Intent-card validation: the buildability contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from pybuilder.intent_card import AcceptanceCriterion, IntentCard, IntentCardError, Level


def _card(**over: object) -> IntentCard:
    base: dict[str, object] = {
        "slug": "demo-tool",
        "root_motivation": "do a thing",
        "target": "cli",
        "acceptance_criteria": [
            AcceptanceCriterion("AC-1", "it works", Level.MUST),
            AcceptanceCriterion("AC-2", "it is nice", Level.SHOULD),
        ],
    }
    base.update(over)
    return IntentCard(**base)  # type: ignore[arg-type]


def test_valid_card_round_trips() -> None:
    card = _card()
    card.validate()
    assert [ac.id for ac in card.must_acs()] == ["AC-1"]


def test_no_must_ac_is_rejected() -> None:
    with pytest.raises(IntentCardError, match="nothing to prove"):
        _card(acceptance_criteria=[AcceptanceCriterion("AC-2", "nice", Level.SHOULD)]).validate()


def test_bad_target_rejected() -> None:
    with pytest.raises(IntentCardError, match="not in"):
        _card(target="service").validate()


def test_duplicate_ac_ids_rejected() -> None:
    with pytest.raises(IntentCardError, match="duplicate"):
        _card(
            acceptance_criteria=[
                AcceptanceCriterion("AC-1", "a", Level.MUST),
                AcceptanceCriterion("AC-1", "b", Level.MUST),
            ]
        ).validate()


def test_save_load_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "card.json"
    _card().save(p)
    loaded = IntentCard.load(p)
    assert loaded.slug == "demo-tool"
    assert loaded.target == "cli"


def test_agent_target_is_in_scope() -> None:
    _card(target="agent").validate()  # resolves vision OQ-1: agent is first-class
