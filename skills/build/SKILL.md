---
name: build
description: >
  Implement a PRD end-to-end and close its lifecycle. Scans the PRD home for
  Status: queued PRDs (oldest first) and drains the queue — or builds one named
  PRD — dispatching each to /pybuilder, then marking it built (and archiving it)
  or blocked based on pybuilder's risk gate, regenerating MANIFEST.md after each.
  Use when the user says /build, /build <prd-path>, or asks you to work through
  the PRD queue.
---

# /build — route a PRD to its builder, then close its lifecycle

`/build` is a thin dispatcher plus the place PRD lifecycle closes. It does not
scaffold, iterate, or gate anything itself — that's `/pybuilder`'s job. Its own
work is: pick the right PRD(s), hand off, and record what happened in the PRD's
own frontmatter (and in `MANIFEST.md`, its derived view). No daemon, no timer —
all of this happens inside one `/build` invocation.

## Resolve the PRD(s)

Same PRD home resolution as `/dream`: `$DREAM_PRD_DIR` if set, else
`~/Documents/PRDs/` if it exists, else `./PRDs/`. Create `$PRD_DIR/archive/` if
it doesn't exist yet.

- **User names a specific PRD path** → build just that one; skip queue draining.
- **User names nothing** → scan `$PRD_DIR/*.md` frontmatter for `Status: queued`,
  oldest `Date` first, and **drain the queue**: loop the per-PRD lifecycle below
  until no `queued` PRDs remain.
- **A `Status: building` PRD turns up at scan time** — that's a stale marker
  from an interrupted run, not an in-progress one (nothing else touches PRDs
  concurrently). Note it, treat it as `queued`, and pick it up in the same
  drain.
- **A `queued` PRD has `build_target: product`** → skip it (say so) and leave
  its `Status` untouched; it's not auto-buildable and doesn't participate in
  the built/blocked lifecycle.

## Route on `build_target`

Read the PRD's frontmatter `build_target`:

- **`python-cli` / `python-lib` / `python-agent`** → invoke `/pybuilder <prd>`.
- **`product`** → not auto-buildable (vision/process/GTM work); see above.
- **Missing or ambiguous `build_target`** → treat it as `python-cli`/
  `python-lib`/`python-agent` (whichever the PRD's shape suggests) and invoke
  `/pybuilder`. Python is the only build family, so there's nothing to
  disambiguate between.

## Per-PRD lifecycle

1. Set `Status: building` in the PRD's frontmatter and save — this is the only
   state a crash mid-run leaves behind, so it must land before the handoff.
2. Invoke `/pybuilder <prd>` and let it run its own pipeline end to end.
3. Judge the outcome from `/pybuilder`'s risk gate:
   - **Pass** → set `Status: built`, add `Built: YYYY-MM-DD` and a `Receipts:
     <path>` line pointing at the gate's receipts, then move the PRD file into
     `$PRD_DIR/archive/` (`git mv` if `$PRD_DIR` is a git repo, else `mv`).
   - **Fail** → set `Status: blocked` and add a one-line `Blocked: <reason>`
     summarizing what the gate reported. Leave the file where it is — a
     blocked PRD is not archived.
4. **Regenerate `MANIFEST.md`** right after this PRD, before touching the next
   one — same scan as `/dream`: `$PRD_DIR/*.md` + `$PRD_DIR/archive/*.md`, one
   line per PRD (filename, Status, build_target, date), atomic write (temp file
   in the same directory, then rename over). This is what makes draining a
   multi-PRD queue interruption-safe: a crash after step 4 leaves the manifest
   accurate as of the last completed PRD.
5. If draining a queue, continue to the next `queued` PRD; otherwise stop.

## Handoff

Pass the resolved PRD path straight through to `/pybuilder` and let it run its
own pipeline (intake, scaffold, gates, whatever it does). `/build` adds no
success/failure judgment of its own beyond reading the risk gate to drive the
status transition above — it reports whichever result `/pybuilder` reports.

## Model routing

Always the cheapest capable model. The ladder: Haiku < Sonnet < Opus/Fable.

- **This skill's own work** — scanning `$PRD_DIR`, frontmatter status flips,
  MANIFEST.md regeneration, git bookkeeping — is mechanical. Run it inline; if
  any of it is delegated to a subagent, spawn that subagent on **Haiku**.
- **Python implementation** happens inside `/pybuilder`, which pins **Sonnet**
  for its coding stages and Haiku for its mechanical stages (see its model
  table). Never escalate code work to Opus or Fable — pybuilder's risk gate,
  not a bigger model, is the quality control.
- **PRD writing is not this skill's job.** That's `/dream`, which drafts on
  **Fable (Opus fallback)**. If a build run reveals a PRD gap, hand it back to
  `/dream` rather than redrafting here on a cheaper model.
