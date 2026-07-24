"""Locked-harness Python project generator.

Given an :class:`~pybuilder.intent_card.IntentCard`, emit a project where the
harness is read-only and the agent edits only ``src/``: ``pyproject.toml`` with
ruff+mypy+pytest+coverage configured, one acceptance-test stub per MUST-AC tagged
with its AC id, a ``run-metrics`` script emitting normalized ``metrics.json``, and
a CI mirror. The empty tree is green (the floor `mcp-tuner` never had). For
``--target agent`` it also emits a :class:`~pybuilder.flowgraph.StateMachine`
skeleton so the agent starts as a drawable, traceable flowchart.
"""

from __future__ import annotations

from pathlib import Path

from .intent_card import AcceptanceCriterion, IntentCard

_PYPROJECT = """\
[project]
name = "{slug}"
version = "0.1.0"
description = "{motivation}"
requires-python = ">=3.11"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{pkg}"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "RUF"]

[tool.mypy]
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
source = ["{pkg}"]
branch = true
"""

_RUN_METRICS = """\
#!/usr/bin/env bash
# run-metrics.sh — READ-ONLY harness. Emits normalized metrics.json for the loop.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
ruff_errors=$(uv run ruff check --quiet . 2>/dev/null | wc -l | tr -d ' ')
mypy_errors=$(uv run mypy src 2>/dev/null | grep 'error:' | wc -l | tr -d ' ')
uv run pytest -q 2>/dev/null; tests_failing=$?
cat > .pybuilder/metrics.json <<JSON
{ "ruff_errors": ${ruff_errors:-0},
  "mypy_errors": ${mypy_errors:-0},
  "tests_failing": ${tests_failing:-0},
  "coverage_pct": 0,
  "coverage_min": 0 }
JSON
echo "wrote .pybuilder/metrics.json"
"""

_CI = """\
name: gate
on: [push, pull_request]
jobs:
  prove:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv run ruff check .
      - run: uv run mypy src
      - run: uv run pytest -q
"""

_AGENT_SKELETON = '''\
"""Agent entrypoint — a traced state machine (the flowchart IS the code)."""

from __future__ import annotations

from pybuilder.flowgraph import HALT, StateMachine


def build_machine() -> StateMachine:
    """Wire the agent's states and transitions. Edit ME (under src/)."""
    sm = StateMachine(entry="start")
    sm.action("greet", lambda state: ("hello", HALT))
    sm.at("start", "greet")
    return sm


def main() -> None:
    trace = build_machine().run({})
    print(" -> ".join(trace.path()))
'''


def _pkg_name(slug: str) -> str:
    return slug.replace("-", "_")


def _ac_stub(ac: AcceptanceCriterion) -> str:
    pkg = "<pkg>"
    if ac.judged:
        body = (
            "    # AC is judged (not mechanically decidable): route to the eval harness.\n"
            "    # See pybuilder.eval — record across dimensions, do not bare-assert.\n"
            "    pytest.skip('judged AC — wire to pybuilder.eval rubric')\n"
        )
    else:
        body = "    pytest.skip('implement against the AC text above')\n"
    return (
        f"def test_{ac.id.lower().replace('-', '_')}() -> None:\n"
        f"    # {ac.id} [{ac.level.value}]: {ac.text}\n"
        f"{body}"
    ).replace("<pkg>", pkg)


class ScaffoldError(RuntimeError):
    pass


def scaffold(card: IntentCard, dest: str | Path, *, force: bool = False) -> Path:
    """Generate the locked-harness tree for ``card`` at ``dest``.

    Refuses a non-empty ``dest`` unless ``force`` (never overwrites uncommitted
    work). Returns the project root.
    """
    card.validate()
    root = Path(dest)
    if root.exists() and any(root.iterdir()) and not force:
        raise ScaffoldError(f"{root} is non-empty; pass force=True to overwrite")

    pkg = _pkg_name(card.slug)
    (root / "src" / pkg).mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / ".pybuilder").mkdir(parents=True, exist_ok=True)
    (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)

    (root / "pyproject.toml").write_text(
        _PYPROJECT.format(
            slug=card.slug, pkg=pkg, motivation=card.root_motivation.replace('"', "'")[:200]
        ),
        encoding="utf-8",
    )
    (root / "src" / pkg / "__init__.py").write_text('"""Agent edits ONLY this tree."""\n', "utf-8")
    if card.target == "agent":
        (root / "src" / pkg / "agent.py").write_text(_AGENT_SKELETON, encoding="utf-8")

    # One read-only acceptance stub per MUST-AC, tagged with its AC id.
    header = "import pytest\n\n\n"
    stubs = "\n\n".join(_ac_stub(ac) for ac in card.must_acs())
    (root / "tests" / "test_acceptance.py").write_text(header + stubs + "\n", encoding="utf-8")

    run_metrics = root / "scripts" / "run-metrics.sh"
    run_metrics.write_text(_RUN_METRICS, encoding="utf-8")
    run_metrics.chmod(0o755)
    (root / ".github" / "workflows" / "gate.yml").write_text(_CI, encoding="utf-8")
    (root / "README.md").write_text(
        f"# {card.slug}\n\n{card.root_motivation}\n\n"
        "Generated by [pybuilder](https://github.com/j0yen/pybuilder). "
        "Harness (`tests/`, `scripts/`, config) is read-only; edit only `src/`.\n",
        encoding="utf-8",
    )
    return root
