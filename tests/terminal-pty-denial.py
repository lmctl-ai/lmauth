#!/usr/bin/env python3
"""Exercise the hidden terminal consent prompt and refusal path without a credential."""
import argparse, errno, os, pathlib, pty, shutil, signal, subprocess, tempfile


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
    command = [str(args.binary.resolve()), "present", "--terminal", "--owner", "lmctl-ai", "--repos", "lmoffice",
               "--mock-api", "http://127.0.0.1:1", "--lmconn-node", str(args.node.resolve()),
               "--lmconn-entry", str(args.lmconn_entry.resolve()), "--lmconn-db", str(work / "store" / "creds.db")]
    env = {"HOME": str(home), "PATH": os.environ["PATH"]}
    child_pid, master = pty.fork()
    if child_pid == 0:
        os.execve(command[0], command, env)
    child_identity = identity(child_pid)
    transcript = bytearray()
    child_status = None
    try:
        while b"Type yes (hidden):" not in transcript:
            try:
                transcript.extend(os.read(master, 4096))
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                _, child_status = os.waitpid(child_pid, 0)
                raise SystemExit("candidate exited before consent prompt")
        print("macOS/Linux hidden consent prompt received", flush=True)
        os.write(master, b"no\n")
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
        _, child_status = os.waitpid(child_pid, 0)
        if os.waitstatus_to_exitcode(child_status) != 4 or b"Paste token here" in transcript:
            raise SystemExit("declined consent did not stop before token collection")
        print("declined consent stopped before token collection", flush=True)
    finally:
        if child_status is None:
            if identity(child_pid) != child_identity:
                raise SystemExit("candidate process identity changed; refusing signal")
            os.kill(child_pid, signal.SIGTERM)
            os.waitpid(child_pid, 0)
        os.close(master)
        shutil.rmtree(root)


if __name__ == "__main__":
    main()
