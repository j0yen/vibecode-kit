"""pybuilder — PRD-driven, evaluation-gated Python code generation.

The Python analog of the Rust ``/autobuilder`` skill, applying the four pillars
of test-driven development for LLM applications:

1. State-machine modeling (``pybuilder.flowgraph``) — the flowchart *is* the code,
   and production traces become replayable test cases.
2. Multi-dimensional evaluation (``pybuilder.eval``) — a quality *vector*
   (exact / fuzzy / static / human / judge) replaces a single pass/fail boolean.
3. Log-don't-assert (``pybuilder.eval.results_bag``) — every dimension is recorded
   per run without aborting on first miss, then aggregated to a DataFrame/CSV.
4. Stability + provenance (``pybuilder.stability``, ``pybuilder.dataset``) — the same
   input is run N times to separate acceptable LLM noise from an underspecified
   prompt, and every eval row is pinned to the git commit that produced it.

The risk gate (``pybuilder.gate``) declares ready/blocked from structured receipts;
nothing self-approves.
"""

__version__ = "0.1.0"

# v1 target scope. `agent` is first-class (resolves vision OQ-1, 2026-06-12):
# the flowgraph state-machine target is the reason this tool exists, not a v2 add-on.
TARGETS = ("cli", "lib", "agent")
