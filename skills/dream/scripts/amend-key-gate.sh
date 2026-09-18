#!/usr/bin/env bash
# amend-key-gate.sh — decide whether /dream amend <slug> may proceed, per
# skills/dream/SKILL.md Hard Rule 2 and its building/blocked/parked
# ownership-key exception. See PRD-build-prd-superseded-by requirement 9 /
# AC13.
#
# Usage: amend-key-gate.sh <status> <has-dispatch-iter-log:yes|no> <keys>
#   status: queued | building | in_progress | blocked | parked | built | archived
#   keys:   comma-separated list of frontmatter keys the amendment would add
#           or change (e.g. "Superseded-by,transferred_acs")
#
# Verdict on stdout: "allow" or "deny: <reason>". Exit 0 for allow, 2 for deny.

set -uo pipefail

usage() { echo "usage: $(basename "$0") <status> <yes|no> <keys>" >&2; exit 1; }
[ $# -eq 3 ] || usage
status=$1
has_iter_log=$2
keys_csv=$3

ownership_keys="Superseded-by transferred_acs"

is_ownership_only() {
  local IFS=','
  local k
  for k in $keys_csv; do
    k="$(echo "$k" | xargs)"
    [ -z "$k" ] && continue
    case " $ownership_keys " in
      *" $k "*) ;;
      *) return 1 ;;
    esac
  done
  return 0
}

if [ "$status" = "queued" ] && [ "$has_iter_log" = "no" ]; then
  echo "allow"
  exit 0
fi

case "$status" in
  building|in_progress|blocked|parked)
    if [ "$has_iter_log" = "yes" ] && [ -n "$keys_csv" ] && is_ownership_only; then
      echo "allow"
      exit 0
    fi
    echo "deny: building/blocked/parked predecessor accepts only ${ownership_keys// /, } via amend; draft a successor for anything else"
    exit 2
    ;;
esac

echo "deny: $status is not amendable in place; draft a successor"
exit 2
