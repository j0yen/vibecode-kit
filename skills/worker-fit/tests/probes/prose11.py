"""Retained reviewer probe (re-review 11 of 74551e2c, probes/prose11.py), source path made relative to this repo. Not collected by unittest discovery."""
import sys
import os; sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
import envelope_validate as ev
V="Xk9fQ2"+"mP7zab"
res=[]
for t in ["access token %s","api key %s","secret key %s","private key %s","the access_token is %s","access_token %s","the api_key is %s","api_key %s","client_secret %s","clientSecret %s","token2 %s","X-Auth-Token %s","key %s","the key is %s","private-key %s","auth %s","creds %s","%s"]:
    res.append((t,V in ev.redact(t%V)))
print(" ".join("%s=%s"%(t.replace(" ","_"),"L" if l else "h") for t,l in res))
