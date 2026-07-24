---
name: rustbuilder
description: >
  PRD-driven Rust implementation with a fully local toolchain. Takes a PRD (file path, or the
  next queued one in the PRD home) and walks it from Draft to Shipped: implement, gate on
  cargo build + cargo test (+ clippy when available), update the PRD status, commit. No cloud
  build servers, no remote infrastructure — everything runs on this machine's cargo. Use when
  the user says /rustbuilder, /rustbuilder <prd-path>, /rustbuilder status, or hands you a PRD
  with build_target rust-cli | rust-lib | rust-extend. Pairs with /dream, which drafts the
  PRDs this skill implements.
---

# /rustbuilder — PRDs to shipped Rust, locally

`/rustbuilder` is the implementation counterpart to `/dream`. Where `/dream` walks
ideas to PRDs, `/rustbuilder` walks PRDs to working, tested Rust code — using only
the local machine: local cargo, local git, local disk. If a step in this file ever
seems to want a remote server, that's a bug in your reading of it; there is none.

## Prerequisites (check before the first action)

- **Rust toolchain** — `cargo --version` must succeed. If not, stop and tell the
  user to install via rustup (https://rustup.rs). Do not attempt the install
  yourself unless asked.
- **git** — used for commits; identity comes from the machine's existing config.
- `cargo clippy` and `cargo fmt` are used when present; their absence downgrades
  those gates to skipped-with-a-note, never to failure.

## Environment discovery (every invocation)

**PRD home** (`$PRD_DIR`) — same resolution as `/dream`, first match wins:
1. `$DREAM_PRD_DIR` if set
2. `~/Documents/PRDs/` if it exists
3. `./PRDs/` under the current working directory

**State** — `~/.local/state/rustbuilder/queue.json`, created on first run:
```json
{
  "prds": {
    "<slug>": {
      "path": "<abs path to PRD-<slug>.md>",
      "status": "queued | in_progress | shipped | blocked | failed",
      "build_target": "rust-cli | rust-lib | rust-extend",
      "build_into": "<abs path or null>",
      "output_path": "<abs path of what was built, once known>",
      "last_action": "<one line>",
      "blockers": []
    }
  }
}
```
Write it atomically (temp file in the same directory, then rename over). Never let a
crash leave a half-written queue.

**Output root** for new crates — `$RUSTBUILDER_OUT_DIR` if set, else `~/projects/`.

## The tick

One invocation = one PRD advanced end-to-end (or one explicit action). Small and
finishable beats broad and abandoned.

### 1. Scan
Glob `$PRD_DIR/PRD-*.md` (top level only; skip any `ARCHIVE/` or `PARKED/`
subdirectories). Parse frontmatter. PRDs with `build_target` starting `rust-` that
aren't in the queue get upserted as `queued`. PRDs whose file vanished get status
`vanished`. Respect `blocked` entries — they sit out until their blockers ship.

### 2. Select
If the user passed a PRD path, that's the selection. Otherwise pick, in order:
a stale `in_progress` (older than one day — resume it), then the oldest `queued`.
Nothing eligible → print the queue table and exit.

### 3. Read the PRD properly
Read the whole PRD. The acceptance criteria are the contract; the requirements'
MUST/SHOULD/MAY levels set priority. If any MUST-level AC is ambiguous or
untestable, stop and ask the user rather than guessing — a wrong guess costs a
rebuild.

### 4. Implement
- **rust-cli / rust-lib (new crate):** `cargo new <slug> --bin|--lib` under the
  output root (or reuse the directory if a previous tick started it). Implement
  module by module. Add dependencies with `cargo add`, preferring well-known,
  actively maintained crates; every dependency must be justifiable by an AC.
- **rust-extend (existing repo):** `build_into` is the target. Work on a branch
  named `prd/<slug>` if the repo has other active work, directly on the current
  branch otherwise. Read the surrounding code first and match its idioms, error
  types, and module layout. Never rewrite code the PRD doesn't touch.

Write tests alongside the code — every MUST AC gets at least one test that would
fail if that AC regressed. Given/When/Then ACs translate almost mechanically into
test cases; do it.

### 5. Gate (all local)
Run in order; all must pass before the PRD can ship:
1. `cargo build` — clean compile, warnings noted
2. `cargo test` — full suite, including pre-existing tests in extended repos
3. `cargo clippy -- -D warnings` — when clippy is installed
4. **AC walk** — go through the PRD's acceptance criteria one by one and state,
   for each, the test or behavior that satisfies it. An AC with no evidence is
   not satisfied; either add the test or report the PRD as incomplete.

A gate failure gets fixed and re-run. Three consecutive failed fix attempts on the
same gate → set status `failed` with a precise `last_action`, report honestly, and
stop. Never mark shipped on a red gate.

### 6. Ship
1. Update the PRD's `- Status:` line in place: `Shipped v1.0 (<date>)` for new
   work, `Built (<date>)` for extensions. This is the only edit ever made to a
   PRD file.
2. Commit the implementation in its repo — specific files, never `git add -A`;
   message `feat(<slug>): <one-line> (PRD-<slug>)`, using the machine's git
   identity. Commit the PRD status change in `$PRD_DIR` if it's a git repo.
   Push only where an origin remote already exists and pushing is the repo's
   established practice; never create remotes or publish repos on your own.
3. Update the queue entry: `shipped`, `output_path`, `last_action`.
4. Tell the user what shipped, where it lives, how to run it, and which queued
   PRD is next.

## Invocations

- `/rustbuilder` → one tick: scan, select, advance one PRD
- `/rustbuilder <prd-path>` → advance that specific PRD
- `/rustbuilder status` → print the queue table (slug, status, target, last action),
  then exit
- `/rustbuilder requeue <slug>` → reset a `failed`/`blocked` entry to `queued`

## Hard rules

1. **Local only.** All cargo invocations run on this machine. No remote build
   servers, no cloud provisioning, no SSH to build hosts.
2. **Tests are the proof.** No PRD ships without its ACs demonstrably covered.
3. **One PRD per tick.** Finish or fail honestly before touching the next.
4. **Never force-push, never rewrite history, never `git add -A`.**
5. **Don't invent scope.** Implement the PRD, not the feature you wish it
   specified. Gaps go back to the user (or into a note for the next `/dream`).
6. **Report honestly.** Failing tests are reported as failing, with output.
   "Shipped" means the gates ran and passed in this session.
