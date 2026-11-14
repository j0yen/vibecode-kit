"""Retained reviewer probe (re-review 14 of bffbfc29, probes/own/human14.py), source path made relative to this repo. Not collected by unittest
discovery."""
import os
import sys, random
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
sys.path.insert(0, S)
import envelope_validate as ev, queue_adapter as qa
r = random.Random(14014)
C = "bcdfghjklmnprstvwxz"; V = "aeiou"
cv = lambda n: "".join(r.choice(C) + r.choice(V) for _ in range(n))
cvc = lambda n: "".join(r.choice(C) + r.choice(V) + r.choice(C) for _ in range(n))
DICT = ("anchor biscuit cabbage dancer eagle feather giraffe hammer island jacket kettle ladder magnet napkin oyster parrot quiver "
        "rabbit saddle tomato umbrella violin walnut yogurt zipper basket candle mirror pillow castle forest puzzle tunnel "
        "geheim salasana parola wachtwoord lozinka haslo").split()
HUMAN = ("michael jessica ashley daniel maggie hannah cheese cookie1 iloveu lovely flower sparky snoopy chelsea liverpool arsenal "
         "matrix mercedes corvette ferrari maverick phoenix cowboy zaq12wsx 1qaz2wsx qwerty123 abcd1234 azerty dallas yankees bandit "
         "hunter ranger thomas robert jasmine lakers diamond silver1 qwer1234 111111a").split()
FORMS = ["Anchor99", "CastleRock", "river-Stone", "Tomato_Soup", "2Fast2Furious", "Kettle7", "BlueSky88", "IceCream", "zebra-crossing",
         "Moon.Walk", "Ocean4ever", "SnowWhite7", "Pepsi-Max", "BigApple", "Hammer_Time"]
GEN = [cv(3) for _ in range(4)] + [cv(4) for _ in range(4)] + [cvc(2) for _ in range(4)] + [cvc(3) for _ in range(3)] + \
      ["Aeph5Ohz", "ieTh9ooj", "Pha7Ahng", "xu0Oowai", "Cai4Eegh"]
PASS2 = ["correct-horse", "battery-staple", "dusty-anchor", "quiet-violin", "rapid-walnut", "worker-biscuit", "deploy-parrot",
         "merge-tomato", "review-castle", "canary-feather", "anchor.review", "violin_merge", "salty-oyster", "noisy-kettle", "hidden-forest"]
LEGIT = ["worker", "review", "deploy", "merge", "controller", "carbon", "hermes", "synthorg", "watch", "runner", "canary", "ledger"]
lists = set(ev._ID_WORDS) | set(ev._free_words()) | set(qa._QUEUE_WORDS) | set(ev._DNS_WORDS)
groups = {"dict": DICT, "human": HUMAN, "forms": FORMS, "gen": GEN, "pass2": PASS2}
FIELDS = [("worker.unit", "ident", "{}"), ("worker.unit", "ident", "{}.service"), ("worker.unit", "ident", "wm-{}-7.service"),
          ("worker.child", "ident", "{}"), ("current_owner", "ident", "{}"), ("owner", "ident", "{}"), ("reviewed_by", "ident", "{}"),
          ("consumer", "ident", "{}"), ("alternate", "ident", "{}"), ("target.branch", "ident", "{}"), ("target.branch", "ident", "rb/{}"),
          ("target.repo", "ident", "{}"), ("target.repo", "ident", "j0yen/{}"), ("task_id", "ident", "{}"), ("task_id", "ident", "A1663-{}"),
          ("result", "path", "/mnt/ssd/cargo-target/{}/out.md"), ("artifact", "path", "/tmp/{}.json"), ("event", "path", "{}.md"),
          ("evidence-ref", "path", "{}"), ("ref", "path", "~/Notes/{}.md"), ("target", "path", "out/{}.log"),
          ("worker.host", "host", "{}"), ("sess-id", "ident", "{}"), ("worker.invocation", "ident", "{}"), ("worker.account", "ident", "{}"),
          ("worker.model", "ident", "{}"),
          # the new exact templates (repair 14), with the word in the template's slot
          ("result", "path", "/home/jsy/Notes/prd-{}-20261113.md"), ("evidence-ref", "path", "/home/jsy/Notes/prd-fleet-{}-20261113.md"),
          ("consumer", "ident", "claude-4242-r7-{}-20261113"), ("worker.unit", "ident", "wm-build-inner{}-a.service")]
ROWS = ["row", "owner", "claim", "status", "waits-on"]


def why(form, v):
    if "prd-" in form:
        return "prd-template-slot"
    if form.startswith("claude-"):
        return "peer-template-slot"
    out = []
    for seg in [x for x in ev._GATE_SPLIT.split(v) if x]:
        low = seg.lower()
        if ev._word(low, frozenset()):
            out.append("vocab")
        elif ev._segment(low, frozenset()):
            out.append("vocab-compound")
        elif seg.isdigit():
            out.append("number")
        elif ev._slug(low):
            out.append("slug")
        elif any(low.startswith(w) and 0 < len(low) - len(w) <= 5 for w in ev._ID_WORDS if len(w) >= 3):
            out.append("vocab+suffix<=5")
        elif len(seg) <= 5:
            out.append("budget<=5")
        else:
            out.append("other")
    return "+".join(out)


nonlegit = [w for g in groups.values() for w in g]
print("values: %d non-legit (%d in a code list: %s)" % (len(nonlegit), sum(w.lower() in lists for w in nonlegit),
                                                       [w for w in nonlegit if w.lower() in lists]))
hits = {}
for gname, vals in list(groups.items()) + [("legit", LEGIT)]:
    n = p = 0
    for w in vals:
        for label, kind, form in FIELDS:
            v = form.format(w)
            n += 1
            if ev.unmark(ev.show(label, v, kind)) == v:
                p += 1
                if gname != "legit":
                    hits.setdefault(w, {}).setdefault(why(form, w), []).append(label + ("" if form == "{}" else "[" + form + "]"))
        for rf in ROWS:
            n += 1
            if ev.show_row(rf, w) == w:
                p += 1
                if gname != "legit":
                    hits.setdefault(w, {}).setdefault(why("{}", w), []).append("row." + rf)
    print("%-6s printed %4d / %4d field-cases" % (gname, p, n))
print("distinct non-legit values printing: %d" % len(hits))
for w, d in sorted(hits.items()):
    for mech, fl in d.items():
        print("HIT %-16s via %-18s in %2d: %s" % (w, mech, len(fl), ", ".join(fl[:8]) + (" ..." if len(fl) > 8 else "")))
