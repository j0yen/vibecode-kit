"""Retained reviewer probe (re-review 11 of 74551e2c, probes/fuzz11.py), source path made relative to this repo. Not collected by unittest discovery."""
import sys,random,collections,json
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import envelope_validate as ev
r=random.Random(11)
A="abcdefghijklmnopqrstuvwxyz";B=A.upper()+A+"0123456789"
b=lambda n,al=B:"".join(r.choice(al) for _ in range(n))
names="password passwd pwd pass pw token api_key apikey secret client_secret access_token auth bearer credential cred passphrase passcode pin otp totp mfa recovery_code seed seedphrase mnemonic privatekey private_key signing_key master_key vault unlock dbpw dbpass sekrit hush xyzzy foo blob data val k s mypass login_pw sshkey ssh_key cookie sessionid csrf nonce salt jwt webhook_secret client_id keyid".split()
names+= ["Password","PASSWORD","passWord","apiKey","clientSecret","x-api-key","X-Auth-Token","pass_word","p4ss","t0ken","s3cret","pa55word","secretkey2","token2","key1","pw1"]
vals={"l9":lambda:b(9,A),"l16":lambda:b(16,A),"mix12":lambda:b(12),"mix8":lambda:b(8),"hex16":lambda:b(16,"0123456789abcdef"),"b62-24":lambda:b(24),"two":lambda:"golden shadow","dash2":lambda:b(4,A)+"-"+b(4,A),"num6":lambda:b(6,"0123456789"),"num4":lambda:b(4,"0123456789"),"num12":lambda:b(12,"0123456789"),"hexshort":lambda:b(5,"0123456789abcdef"), "mixshort":lambda:b(5)}
fmts={"kv":"%s=%s","colon":"%s: %s","flag":"--%s %s","flageq":"--%s=%s","json":'{"%s": "%s"}',"query":"?%s=%s&x=1","quoted":"%s=\"%s\"","jsonesc":'{\\"%s\\": \\"%s\\"}',"space":"%s %s","hdr":"%s: Bearer %s","env":"%s_X=%s","sq":"%s='%s'"}
leaks=collections.defaultdict(list); n=0
for nm in names:
  for vn,vf in vals.items():
    for fn,f in fmts.items():
      v=vf(); t=f%(nm,v); n+=1
      o=ev.redact(t)
      if v in o: leaks[(vn)].append((fn,nm))
print("cases",n)
for vn,l in sorted(leaks.items(),key=lambda x:-len(x[1])):
    fm=collections.Counter(x[0] for x in l); nm=collections.Counter(x[1] for x in l)
    print("%-9s %4d leaks | fmts %s | names %s"%(vn,len(l),dict(fm.most_common(4)),[k for k,_ in nm.most_common(8)]))
