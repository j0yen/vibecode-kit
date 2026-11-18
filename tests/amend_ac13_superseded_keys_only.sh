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

# A key list is split on commas only; each key is trimmed of surrounding
# whitespace and compared literally. A list that names no key is refused for
# every status in the ownership arm, dispatched or not.
for st_it in "blocked no" "parked no" "building yes"; do
  read -r st it <<<"$st_it"
  for keys in "," ",," " " " , "; do
    check_deny_says "$st/$it + '$keys' names no key" "deny: no keys named" "$st" "$it" "$keys"
  done
done

# A foreign key is refused and printed as typed: nothing (quote handling, echo
# options) may erase it on the way.
for it in no yes; do
  check_deny_says "blocked/$it + apostrophe key" \
    "deny: AC3's wording is not an ownership key" blocked "$it" "AC3's wording"
  check_deny_says "blocked/$it + unmatched trailing quote" \
    "deny: Status' is not an ownership key" blocked "$it" "Status'"
  check_deny_says "blocked/$it + over-quoted list" \
    "deny: 'Status is not an ownership key" blocked "$it" "'Status,Depends-on'"
  check_deny_says "blocked/$it + echo-option key" \
    "deny: -n is not an ownership key" blocked "$it" "-n"
  check_deny_says "blocked/$it + ownership key then echo-option key" \
    "deny: -n is not an ownership key" blocked "$it" "Superseded-by,-n"
  check_deny_says "blocked/$it + space-joined keys are one foreign key" \
    "deny: Superseded-by transferred_acs is not an ownership key" blocked "$it" "Superseded-by transferred_acs"
done

# A key is never glob-expanded: '*' run from a directory holding a file named
# Superseded-by stays the foreign key '*'.
globdir="$(mktemp -d)"
trap 'rm -rf "$globdir"' EXIT
: > "$globdir/Superseded-by"
(cd "$globdir" && check_deny_says "blocked/no + '*' beside a file named Superseded-by" \
  "deny: * is not an ownership key" blocked no "*")

# Whitespace and empty fields around real keys are not keys.
check_allow "blocked/no + ownership keys with blanks and an empty field" \
  blocked no " Superseded-by ,, transferred_acs "

# The queued + dispatch iter_log deny says why.
check_deny_says "queued + dispatch iter_log: reason names the dispatch iter_log" \
  "deny: queued PRD has a dispatch iter_log" queued yes "Superseded-by"

echo "ok"
