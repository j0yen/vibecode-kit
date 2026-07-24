"""A worked example: the whole pipeline on a tiny agent, end to end.

Demonstrates every pillar — state machine + trace, multi-dimensional log-don't-assert
eval, stability classification, and a receipt-driven gate — without any network or
optional dependency.
"""

from __future__ import annotations

from .eval.results_bag import ResultsBag
from .eval.vector import DEFAULT_WEIGHTS, weighted_aggregate
from .flowgraph import HALT, StateMachine, trace_to_testcase
from .stability import run_stability


def _build_agent() -> StateMachine:
    """A 2-state agent: classify an intent, then answer."""
    sm = StateMachine(entry="classify")
    sm.action("classify", lambda s: ("greeting", "answer"))
    sm.action("answer", lambda s: ("hello there", HALT))
    sm.at("classify", "classify")
    sm.at("answer", "answer")
    return sm


def run_demo() -> None:
    sm = _build_agent()
    trace = sm.run({"utterance": "hi"})
    print("agent path:", " -> ".join(trace.path()))

    case = trace_to_testcase(trace, "greeting_flow")
    print("extracted testcase replayable:", case.replayable, "path:", case.expected_path)

    # Multi-dimensional eval of the agent's final answer.
    bag = ResultsBag()
    final = trace.steps[-1].output
    bag.record("answer", expected="hello there", actual=final, dimensions=["exact", "fuzzy"])
    bag.record("near", expected="hello friend", actual=final, dimensions=["exact", "fuzzy"])
    vec = weighted_aggregate(bag.rows, DEFAULT_WEIGHTS["agent"])
    print("quality vector:", vec.per_dimension, "aggregate:", round(vec.aggregate, 3))

    # Stability: a deterministic agent is STABLE; perturb it to see UNDERSPECIFIED.
    report = run_stability(
        lambda: sm.run({}).steps[-1].output,
        expected="hello there",
        n=5,
        context={"nondeterministic": False},
    )
    print("stability:", report.classification.value, "spread:", report.correctness_spread)
