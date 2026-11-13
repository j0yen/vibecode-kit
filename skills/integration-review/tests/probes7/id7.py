import json
from mods6 import *
def show(t,rows,**kw):
    o=NEW.convert(rows,"partial",**kw); recs=o["register"]["records"]
    print(t,"->",len(recs),"rec", [(r["record_id"][:8],r.get("fusion_basis"),[ (s.get("repo"),s.get("commit","-")[:3],s.get("path_or_command")) for s in r.get("sources",[r.get("source_identity")])],r.get("path_or_command"),r["installed_state"],len(r["evidence"])) for r in recs], {k:v for k,v in o["stats"].items() if k in("fused_multi_source_components","multi_source_records")})
    return o
# P1 pathless diff repos distinct commits
show("P1 pathless o1/o2 distinct commits",[row(0,repo="o1/r",ident=cm("1")),row(1,repo="o2/r",ident=cm("2"))])
show("P2 pathless o1/o2 same commit",[row(0,repo="o1/r",ident=cm("1")),row(1,repo="o2/r",ident=cm("1"))])
show("P3 pathless o1/o2 sha differ",[row(0,repo="o1/r",ident=sha("a")),row(1,repo="o2/r",ident=sha("b"))])
# hidden gap: second repo's row carries no evidence
o=show("P4 pathless: o2 row no evidence",[row(0,repo="o1/r",ident=cm("1")),row(1,repo="o2/r",ident=cm("2"),ev="")])
# P5 order dependence of unstated-repo row
a=show("P5a o1,o2,unk",[row(0,repo="o1/r",ident=cm("1"),path="a.py"),row(1,repo="o2/r",ident=cm("2"),path="a.py"),row(2,repo=None,ident=None,path="a.py",ev="side=producer")])
b=show("P5b unk,o1,o2",[row(2,repo=None,ident=None,path="a.py",ev="side=producer"),row(0,repo="o1/r",ident=cm("1"),path="a.py"),row(1,repo="o2/r",ident=cm("2"),path="a.py")])
c=show("P5c o2,o1,unk",[row(1,repo="o2/r",ident=cm("2"),path="a.py"),row(0,repo="o1/r",ident=cm("1"),path="a.py"),row(2,repo=None,ident=None,path="a.py",ev="side=producer")])
# P6 commit-less row same repo joins first of two commits
show("P6 o1 c1, o1 c2, o1 none",[row(0,repo="o1/r",ident=cm("1"),path="a.py"),row(1,repo="o1/r",ident=cm("2"),path="a.py"),row(2,repo="o1/r",ident=None,path="a.py",ev="x")])
# P7 chain: unknown-repo row merging two eps? ep1 o1 c1; row2 unk repo c2 ; row3 o1 c? 
show("P7 o1 c1 ; unk repo c2 ; o1 c2",[row(0,repo="o1/r",ident=cm("1"),path="a.py"),row(1,repo=None,ident=cm("2"),path="a.py"),row(2,repo="o1/r",ident=cm("2"),path="a.py")])
# P8 repo case/spelling same repo different spellings, distinct commits
show("P8 spelling same repo c1/c1",[row(0,repo="https://github.com/o/r.git",ident=cm("1"),path="a.py"),row(1,repo="git@github.com:o/r",ident=cm("1"),path="a.py")])
# P9 same path 3 repos, cross sha fuse with a different path
show("P9 sha crosses",[row(0,repo="o1/r",ident="path+sha256:/p/a.py "+"a"*64,path="a.py"),row(1,repo="o2/r",ident="path+sha256:/p/a.py "+"b"*64,path="a.py"),row(2,repo="o3/r",ident="path+sha256:/q/b.py "+"b"*64,path="b.py")])
