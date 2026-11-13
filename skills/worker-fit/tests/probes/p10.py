"""Retained reviewer probe (re-review 10 of 8f250d8e, probes/p10.py), source path made relative to this repo. Run: python3 p10.py. Not collected by unittest discovery; test_review_fixes11.RetainedReviewerProbes runs it."""
import sys,itertools
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import envelope_validate as ev
names="password pass pin pw dbpw foo xyzzy blob val data auth0 mfa totp unlock recoverycode seedphrase thesauce k s z1 hush sekrit privateval mypass access_pin card_pin".split()
vals=["1234","0000","8675","abc-def","xk2-9q7","ab1","a1b","zz9","x7k","q-w-e-r-t-y","ab-cd-ef","golden-shadow-nested","nested negative","1234567890"]
res={}
for n in names:
  for v in vals:
    for tpl in ("%s=%s","%s: %s","--%s %s",'{"%s":"%s"}',"%s=\"%s\"","?%s=%s"):
      t=tpl%(n,v)
      o=ev.redact(t)
      if v in o: res.setdefault(v,[]).append(t)
for v,l in res.items(): print("%-22s %3d  e.g. %s"%(v,len(l),l[:3]))
