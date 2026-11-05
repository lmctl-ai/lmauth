#!/usr/bin/env python3
"""Prove SIGTERM closes an active loopback page in the released session binary."""
import argparse, json, os, pathlib, signal, subprocess, urllib.error, urllib.request
from urllib.parse import urlsplit
p=argparse.ArgumentParser();p.add_argument("--binary",required=True,type=pathlib.Path);a=p.parse_args()
proc=subprocess.Popen([str(a.binary.resolve()),"session"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={"HOME":os.environ.get("RUNNER_TEMP","/tmp"),"PATH":os.environ["PATH"]})
def identity(pid): return subprocess.check_output(["ps","-p",str(pid),"-o","lstart=,command="],text=True).strip()
start=identity(proc.pid)
try:
    proc.stdin.write(json.dumps({"command":"plan","provider":"npm","owner":"lmctl-ai","repositories":["lmauth"]})+"\n");proc.stdin.flush()
    plan=json.loads(proc.stdout.readline());proc.stdin.write(json.dumps({"command":"present","handle":plan["handle"]})+"\n");proc.stdin.flush()
    shown=json.loads(proc.stdout.readline());url=shown["operatorPage"]
    if urlsplit(url).hostname!="127.0.0.1": raise SystemExit("candidate page did not bind to loopback")
    with urllib.request.urlopen(url) as response:
        if response.status!=200: raise SystemExit("active page did not respond before signal")
    if identity(proc.pid)!=start: raise SystemExit("candidate process identity changed; refusing signal")
    proc.send_signal(signal.SIGTERM);out,err=proc.communicate()
    if proc.returncode!=4 or '"code":"cancelled"' not in err: raise SystemExit("SIGTERM cancellation mismatch: exit="+str(proc.returncode)+" stderr="+err)
    try:
        urllib.request.urlopen(url,timeout=2)
    except (urllib.error.URLError,ConnectionError,OSError):
        pass
    else: raise SystemExit("candidate page listener remained open after SIGTERM")
    print("active page closed after SIGTERM with structured cancellation")
finally:
    if proc.poll() is None:
        if identity(proc.pid)!=start: raise SystemExit("candidate process identity changed; refusing signal")
        proc.send_signal(signal.SIGTERM);proc.wait()
