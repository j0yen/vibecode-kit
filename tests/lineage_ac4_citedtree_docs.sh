#!/usr/bin/env bash
# AC4 — Given a "behind" verdict, When a dream drafts a PRD citing that
# repo, Then the PRD frontmatter carries "- Cited-tree: <repo>@<remote
# sha>". Dream's drafting is an LLM step this fixture can't execute
# directly; what's checkable mechanically is that the skill's own
# instructions require it — SKILL.md's frontmatter template names the
# key, and Phase -1 ties it to the "behind" verdict and the script's
# remote-sha= output.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill="$here/../skills/dream/SKILL.md"

[ -f "$skill" ] || { echo "FAIL: $skill missing" >&2; exit 1; }

grep -q '^- Cited-tree:' "$skill" \
  || { echo "FAIL: frontmatter template missing '- Cited-tree:'" >&2; exit 1; }

grep -qE 'behind.*Cited-tree|Cited-tree.*behind' <(tr '\n' ' ' < "$skill") \
  || { echo "FAIL: SKILL.md never ties Cited-tree to a behind verdict" >&2; exit 1; }

grep -q 'remote-sha=' "$skill" \
  || { echo "FAIL: SKILL.md never reads the script's remote-sha= line" >&2; exit 1; }

echo "ok"
