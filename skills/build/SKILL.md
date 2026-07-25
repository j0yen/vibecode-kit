---
name: build
description: >
  Implement a PRD end-to-end by routing to the right builder. Reads the PRD's
  build_target and dispatches to /pybuilder (python-*, the default) or
  /rustbuilder (rust-*, only when the PRD or user explicitly calls for Rust).
  Use when the user says /build, /build <prd-path>, or hands you a PRD and asks
  you to implement it without naming a builder.
---

# /build — route a PRD to its builder

`/build` is a thin dispatcher. It does not scaffold, iterate, or gate anything
itself — that's `/pybuilder`'s and `/rustbuilder`'s job. Its only work is
picking the right one and handing off.

## Resolve the PRD

Same PRD home resolution as `/dream`: `$DREAM_PRD_DIR` if set, else
`~/Documents/PRDs/` if it exists, else `./PRDs/`. If the user names a path, use
it directly. If they name nothing, take the next `queued` PRD in that home
(oldest first).

## Route on `build_target`

Read the PRD's frontmatter `build_target`:

- **`python-cli` / `python-lib` / `python-agent`** → invoke `/pybuilder <prd>`.
- **`rust-cli` / `rust-lib` / `rust-extend`** → invoke `/rustbuilder <prd>`,
  but only when the PRD or the user's request explicitly calls for Rust
  (systems-level work, a `cargo`/crate target, a stated performance
  requirement Python can't meet).
- **`product`** → not auto-buildable (vision/process/GTM work). Say so and
  stop; don't force it through a builder.
- **Missing or ambiguous `build_target`** → check `echo $DREAM_DEFAULT_TARGET`.
  If it's set to `rust`, treat the PRD as `rust-cli`/`rust-lib`/`rust-extend`
  and invoke `/rustbuilder`. Otherwise (unset or any other value) default to
  Python: treat it as `python-cli`/`python-lib`/`python-agent` (whichever the
  PRD's shape suggests) and invoke `/pybuilder`. Either way, an explicit Rust
  ask in the PRD body or the user's request wins over the env var.

## Handoff

Pass the resolved PRD path straight through to the chosen builder and let it
run its own pipeline (intake, scaffold, gates, whatever that builder does).
Report back whichever result the builder reports — `/build` doesn't add its
own success/failure judgment on top.
