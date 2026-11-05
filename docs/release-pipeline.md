# lmauth release pipeline

The private producer is `lmctlhq/lmauth/.github/workflows/ci.yml`. It runs only by `workflow_dispatch` on `main`; pushing workflows or source does not start a private build. The operator command is:

```sh
gh workflow run ci.yml --repo lmctlhq/lmauth --ref main
```

The single throwaway failure control is selected before candidate sealing:

```sh
gh workflow run ci.yml --repo lmctlhq/lmauth --ref main -f deliberate_public_failure=true
```

The private workflow builds and tests Linux x64/arm64, macOS x64/arm64, and Windows x64 binaries with `CGO_ENABLED=0`. The version is the committed `VERSION` floor plus the workflow run number in PATCH. A candidate contains the five binaries, `LICENSE`, `RELEASE-MANIFEST.json`, and `SHA256SUMS`. A trusted private publisher validates the original workflow run and successful job identities, seals the public release/asset identities, obtains GitHub build provenance, uploads a draft to `lmctl-ai/lmauth`, then sends a repository dispatch containing only fixed identity fields and the seal digest. `RELEASE_TOKEN` is step-scoped to public draft staging and dispatch.

The public job permission boundary is checked by the offline regression suite:

| Job | Permissions |
|---|---|
| regression | contents:read |
| promote | contents:write; actions:read |
| candidate | contents:read; actions:read |
| qualify-macos-arm64 | contents:read; actions:read |
| integration | contents:read; actions:read |
| deliberate-failure-test | contents:read |

The public broker is the only job with `contents:write`. It validates the draft assets by fixed IDs and their complete hashes, verifies the private GitHub provenance, uploads a sealed handoff artifact, dispatches the separate read-only native workflow, waits for it, and checks the exact source/run and every required platform job through the Actions API. Candidate binaries run only on the worker jobs, which have read-only permissions, non-persisted checkout credentials, and no `GH_TOKEN` in candidate-running steps. Candidate subprocess environments remove GitHub and OIDC credentials. Promotion rechecks live revocation, Latest freshness, release immutability, and the complete frozen asset identity before publishing and setting Latest. A failed platform gate leaves the draft unpublished. A sealed throwaway failure is the only path that records revocation and cleans up its own draft object.

Each platform installs the exact candidate through the ordinary `lmscript install github:lmctl-ai/lmauth@TAG` route with the verified candidate binary staged on an isolated PATH; the install result must identify that exact binary and its checksum is rechecked. Black-box checks cover version/plan/schema/signatures, invocation manifest rejection before dispatch, dry mode and terminal frame, retired flags, and Windows' fail-closed credential-store message. Linux and macOS also run the released lmmock v0.1.105 GitHub device-flow mock and lmconn at commit `83cdec653e336167b55d5c1b4e5cd91f9572fce9` from a private prefix with a synthetic token, including terminal PTY and signal shutdown checks. No real identity provider or credential is used.

## Watch a run

```sh
gh run list --repo lmctlhq/lmauth --workflow ci.yml --limit 5
gh run view PRIVATE_RUN --repo lmctlhq/lmauth
gh run list --repo lmctl-ai/lmauth --workflow qualify-private-draft.yml --limit 10
gh run view BROKER_RUN --repo lmctl-ai/lmauth
gh run list --repo lmctl-ai/lmauth --workflow qualify-platforms.yml --limit 10
gh release list --repo lmctl-ai/lmauth --limit 10
```

Private publish-job retries reuse and verify the original frozen bytes. Do not rerun the full workflow for the same candidate after sealing. Public `workflow_dispatch` is only a replay of a previously recorded candidate; it is not authority to select an unrecorded release.

## Rollback

Rollback is an operator incident action, not a pipeline job. First stop new dispatch/replay and wait for any active broker to finish. Append the bad tag and incident reason to the public `REVOKED` file and push that append to `main`. Verify it landed before changing release visibility or Latest. Then mark the bad release as a prerelease and move Latest to a known-good published tag. If policy requires deleting the release object, delete without `--cleanup-tag`; never reuse the immutable tag. Installed binaries and caches do not roll back automatically.

## Porting notes

The shared policy and trusted helpers are copied from the reviewed lmoffice pilot and covered by offline tests plus deliberate mutations. lmauth-specific policy names the private workflow, eight required producer jobs, five binary assets and license. Public source contains only distribution documentation, release automation and public qualification tests; private Go source stays private. GitHub release immutability is enabled on this public repository. The pipeline publishes GitHub release assets only; it does not write npm credentials or Actions secrets.
