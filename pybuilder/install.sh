#!/usr/bin/env bash
# install.sh — install the pybuilder Claude Code skill + CLI from one repo.
#
# Two modes (mirrors j0yen/autobuilder):
#   1. Repo-local: run as `./install.sh` from a checkout. Symlinks
#      ~/.claude/skills/pybuilder -> <repo>/skill and installs the CLI.
#   2. Curl-piped: `curl ... | bash`. No checkout exists; self-clones
#      (sparse: skill/ + src/ + pyproject) into ~/.local/share/pybuilder.
#
# The skill tree references the pybuilder CLI (`pybuilder scaffold|audit|gate`);
# the CLI is installed from the repo's src/ via `uv tool install` when uv is
# present, else left to the user.
set -euo pipefail

SKILL_TARGET="$HOME/.claude/skills/pybuilder"
PRD_WRITER_TARGET="$HOME/.claude/skills/prd-writer"

SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
REPO_DIR=""
if [ -f "$SCRIPT_PATH" ]; then
  REPO_DIR=$(cd "$(dirname "$SCRIPT_PATH")" && pwd)
fi

# --- Mode 2: curl|bash self-clone -------------------------------------------
if [ -z "$REPO_DIR" ] || [ ! -f "$REPO_DIR/skill/SKILL.md" ]; then
  echo "→ no local checkout detected; self-cloning j0yen/vibecode-kit..."
  command -v git >/dev/null 2>&1 || { echo "fatal: git not found" >&2; exit 1; }
  CLONE_ROOT="${PYBUILDER_CLONE_ROOT:-$HOME/.local/share/vibecode-kit}"
  mkdir -p "$(dirname "$CLONE_ROOT")"
  if [ -d "$CLONE_ROOT/.git" ]; then
    echo "→ refreshing existing clone at $CLONE_ROOT"
    git -C "$CLONE_ROOT" fetch --depth 1 origin main
    git -C "$CLONE_ROOT" reset --hard origin/main
  else
    echo "→ clone into $CLONE_ROOT"
    git clone --depth 1 https://github.com/j0yen/vibecode-kit.git "$CLONE_ROOT"
  fi
  REPO_DIR="$CLONE_ROOT/pybuilder"
fi

# --- Symlink /pybuilder skill -----------------------------------------------
mkdir -p "$(dirname "$SKILL_TARGET")"

# Rescue runtime state (proposals/, datasets/) across re-installs.
RESCUE=""
if [ -e "$SKILL_TARGET" ] && [ ! -L "$SKILL_TARGET" ]; then
  for state in proposals datasets; do
    if [ -d "$SKILL_TARGET/$state" ]; then
      RESCUE=$(mktemp -d)
      cp -a "$SKILL_TARGET/$state" "$RESCUE/$state"
    fi
  done
fi

rm -rf "$SKILL_TARGET"
ln -s "$REPO_DIR/skill" "$SKILL_TARGET"
echo "→ skill linked: $SKILL_TARGET -> $REPO_DIR/skill"

if [ -n "$RESCUE" ]; then
  for state in proposals datasets; do
    [ -d "$RESCUE/$state" ] && cp -a "$RESCUE/$state" "$REPO_DIR/skill/$state"
  done
  rm -rf "$RESCUE"
  echo "→ rescued runtime state across re-install"
fi

# --- Symlink /prd-writer skill -----------------------------------------------
if [ -d "$REPO_DIR/skills/prd-writer" ]; then
  rm -rf "$PRD_WRITER_TARGET"
  ln -s "$REPO_DIR/skills/prd-writer" "$PRD_WRITER_TARGET"
  echo "→ skill linked: $PRD_WRITER_TARGET -> $REPO_DIR/skills/prd-writer"
fi

# --- Install the CLI ---------------------------------------------------------
if command -v uv >/dev/null 2>&1; then
  echo "→ installing pybuilder CLI via uv tool"
  uv tool install --force "$REPO_DIR" >/dev/null 2>&1 \
    && echo "→ CLI installed: $(command -v pybuilder || echo '~/.local/bin/pybuilder')" \
    || echo "⚠ uv tool install failed; run 'uv run pybuilder' from $REPO_DIR"
else
  echo "⚠ uv not found; CLI not installed. Install uv, then: uv tool install $REPO_DIR"
fi

echo "✓ installed: /pybuilder + /prd-writer. Start with: /prd-writer"
