#!/usr/bin/env bash
# AC13 — Given a building predecessor, When /dream amend adds only
# Superseded-by: and transferred_acs:, Then the amendment is accepted
# (amend-key-gate.sh prints "allow", exit 0); adding any other key, or
# amending a status the gate doesn't cover, is refused (exit 2).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
gate="$(cd "$here/.." && pwd)/skills/dream/scripts/amend-key-gate.sh"

fail() { echo "FAIL: $*" >&2; exit 1; }

check_allow() {
  local desc=$1; shift
  local out rc=0
  out=$("$gate" "$@") || rc=$?
  [ "$rc" -eq 0 ] || fail "$desc: expected exit 0, got $rc ($out)"
  [ "$out" = "allow" ] || fail "$desc: expected 'allow', got '$out'"
}

check_deny() {
  local desc=$1; shift
  local out rc=0
  out=$("$gate" "$@") || rc=$?
  [ "$rc" -eq 2 ] || fail "$desc: expected exit 2, got $rc ($out)"
  case "$out" in
    deny:*) ;;
    *) fail "$desc: expected a deny: reason, got '$out'" ;;
  esac
}

# AC13's own scenario: building predecessor, dispatch iter_log present,
# ownership keys only.
check_allow "building + ownership keys" building yes "Superseded-by,transferred_acs"
check_allow "blocked + single ownership key" blocked yes "transferred_acs"
check_allow "parked + single ownership key" parked yes "Superseded-by"

# Reject: any non-ownership key mixed in, even alongside a valid one.
check_deny "building + ownership + AC-text key" building yes "Superseded-by,transferred_acs,AC5-text"

# Reject: no keys named at all.
check_deny "building + no keys" building yes ""

# Regression: pre-existing full-amend path (queued, untouched) unaffected.
check_allow "queued + untouched, any key" queued no "anything"

# Regression: queued PRD that already has a dispatch iter_log stays refused.
check_deny "queued + dispatch iter_log" queued yes "Superseded-by"

# built/archived predecessors are never amendable in place.
check_deny "built predecessor" built yes "Superseded-by"

echo "ok"
