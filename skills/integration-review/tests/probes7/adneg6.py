from t6 import *
def adopt(ref):
    g=good(); g[0].update(installed_state="loaded",adoption_evidence=[{"ref":ref,"observed_at":"2026-11-12T10:00:00Z"}]); return V(reg(g))[0]
for ref in ["pid 4242 exe /x not running","pid 4242 exe /x process exited","pid 4242 exe /x gone","pid 4242 comm qd terminated","pid 4242 comm qd (stopped)","pid 4242 comm qd killed","pid 4242 exe /x No such file or directory","pid 4242 exe /x ESRCH","pid-1 exe /bin/x","pid:-4242 exe /x","pid 4242 exe /x missing","pid 4242 exe /x absent","pid 4242 exe /x died","pid 4242 comm qd exited with 1","pid 4242 exe /x was not found","pid 4242 comm qd (zombie)","pid 4242 exe /x <defunct>"]:
    print("ACCEPTED(rc0)" if adopt(ref)==0 else "refused", "|", ref)
