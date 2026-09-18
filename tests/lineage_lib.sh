#!/usr/bin/env bash
# lineage_lib.sh — shared fixture helpers for the lineage_ac*.sh tests.
# Not a test itself (no ac<N> in the name), so verified-completed.sh's
# derive scan skips it.

SCRIPT_UNDER_TEST="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/skills/dream/scripts/lineage-freshness.sh"

fail() { echo "FAIL: $*" >&2; exit 1; }

# make_fixture <workdir> — creates <workdir>/remote.git (bare, HEAD=main)
# and <workdir>/origin_clone with one commit pushed to it.
make_fixture() {
  local dir=$1
  mkdir -p "$dir"
  git init -q --bare "$dir/remote.git"
  git -C "$dir/remote.git" symbolic-ref HEAD refs/heads/main
  git clone -q "$dir/remote.git" "$dir/origin_clone"
  git -C "$dir/origin_clone" config user.email t@example.com
  git -C "$dir/origin_clone" config user.name Test
  cat > "$dir/origin_clone/Cargo.toml" <<'EOF'
[package]
name = "fixture"
version = "1.0.0"
EOF
  git -C "$dir/origin_clone" add Cargo.toml
  git -C "$dir/origin_clone" commit -q -m init
  git -C "$dir/origin_clone" push -q -u origin main
}
