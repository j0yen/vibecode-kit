# pybuilder

**Turn an idea into working, tested Python software** — using Claude Code as your build partner.

You describe what you want to build. pybuilder scaffolds the project, writes the code, tests it,
and won't declare it done until it actually works. Not "it compiled" works — *"it does what you
asked for"* works.

It's designed for people who have a clear idea of what they want, but don't want to spend their
time wiring up boilerplate, writing test harnesses, or second-guessing whether the code is any
good. pybuilder handles all of that.

## What it builds

Three kinds of Python projects:

- **CLI tool** — a command you run in the terminal. Good for automation, file processing,
  data wrangling, scheduled tasks. The fastest thing to build and the best starting point
  if you're not sure which type you need.

- **Library** — reusable code another project imports. Good for shared logic, data models,
  API wrappers.

- **Agent** — a program that reasons and makes decisions, not just executes steps.
  Good for anything that involves language models, multi-step workflows, or adaptive behavior.
  This is pybuilder's specialty.

## How it works

You start with a PRD — a short document describing what you want. If you don't have one yet,
use `/prd-writer` first (it's included). Then you invoke `/pybuilder` in Claude Code.

Behind the scenes, pybuilder runs a loop:

1. **Understand** — extracts your requirements and acceptance criteria from the PRD
2. **Scaffold** — creates the project structure and a locked test harness you can't accidentally break
3. **Build** — writes code in `src/` only, then runs the full quality check
4. **Evaluate** — measures the result across multiple dimensions (not just "did it crash?")
5. **Gate** — an independent review that must pass before anything is declared ready

It won't ship on a green test suite alone. LLM-bearing code behaves differently across runs, so
pybuilder runs the same inputs multiple times and checks for consistency. A flaky result is a
signal that the spec needs sharpening, not that you should ignore it.

## Getting started

**First time?** Start with `/prd-writer`. It helps you turn any idea into the kind of clear
description pybuilder can act on. Takes about ten minutes.

**Have a PRD?** Install everything in one step:

```bash
curl -fsSL https://raw.githubusercontent.com/j0yen/vibecode-kit/main/install.sh | bash
```

This installs two Claude Code skills (`/prd-writer` and `/pybuilder`) and the `pybuilder`
command-line tool.

**Then in Claude Code:**
```
/pybuilder path/to/your-prd.md
```

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **git**
- **[Claude Code](https://claude.ai/code)**

That's it. No Docker, no cloud accounts, no infrastructure to set up.

## Models

pybuilder uses different Claude models for different stages — so it's efficient for people
with lower API rate limits while still using the strongest model where it matters.

| Stage | Model |
|---|---|
| Reading and understanding the PRD | Sonnet |
| Generating project structure (scaffold) | Haiku |
| Writing code, evaluating quality | Sonnet |
| Checking receipts and gate results | Haiku |
| Independent reviewer (final approval) | Sonnet |
| Postmortem summary | Haiku |

**The reviewer is always a fresh, independent agent** — that's the second opinion that
ensures pybuilder can't approve its own work. Its independence comes from the separate
agent and clean context, not from model size, so it runs on Sonnet like the other
reasoning steps (escalate to Opus only when the user explicitly asks). Haiku covers the
mechanical steps. Cheapest capable model, always.

These defaults are set in `src/pybuilder/models.py` and can be overridden with environment
variables (`PYBUILDER_BUILD_MODEL`, `PYBUILDER_REVIEW_MODEL`, `PYBUILDER_FAST_MODEL`) if
you need to.

An `ANTHROPIC_API_KEY` is required for the reviewer and judge steps. Everything else
(scaffold, audit, gate receipt checks) runs locally with no network call.

## What's in the repo

```
src/pybuilder/        the build pipeline
skill/                the /pybuilder Claude Code skill
skills/prd-writer/    the /prd-writer Claude Code skill
tests/                the test suite
install.sh            installs both skills and the CLI
```

## License

MIT OR Apache-2.0.
