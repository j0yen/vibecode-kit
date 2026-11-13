#!/usr/bin/env python3
"""worker-fit recommender: one recommendation per task, with the evidence it used.

Usage: recommend.py [--queue] [--observed-at TS] [--format text|json] FILE
  FILE = envelope(s) JSON, or with --queue a canonical-queue rows JSON (converted by queue_adapter.py).
Read-only, standard library only, no network. It launches, claims, kills, installs and writes nothing,
and a recommendation grants no action authority. A source-only or fixture result does not prove
production behavior; a wrapper or queue entry is not a worker launch; UNKNOWN is reported, never filled.
Exit 0 on output (a refusal is a recommendation), 2 on unreadable input.
"""
import json
import os
import string
import sys

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
        out += ["%s.%s" % (grp, k) for k, v in d[grp].items() if v == UNKNOWN]
    for k in ("current_owner", "owner_reachable", "next_action"):
        if d[k] == UNKNOWN:
            out.append(k)
    for k in ("named", "available"):
        if d["consumer"][k] == UNKNOWN:
            out.append("consumer." + k)
    if d["effect"]["state"] == UNKNOWN:
        out.append("effect.state")
    return out


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
        # a durable terminal is consumed; owner reachability and effect state do not block reading it
        reviewed = res["reviewed"] is True
        r.update(disposition="consume-completed-terminal", role="coordinator-decision" if reviewed else "independent-verification",
                 terminal_durable=True, no_takeover=True, no_replay=True)
        later = [] if not cons["named"] or cons["named"] == UNKNOWN else [cons["named"]]
        r["next_consumer"] = cons["named"]
        what = "accept/install owner decides next" if reviewed else "exact-head independent review of the terminal result"
        if cons["available"] is True:
            r["action"] = "%s consumes the retained terminal (%s); no new coder." % (cons["named"], what)
        else:
            alt = cons["alternate"]
            if alt and cons["alternate_authorized"]:
                later.append(alt)
                tail = "authorized alternate %s may consume" % alt
            elif alt:
                tail = "alternate %s is a label with no authority; not used" % alt
            else:
                tail = "UNKNOWN alternate: none on record"
            r["action"] = ("Consumer %s busy/unavailable (available=%s): terminal stays durable and unconsumed; %s (%s); "
                           "no ACK recorded, no new coder." % (cons["named"], cons["available"], what, tail))
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
                 action="No takeover, no launch, no replay: owner %s is unreachable. Reach the owner or wait; a claim is not released by this recommendation." % d["current_owner"])
        return r
    if st == "RUNNING":
        if d["owner_reachable"] is True:
            r.update(disposition="reuse-active-worker", role=shape_role, no_takeover=False, no_replay=True,
                     action="Reuse worker %s on %s (unit %s, child %s); do not start another implementation." %
                            (d["worker"]["session"], d["task_id"], d["worker"]["unit"], d["worker"]["child"]))
        else:
            r.update(disposition=UNKNOWN, role=shape_role, reasons=["owner reachability UNKNOWN"],
                     action="No takeover, no launch: owner reachability is UNKNOWN. Observe the owner first.")
        return r
    if st == "NOT_STARTED":
        r.update(disposition="ready-unowned-slice", role=shape_role, no_takeover=False,
                 action="Slice has no worker and no conflicting live target in this set; a supported launcher may start it (this recommendation does not launch).")
        return r
    if st == "BLOCKED":
        r.update(disposition="blocked", role="coordinator-decision", action="Blocked: %s" % d["next_action"])
        return r
    r.update(disposition=UNKNOWN, role=shape_role, reasons=["state UNKNOWN"],
             action="State UNKNOWN: report it; no takeover, no launch, no replay.")
    return r


def recommend_set(obj):
    res = ev.validate_set(obj)
    recs, _ = ev._records(obj)
    return [recommend_one(d, res["findings_by_index"][i]) for i, d in enumerate(recs)]


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


def main(argv):
    queue, observed, fmt, path = False, queue_adapter.UNKNOWN, "text", None
    it = iter(argv)
    for a in it:
        if a == "--queue":
            queue = True
        elif a == "--observed-at":
            observed = next(it, UNKNOWN)
        elif a == "--format":
            fmt = next(it, "text")
        else:
            path = a
    if path is None:
        print(__doc__)
        return 2
    try:
        with open(path) as fh:
            obj = json.load(fh)
    except (OSError, ValueError) as e:
        print("UNREADABLE %s: %s" % (path, e))
        return 2
    if queue:
        obj = {"envelopes": queue_adapter.rows_to_envelopes(obj, observed)}
    recs = recommend_set(obj)
    print(json.dumps(recs, indent=1) if fmt == "json" else render_text(recs), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
