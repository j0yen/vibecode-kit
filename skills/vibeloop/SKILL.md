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
├── state.json     # {cycle, no_progress_streak, max_prds_per_cycle, plateau_limit,
│                   #  max_actions_per_prd_per_cycle, build_mode,
│                   #  waiting_streak, waiting_limit}
├── ledger.md       # append-only, one line per cycle
├── STOP            # absent = running; present = halted, contains the reason
└── intent.md       # optional — operator-authored standing dream seed
```
`max_actions_per_prd_per_cycle` (default `1`) and `build_mode` (`serial` default,
`parallel` opt-in) are throughput knobs — see Build (R4) below. `waiting_streak`
(default `0`) and `waiting_limit` (default `12`) track consecutive `WAITING` cycles —
see Digest (R5) and the Plateau and waiting pauses step below. All four are new-ish; a
`state.json` written before any of them existed is missing the keys, which read as their
defaults and get written back the next time Digest (R5) runs.

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
           'plateau_limit': 3,
           'max_actions_per_prd_per_cycle': 1,
           'build_mode': 'serial',
           'waiting_streak': 0,
           'waiting_limit': 12
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

1. **P1 — resolve stale external blocks first.** Scan `$PRD_DIR/build-queue/` (or wherever the
   installed `/build`'s contract keeps in-progress PRDs) for any PRD whose `Status:` is `blocked`
   (set by a prior `/build` call after a failed risk-gate run — README's lifecycle: `blocked`
   stays in place with a `Blocked: <reason>` line) whose `Blocked:` text names another PRD by
   filename or slug. If that named PRD is now present in `$PRD_DIR/built-prds/`, requeue this one:
   set `Status: queued` (keep the existing `Blocked:` line in place as a note — do not delete it),
   and let it flow into the list below same as any other queued PRD; it may be classified
   `selectable` and picked up in this same cycle's selection at step 3. This is the only case
   where vibeloop itself edits a PRD's `Status:` line — every other status transition belongs to
   `/build` (Hard rule 13).
2. List queued PRDs (`Status: queued`, including any newly dreamed ones and any just requeued by
   step 1), oldest `Drafted`/`Date` first — same ordering `/build` uses when draining. For
   **every** PRD in this full list — not just the ones about to be selected — read its
   frontmatter and classify why it either can or cannot be selected this cycle:
   - `depends-on:<slug>` — the PRD has a `Depends-on:` line naming another PRD, and that PRD's
     slug is not present in `$PRD_DIR/built-prds/` (the same location `/build`'s own lifecycle
     moves a shipped PRD to — this step only reads that outcome, it does not reimplement
     dependency resolution).
   - `blocked:<reason>` — the PRD has no unresolved `Depends-on:`, but carries a `Blocked:` line
     whose text contains one of a small listed vocabulary of external-event words (case-
     insensitive substring match, first match in this order wins): `measurement`, `human`,
     `credential`, `host`, `gate`. Tag it with that word, e.g. `blocked:human` for `Blocked: needs
     human sign-off`. A `Blocked:` line whose text matches none of these words does not count as
     external — leave the PRD `selectable`; `/build`'s own risk gate is what decides whether it
     can actually proceed.
   - `selectable` — neither of the above.
   Record this per-PRD classification (call the non-`selectable` ones this cycle's
   `unselectable=[...]`) for Digest (R5) step 2's `WAITING` decision and the ledger's
   `waiting_on=` field.
3. Take the first `max_prds_per_cycle` (from state.json) **`selectable`** PRDs off that list —
   skip any classified `depends-on:...` or `blocked:...`; they are recorded above but never named
   in a `/build` call this cycle. This cap is vibeloop's,
   not `/build`'s, and it bounds this whole step: **no more than these `max_prds_per_cycle`
   PRDs are ever touched this cycle**, in either mode below. Read `max_actions_per_prd_per_cycle`
   and `build_mode` from state.json (defaults `1` and `serial` — see Phase −1) and dispatch with
   one of the two modes.

   **Reading progress after a call**, used by both modes: re-read the PRD's `- Status:` line, and
   — when `~/.claude/skills/build/state/manifest.json` exists (the private build; the kit's
   Python-only `/build` does not write one, so fall back to `Status` alone there) — its recorded
   `action` for this PRD:
   ```bash
   python3 -c "
   import json, pathlib
   p = pathlib.Path.home() / '.claude/skills/build/state/manifest.json'
   slug = pathlib.Path('<prd-path>').stem.removeprefix('PRD-')
   if p.exists():
       m = json.loads(p.read_text())
       print(m.get('prds', {}).get(slug, {}).get('action'))
   else:
       print(None)
   "
   ```

   **Serial mode** (`build_mode: serial`, today's default): for each selected PRD, in order:
   1. Check `$PRD_DIR/vibeloop/STOP`. If present, stop the whole drain immediately — no further
      `/build` call, of any PRD — and let Digest record what happened up to that point.
   2. Invoke `/build <prd-path>`, naming this one PRD's exact path. Increment its action count.
   3. Re-read its `Status` (and manifest `action`, if present) per above.
   4. If `Status` is now `built`: record `built=[<file>(<actions>)]` and move to the next
      selected PRD. If `blocked`: record `blocked=[<file>(<actions>): "<Blocked: reason>"]` and
      move on — **never call `/build` on it again this cycle**, even if PRDs remain.
   5. Otherwise (still in progress): if `actions < max_actions_per_prd_per_cycle`, go back to
      step 2 for this same PRD. If the cap is reached, record it as `pending=[<file>(<actions>)]`
      — or as `advanced=[<file>(<actions>)]` instead, per Digest (R5) step 2's PROGRESS definition below, if `Status` or the
      manifest `action` changed from its value before this PRD's first call this cycle — and move
      to the next selected PRD.
   This reproduces exactly today's behavior when `max_actions_per_prd_per_cycle: 1`: one
   `/build` call per selected PRD, then record built/blocked/pending/advanced and stop.

   **Parallel mode** (`build_mode: parallel`): snapshot every selected PRD's `Status` (and
   `Blocked:` line, and manifest `action` if present) before the round. Make **one** bare
   `/build` call naming all selected PRDs' paths space-separated, with the instruction that it
   advance exactly this set this tick using its own parallel dispatch rules (up to 30 PRDs
   concurrently, per-PRD worktrees — vibeloop adds no locking of its own) and touch no other
   queued PRD. Snapshot again afterward and diff against the pre-round snapshot per selected PRD:
   - now `built` → `built=[<file>(<round>)]` (rounds so far count as its "actions").
   - now `blocked` → `blocked=[<file>(<round>): "<Blocked: reason>"]`; drop it from the next
     round's PRD list — never name a `blocked` PRD in a later `/build` call this cycle.
   - still in progress, `Status` or manifest `action` unchanged from the pre-round snapshot →
     stays `pending=[<file>(<round>)]` for now.
   - still in progress, `Status` or manifest `action` changed → `advanced=[<file>(<round>)]` for
     now (may still finish in a later round and become `built`/`blocked`).
   Before each round (including the first), check `$PRD_DIR/vibeloop/STOP`; if present, stop —
   no further bare `/build` call — and let Digest record the last snapshot's classification.
   Otherwise repeat the round — re-snapshot, one more bare `/build` call over whatever selected
   PRDs are still in progress, re-diff — while any selected PRD is still not `built`/`blocked`
   and the round count is below `max_actions_per_prd_per_cycle` (the cap applies per PRD, but
   since one call advances all of them together, it doubles as the round cap here). If that bare
   `/build` call also advances or builds a PRD outside this cycle's selection, do not count it in
   `built`/`blocked`/`pending`/`advanced` — mention it in the ledger's free-text `note=` field
   instead (omit `note=` when there is nothing to say).

### 5. Digest (R5) — append one ledger line, update state, commit

1. Re-count the queue the same way as step 1.4 — `queue_after`.
2. Decide this cycle's verdict:
   - `HALTED` / `ABORTED` were already decided (and the cycle already ended) in steps 1–2.
   - `PROGRESS` — at least one PRD was built, dreamed, **or advanced** this cycle (`advanced`
     meaning: still in progress at the action/round cap, but its `Status` or the manifest
     `action` changed during this cycle — see the serial-mode step 5 and parallel-mode diff rules in Build (R4)). A cycle that made real
     headway on a long PRD is not `IDLE` just because nothing finished.
   - `WAITING` — nothing built, dreamed, or advanced; `queue_after` (equivalently `queue_before`,
     since nothing moved) is non-empty; **zero PRDs were
     `selectable`** this cycle (Build (R4) step 2's per-PRD classification — no PRD ever entered
     the selection pool, so no `/build` call happened at all); and every unselectable PRD's
     reason is `depends-on:<slug>` or a `blocked:<reason>` in the external vocabulary — never a
     plain `selectable` PRD that was simply not attempted. Record the distinct reasons (dedupe
     identical `depends-on:<slug>`/`blocked:<reason>` tags across PRDs, keeping a count) as
     `waiting_on=[...]` in the ledger line (step 3). `no_progress_streak` is **left unchanged** by
     a `WAITING` cycle — only `waiting_streak` moves (step 4). This is the case this PRD exists
     for: a loop correctly waiting on a dependency (e.g. every queued PRD's `Depends-on` names a
     measurement PRD not yet built) is not the same as a loop that could have built something and
     didn't.
   - `IDLE` — nothing built, dreamed, or advanced, and either the queue is empty or at least one
     queued PRD was `selectable` this cycle (so vibeloop could have attempted something and chose
     not to, or attempted it and it didn't finish), and the resulting `no_progress_streak` (below)
     is still under `plateau_limit`.
   - `PLATEAU` — same condition as `IDLE` above, and `no_progress_streak` has just reached
     `plateau_limit`. (Step 6 handles what this triggers.)

   Open question carried from the PRD (owner: Joe, due after ten cycles under this rule):
   whether `advanced` resetting `no_progress_streak` the same way `built`/`dreamed` does is
   right long-term, or whether a PRD that never finishes should eventually still read as
   stalled. Today it resets the streak like `built` — see step 4.
3. Append exactly one line to `$PRD_DIR/vibeloop/ledger.md` (never rewrite or reorder existing
   lines — append-only):
   ```
   <ISO-ts> cycle=<n> goal="<first ~8 words of intent.md>" queue=<before>-><after> built=[...] blocked=[...] pending=[...] advanced=[...] dreamed=[...] verdict=<PROGRESS|IDLE|PLATEAU|WAITING|ABORTED|HALTED> waiting_on=[...] note="<free text, optional>"
   ```
   `built`/`blocked`/`pending`/`advanced` entries carry the per-PRD action count, e.g.
   `built=[PRD-x.md(3)]`, `blocked=[PRD-x.md(2): "<Blocked: reason>"]`, `pending=[PRD-y.md(4)]`,
   `advanced=[PRD-z.md(4)]`. Use empty `[]` for any of `built`/`blocked`/`pending`/`advanced`/
   `dreamed` that had nothing to report; omit the `goal=` field entirely when no `intent.md`
   exists, and omit the trailing `note="..."` when there is nothing to say (it is the one free-text field, used for out-of-selection activity in parallel mode and any other remark worth keeping).
   Omit `waiting_on=` entirely except on a `WAITING` verdict line, where it lists the distinct
   unselectable reasons from Build (R4) step 2 with counts, e.g.
   `waiting_on=[depends-on:PRD-mcphost-measure-comparable x3]` or
   `waiting_on=[blocked:measurement x1, blocked:human x1]`.
4. Update `state.json`: increment `cycle`; update `no_progress_streak` and `waiting_streak`
   per the verdict decided in step 2; and write back
   `max_actions_per_prd_per_cycle`/`build_mode`/`waiting_streak`/`waiting_limit` defaults if a
   pre-existing state.json was missing them (Phase −1 already defaults them for a brand-new file
   — this is for one written before these keys existed). Example:
   ```bash
   python3 -c "
   import json, pathlib
   p = pathlib.Path('$PRD_DIR/vibeloop/state.json')
   s = json.loads(p.read_text())
   s['cycle'] += 1
   s.setdefault('no_progress_streak', 0)
   s.setdefault('waiting_streak', 0)
   s.setdefault('max_actions_per_prd_per_cycle', 1)
   s.setdefault('build_mode', 'serial')
   s.setdefault('waiting_limit', 12)
   if verdict == 'WAITING':
       s['waiting_streak'] += 1
       # no_progress_streak is untouched on a WAITING cycle
   else:
       s['waiting_streak'] = 0
       s['no_progress_streak'] = 0 if made_progress else s['no_progress_streak'] + 1
   p.write_text(json.dumps(s, indent=2) + '\n')
   "
   ```
   (Substitute the literal `True`/`False` for `made_progress`, and the literal verdict string
   for `verdict`, when running this — both are placeholders for what step 2 decided.
   `made_progress` is `True` when anything was built, dreamed, or advanced; it is always `False`
   on a `WAITING` cycle by definition, but `no_progress_streak` still must not move then.)
5. Commit, path-scoped to exactly what this cycle touched: `ledger.md`, `state.json`, and any
   PRD/vision/manifest files `/dream` or `/build` wrote or moved. Use the workspace's existing
   git identity — never set or hardcode one, never `git add -A`. Suggested message:
   `vibeloop: cycle <n> — <verdict>`. Push only if `origin` exists; a push failure is a warning
   told to the user, not an error that fails the cycle. Never force-push.

### 6. Plateau and waiting pauses (R6)

If step 5.2 decided `PLATEAU`: write `$PRD_DIR/vibeloop/STOP` containing the reason, e.g.:
```
PLATEAU: 3 consecutive cycles with no PRD built, advanced, or dreamed (plateau_limit=3).
Resume by deleting this file: rm $PRD_DIR/vibeloop/STOP
```

If step 5.2 decided `WAITING` and the just-updated `waiting_streak` (step 5.4) is now **greater
than** `waiting_limit`: write `$PRD_DIR/vibeloop/STOP` containing the reason, e.g.:
```
WAITING: depends-on:PRD-mcphost-measure-comparable for 13 cycles (waiting_limit=12).
Resume by deleting this file: rm $PRD_DIR/vibeloop/STOP
```
Use this cycle's `waiting_on=` reasons (step 5.3) and `waiting_streak` in the message. This is a
separate limit from `plateau_limit` — a loop that is correctly waiting on a real dependency still
halts eventually, with a reason a human can act on, rather than polling a blocked dependency
forever unattended (Goals: "keep the plateau rule for the case it was written for" — this is the
matching guardrail for the `WAITING` case).

Either way, state this to the user plainly, in addition to the ledger line: the loop has paused
itself, and resuming is a human act — nothing in this skill deletes STOP, ever, including a later
`/vibeloop` invocation. A `/vibeloop` call while STOP exists only ever produces `HALTED` (step 1).

## `/vibeloop status` (R8) — read-only, mutates nothing

A separate invocation shape. Do not run any of the cycle steps above. Report, in one screen:
- Queue depth (same scan as step 1.4, right now).
- The last 5 lines of `$PRD_DIR/vibeloop/ledger.md` (`tail -n 5`, or fewer if the ledger is
  shorter — never fabricate lines that are not there).
- `state.json`'s counters as-is, including `max_actions_per_prd_per_cycle` and `build_mode`
  beside `max_prds_per_cycle` and `plateau_limit` (defaults `1` and `serial` if the keys are
  absent — read-only status never writes them back). Say plainly which build mode is in force:
  "serial — one `/build` call per selected PRD" or "parallel — one bare `/build` call per round
  across the selection."
- `waiting_streak` and `waiting_limit` from `state.json` (defaults `0` and `12` if the keys are
  absent), and **`waiting on:`** — scan `ledger.md` backward for the most recent line with
  `verdict=WAITING` and print its `waiting_on=[...]` reasons verbatim, e.g. `waiting on:
  depends-on:PRD-mcphost-measure-comparable x3`. If no `WAITING` line has ever been recorded, say
  so plainly ("waiting on: none recorded yet") rather than omitting the line.
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

A multi-action or parallel cycle (`max_actions_per_prd_per_cycle > 1` or `build_mode: parallel`)
can run longer wall-clock per invocation than the single-action default. On RedBaron this changes
nothing about the outer envelope: the launcher's own tick cap, `RuntimeMaxSec`, and inactivity
watchdog still wrap every `/vibeloop` call exactly as before — this skill has no opinion on them
and does not need to, since they bound the invocation from outside regardless of how much work
one cycle does inside it.

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
10. **Never exceed `max_prds_per_cycle` distinct PRDs in one cycle.** Build (R4) selects that
    many at step 4.3 and touches no others, in either mode, for the rest of the cycle.
11. **Never call `/build` once `$PRD_DIR/vibeloop/STOP` appears.** Checked before every call in
    serial mode and before every round in parallel mode (R4); a STOP written mid-cycle by a
    concurrent process ends the drain immediately, same as rule 6.
12. **Never retry a `blocked` PRD within the same cycle.** Once a selected PRD reads `blocked`,
    it is recorded and dropped from every later `/build` call this cycle, in both modes.
13. **Vibeloop edits a PRD's `Status:` line in exactly one case.** Requeuing a stale `blocked`
    PRD whose `Blocked:` line names another PRD now present in `built-prds/` (Build (R4) step 1,
    P1). Every other status transition — `queued` → `building` → `built`/`blocked` — belongs to
    `/build`, never to vibeloop itself.
