# First real lmauth publish to npm (2026-11-21)

Package: @lmctl-ai/lmwebtest 0.1.73. It existed on npm (0.1.0, published by hand) but had no trusted publisher, so its OIDC workflow (release.yml) failed with ENEEDAUTH. One `lmauth publish --login --expect-user mikema3 --trust-repo lmctl-ai/lmwebtest --trust-file release.yml` run fixed both: receipt `published_confirmed`, `trust: configured`, `verified: true`.

What the operator saw: two pages. npm-approve-1 was npm's web login, npm-approve-2 the 2FA approval for the publish. That one approval also covered setting the trusted publisher. The agent relayed each `{"approve":...}` line from stderr.

What was missing from the docs and is now in docs/npm-publish.md:

- LMBRIDGE_APPKEY is the `appkey` field of ~/.config/lmctl/appkey.json.
- A first login needs lmconn 4f5b14e or later. Before it, lmconn answered `npm whoami` on a never-stored handle with CREDENTIAL_POLICY, and lmauth stopped with `login_check_failed` before any page (lmconn durable-memory/npm-missing-key-2026-11-21.md).
- lmconn's default branch is master; the trusted copy under ~/.lmauth-trusted needs `npm ci --omit=dev` and a refresh after lmconn fixes.
- For a few minutes after publishing, `npm install NAME@VERSION` can say notarget; the version document is already right.

Unverified: the first no-click OIDC publish by release.yml (lmwebtest 0.1.74 or later) is the real proof that the trusted publisher works.
