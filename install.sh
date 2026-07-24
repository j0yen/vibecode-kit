#!/usr/bin/env bash
# install.sh — install the vibecode-kit Claude Code skills.
#
# Two modes:
#   1. Repo-local: run as `./install.sh` from a checkout. Symlinks each skill
#      into ~/.claude/skills/.
#   2. Curl-piped: `curl -fsSL https://raw.githubusercontent.com/j0yen/vibecode-kit/main/install.sh | bash`
#      Self-clones into ~/.local/share/vibecode-kit, then symlinks.
#
# Skills installed:
#   /dream               — turn a direction into a fleet of AtScale product PRDs
#   /rustbuilder         — implement rust-* PRDs with local cargo
#   /pybuilder           — implement python-* PRDs (skill + CLI)
#   /prd-writer          — shape a personal-project idea into a buildable PRD
#   /atscale-prd-writer  — the enterprise B2B PRD-writing standard /dream follows
#
# Existing skills are left untouched unless --force is passed, so an already-
# customized setup keeps its own canonical checkouts.
set -euo pipefail

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
REPO_DIR=""
if [ -f "$SCRIPT_PATH" ]; then
  REPO_DIR=$(cd "$(dirname "$SCRIPT_PATH")" && pwd)
fi

# --- Mode 2: curl|bash self-clone -------------------------------------------
if [ -z "$REPO_DIR" ] || [ ! -f "$REPO_DIR/skills/dream/SKILL.md" ]; then
  echo "→ no local checkout detected; self-cloning j0yen/vibecode-kit..."
  command -v git >/dev/null 2>&1 || { echo "fatal: git not found" >&2; exit 1; }
  CLONE_ROOT="${VIBECODE_KIT_CLONE_ROOT:-$HOME/.local/share/vibecode-kit}"
  mkdir -p "$(dirname "$CLONE_ROOT")"
  if [ -d "$CLONE_ROOT/.git" ]; then
    echo "→ refreshing existing clone at $CLONE_ROOT"
    git -C "$CLONE_ROOT" fetch --depth 1 origin main
    git -C "$CLONE_ROOT" reset --hard origin/main
  else
    git clone --depth 1 https://github.com/j0yen/vibecode-kit.git "$CLONE_ROOT"
  fi
  REPO_DIR="$CLONE_ROOT"
fi

SKILLS_DIR="$HOME/.claude/skills"
mkdir -p "$SKILLS_DIR"

link_skill() {
  local name="$1" src="$2" target="$SKILLS_DIR/$1"
  if [ -e "$target" ] || [ -L "$target" ]; then
    if [ "$FORCE" -eq 1 ]; then
      rm -rf "$target"
    else
      echo "• $name: already installed at $target — skipped (re-run with --force to replace)"
      return 0
    fi
  fi
  ln -s "$src" "$target"
  echo "→ /$name linked: $target -> $src"
}

link_skill dream               "$REPO_DIR/skills/dream"
link_skill rustbuilder         "$REPO_DIR/skills/rustbuilder"
link_skill prd-writer          "$REPO_DIR/skills/prd-writer"
link_skill atscale-prd-writer  "$REPO_DIR/skills/atscale-prd-writer"
link_skill pybuilder           "$REPO_DIR/pybuilder/skill"

# --- pybuilder CLI (optional but recommended) --------------------------------
if command -v uv >/dev/null 2>&1; then
  echo "→ installing pybuilder CLI via uv tool"
  uv tool install --force "$REPO_DIR/pybuilder" >/dev/null 2>&1 \
    && echo "→ CLI installed: $(command -v pybuilder || echo "$HOME/.local/bin/pybuilder")" \
    || echo "⚠ uv tool install failed; run 'uv run pybuilder' from $REPO_DIR/pybuilder"
else
  echo "⚠ uv not found — pybuilder CLI not installed (the /pybuilder skill needs it)."
  echo "  Install uv (https://docs.astral.sh/uv/), then: uv tool install $REPO_DIR/pybuilder"
fi

# --- doctor ------------------------------------------------------------------
echo
echo "Dependency check:"
command -v git   >/dev/null 2>&1 && echo "  ✓ git"   || echo "  ✗ git   — required by /dream, /rustbuilder"
command -v cargo >/dev/null 2>&1 && echo "  ✓ cargo" || echo "  – cargo — needed only for /rustbuilder (install via https://rustup.rs)"
command -v uv    >/dev/null 2>&1 && echo "  ✓ uv"    || echo "  – uv    — needed only for /pybuilder's CLI"
echo
echo "✓ vibecode-kit installed. Start in Claude Code with: /dream <what you wish existed>"
