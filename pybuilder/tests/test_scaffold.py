"""Scaffold: locked harness, green-on-empty, AC-tagged stubs, agent skeleton."""

from __future__ import annotations

from pathlib import Path

import pytest

from pybuilder.intent_card import AcceptanceCriterion, IntentCard, Level
from pybuilder.scaffold import ScaffoldError, scaffold


def _card(target: str = "cli") -> IntentCard:
    return IntentCard(
        slug="widget",
        root_motivation="build a widget",
        target=target,
        acceptance_criteria=[
            AcceptanceCriterion("AC-1", "widget greets", Level.MUST),
            AcceptanceCriterion("AC-2", "widget is judged faithful", Level.MUST, judged=True),
            AcceptanceCriterion("AC-3", "widget is pretty", Level.SHOULD),
        ],
    )


def test_emits_one_stub_per_must_ac_tagged_with_id(tmp_path: Path) -> None:
    root = scaffold(_card(), tmp_path / "p")
    acceptance = (root / "tests" / "test_acceptance.py").read_text(encoding="utf-8")
    assert "# AC-1 [MUST]" in acceptance
    assert "# AC-2 [MUST]" in acceptance
    assert "AC-3" not in acceptance  # SHOULD is not a MUST stub


def test_judged_ac_routes_to_eval_not_bare_assert(tmp_path: Path) -> None:
    root = scaffold(_card(), tmp_path / "p")
    acceptance = (root / "tests" / "test_acceptance.py").read_text(encoding="utf-8")
    assert "pybuilder.eval" in acceptance


def test_locked_harness_files_present(tmp_path: Path) -> None:
    root = scaffold(_card(), tmp_path / "p")
    assert (root / "pyproject.toml").exists()
    assert (root / "scripts" / "run-metrics.sh").exists()
    assert (root / ".github" / "workflows" / "gate.yml").exists()
    assert (root / "src" / "widget" / "__init__.py").exists()


def test_agent_target_emits_state_machine_skeleton(tmp_path: Path) -> None:
    root = scaffold(_card("agent"), tmp_path / "p")
    agent = (root / "src" / "widget" / "agent.py").read_text(encoding="utf-8")
    assert "StateMachine" in agent
    assert "flowgraph" in agent


def test_refuses_nonempty_dir_without_force(tmp_path: Path) -> None:
    dest = tmp_path / "p"
    dest.mkdir()
    (dest / "existing.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(ScaffoldError, match="non-empty"):
        scaffold(_card(), dest)
    scaffold(_card(), dest, force=True)  # force succeeds
