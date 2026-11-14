"""Retained reviewer probe (re-review 12 of d970f49c, probes/prose12.py), source path made relative to this repo; literal canary words are
assembled from fragments. Not collected by unittest discovery."""
import os
import sys,random
sys.path.insert(0,sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import envelope_validate as ev
r=random.Random(5)
A="abcdefghijklmnopqrstuvwxyz"
names="password passwd pwd pass pw token api_key apikey secret client_secret access_token auth bearer credential cred creds passphrase passcode pin otp totp mfa key api-key private_key secret_key dbpass dbpw vault unlock sekrit hush".split()
vals={"l9":lambda:"".join(r.choice(A) for _ in range(9)),"mixed12":lambda:"Xk9fQ"+"2mP7zab","l16":lambda:"".join(r.choice(A) for _ in range(16)),"num6":lambda:"482917","dig4":lambda:"4821","l6":lambda:"".join(r.choice(A) for _ in range(6))}
for vn,vf in vals.items():
    L=[]
    for nm in names:
        v=vf()
        for t in ("%s %s","the %s is %s","%s is %s"):
            if v in ev.redact(t%(nm,v)): L.append((nm,t.split("%s")[0] or "-")); 
    print(vn, sorted(set(n for n,_ in L)))
