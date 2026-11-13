#!/usr/bin/env python3
"""worker-fit recommender: one recommendation per task, with the evidence it used.

Usage: recommend.py [--queue] [--observed-at TS] [--now TS|system] [--format text|json] FILE
  Exactly one FILE: a second file (or an unknown option) is a usage error, exit 2, never silently dropped.
  FILE = envelope(s) JSON, or with --queue a canonical-queue rows JSON (converted by queue_adapter.py).
Read-only, standard library only, no network. It launches, claims, kills, installs and writes nothing,
and a recommendation grants no action authority. A source-only or fixture result does not prove
production behavior; a wrapper or queue entry is not a worker launch; UNKNOWN is reported, never filled.
--now sets the reference clock for the observation window (default = the host clock, system = same; never the newest
observation in the set, see envelope_validate.py). Credential-shaped values are redacted from all output.
Exit 0 on output (a refusal is a recommendation), 2 on unreadable input (not JSON, duplicate-free structure
broken such as {"envelopes": null} or {"rows": null}, bad --now).
"""
import json
import os
import string
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envelope_validate as ev  # noqa: E402
import queue_adapter  # noqa: E402

UNKNOWN = "UNKNOWN"
ROLE_OF_SHAPE = {"implementation": "implementation", "review": "independent-verification",
                 "decision": "coordinator-decision", "deterministic": "deterministic-service", "UNKNOWN": "UNKNOWN"}
FOOTER = ("Recommendation only: nothing was launched, claimed, killed, installed or written, and no authority is granted. "
          "A source-only or fixture result does not prove production behavior; a wrapper or queue entry is not a worker launch; "
          "UNKNOWN account/consumer is reported, never filled in.")


def _unknown_fields(d):
    out = []
    for grp in ("target", "worker"):
        out += ["%s.%s" % (grp, k) for k, v in d[grp].items() if ev.is_unknown(v)]
    for k in ("current_owner", "owner_reachable", "next_action"):
        if ev.is_unknown(d[k]):
            out.append(k)
    for k in ("named", "available"):
        if ev.is_unknown(d["consumer"][k]):
            out.append("consumer." + k)
    if d["effect"]["state"] == UNKNOWN:
        out.append("effect.state")
    return out


def _own_identities(d):
    """The worker's own session/invocation ids: a consumer matching one of these is not independent."""
    return {ev_norm(d["worker"][k]) for k in ("session", "invocation") if not ev.is_unknown(d["worker"][k])}


def ev_norm(v):
    return ev.norm_text(v)


def _distinct_reviewer(d):
    res = d["result"]
    by = res.get("reviewed_by")
    return res["reviewed"] is True and ev.ident(by) is not None and ev_norm(by) not in _own_identities(d)


def _evidence(d):
    ev_used = ["state=%s" % d["state"], "work_shape=%s" % d["work_shape"], "owner=%s reachable=%s" % (d["current_owner"], d["owner_reachable"]),
               "effect=%s no_replay=%s" % (d["effect"]["state"], d["effect"]["no_replay"])]
    ev_used += ["worker.%s=%s" % (k, v) for k, v in d["worker"].items()]
    ev_used.append("target=%s@%s head=%s" % (d["target"]["repo"], d["target"]["branch"], d["target"]["head"]))
    if d["result"]["artifact"] or d["result"]["event"]:
        ev_used.append("result=%s reviewed=%s" % (d["result"]["artifact"] or d["result"]["event"], d["result"]["reviewed"]))
    ev_used += ["evidence %s (task %s rev %s at %s)" % (e["ref"], e["task_id"], e["revision"], e["observed_at"]) for e in d["evidence"]]
    ev_used += ["coverage gap: " + g for g in d["coverage_gaps"]]
    return ev_used


def _base(task_id, revision):
    return {"task_id": task_id, "revision": revision, "role": UNKNOWN, "disposition": UNKNOWN, "refused": False,
            "reason_codes": [], "reasons": [], "no_takeover": True, "no_replay": True, "new_worker_recommended": False,
            "terminal_durable": False, "next_consumer": UNKNOWN, "later_consumers": [], "ack_recorded": False,
            "grants_authority": False, "action": "", "evidence_used": [], "unknown_fields": []}


def recommend_one(d, findings):
    refusals = [f for f in findings if f["severity"] == "REFUSE"]
    tid = d.get("task_id", UNKNOWN) if isinstance(d, dict) else UNKNOWN
    rev = d.get("revision", UNKNOWN) if isinstance(d, dict) else UNKNOWN
    r = _base(tid if isinstance(tid, str) and tid else UNKNOWN, rev)
    if refusals:
        r.update(refused=True, reason_codes=sorted({f["code"] for f in refusals}),
                 reasons=["%s %s: %s" % (f["code"], f["path"], f["message"]) for f in refusals],
                 action="REFUSED: evidence does not support a placement. Repair the envelope or its source; no launch, no takeover, no replay.")
        if isinstance(d, dict) and isinstance(d.get("effect"), dict):
            r["no_replay"] = True
        return r
    r["evidence_used"], r["unknown_fields"] = _evidence(d), _unknown_fields(d)
    st, eff, cons, res = d["state"], d["effect"]["state"], d["consumer"], d["result"]
    shape_role = ROLE_OF_SHAPE[d["work_shape"]]
    if st == "DONE":
        # a durable terminal is consumed; owner reachability and effect state do not block reading it.
        # "reviewed" counts only with a reviewer identity distinct from the worker; the flag alone is the author's word.
        distinct = _distinct_reviewer(d)
        own = _own_identities(d)
        r.update(disposition="consume-completed-terminal", role="coordinator-decision" if distinct else "independent-verification",
                 terminal_durable=True, no_takeover=True, no_replay=True)
        if res["reviewed"] is True and not distinct:
            r["reasons"].append("result.reviewed=true carries no distinct reviewer identity: independent verification kept")
        # The action sentence is built from tool-owned text only. Envelope strings (consumer, session, unit, owner,
        # authorization reference, task id) are never echoed into it: they appear, redacted, in evidence_used, and the
        # validated consumer identifiers in next_consumer / later_consumers.
        named = ev.ident(cons["named"])
        named_ok = named is not None and (distinct or ev_norm(named) not in own)
        later = [named] if named_ok else []
        r["next_consumer"] = named if named_ok else UNKNOWN
        what = "accept/install owner decides next" if distinct else "exact-head independent review of the terminal result"
        if named_ok and cons["available"] is True:
            r["action"] = "The named consumer (next_consumer) consumes the retained terminal (%s); no new coder." % what
        else:
            alt = ev.ident(cons["alternate"])
            alt_ok = alt is not None and (distinct or ev_norm(alt) not in own)
            ref_ok = ev.ref_like(cons.get("alternate_authorization_ref"))
            if alt_ok and cons["alternate_authorized"] and ref_ok:
                later.append(alt)
                tail = "an authorized alternate (later_consumers) may consume; its authorization reference is recorded in evidence_used"
            elif alt_ok and cons["alternate_authorized"]:
                tail = "the alternate is marked authorized with no authorization evidence reference: no authority; not used"
            elif alt_ok:
                tail = "the alternate is a label with no authority; not used"
            elif alt is not None:
                tail = "the alternate is the worker's own session: not independent; not used"
            else:
                tail = "UNKNOWN alternate: none on record"
            if not ev.is_unknown(cons["named"]) and named is not None and not named_ok:
                lead = "The named consumer is the worker's own session: not independent, not used for verification"
            elif named is None and not ev.is_unknown(cons["named"]):
                lead = "The named consumer is not a valid identifier and is not used"
            else:
                lead = "The named consumer is busy/unavailable (available=%s)" % cons["available"]
            r["action"] = ("%s: terminal stays durable and unconsumed; %s (%s); "
                           "no ACK recorded, no new coder." % (lead, what, tail))
        r["later_consumers"] = later
        return r
    if eff == UNKNOWN:
        r.update(disposition=UNKNOWN, role=shape_role, no_takeover=True, no_replay=True,
                 reasons=["effect state UNKNOWN: preserved, not replayed"],
                 action="No takeover, no launch, no replay: effect state is UNKNOWN. Read the effect first through its owner.")
        return r
    if st in ("RUNNING", "NOT_STARTED", "BLOCKED") and d["owner_reachable"] is False:
        r.update(disposition="blocked", role="coordinator-decision", no_takeover=True, no_replay=True,
                 reasons=["owner unreachable: no takeover of a live claim"],
                 action="No takeover, no launch, no replay: the recorded owner (current_owner) is unreachable. Reach the owner or wait; a claim is not released by this recommendation.")
        return r
    if st == "RUNNING":
        if d["owner_reachable"] is True:
            r.update(disposition="reuse-active-worker", role=shape_role, no_takeover=False, no_replay=True,
                     action="Reuse the recorded active worker (worker fields in evidence_used); do not start another implementation.")
        else:
            r.update(disposition=UNKNOWN, role=shape_role, reasons=["owner reachability UNKNOWN"],
                     action="No takeover, no launch: owner reachability is UNKNOWN. Observe the owner first.")
        return r
    if st == "NOT_STARTED" and (eff != "none" or not (ev.is_unknown(d["worker"]["unit"]) and ev.is_unknown(d["worker"]["child"]))):
        r.update(disposition=UNKNOWN, role=shape_role, no_takeover=True, no_replay=True,
                 reasons=["NOT_STARTED with effect %s: an unowned slice needs effect none and no worker evidence" % eff],
                 action="No launch, no takeover, no replay: effect is %s on a task marked NOT_STARTED. Read the effect and any worker through their owner first." % eff)
        return r
    if st == "NOT_STARTED" and d["owner_reachable"] is not True:
        r.update(disposition=UNKNOWN, role=shape_role, no_takeover=True, no_replay=True, reasons=["owner reachability UNKNOWN"],
                 action="No takeover, no launch: owner reachability is UNKNOWN. Observe the owner first.")
        return r
    if st == "NOT_STARTED":
        r.update(disposition="ready-unowned-slice", role=shape_role, no_takeover=False,
                 action="Slice has no worker and no conflicting live target in this set; a supported launcher may start it (this recommendation does not launch).")
        return r
    if st == "BLOCKED":
        r.update(disposition="blocked", role="coordinator-decision", action="Blocked on a named dependency or unreachable owner: read the envelope's next_action through its owner; "
                      "its text is not relayed as an action here.")
        return r
    r.update(disposition=UNKNOWN, role=shape_role, reasons=["state UNKNOWN"],
             action="State UNKNOWN: report it; no takeover, no launch, no replay.")
    return r


def _scrub(v):
    return ev.scrub(v)


def recommend_set(obj, now=None):
    res = ev.validate_set(obj, now)
    recs, _ = ev._records(obj)
    if not isinstance(recs, list):  # structurally null/invalid wrapper: one refusal, never a crash
        return [_scrub(recommend_one(None, res["set_findings"]))]
    return [_scrub(recommend_one(d, res["findings_by_index"][i])) for i, d in enumerate(recs)]


def render_text(recs):
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "templates", "recommendation-report.md")) as fh:
        tpl = string.Template(fh.read())
    blocks = []
    for r in recs:
        blocks.append(tpl.substitute(
            task_id=r["task_id"], revision=r["revision"], verdict="REFUSED" if r["refused"] else "recommendation",
            role=r["role"], disposition=r["disposition"], new_worker="yes" if r["new_worker_recommended"] else "no",
            no_takeover="yes" if r["no_takeover"] else "no", no_replay="yes" if r["no_replay"] else "no",
            next_consumer=r["next_consumer"], later=", ".join(r["later_consumers"]) or "none",
            terminal_durable="yes" if r["terminal_durable"] else "no", ack="none recorded",
            action=r["action"], reasons="; ".join(r["reasons"]) or "-",
            evidence="\n".join("  - " + e for e in r["evidence_used"]) or "  - (none: refused)",
            unknown=", ".join(r["unknown_fields"]) or "none"))
    return "\n".join(blocks) + "\n" + FOOTER + "\n"


def _usage_error(msg):
    ev.emit(ev.redact("UNREADABLE usage: %s" % msg))
    return 2


def main(argv):
    queue, observed, fmt, paths, now = False, queue_adapter.UNKNOWN, "text", [], None
    it = iter(argv)
    try:
        for a in it:
            if a == "--queue":
                queue = True
            elif a == "--observed-at":
                observed = next(it, None)
                if observed is None:
                    return _usage_error("--observed-at needs a value")
            elif a == "--format":
                fmt = next(it, None)
                if fmt not in ("text", "json"):
                    return _usage_error("--format must be text or json")
            elif a == "--now":
                v = next(it, None)
                if v is None:
                    raise ValueError("--now needs a timestamp or 'system'")
                now = ev.host_now() if v == "system" else ev.as_now(v)
            elif a.startswith("--"):
                return _usage_error("unknown option %s" % a)
            else:
                paths.append(a)
    except ValueError as e:
        ev.emit(ev.redact("UNREADABLE --now: %s" % e))
        return 2
    if len(paths) > 1:
        return _usage_error("recommend.py takes exactly one FILE; extra argument(s) not evaluated: %s" % ", ".join(paths[1:]))
    path = paths[0] if paths else None
    if path is None:
        ev.emit(__doc__)
        return 2
    try:
        obj = ev.load_json_file(path)
        if queue:
            obj = {"envelopes": queue_adapter.rows_to_envelopes(obj, observed)}
        elif isinstance(obj, dict) and "envelopes" in obj and not isinstance(obj["envelopes"], list):
            raise ValueError("envelopes must be a list")
    except (OSError, ValueError) as e:
        ev.emit(ev.redact("UNREADABLE %s: %s" % (path, e)))
        return 2
    recs = recommend_set(obj, now)
    ev.emit(json.dumps(recs, indent=1) if fmt == "json" else render_text(recs), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
