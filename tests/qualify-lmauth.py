#!/usr/bin/env python3
"""Black-box qualification of the exact lmauth candidate, without provider credentials."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def run(binary, args, env=None):
    clean = {k: v for k, v in os.environ.items() if k not in {
        "GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN",
        "ACTIONS_ID_TOKEN_REQUEST_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_URL",
    }}
    if env:
        clean.update(env)
    return subprocess.run([str(binary), *args], capture_output=True, text=True, env=clean)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    binary = args.binary.resolve()

    version = run(binary, ["--version"])
    if version.returncode or not version.stdout.strip().startswith("lmauth 0.1."):
        raise SystemExit("candidate --version failed or did not report the release version")
    schema = run(binary, ["--lmcode-schema", "--json"])
    if schema.returncode:
        raise SystemExit("candidate lmcode schema route failed")
    schema_value = json.loads(schema.stdout)
    if "auth_plan" not in json.dumps(schema_value):
        raise SystemExit("candidate schema omitted auth_plan")
    signatures = run(binary, ["--lmcode-signatures"])
    if signatures.returncode or "auth_plan" not in signatures.stdout:
        raise SystemExit("candidate lmcode signatures route failed")

    planned = run(binary, ["plan", "--owner", "lmctl-ai", "--repos", "lmoffice"])
    if planned.returncode or "lmoffice" not in planned.stdout or "Contents: write" not in planned.stdout:
        raise SystemExit("candidate GitHub recipe plan failed")

    fixture = Path(__file__).resolve().parent / "flow.lmcodeb"
    with tempfile.TemporaryDirectory(prefix="lmauth-dry-", dir=args.evidence) as scratch:
        manifest_path = Path(scratch) / "manifest.json"
        manifest = {"version": 1, "mode": "single", "dry": True,
                    "parts": [{"index": 0, "file": str(fixture)}]}
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        dry = run(binary, ["--mock-api", "http://127.0.0.1:1", "--lmcode", str(fixture)],
                  {"LMCODE_INVOCATION_FILE": str(manifest_path)})
        if dry.returncode or '"dry":true' not in dry.stdout or "LMCODE_RETURN_BEGIN" not in dry.stdout or "dry-no-auth" not in dry.stdout:
            raise SystemExit("candidate dry lmcode invocation failed or omitted its terminal frame")
        if "operatorPage" in dry.stderr:
            raise SystemExit("dry lmcode invocation started a local authorization page")

        malformed = [
            {"version": 1, "mode": "single", "parts": [{"index": 0, "file": str(fixture)}]},
            {"version": 1, "mode": "single", "dry": "true", "parts": [{"index": 0, "file": str(fixture)}]},
        ]
        for index, value in enumerate(malformed):
            manifest_path.write_text(json.dumps(value), encoding="utf-8")
            result = run(binary, ["--lmcode", str(fixture)], {"LMCODE_INVOCATION_FILE": str(manifest_path)})
            if result.returncode != 2 or "operatorPage" in result.stdout + result.stderr:
                raise SystemExit("candidate did not reject malformed invocation manifest before dispatch")

    for retired in ("--first", "--last"):
        result = run(binary, [retired])
        if result.returncode != 2:
            raise SystemExit("candidate accepted retired builder option " + retired)

    if args.platform == "windows-x64":
        result = run(binary, ["present", "--owner", "lmctl-ai", "--repos", "lmpdf",
                              "--lmconn-node", "C:\\lmauth-test\\node.exe",
                              "--lmconn-entry", "C:\\lmauth-test\\lmconn.js",
                              "--lmconn-db", "C:\\lmauth-test\\creds.db"])
        if result.returncode != 4 or "private_store_acl_not_implemented" not in result.stderr:
            raise SystemExit("Windows storage did not fail closed with private_store_acl_not_implemented")

    (args.evidence / "qualification.json").write_text(json.dumps({
        "version": version.stdout.strip(), "plan": "lmctl-ai/lmoffice",
        "schema": "pass", "signatures": "pass", "dry_manifest": "pass",
        "missing_and_non_boolean_dry_rejected_before_dispatch": True,
        "retired_builder_options_refused": True,
        "windows_storage_fail_closed": args.platform == "windows-x64",
    }, indent=2) + "\n", encoding="utf-8")
    print("lmauth black-box checks passed for " + args.platform)


if __name__ == "__main__":
    main()
