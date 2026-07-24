"""State-machine runtime + trace->testcase + secret redaction (the agent target)."""

from __future__ import annotations

from pybuilder.flowgraph import HALT, StateMachine, redact_secrets, trace_to_testcase


def _linear_machine() -> StateMachine:
    sm = StateMachine(entry="a")
    sm.action("a", lambda s: ("out-a", "b"))
    sm.action("b", lambda s: ("out-b", HALT))
    sm.at("a", "a")
    sm.at("b", "b")
    return sm


def test_run_records_path_and_halts() -> None:
    trace = _linear_machine().run({})
    assert trace.path() == ["a", "b"]
    assert trace.halted is True


def test_trace_to_testcase_is_replayable_when_deterministic() -> None:
    case = trace_to_testcase(_linear_machine().run({}), "linear")
    assert case.replayable is True
    assert case.expected_path == ["a", "b"]
    assert case.expected_outputs == ["out-a", "out-b"]


def test_nondeterministic_step_without_capture_is_non_replayable() -> None:
    sm = StateMachine(entry="llm")
    # nondeterministic action that returns None output (nothing captured)
    sm.action("llm", lambda s: (None, HALT), nondeterministic=True)
    sm.at("llm", "llm")
    case = trace_to_testcase(sm.run({}), "llm_case")
    assert case.replayable is False
    assert "no captured output" in case.reason


def test_crash_is_captured_as_terminal_step() -> None:
    sm = StateMachine(entry="x")

    def crash(_s: dict[str, object]) -> tuple[object, str]:
        raise RuntimeError("kaboom")

    sm.action("x", crash)
    sm.at("x", "x")
    trace = sm.run({})
    assert "kaboom" in trace.crashed
    assert trace.path() == ["x"]


def test_loop_is_bounded() -> None:
    sm = StateMachine(entry="loop", max_steps=5)
    sm.action("loop", lambda s: ("again", "loop"))  # cycles forever
    sm.at("loop", "loop")
    trace = sm.run({})
    assert len(trace.steps) == 5  # bounded, not unbounded


def test_secrets_are_redacted_before_persisting() -> None:
    sm = StateMachine(entry="tool")
    sm.action("tool", lambda s: ({"headers": "Bearer abcdef1234567890token"}, HALT))
    sm.at("tool", "tool")
    case = trace_to_testcase(sm.run({}), "tool_case")
    assert "abcdef1234567890token" not in repr(case.expected_outputs)
    assert "REDACTED_SECRET" in repr(case.expected_outputs)


def test_redact_handles_nested_structures() -> None:
    red = redact_secrets({"a": ["api_key=supersecretvalue123", "ok"]})
    assert "supersecretvalue123" not in repr(red)
