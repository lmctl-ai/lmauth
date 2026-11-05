## Operator quickstart

Install the release with an exact pin:

```sh
lmscript install github:lmctl-ai/lmauth@v0.1.X
lmauth --version
```

For the example use case of uploading a public draft release and sending `repository_dispatch` to `lmctl-ai/lmoffice`, first print the guided GitHub recipe:

```sh
lmauth plan --owner lmctl-ai --repos lmoffice
```

The recipe asks the human to create a fine-grained GitHub token limited to the `lmoffice` repository, with Contents write and Metadata read, then a seven-day expiry. Those grants and repository selection are human-attested. lmauth can verify the GitHub identity and observe public repository metadata, but GitHub does not expose enough evidence here to prove the selected grant set, effective write authority, expiry policy, or organization approval. A successful public API read is not proof of write access. This example describes token setup only: lmauth does not create GitHub Actions secrets or perform uploads/dispatches in this slice.

To present the operator instructions and collect/store a token, use a private lmconn database directory and trusted lmconn installation:

```sh
lmauth present --owner lmctl-ai --repos lmoffice \
  --lmconn-node /absolute/path/to/node \
  --lmconn-entry /absolute/path/to/lmconn/bin/lmconn.js \
  --lmconn-db /absolute/path/to/private-directory/credentials.db
```

The token is entered only in the local operator page (or hidden terminal prompt) and passed to the lmconn broker over stdin. lmconn stores it as non-revealable credential data. The lmauth caller and an LLM receive only random handles and a nonsecret verification summary; they never receive the token. The operator must configure any downstream GitHub Actions secret through an approved secret-management path. Do not paste a token into chat or a recipe input.

The Windows binary reports `private_store_acl_not_implemented` for storage and fails closed until native ACL checks are implemented. This slice supports the GitHub fine-grained PAT guidance flow; it does not automate browser login, prove GitHub permission grants, write Actions secrets, or isolate an agent running under the operator's OS account from every local file, browser, or debugging interface. Keep the operator browser outside agent screenshot/CDP access. npm currently produces instructions only and does not make npm API calls or store npm tokens.

The release pipeline builds five native binaries, verifies sealed checksums and private provenance, and publishes only after Linux x64/arm64, macOS x64/arm64, and Windows x64 qualification succeeds. Its public qualification uses synthetic lmmock data and a private lmconn prefix; it does not contact a real identity provider.
