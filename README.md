# vibecode-kit

A self-contained set of Claude Code skills for going from *"I wish we had X"* to
working, tested code — with a real Product Requirements Document in between.

Everything referenced by these skills ships in this repo. No private repos, no
company infrastructure, no cloud build servers. If you have Claude Code and git,
the kit works; a few optional tools light up extra capability (see below).

## Install as a plugin

This repo is a self-hosted Claude Code plugin marketplace. From Claude Code:

```
/plugin marketplace add j0yen/vibecode-kit
/plugin install vibecode-kit@vibecode
```

Updates arrive with `/plugin marketplace update vibecode`.

Skills install namespaced to this plugin — `/vibecode-kit:dream`,
`/vibecode-kit:build`, etc. — so they never collide with skills you already
have under your own name.

The default build target is Python; power users who want Rust by default can
set `DREAM_DEFAULT_TARGET=rust` in their own environment.

### Team auto-install

Drop this into a shared repo's `.claude/settings.json` so anyone who opens the
project in Claude Code gets the plugin automatically:

```json
{
  "extraKnownMarketplaces": {
    "vibecode": { "source": { "source": "github", "repo": "j0yen/vibecode-kit" } }
  },
  "enabledPlugins": { "vibecode-kit@vibecode": true }
}
```

## The loop

```
idea ──► /dream ───────► PRDs (+ vision doc, in your PRD folder)
              │
              ├─ build_target: python-*  ──► /pybuilder    (eval-gated Python, DEFAULT)
              └─ build_target: rust-*    ──► /rustbuilder  (local cargo, on request)
```

Handing a PRD to `/build` does this routing for you: Python by default, Rust
only when the PRD or you explicitly ask for it.

1. **`/dream <topic>`** — listens, gathers evidence, writes a vision, then drafts
   three to seven PRDs to the enterprise PRD standard. Each PRD says what to build,
   for whom, why, and how you'll know it worked.
2. **`/rustbuilder`** — implements `rust-*` PRDs one at a time on your machine's
   cargo: build + test + clippy gates, acceptance-criteria walk, honest reporting.
3. **`/pybuilder <prd>`** — implements `python-*` PRDs through a five-stage,
   evaluation-gated pipeline (intake → scaffold → iterate-and-prove → risk gate →
   postmortem).

Two supporting skills round out the set:

- **`/atscale-prd-writer`** — the PRD-writing standard `/dream` follows
  (14-section template, Customer Pain Test, MUST/SHOULD/MAY, anti-pattern audit).
  Also useful on its own for drafting or reviewing any PRD.
- **`/prd-writer`** — the same idea for personal projects: turn a loose idea into
  a spec `/pybuilder` can build, no PM background required.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/j0yen/vibecode-kit/main/install.sh | bash
```

or from a checkout:

```bash
git clone https://github.com/j0yen/vibecode-kit.git
cd vibecode-kit && ./install.sh
```

The installer symlinks the five skills into `~/.claude/skills/` and installs the
pybuilder CLI when `uv` is available. Skills you already have are left untouched
(re-run with `--force` to replace them).

## Requirements

| Tool | Needed for | Notes |
|------|-----------|-------|
| Claude Code | everything | |
| git | /dream, /rustbuilder | commits use your existing git identity |
| Rust toolchain (`cargo`) | /rustbuilder only | install via [rustup](https://rustup.rs) |
| [`uv`](https://docs.astral.sh/uv/) | /pybuilder CLI only | |
| Atlassian MCP connection | optional | `/dream` uses Jira/Confluence for evidence when connected; otherwise it works from what you give it |

## Where things go

- **PRDs** — `/dream` and the builders share one PRD home, resolved at runtime:
  `$DREAM_PRD_DIR` if set, else `~/Documents/PRDs/` if it exists, else `./PRDs/`
  in your current project. A git repo there is used if present, never required.
- **Build state** — `/rustbuilder` keeps its queue in
  `~/.local/state/rustbuilder/`; `/pybuilder` writes receipts inside each project.

## Repo layout

```
vibecode-kit/
├── install.sh                      # installs all five skills
├── skills/
│   ├── dream/                      # /dream
│   ├── build/                      # /build — routes a PRD to its builder
│   ├── rustbuilder/                # /rustbuilder
│   ├── prd-writer/                 # /prd-writer
│   └── atscale-prd-writer/         # /atscale-prd-writer
└── pybuilder/                      # /pybuilder — skill + CLI source (Python ≥3.11)
```

## License

Dual-licensed under MIT or Apache-2.0, at your option.
