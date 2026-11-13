"""Retained reviewer probe (re-review 10 of 8f250d8e, probes/pairs10b.py), source path made relative to this repo. Run: python3 pairs10b.py. Not collected by unittest discovery; test_review_fixes11.RetainedReviewerProbes runs it."""
import sys,json,urllib.parse as up
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import envelope_validate as ev
S="zq"+"vkwj"+"hxd"  # canary fragments
S2="lm"+"4tr9"+"wb"
cases=[
("kv","exit=0","password=%s"%S,S),
("flag-sp","--timeout 30","--password %s"%S,S),
("flag-eq","--retries=3","--api-key=%s"%S,S),
("short","-n 5","-p %s"%S,S),   # short flag -p
("short-u","-v","-u bob:%s"%S,S),
("json","{\"line\": 12}","{\"client_secret\": \"%s\"}"%S,S),
("json-esc","{\\\"line\\\": 12}","{\\\"client_secret\\\": \\\"%s\\\"}"%S,S),
("json-u","{\"line\": 12}","{\"pass\\u0077ord\": \"%s\"}"%S,S),
("json-dbl","\\\\\"line\\\\\": 12","\\\\\"secret\\\\\": \\\\\"%s\\\\\""%S,S),
("json-str",json.dumps({"x":json.dumps({"line":12})}),json.dumps({"x":json.dumps({"password":S})}),S),
("nested-obj","{\"meta\": {\"line\": 12}}","{\"credentials\": {\"inner\": {\"v\": \"%s\"}}}"%S,S),
("nested-arr","{\"lines\": [1,2]}","{\"tokens\": [\"%s\", \"%s\"]}"%(S,S2),S),
("pct","path=%2Fvar%2Flog","password%%3D%s"%S,S),
("pct-val","x=a%20b","pass=%s%%21"%S,S),
("url","https://host.example/p?x=1","https://bob:%s@host.example/p"%S,S),
("url-q","https://host.example/p?page=2","https://host.example/p?access_token=%s"%S,S),
("camel","lineCount=12","clientSecret=%s"%S,S),
("leet","line=12","p4ssw0rd=%s"%S,S),
("leet2","line=12","t0k3n=%s"%S,S),
("glue","line=12","passwd%s=ok"%S,S),
("glue-d","line=12","password%s"%S,S),
("glue-suf","line=12","token_%s"%S,S),
("quoted-mw","note=\"build ok\"","password=\"%s %s\""%(S,S2),S),
("prose","the build is ok","the password is %s"%S,S),
("prose2","rotated the key","pass %s"%S,S),
("hdr","Accept: text/plain","Authorization: Bearer %s"%S,S),
("cookie","Accept: json","Cookie: sid=%s"%S,S),
("env","LINES=12","AWS_SECRET_ACCESS_KEY=%s"%S,S),
("multiline","a=1\nb=2","a=1\npassword=%s\nb=2"%S,S),
("kv-colon","n: 4","apikey: %s"%S,S),
]
bad=0
for lbl,pos,neg,v in cases:
    for fn,nm in ((ev.redact,"redact"),(ev.redact_tool,"tool")):
        o=fn(neg); leak=v in o
        if nm=="redact" or True:
            print("%-11s %-6s %s"%(lbl,nm,"LEAK" if leak else "hid"))
