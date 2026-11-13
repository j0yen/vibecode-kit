import time, random
from mods6 import *
random.seed(5)
def shapes(n):
    S={}
    S["interleave-repo-then-commitonly"]=[row(i,repo=(f"o{i}/r" if i%2==0 else None),ident=(None if i%2==0 else cm("%x"%(i%15+1))),path="a.py",ev="side=producer") for i in range(n)]
    S["sha-shared-n-distinct-commit-rows"]=[row(i,repo="o/r",ident=(sha("a") if i==0 else cm("%040x"%i)[:0]+"commit "+("%040x"%i)),path=f"p{i%3}.py",ev="side=producer") for i in range(n)]
    S["same-sha-distinct-repo-same-path"]=[row(i,repo=f"o{i}/r",ident=sha("a"),path="a.py",ev="side=producer") for i in range(n)]
    S["same-sha-no-repo-distinct-path"]=[row(i,repo=None,ident="path+sha256:/p/x.py "+"d"*64,path=f"p{i}.py",ev="side=producer") for i in range(n)]
    S["repo-path-shared-distinct-commit-chain"]=[row(i,repo="o/r",ident=cm("%x"%(i%15+1)),path=f"q{i%2}.py",ev="side=producer") for i in range(n)]
    S["nocommit-then-many-commit"]=[row(0,repo="o/r",ident=None,path="a.py",ev="side=producer")]+[row(i,repo="o/r",ident="commit %040x"%i,path="a.py",ev="side=producer") for i in range(1,n)]
    S["commit-only-then-many-repo"]=[row(i,repo=None,ident="commit %040x"%i,path="a.py",ev="side=producer") for i in range(n//2)]+[row(i,repo=f"o{i}/r",ident=None,path="a.py",ev="side=producer") for i in range(n//2,n)]
    S["repoOnly-mixed-sha-multi"]=[row(i,repo=f"o{i%5}/r",ident=sha("%x"%(i%4)),path=f"p{i%7}.py",comp="c",ev="side=producer") for i in range(n)]
    S["many-evidence-same-ep"]=[row(i,repo="o/r",ident=cm("1"),path="a.py",ev=f"side=producer ev{i}") for i in range(n)]
    return S
res={}
for n in (500,1000,2000,4000):
    for k,rows in shapes(n).items():
        for h in (False,True):
            t=time.time(); NEW.convert(rows,"partial",heuristic_fusion=h); d=time.time()-t
            res[(k,h,n)]=d
for k in sorted({a for a,_,_ in res}):
    for h in (False,True):
        print(f"{k:45s} {'heur' if h else 'def '}", " ".join(f"n={n}:{res[(k,h,n)]:.2f}" for n in (500,1000,2000,4000)))
