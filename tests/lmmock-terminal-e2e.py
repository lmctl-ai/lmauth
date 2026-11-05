#!/usr/bin/env python3
"""Use the pinned lmmock and real lmconn with a public synthetic credential."""
import argparse, errno, fcntl, json, os, pathlib, pty, shutil, signal, subprocess, tempfile, termios, time
TOKEN = "github_pat_mock_fine_grained_token"
def identity(pid):
    return subprocess.check_output(["ps", "-p", str(pid), "-o", "lstart=,command="], text=True).strip()
def stop_owned(proc, start):
    if proc.poll() is None:
        if identity(proc.pid) != start: raise SystemExit("owned process identity changed; refusing signal")
        proc.send_signal(signal.SIGINT)
    proc.wait()
def main():
    p=argparse.ArgumentParser()
    for name in ("binary","evidence","node","lmconn-entry","lmmock","lmcode","config"):
        p.add_argument("--"+name,required=True,type=pathlib.Path)
    a=p.parse_args(); evidence=a.evidence.resolve(); evidence.mkdir(parents=True,exist_ok=False,mode=0o700)
    private_root=pathlib.Path(tempfile.mkdtemp(prefix="lmauth-private-",dir="/tmp")).resolve()
    private_root.chmod(0o700)
    private_home=private_root/"lmauth-home"; private_home.mkdir(mode=0o700,exist_ok=True)
    work=pathlib.Path(tempfile.mkdtemp(prefix="lmauth-mock-",dir=private_root)); ready=work/"ready.json"
    env={"HOME":str(private_home),"PATH":os.environ["PATH"]}
    mock=subprocess.Popen([str(a.lmmock.resolve()),"serve","--lmcode",str(a.lmcode.resolve()),"--config",str(a.config.resolve()),"--listen","127.0.0.1:0","--ready-file",str(ready)],cwd=work,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env)
    mock_id=identity(mock.pid)
    while mock.poll() is None:
        if ready.is_file():
            base=json.loads(ready.read_text())["url"]
            if base.startswith("http://127.0.0.1:"): break
        time.sleep(0.05)
    else: raise SystemExit("pinned lmmock exited before ready")
    master,slave=pty.openpty()
    def child_session(): os.setsid(); fcntl.ioctl(slave,termios.TIOCSCTTY,0)
    db=work/"store"/"creds.db"
    cmd=[str(a.binary.resolve()),"present","--owner","lmctl-ai","--repos","lmpdf","--lmconn-node",str(a.node.resolve()),"--lmconn-entry",str(a.lmconn_entry.resolve()),"--lmconn-db",str(db),"--terminal","--mock-api",base]
    child=subprocess.Popen(cmd,stdin=slave,stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec_fn=child_session,env=env); child_id=identity(child.pid);os.close(slave); transcript=bytearray()
    try:
        def read_until(prompt):
            while prompt not in transcript:
                try: transcript.extend(os.read(master,4096))
                except OSError as error:
                    if error.errno != errno.EIO: raise
                    out, err = child.communicate()
                    safe = err.decode(errors="replace").replace(TOKEN, "[redacted synthetic canary]")
                    raise SystemExit("candidate exited before terminal prompt: " + safe)
        read_until(b"Type yes (hidden):")
        os.write(master,b"yes\n")
        read_until(b"Paste token here (hidden, never in chat):")
        os.write(master,TOKEN.encode()+b"\n"); out,err=child.communicate()
        while True:
            try:
                chunk=os.read(master,4096)
                if not chunk: break
                transcript.extend(chunk)
            except OSError as error:
                if error.errno!=errno.EIO: raise
                break
        if child.returncode or TOKEN.encode() in out+err+bytes(transcript): raise SystemExit("terminal flow failed or synthetic canary leaked")
        receipt=json.loads(out)
        if not receipt.get("stored") or receipt["verification"].get("identity")!="fixture-user" or receipt["verification"].get("strictVerified") is not False: raise SystemExit("candidate verification result differs from expected human-attested fixture")
        probe="import {DatabaseSync} from 'node:sqlite';const d=new DatabaseSync(process.argv[1]);console.log(d.prepare('select value from creds').all().some(x=>x.value===process.argv[2]));d.close();"
        result=subprocess.run([str(a.node.resolve()),"--input-type=module","-e",probe,str(db),TOKEN],capture_output=True,text=True,env=env,check=True)
        if result.stdout.strip()!="true": raise SystemExit("real lmconn did not store the synthetic mock token")
        reveal=subprocess.run([str(a.node.resolve()),str(a.lmconn_entry.resolve()),"cred","get","lmauth:"+receipt["handle"],"access_token","--reveal"],capture_output=True,text=True,env={"LMCONN_STORE_MODE":"broker","LMCONN_DB":str(db)})
        if reveal.returncode==0 or "CREDENTIAL_POLICY" not in reveal.stdout+reveal.stderr or TOKEN in reveal.stdout+reveal.stderr: raise SystemExit("lmconn did not refuse revealing the stored token")
        (evidence/"integration.json").write_text(json.dumps({"lmmock":"v0.1.105","lmconn":"83cdec653e336167b55d5c1b4e5cd91f9572fce9","identity":"fixture-user","grants":"human-attested","canary_absent_from_output":True,"store_verified":True,"reveal_refused":True},indent=2)+"\n")
        print("lmmock/lmconn synthetic candidate integration passed")
    finally:
        if child.poll() is None:
            if identity(child.pid)!=child_id: raise SystemExit("candidate process identity changed; refusing signal")
            child.send_signal(signal.SIGTERM);child.wait()
        os.close(master)
        try: stop_owned(mock,mock_id)
        finally: shutil.rmtree(private_root)
if __name__=="__main__": main()
