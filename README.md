# lmauth

Guided, LLM-drivable authorization helper: click-through token setup that never shows the secret to the caller.

lmauth provides a GitHub authorization recipe, a local operator page or hidden terminal prompt, identity and public-repository verification, and write-only storage through the lmconn broker. The caller receives random handles and nonsecret summaries. The current slice does not prove token permissions or create GitHub Actions secrets.

## Install

```sh
lmscript install github:lmctl-ai/lmauth@v0.1.9
lmauth --version
```

[Read the operator quickstart](docs/operator-quickstart.md) for the pinned install, the public draft upload and repository-dispatch example for `lmctl-ai/lmoffice`, the human-attestation boundary, and the storage limits.

## Releases

Only the private repository's manual `workflow_dispatch` producer can create a draft candidate. This public repository verifies its sealed identity, runs the native qualification matrix without candidate execution credentials, and promotes only through the single trusted broker after all five platform jobs succeed. See [release-pipeline.md](docs/release-pipeline.md).

## License

The binary distribution is provided under the [Lattice Systems Binary License](LICENSE). The public repository contains release policy, qualification tests and distribution documentation; it does not contain the private Go implementation.
