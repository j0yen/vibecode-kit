import json
import val7
S,H,H2=val7.S,val7.H,val7.H2
from t6 import V,rec,reg
def go(label,a,b):
    rc,o=V(reg([a,b,rec("cons",role="consumer",comp="c2")]),label=label)
    print(label,"rc",rc,[l for l in o.splitlines() if l.startswith(("OK","REFUSED","ERROR","WARN"))][:3])
# same endpoint twice, conflicting installed_state, one states commit
a=val7.R("r1",source_identity=S("o/r",H)); a["installed_state"]="source-only"
b=val7.R("r2",source_identity=S("o/r")); b["installed_state"]="installed"
go("conflict states, commit stated on one only",a,b)
# same, both commits stated
b2=val7.R("r2",source_identity=S("o/r",H)); b2["installed_state"]="installed"
go("conflict states, same commit (control)",a,b2)
# spelling
a3=val7.R("r1",source_identity=S("https://github.com/o/r",H)); b3=val7.R("r2",source_identity=S("git@github.com:o/r.git",H))
go("same repo two spellings, same commit",a3,b3)
# source with repo, other without repo & without commit but sha same
a4=val7.R("r1",source_identity=S("o/r",H)); b4=val7.R("r2",source_identity=S("o/r",H)); b4["source_identity"]["extra"]="x"
go("extra field",a4,b4)
