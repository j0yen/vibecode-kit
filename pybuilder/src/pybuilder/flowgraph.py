"""State-machine scaffolding for agents + trace→testcase extraction.

The article's first pillar: model an LLM app as a state machine so "if you can
draw a flowchart of your application, your code structure mirrors it" — then turn
real runs into replayable tests.

A :class:`StateMachine` is named :class:`Action`s and declared transitions. Running
it produces a :class:`Trace` (the ordered steps with inputs/outputs and the path
taken). :func:`trace_to_testcase` converts a recorded trace into a replayable test
case: nondeterministic outputs are captured so replay is deterministic, secrets are
redacted to env-var references, and loops are bounded so a cyclic agent still
extracts. This is the minimal-but-real engine the ``--target agent`` scaffold emits
against (vision OQ-1: adopt Burr vs. a thin internal engine — this is the thin
internal engine, kept dependency-free).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

# state == terminal sentinel
HALT = "__halt__"

# Patterns that look like secrets in captured tool args/outputs.
_SECRET_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{12,}"),
    re.compile(r"(?i)(api[_-]?key\"?\s*[:=]\s*\"?)[A-Za-z0-9._\-]{12,}"),
    re.compile(r"(?i)(password\"?\s*[:=]\s*\"?)[^\s\"]{6,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
]


def redact_secrets(value: Any) -> Any:
    """Replace secret-looking substrings with env-var references, recursively."""
    if isinstance(value, str):
        out = value
        for pat in _SECRET_PATTERNS:
            out = pat.sub(lambda m: f"{_group_prefix(m)}${{REDACTED_SECRET}}", out)
        return out
    if isinstance(value, Mapping):
        return {k: redact_secrets(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_secrets(v) for v in value]
    return value


def _group_prefix(m: re.Match[str]) -> str:
    return m.group(1) if m.lastindex else ""


@dataclass
class Step:
    """One executed action within a trace."""

    action: str
    state_in: str
    state_out: str
    inputs: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    # True when the action's output came from a nondeterministic source (LLM/API)
    # and must be captured for deterministic replay.
    nondeterministic: bool = False


@dataclass
class Trace:
    """An ordered record of a state-machine run."""

    steps: list[Step] = field(default_factory=list)
    halted: bool = False
    crashed: str = ""  # non-empty: the exception that ended the run mid-flight

    def path(self) -> list[str]:
        return [s.action for s in self.steps]

    def redacted(self) -> Trace:
        return Trace(
            steps=[
                Step(
                    action=s.action,
                    state_in=s.state_in,
                    state_out=s.state_out,
                    inputs=redact_secrets(s.inputs),
                    output=redact_secrets(s.output),
                    nondeterministic=s.nondeterministic,
                )
                for s in self.steps
            ],
            halted=self.halted,
            crashed=self.crashed,
        )


# An action: given the running state dict, return (output, next_state).
ActionFn = Callable[[dict[str, Any]], tuple[Any, str]]


@dataclass
class Action:
    name: str
    fn: ActionFn
    nondeterministic: bool = False


class StateMachine:
    """A traced state machine: named actions + transitions.

    Transitions map ``state -> action_name``. Running from ``entry`` follows the
    action each state names, recording a :class:`Step` per hop, until an action
    routes to :data:`HALT`, no transition exists, or ``max_steps`` is hit (loop
    guard — a cyclic agent is traced and extractable, never unbounded).
    """

    def __init__(self, entry: str, max_steps: int = 100) -> None:
        self.entry = entry
        self.max_steps = max_steps
        self.actions: dict[str, Action] = {}
        self.transitions: dict[str, str] = {}

    def action(self, name: str, fn: ActionFn, *, nondeterministic: bool = False) -> StateMachine:
        self.actions[name] = Action(name, fn, nondeterministic)
        return self

    def at(self, state: str, action_name: str) -> StateMachine:
        """At ``state``, run ``action_name``."""
        self.transitions[state] = action_name
        return self

    def run(self, state: dict[str, Any] | None = None) -> Trace:
        st: dict[str, Any] = dict(state or {})
        current = self.entry
        trace = Trace()
        for _ in range(self.max_steps):
            if current == HALT:
                trace.halted = True
                break
            action_name = self.transitions.get(current)
            if action_name is None:
                break
            action = self.actions.get(action_name)
            if action is None:
                trace.crashed = f"no action registered for {action_name!r}"
                break
            try:
                output, next_state = action.fn(st)
            except Exception as exc:  # noqa: BLE001 — capture the crash state as a step
                trace.steps.append(
                    Step(action_name, current, current, dict(st), None, action.nondeterministic)
                )
                trace.crashed = f"{type(exc).__name__}: {exc}"
                break
            trace.steps.append(
                Step(action_name, current, next_state, dict(st), output, action.nondeterministic)
            )
            current = next_state
        return trace


@dataclass
class TestCase:
    """A replayable, secret-free regression case extracted from a trace."""

    name: str
    expected_path: list[str]
    expected_outputs: list[Any]
    halted: bool
    crashed: str
    replayable: bool
    reason: str = ""  # why not replayable, when replayable is False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "expected_path": self.expected_path,
            "expected_outputs": self.expected_outputs,
            "halted": self.halted,
            "crashed": self.crashed,
            "replayable": self.replayable,
            "reason": self.reason,
        }


def trace_to_testcase(trace: Trace, name: str) -> TestCase:
    """Convert a trace into a replayable pytest-able case.

    Nondeterministic step outputs are captured (so replay is deterministic). If a
    nondeterministic step has no captured output, the case is marked
    ``replayable=False`` with a reason rather than silently producing a flaky test.
    Secrets are redacted before anything is persisted.
    """
    red = trace.redacted()
    replayable = True
    reason = ""
    for step in red.steps:
        if step.nondeterministic and step.output is None and not red.crashed:
            replayable = False
            reason = f"nondeterministic action {step.action!r} has no captured output"
            break
    return TestCase(
        name=name,
        expected_path=red.path(),
        expected_outputs=[s.output for s in red.steps],
        halted=red.halted,
        crashed=red.crashed,
        replayable=replayable,
        reason=reason,
    )
