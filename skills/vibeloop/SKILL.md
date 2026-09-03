---
name: vibeloop
description: >
  Run one complete orient -> preflight -> dream -> build -> digest cycle over the PRD queue,
  and leave a durable ledger record. Markdown-only: no shipped scripts or binaries, state
  manipulation via git, plain file writes, and python3 -c one-liners. Re-arms through Claude
  Code's own scheduling (a routine, or /loop in a live session) rather than any OS service.
  The primary invocation is goal-driven: /vibeloop <goal> points every cycle at a target
  outcome (e.g. "drive NLQ accuracy on the eval corpus", "translate the DAX workbook
  backlog") — the goal becomes the standing intent that dreaming serves. Also use for
  /vibeloop (bare — continue the standing goal or just drain the queue), /vibeloop status,
  "run the loop", "keep dreaming and building", "drain the queue continuously". One
  invocation is exactly one cycle — it never loops internally and never schedules itself.
---

# /vibeloop — the portable dream-build-evaluate loop

`/vibeloop` closes the gap between `/dream` and `/build`: instead of a human invoking each
skill by hand, one `/vibeloop` invocation orients, checks preflight, dreams only if the queue
is empty and the operator asked for that, builds up to a capped number of queued PRDs, and
writes one ledger line recording what happened. It never overrides `/pybuild`'s risk gate —
`/build` reports the verdict, vibeloop just records it. It never schedules itself — the operator
opts in to a cadence, documented below.

## Goal-driven invocation — the primary use case

The loops that have paid for themselves were never "drain whatever is queued" — they chased
a named outcome: driving natural-language-query accuracy against an eval corpus cycle after
cycle, or working through a DAX-translation backlog until it was empty. `/vibeloop <goal>` is
that pattern:

- The goal text is written to `$PRD_DIR/vibeloop/intent.md`, overwriting what was there (git
  history preserves prior goals). From then on it is the **standing goal**: every cycle —
  this one and every scheduled one after it — carries it until the operator replaces it.
- The goal steers the Dream phase (it is the seed `/dream` receives when the queue empties)
  and frames the ledger: cycles record `goal="<short form>"` so the trail reads as progress
  toward the outcome, not just queue mechanics.
- A good goal names an outcome and, when one exists, the measure: "raise NLQ accuracy on the
  tpcds eval set", "every workbook in the migration folder translated and verified". A goal
  with a measurable target is what turns the plateau pause from "queue empty" into "target
  reached or progress stalled — human, look."
- Bare `/vibeloop` continues under the standing goal if `intent.md` exists, and is plain
  queue-draining if it does not. Both are supported; the goal-driven form is the reason the
  skill exists.

This skill carries no code. Every phase below is prose instructions to the model, in the same
style as `/dream` and `/build` — runtime discovery, no hardcoded paths, the same `$PRD_DIR`
resolution. Any state read or write is a `git` command, a plain file write, or a `python3 -c`
one-liner spelled out in this document.

## Phase −1 — Discover the environment (always run first)

**PRD home** (`$PRD_DIR` below) — identical resolution to `/dream` and `/build`, first match
wins:
1. `$DREAM_PRD_DIR` if the env var is set.
2. `~/Documents/PRDs/` if it exists.
3. `./PRDs/` under the current working directory.

**Loop state** lives under `$PRD_DIR/vibeloop/`, created on first run:
```
$PRD_DIR/vibeloop/
├── state.json     # {cycle, no_progress_streak, max_prds_per_cycle, plateau_limit}
├── ledger.md       # append-only, one line per cycle
├── STOP            # absent = running; present = halted, contains the reason
└── intent.md       # optional — operator-authored standing dream seed
```

**Git** — same contract as `/dream`: commit with whatever identity is already configured (never
set or hardcode one); push only if `origin` already exists, and treat a push failure as a
warning, never an error. If `$PRD_DIR` is not a git repo, vibeloop still works — commits are
just skipped, said out loud once.

State this discovery in one short line before continuing: where `$PRD_DIR` resolved to, whether
`vibeloop/` already existed, and whether the workspace is a git repo.

## The cycle (one invocation = exactly one cycle)

### 1. Orient (R1)

1. Check `$PRD_DIR/vibeloop/STOP`. If it exists, read its contents, append a `HALTED` ledger
   line (format below) quoting the STOP reason, tell the user the loop is halted and why, and
   **end the cycle here** — nothing else in this skill runs.
2. Read `$PRD_DIR/vibeloop/state.json`. If it does not exist, create it with the defaults below
   before reading further:
   ```bash
   python3 -c "
   import json, pathlib
   p = pathlib.Path('$PRD_DIR/vibeloop/state.json')
   p.parent.mkdir(parents=True, exist_ok=True)
   if not p.exists():
       p.write_text(json.dumps({
           'cycle': 0,
           'no_progress_streak': 0,
           'max_prds_per_cycle': 2,
           'plateau_limit': 3
       }, indent=2) + '\n')
   print(p.read_text())
   "
   ```
3. Read the last few lines of `$PRD_DIR/vibeloop/ledger.md` (create it empty if absent — do not
   invent past history).
4. Count the queue: PRDs in the installed `/build`'s queue directory — `$PRD_DIR/build-queue/*.md` per its build contract (`$PRD_DIR/*.md` in the flat kit layout) — whose frontmatter has `Status: queued`
   (the same scan `/dream` and `/build` use — stale `Status: building` markers count as queued
   too, per `/build`'s own rule). Record this as `queue_before`.

### 2. Preflight (R2) — cheap checks, before any model-expensive step

Run all of these before touching `/dream` or `/build`. On the first failure, append an
`ABORTED <reason>` ledger line, tell the user what failed, and end the cycle — no dream, no
build.

- **Git identity set**: `git config user.name` and `git config user.email` both resolve to a
  non-empty value (global or local — do not set one if missing, that is a fatal preflight gap,
  not something vibeloop fixes).
- **`uv` present**: `command -v uv` succeeds (required by `/pybuild`, which `/build` invokes).
- **`$PRD_DIR` writable**: a trivial write-and-remove of a scratch file succeeds.
- **Origin reachable, if one is configured**: if `git -C "$PRD_DIR" remote get-url origin`
  succeeds, confirm it is reachable (e.g. `git -C "$PRD_DIR" ls-remote --exit-code origin
  HEAD`). No origin configured is not a failure — it just means step 5's push is skipped.

### 3. Dream (R3) — only when the queue is empty AND the operator opted in

- If `queue_before > 0`: skip dreaming entirely, move to Build.
- If `queue_before == 0` and `$PRD_DIR/vibeloop/intent.md` does not exist: skip dreaming, record
  no PRDs dreamed, this cycle's verdict leans `IDLE` (final verdict decided in Digest).
- If `queue_before == 0` and `intent.md` exists: invoke `/dream` seeded with the full contents of
  `intent.md` as the topic/seed. (`intent.md` IS the standing goal — usually written by a
  `/vibeloop <goal>` invocation; a hand-authored file works identically.) Let `/dream` run its own phases untouched — Atlassian evidence,
  user-provided evidence, whatever it finds. If grounding tools are not connected in this
  session, `/dream` degrades to its own ungrounded mode by its own rules; vibeloop does not
  paper over that gap or invent evidence on `/dream`'s behalf (Law 3, both skills). Record the
  filenames of any PRDs `/dream` wrote as `dreamed=[...]`.

### 4. Build (R4) — drain up to `max_prds_per_cycle` queued PRDs

1. List queued PRDs (`Status: queued`, including any newly dreamed ones), oldest `Drafted`/`Date`
   first — same ordering `/build` uses when draining.
2. Take the first `max_prds_per_cycle` (from state.json) off that list. This cap is vibeloop's,
   not `/build`'s: invoke `/build <prd-path>` once per selected PRD, sequentially, naming the
   exact PRD path each time, rather than letting `/build` drain the whole queue in one call.
3. For each invocation, record the PRD's filename under `built=[...]` if `/build` marked it
   `Status: built`, or under `blocked=[...]` if `/build` marked it `Status: blocked`, quoting the
   `Blocked:` reason `/build` wrote. `/build` (via `/pybuild`'s risk gate) is the sole source of
   this verdict — vibeloop adds no judgment of its own and never re-runs or overrides a gate
   result.
4. If `$PRD_DIR/vibeloop/STOP` appears mid-drain (a plateau or manual stop from a concurrent
   invocation is not expected, but check), stop the drain immediately and let Digest record what
   happened up to that point.

### 5. Digest (R5) — append one ledger line, update state, commit

1. Re-count the queue the same way as step 1.4 — `queue_after`.
2. Decide this cycle's verdict:
   - `HALTED` / `ABORTED` were already decided (and the cycle already ended) in steps 1–2.
   - `PROGRESS` — at least one PRD was built or dreamed this cycle.
   - `IDLE` — nothing built, nothing dreamed, and the resulting `no_progress_streak` (below) is
     still under `plateau_limit`.
   - `PLATEAU` — nothing built, nothing dreamed, and `no_progress_streak` has just reached
     `plateau_limit`. (Step 6 handles what this triggers.)
3. Append exactly one line to `$PRD_DIR/vibeloop/ledger.md` (never rewrite or reorder existing
   lines — append-only):
   ```
   <ISO-ts> cycle=<n> goal="<first ~8 words of intent.md>" queue=<before>-><after> built=[...] blocked=[...] dreamed=[...] verdict=<PROGRESS|IDLE|PLATEAU|ABORTED|HALTED>
   ```
   Use empty `[]` for any of `built`/`blocked`/`dreamed` that had nothing to report; omit the
   `goal=` field entirely when no `intent.md` exists.
4. Update `state.json`: increment `cycle`; if this cycle built or dreamed anything, reset
   `no_progress_streak` to `0`, otherwise increment it by `1`. Example:
   ```bash
   python3 -c "
   import json, pathlib
   p = pathlib.Path('$PRD_DIR/vibeloop/state.json')
   s = json.loads(p.read_text())
   s['cycle'] += 1
   s['no_progress_streak'] = 0 if made_progress else s['no_progress_streak'] + 1
   p.write_text(json.dumps(s, indent=2) + '\n')
   "
   ```
   (Substitute the literal `True`/`False` for `made_progress` when running this — it is written
   here as a placeholder for the boolean decided in step 2.)
5. Commit, path-scoped to exactly what this cycle touched: `ledger.md`, `state.json`, and any
   PRD/vision/manifest files `/dream` or `/build` wrote or moved. Use the workspace's existing
   git identity — never set or hardcode one, never `git add -A`. Suggested message:
   `vibeloop: cycle <n> — <verdict>`. Push only if `origin` exists; a push failure is a warning
   told to the user, not an error that fails the cycle. Never force-push.

### 6. Plateau pause (R6)

If step 5.2 decided `PLATEAU`: write `$PRD_DIR/vibeloop/STOP` containing the reason, e.g.:
```
PLATEAU: 3 consecutive cycles with no PRD built and nothing dreamed (plateau_limit=3).
Resume by deleting this file: rm $PRD_DIR/vibeloop/STOP
```
State this to the user plainly, in addition to the ledger line: the loop has paused itself, and
resuming is a human act — nothing in this skill deletes STOP, ever, including a later `/vibeloop`
invocation. A `/vibeloop` call while STOP exists only ever produces `HALTED` (step 1).

## `/vibeloop status` (R8) — read-only, mutates nothing

A separate invocation shape. Do not run any of the cycle steps above. Report, in one screen:
- Queue depth (same scan as step 1.4, right now).
- The last 5 lines of `$PRD_DIR/vibeloop/ledger.md` (`tail -n 5`, or fewer if the ledger is
  shorter — never fabricate lines that are not there).
- `state.json`'s counters as-is.
- Whether `$PRD_DIR/vibeloop/STOP` is present, and if so, its contents.

Nothing is written, moved, or committed by `/vibeloop status`.

## Re-arm guidance — vibeloop never re-arms itself (R7)

`/vibeloop` performs exactly one cycle and stops. Two supported ways to keep it going, both
opt-in by the operator:

- **Supervised nonstop**, in a live session: `/loop /vibeloop`. The built-in `/loop` skill
  re-invokes `/vibeloop` on an interval (or self-paced) while the session stays open. Good for a
  working session where progress should keep happening while the operator does something else,
  with the operator present to notice a `HALTED` or `PLATEAU` verdict and stop `/loop` if needed.
- **Unattended**, across sessions: a Claude Code scheduled routine that runs `/vibeloop` on a
  cron cadence, set up via the paste-prompt in `SETUP.md` §6. This is the path for a colleague
  who wants the queue draining while they are not at the keyboard.

State which mode (if either) is already active whenever `/vibeloop` or `/vibeloop status` runs,
if that is knowable (a routine calling this skill can say so in its own context). vibeloop itself
never creates a schedule and never starts `/loop` — both require the operator's explicit,
separate action. If a user asks vibeloop to "set up the schedule" mid-cycle, point them at
`SETUP.md` §6 or `/schedule` rather than doing it inline.

## Model routing

Cheapest capable model always — the ladder is Haiku < Sonnet < Opus/Fable.

- **This skill's own orchestration** — `$PRD_DIR` discovery, STOP/state.json reads and writes,
  queue counting, ledger appends, git bookkeeping — is mechanical. Run it inline; if any of it is
  delegated to a subagent, spawn that subagent on **Haiku**.
- **Dreaming** happens entirely inside `/dream`, which drafts on **Fable, with Opus as the
  fallback**. vibeloop does not draft PRD content itself — it only decides whether to invoke
  `/dream` and passes `intent.md` through as the seed.
- **Building** happens entirely inside `/build` → `/pybuild`, which pins **Sonnet** for coding
  stages and Haiku for its own mechanical stages.
- **Never escalate vibeloop's own orchestration to Opus or Fable.** There is no reasoning-heavy
  work in this skill — every decision above is a rule applied to file contents, not synthesis.

## Invocations

- `/vibeloop <goal>` — **the primary form.** Write the goal to
  `$PRD_DIR/vibeloop/intent.md` (overwrite; git history keeps prior goals), then run one
  cycle end to end under it. Examples: `/vibeloop drive NLQ accuracy on the tpcds eval set`,
  `/vibeloop translate the DAX workbook backlog to SML`.
- `/vibeloop` — run one cycle under the standing goal if `intent.md` exists, else plain
  queue-draining.
- `/vibeloop status` — read-only readout, no mutation.

## Hard rules

1. **Markdown-only.** This skill ships no scripts and no binaries (R9). Every state mutation is a
   `git` command, a plain file write, or a `python3 -c` one-liner spelled out in this document.
2. **Ledger is append-only.** Never rewrite, reorder, or delete a line already in `ledger.md`.
3. **Never force-push, never set or hardcode a git identity.** Use whatever is already
   configured; push only when `origin` exists; a push failure is a warning, not an error.
4. **Never create a schedule and never start `/loop` on your own.** Re-arming is always the
   operator's explicit action (R7).
5. **Never override the `/pybuild` risk gate.** `/build`'s reported verdict (built/blocked) is
   recorded verbatim; vibeloop adds no judgment of its own.
6. **STOP is sacred.** Any phase that finds `$PRD_DIR/vibeloop/STOP` present halts immediately
   with a `HALTED` ledger line. Only a human deleting the file resumes the loop.
7. **One cycle per invocation.** `/vibeloop` never loops internally — that is what `/loop` and
   scheduled routines are for.
8. **Dream never invents evidence.** When grounding tools are absent, `/vibeloop`'s Dream phase
   proceeds only on whatever `/dream` itself is willing to work from — absence of evidence is
   never papered over (Law 3).
9. **Discovery over assumption.** Re-run Phase −1 every invocation; `$PRD_DIR` and the git/tool
   environment can change between runs.
