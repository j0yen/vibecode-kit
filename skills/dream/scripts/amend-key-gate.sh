#!/usr/bin/env bash
# amend-key-gate.sh — decide whether /dream amend <slug> may proceed, per
# skills/dream/SKILL.md Hard Rule 2 and its building/blocked/parked
# ownership-key exception. See PRD-build-prd-superseded-by requirement 9 /
# AC13.
#
# Usage: amend-key-gate.sh <status> <has-dispatch-iter-log:yes|no> <keys>
#   status: queued | building | in_progress | blocked | parked | built | shipped
#           | archived
#   keys:   comma-separated list of frontmatter keys the amendment would add
#           or change (e.g. "Superseded-by,transferred_acs"); each key is
#           trimmed of surrounding whitespace and compared literally, and a
#           list that names no key is refused
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

# is_ownership_only: rc 0 when the list names at least one key and every
# named key is literally an ownership key; otherwise rc 1, with the first other
# key on stdout verbatim (nothing when the list names no key). The list is split
# on commas and each key trimmed with parameter expansion only, so no quote,
# backslash or option-shaped key is lost and no key is word-split or
# glob-expanded.
is_ownership_only() {
  local rest="$keys_csv," k o named=0 owned
  while [ -n "$rest" ]; do
    k="${rest%%,*}"
    rest="${rest#*,}"
    k="${k#"${k%%[![:space:]]*}"}"
    k="${k%"${k##*[![:space:]]}"}"
    [ -z "$k" ] && continue
    owned=no
    for o in $ownership_keys; do
      [ "$k" = "$o" ] && owned=yes
    done
    if [ "$owned" = no ]; then
      printf '%s\n' "$k"
      return 1
    fi
    named=$((named + 1))
  done
  [ "$named" -gt 0 ]
}

if [ "$status" = "queued" ] && [ "$has_iter_log" = "no" ]; then
  echo "allow"
  exit 0
fi

if [ "$status" = "queued" ] && [ "$has_iter_log" = "yes" ]; then
  echo "deny: queued PRD has a dispatch iter_log; draft a successor"
  exit 2
fi

case "$status" in
  building|in_progress|blocked|parked)
    owned="${ownership_keys// /, }"
    article=a
    [ "$status" = in_progress ] && article=an
    if ! other="$(is_ownership_only)"; then
      if [ -z "$other" ]; then
        echo "deny: no keys named; $article $status predecessor accepts only $owned via amend"
      else
        printf 'deny: %s is not an ownership key; %s %s predecessor accepts only %s via amend; draft a successor for anything else\n' "$other" "$article" "$status" "$owned"
      fi
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

echo "deny: ${status:-an empty status} is not amendable in place; draft a successor"
exit 2
