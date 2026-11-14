"""Retained reviewer probe (re-review 12 of d970f49c, probes/human12.py), source path made relative to this repo; literal canary words are
assembled from fragments. Not collected by unittest discovery."""
import os
import sys
sys.path.insert(0,sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import envelope_validate as ev
pw=['suns'+'hine', 'drag'+'onfly', 'prin'+'cess', 'letmei'+'nplease', 'mus'+'tang', 'pass'+'word1', 'trus'+'tno1', 'ilov'+'eyou', 'foot'+'ball', 'qwert'+'yuiop', 'monkeyb'+'usiness', 'correc'+'thorse', 'batter'+'ystaple', 'pwgen'+'style', 'ohva'+'esho', 'tieg'+'heng', 'Ahco'+'h3te']
fields=[("current_owner","ident"),("target.branch","ident"),("target.repo","ident"),("worker.unit","ident"),("consumer","ident"),("task_id","ident"),("reviewed_by","ident"),("result","path"),("worker.account","ident")]
for f,k in fields:
    pr=[]
    for p in pw:
        v=p+".service" if f=="worker.unit" else ("/mnt/ssd/x/"+p+".md" if k=="path" else p)
        if p in ev.show(f,v,k): pr.append(p)
    print("%-15s prints %d/%d: %s"%(f,len(pr),len(pw),pr))
for v in ['correct-ho'+'rse-battery', 'correcthorse-'+'batterystaple', 'dragonfly'+'-sunshine', 'sunshine-'+'dragonfly']:
    print(v,[f for f,k in fields if v in ev.show(f,v,k)])
