## Operator quickstart

Install the exact released version. The first command is:

```sh
lmscript install github:lmctl-ai/lmauth@v0.1.10
```

Confirm the installed version and print the guided recipe for the example use case: a public draft upload followed by `repository_dispatch` to `lmctl-ai/lmoffice`.

```sh
lmauth --version
lmauth plan --owner lmctl-ai --repos lmoffice
```

The plan describes a fine-grained GitHub token scoped to the `lmoffice` repository, with Contents write and Metadata read, and a seven-day expiry. The repository selection and grants are human-attested. lmauth verifies the GitHub identity and observes public repository metadata, but cannot prove the selected grant set, effective write authority, expiry policy, or organization approval. A successful API read does not prove write access.

To present the instructions and collect/store a token, point lmauth at a trusted lmconn installation and a new private database path:

```sh
lmauth present --owner lmctl-ai --repos lmoffice \
  --lmconn-node /absolute/path/to/node \
  --lmconn-entry /absolute/path/to/lmconn/bin/lmconn.js \
  --lmconn-db /absolute/path/to/private-directory/credentials.db
```

The token is entered only in the local operator page or hidden terminal prompt. lmauth passes it to the lmconn broker over stdin; lmconn stores it as non-revealable credential data. The caller and an LLM receive only a random handle and a nonsecret verification summary. They never receive the token. The operator must configure any downstream GitHub Actions secret through the approved secret-management path. This example guides token setup; lmauth does not create secrets, upload a release, or send `repository_dispatch`.

The release is built for Linux x64/arm64, macOS x64/arm64, and Windows x64. Qualification proves the sealed assets and private build provenance, exercises the exact candidate with offline dry/invocation checks, and tests the released lmmock fixture with real lmconn using synthetic markers. The native macOS lane checks terminal refusal and signal shutdown; Windows storage deliberately fails closed with `private_store_acl_not_implemented`. Qualification makes no real identity-provider requests. Human-attested grants remain unproven by the tool.

Limits: this slice does not automate browser login, create GitHub secrets, or isolate an agent running under the operator's OS account from every local file, browser, or debugging interface. Keep the operator browser outside agent screenshot/CDP access. Windows credential storage stays disabled until native ACL checks are implemented. npm currently provides instructions only and does not call npm APIs or store npm credentials.
