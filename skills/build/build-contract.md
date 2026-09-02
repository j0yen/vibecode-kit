# /build — PRD intake contract (vibecode-kit)

> **Fleet note (2026-09-02):** in the j0yen fleet the installed `/build` is
> [`j0yen/build-skill`](https://github.com/j0yen/build-skill), whose
> `build-contract.md` covers both Rust and Python targets and is the contract
> `/dream` reads. This kit copy is the Python-only reference router for
> standalone kit users; do not install it as `/build` on a fleet node.


`/dream` reads this file at the start of every run and writes PRDs to it. This
is the kit's router: every buildable PRD goes to `/pybuild`.

## Where PRDs live

- `$PRD_DIR` = `$DREAM_PRD_DIR`, else `~/Documents/PRDs/`, else `./PRDs/`.
- Queue: `$PRD_DIR/build-queue/PRD-<slug>.md` (the only directory `/build`
  reads). Done: `$PRD_DIR/built-prds/` (moved on ship). Parked:
  `$PRD_DIR/parked/` (never scanned; a human moves files in and out).
  Visions in `visions/`, project profiles in `projects/`, run log in
  `notes/dream-log.md`. The PRD's frontmatter is the state; any manifest is a
  derived cache. Keep `$PRD_DIR` a git repo with an origin so the workspace is
  shared across machines.

## Frontmatter (bullet form, first 80 lines)

| key | values | required |
|---|---|---|
| `Status` | `queued` → `building` / `built` / `blocked` | yes |
| `build_target` | `python-cli` `python-lib` `python-agent` (→ `/pybuild`); `product` (skipped) | yes |
| `build_into` | path of an existing repo to extend | when extending |
| `publish` | `<gh-user>/private` `<gh-user>/public` `none` | no — default: no publish |
| `Vision` | `visions/<slug>.md` | yes |
| `Depends-on` | `PRD-<slug>.md`, comma-separated | no |
| `Loop` | `<loop-name>: <metric it moves>` | loop-ready fleets only |

## Acceptance criteria

`## Acceptance criteria`, one AC per line as `N. P0|P1|P2 — Given …, When …, Then …`.
`/pybuild` reads them in plain English; the numbered form keeps them countable
by any stricter builder.
