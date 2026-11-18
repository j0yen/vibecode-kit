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

# A1723: a blocked or parked PRD takes the two ownership keys whether or not
# it was ever dispatched (SKILL.md: "Started, blocked, or parked -> only
# Superseded-by: / transferred_acs:"). /dream drafts some PRDs as blocked, and
# those never carry a dispatch iter_log.
check_allow "blocked, never dispatched + ownership keys" blocked no "Superseded-by,transferred_acs"
check_allow "parked, never dispatched + ownership key" parked no "Superseded-by"
check_deny "blocked, never dispatched + other key" blocked no "Superseded-by,Status"
check_deny "blocked, never dispatched + no keys" blocked no ""

# building/in_progress with no dispatch iter_log is an anomaly: still refused.
check_deny "building, no dispatch + ownership keys" building no "Superseded-by"
check_deny "in_progress, no dispatch + ownership keys" in_progress no "Superseded-by"

# The deny reason names the condition that failed.
check_deny_says() {
  local desc=$1 want=$2; shift 2
  local out rc=0
  out=$("$gate" "$@") || rc=$?
  [ "$rc" -eq 2 ] || fail "$desc: expected exit 2, got $rc ($out)"
  case "$out" in
    *"$want"*) ;;
    *) fail "$desc: expected the reason to say '$want', got '$out'" ;;
  esac
}
check_deny_says "building, no dispatch: reason names the dispatch iter_log" \
  "no dispatch iter_log" building no "Superseded-by"
check_deny_says "blocked + other key: reason names the key" \
  "Status is not an ownership key" blocked no "Superseded-by,Status"
check_deny_says "parked + no keys: reason names the empty list" \
  "no keys named" parked no ""

echo "ok"
