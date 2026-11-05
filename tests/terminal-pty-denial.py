#!/usr/bin/env python3
"""Exercise the hidden terminal consent prompt and refusal path without a credential."""
import argparse, errno, fcntl, os, pathlib, pty, shutil, signal, subprocess, tempfile, termios


def identity(pid):
    return subprocess.check_output(["ps", "-p", str(pid), "-o", "lstart=,command="], text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    for name in ("binary", "node", "lmconn-entry"):
        parser.add_argument("--" + name, required=True, type=pathlib.Path)
    args = parser.parse_args()
    root = pathlib.Path(tempfile.mkdtemp(prefix="lmauth-terminal-denial-", dir="/tmp")).resolve()
    root.chmod(0o700)
    home = root / "home"
    home.mkdir(mode=0o700)
    work = root / "work"
    work.mkdir(mode=0o700)
    master, slave = pty.openpty()

    def child_session():
        os.setsid()
        fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

    command = [str(args.binary.resolve()), "present", "--terminal", "--owner", "lmctl-ai", "--repos", "lmoffice",
               "--mock-api", "http://127.0.0.1:1", "--lmconn-node", str(args.node.resolve()),
               "--lmconn-entry", str(args.lmconn_entry.resolve()), "--lmconn-db", str(work / "store" / "creds.db")]
    env = {"HOME": str(home), "PATH": os.environ["PATH"]}
    child = subprocess.Popen(command, stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             preexec_fn=child_session, env=env)
    child_identity = identity(child.pid)
    os.close(slave)
    transcript = bytearray()
    try:
        while b"Type yes (hidden):" not in transcript:
            try:
                transcript.extend(os.read(master, 4096))
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                out, err = child.communicate()
                raise SystemExit("candidate exited before consent prompt: " + err.decode(errors="replace"))
        print("macOS/Linux hidden consent prompt received", flush=True)
        os.write(master, b"no\n")
        out, err = child.communicate()
        while True:
            try:
                chunk = os.read(master, 4096)
                if not chunk:
                    break
                transcript.extend(chunk)
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                break
        if child.returncode != 4 or b"Paste token here" in transcript or b"Paste token here" in out + err:
            raise SystemExit("declined consent did not stop before token collection")
        print("declined consent stopped before token collection", flush=True)
    finally:
        if child.poll() is None:
            if identity(child.pid) != child_identity:
                raise SystemExit("candidate process identity changed; refusing signal")
            child.send_signal(signal.SIGTERM)
            child.wait()
        os.close(master)
        shutil.rmtree(root)


if __name__ == "__main__":
    main()
