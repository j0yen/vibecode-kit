"""Retained reviewer probe (re-review 12 of d970f49c, probes/pron12.py), source path made relative to this repo; literal canary words are
assembled from fragments. Not collected by unittest discovery."""
import os
import sys,random
sys.path.insert(0,sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import envelope_validate as ev
r=random.Random(3)
C="bcdfghjklmnprstvwz"; V="aeiou"
def cv(n): return "".join(r.choice(C)+r.choice(V) for _ in range(n))
def cvc(n): return "".join(r.choice(C)+r.choice(V)+r.choice(C) for _ in range(n))
fields=[("worker.account","ident"),("current_owner","ident"),("target.branch","ident"),("target.repo","ident"),("worker.unit","ident"),("consumer","ident"),("task_id","ident"),("worker.session","ident"),("worker.model","ident"),("worker.host","host"),("result","path")]
shapes={"cv3(6)":lambda:cv(3),"cv4(8)":lambda:cv(4),"cv5(10)":lambda:cv(5),"cvc2":lambda:cvc(2),"cvc3(9)":lambda:cvc(3),"cv3-cv3":lambda:cv(3)+"-"+cv(3),"cv4.cv4":lambda:cv(4)+"."+cv(4),"cv4 cv4 cv4":lambda:"-".join(cv(4) for _ in range(3)),"A1303+cv4":lambda:"r7-"+cv(4)}
N=300
for f,k in fields:
    row=[]
    for sn,sf in shapes.items():
        hit=0
        for _ in range(N):
            v=sf()
            if k=="path": v="/mnt/ssd/"+v+".md"
            if k=="ident" and f=="worker.unit": v=v+".service"
            if v in ev.show(f,v,k): hit+=1
        row.append("%s=%d%%"%(sn,100*hit//N))
    print("%-16s"%f," ".join(row))
