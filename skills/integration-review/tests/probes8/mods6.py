import os, tempfile
_HERE = os.path.dirname(os.path.abspath(__file__))
SKR = os.environ.get("IRS") or os.path.normpath(os.path.join(_HERE, "..", ".."))
R = os.environ.get("IRV_PROBE_WORK") or tempfile.mkdtemp(prefix="irv8-probes-")
for _d in ("out", "probes", "probes/w8"):
    os.makedirs(os.path.join(R, _d), exist_ok=True)
import importlib.util, sys, os
def load(name, path):
    sp=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
NEW=load("new_er",SKR+"/scripts/extract_register.py")
OLD=load("old_er",os.environ.get("IRV_OLD_EXTRACT") or (SKR+"/scripts/extract_register.py"))
def row(i,*,fam="IF001",role="producer",comp="c",repo="o/r",ident=None,path=None,state="source-only",ev="ev",host="h"):
    r={"family":fam,"role":role,"host":host,"component":comp,"interface_kind":"http","installed_state":state,"evidence":ev}
    if repo is not None: r["source_repo"]=repo
    if ident is not None: r["source_identity"]=ident
    if path is not None: r["path_or_command"]=path
    return r
def sha(c): return "path+sha256:/p/x.py "+c*64
def cm(c): return "commit "+c*40
