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
# Rule:
#   queued + no dispatch iter_log      -> any keys (full amend)
#   blocked | parked                   -> only Superseded-by / transferred_acs,
#                                         dispatched or not (/dream drafts some
#                                         PRDs blocked, and those have no
#                                         dispatch iter_log)
#   building | in_progress             -> the same two keys, and only with a
#                                         dispatch iter_log
#   anything else                      -> deny; draft a successor
#
# Verdict on stdout: "allow" or "deny: <reason>", the reason naming the
# condition that failed. Exit 0 for allow, 2 for deny.

set -uo pipefail

usage() { echo "usage: $(basename "$0") <status> <yes|no> <keys>" >&2; exit 1; }
[ $# -eq 3 ] || usage
status=$1
has_iter_log=$2
keys_csv=$3

ownership_keys="Superseded-by transferred_acs"

# is_ownership_only: rc 0 when every key is an ownership key; otherwise rc 1
# and the first other key on stdout.
is_ownership_only() {
  local IFS=','
  local k
  for k in $keys_csv; do
    k="$(echo "$k" | xargs)"
    [ -z "$k" ] && continue
    case " $ownership_keys " in
      *" $k "*) ;;
      *) echo "$k"; return 1 ;;
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
    owned="${ownership_keys// /, }"
    if [ -z "$keys_csv" ]; then
      echo "deny: no keys named; a $status predecessor accepts only $owned via amend"
      exit 2
    fi
    if ! other="$(is_ownership_only)"; then
      echo "deny: $other is not an ownership key; a $status predecessor accepts only $owned via amend; draft a successor for anything else"
      exit 2
    fi
    case "$status" in
      building|in_progress)
        if [ "$has_iter_log" != "yes" ]; then
          echo "deny: $status predecessor has no dispatch iter_log; $owned are accepted on a building/in_progress PRD only after a dispatch"
          exit 2
        fi
        ;;
    esac
    echo "allow"
    exit 0
    ;;
esac

echo "deny: $status is not amendable in place; draft a successor"
exit 2
