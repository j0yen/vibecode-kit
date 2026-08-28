# vibecode-kit

A self-contained set of Claude Code skills for going from *"I wish we had X"* to
working, tested code — with a real Product Requirements Document in between.

Everything referenced by these skills ships in this repo. No private repos, no
company infrastructure, no cloud build servers. If you have Claude Code and git,
the kit works; a few optional tools light up extra capability (see below).

Once installed, open **[SETUP.md](SETUP.md)** — six copy-paste prompts that
Claude Code runs for you: GitHub versioning + a private PRD workspace repo
(required), Jira/Confluence/GitHub connections that ground `/dream` in real
tickets, pages, and code (recommended), and an optional unattended cadence for
`/vibeloop`. No terminal skills needed.

## Install as a plugin

### Prerequisites

None of this is needed to merely install the plugin — `/plugin marketplace add`
and `/plugin install` only need Claude Code itself. These are for actually
using the skills day to day.

**git** (required — `/dream` commits PRDs and visions as it drafts them)

```bash
# macOS
brew install git
# Ubuntu / Debian
sudo apt install git
```

Make sure your identity is set, since `/dream` commits with whatever's already
configured — it never sets or hardcodes one:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

**Python toolchain for `/pybuilder`** (required to actually build — pybuilder
needs Python 3.11+ and `uv`; the core pipeline has zero other third-party
runtime dependencies)

```bash
python3 --version   # need 3.11+ — install via your OS package manager or python.org if older
curl -LsSf https://astral.sh/uv/install.sh | sh   # or: brew install uv
```

This repo is a self-hosted Claude Code plugin marketplace. From Claude Code:

```
/plugin marketplace add j0yen/vibecode-kit
/plugin install vibecode-kit@vibecode
```

Updates arrive with `/plugin marketplace update vibecode`.

Skills install namespaced to this plugin — `/vibecode-kit:dream`,
`/vibecode-kit:build`, etc. — so they never collide with skills you already
have under your own name.

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
              └─ /build ──► /pybuilder  (eval-gated Python)
```

1. **`/dream <topic>`** — listens, gathers evidence, writes a vision, then drafts
   three to seven PRDs to the enterprise PRD standard. Each PRD says what to build,
   for whom, why, and how you'll know it worked. The PRD format mirrors how real
   AtScale PRDs are structured on Confluence, and `/dream` can optionally publish
   there too — but only after asking, never on its own. PRD prose follows a
   bundled writing standard (evidence-first, no hype vocabulary, three-pass
   drafting), and drafting is grounded by a bundled domain reference
   (technical, positioning, PM frameworks).
2. **`/build`** — routes a PRD to `/pybuilder`.
3. **`/pybuilder <prd>`** — implements `python-*` PRDs through a five-stage,
   evaluation-gated pipeline (intake → scaffold → iterate-and-prove → risk gate →
   postmortem).

Two supporting skills round out the set:

- **`/atscale-prd-writer`** — the PRD-writing standard `/dream` follows
  (14-section template, Customer Pain Test, MUST/SHOULD/MAY, anti-pattern audit).
  Also useful on its own for drafting or reviewing any PRD.
- **`/prd-writer`** — the same idea for personal projects: turn a loose idea into
  a spec `/pybuilder` can build, no PM background required.

`/vibeloop` closes this cycle end to end, and its primary form is goal-driven:
`/vibeloop <goal>` points every cycle at a target outcome — the loops that
earn their keep chase a named result (drive NLQ accuracy on an eval set,
translate a DAX workbook backlog), not just an empty queue. The goal persists
across cycles as the standing intent that `/dream` serves; each invocation
runs one dream-build-digest pass, leaves a ledger record, and can run on a
schedule so the work continues while you are away — see
[SETUP.md §6](SETUP.md#6-unattended-loop-cadence-optional).

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/j0yen/vibecode-kit/main/install.sh | bash
```

or from a checkout:

```bash
git clone https://github.com/j0yen/vibecode-kit.git
cd vibecode-kit && ./install.sh
```

The installer symlinks the six skills into `~/.claude/skills/` and installs the
pybuilder CLI when `uv` is available. Skills you already have are left untouched
(re-run with `--force` to replace them).

## Requirements

| Tool | Needed for | Notes |
|------|-----------|-------|
| Claude Code | everything | |
| git | /dream | commits use your existing git identity |
| [`uv`](https://docs.astral.sh/uv/) | /pybuilder CLI only | |
| GitHub CLI (`gh`) + private workspace repo | versioning + offsite backup | [SETUP.md](SETUP.md) §1–2 — paste-prompt setup; `/dream` and `/build` push automatically once origin exists |
| Atlassian MCP connection | optional | `/dream` uses Jira/Confluence for evidence when connected; otherwise it works from what you give it — [SETUP.md](SETUP.md) §3 |
| Atlassian CLI (`acli`), GitHub MCP | optional | bulk Jira ops and richer code grounding — [SETUP.md](SETUP.md) §4–5 |

## Where things go

- **PRDs** — `/dream` and `/build` share one PRD home, resolved at runtime:
  `$DREAM_PRD_DIR` if set, else `~/Documents/PRDs/` if it exists, else `./PRDs/`
  in your current project. A git repo there is used if present, never required.
- **Build state** — `/pybuilder` writes receipts inside each project.

## PRD lifecycle

A PRD's frontmatter `Status` field is the single source of truth; `MANIFEST.md`
is just a derived index regenerated from it — never hand-edit the manifest.
`MANIFEST.md` is rebuilt by scanning frontmatter across both `$PRD_DIR/*.md`
and `$PRD_DIR/built-prds/*.md`, written atomically (temp file, then rename).

```
queued ──► building ──► built ──► (file moves to built-prds/)
              │
              └──► blocked  (stays in place, with a Blocked: reason)
```

- `/dream` writes every new PRD as `Status: queued`, in `$PRD_DIR/`.
- `/build` picks up `queued` PRDs (oldest first, draining the whole queue),
  marks each `building` while it works, then resolves it: `built` (+ `Built:`
  date and `Receipts:` pointer, file moved to `$PRD_DIR/built-prds/`) or `blocked`
  (+ a one-line `Blocked:` reason, file left in place). No daemon or timer is
  involved — the transitions happen inside the `/dream` and `/build` skill
  runs themselves.
- Exception: PRDs with `build_target: product` are product docs, not
  auto-buildable — `/build` skips them and they stay `queued`, outside the
  built/blocked flow.

## Project profiles, build contracts, loop-ready fleets

Three additions (v0.10.0) let one `/dream` serve more than one build system and more
than one project:

- **Build contract.** `/dream` reads the installed `/build`'s `build-contract.md` at
  run start and writes PRDs to it — accepted `build_target` values, extra keys, the
  archive directory, the countable acceptance-criteria line (`1. P0 — Given …, When …,
  Then …`). This kit's `/build` ships a Python-only contract; a private `/build` can
  ship a Rust+Python one and the same `/dream` follows it.
- **Project profiles.** `$PRD_DIR/projects/<name>.md` holds a project's seed source,
  slug prefix, lineage decision, and build defaults. `/dream project <name>` re-reads
  the seed every run, so a note that changed changes the fleet.
- **Loop-ready fleets.** `/dream loop <name>` drafts the measurement harness PRD
  first and writes a Loop contract into the vision (metric, corpus + gold, measure
  command, preflight probes, deploy target, write scope), so a closed-loop scaffolder
  can drive the fleet after the first build. Feature PRDs name the metric they move.

## Repo layout

```
vibecode-kit/
├── install.sh                      # installs all six skills
├── skills/
│   ├── dream/                      # /dream
│   ├── build/                      # /build — routes a PRD to /pybuilder
│   ├── vibeloop/                   # /vibeloop — the dream-build-digest loop
│   ├── prd-writer/                 # /prd-writer
│   └── atscale-prd-writer/         # /atscale-prd-writer
└── pybuilder/                      # /pybuilder — skill + CLI source (Python ≥3.11)
```

## License

Dual-licensed under MIT or Apache-2.0, at your option.
