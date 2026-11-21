# Publishing to npm with lmauth (and setting the trusted publisher)

lmauth publishes npm packages for you. You only click approval links on a page; the npm token goes from npm into the local lmconn store and is never shown to you, the agent, the page or a log. Use this when:

- a package exists on npm but its GitHub workflow cannot publish (`npm error code ENEEDAUTH` in a trusted-publishing workflow means npm has no trusted publisher for that package yet), or
- a package is brand new (npm only accepts a trusted publisher for a package that already exists).

After one lmauth run with `--trust-repo` and `--trust-file`, the repository's workflow publishes later versions through OIDC with no token and no click.

Which command:

| Package source | Command |
| --- | --- |
| A directory with package.json (or a .tgz), for example a Node tool | `lmauth publish` (this page) |
| Native binaries attached to a GitHub release | `lmauth npm-release` (see [releasing.md](releasing.md)) |

## One-time setup

All four steps are needed once per machine.

```sh
# 1. Trusted node and lmconn: lmauth refuses (store_not_private) a node from PATH or anything others can write.
T=$HOME/.lmauth-trusted
mkdir -m 755 "$T"
cp "$(readlink -f "$(command -v node)")" "$T/node"
git clone https://github.com/lmctl-ai/lmconn "$T/lmconn"   # default branch is master
(cd "$T/lmconn" && npm ci --omit=dev)
chmod -R go-w "$T"

# 2. A private credential store directly under $HOME.
D=$(mktemp -d "$HOME/.lmauth-store-XXXXXX"); chmod 700 "$D"

# 3. The npm that lmconn runs (pinned; lmconn refuses a group- or world-writable npm).
npm install --prefix ~/.lmconn/npm npm@11.19.1 --ignore-scripts
chmod -R go-w ~/.lmconn/npm

# 4. The bridge key: the "appkey" field of ~/.config/lmctl/appkey.json (written by `lmchat login`).
export LMBRIDGE_APPKEY="$(node -p "require(process.env.HOME + '/.config/lmctl/appkey.json').appkey")"
```

lmconn must be at commit `4f5b14e` (2026-11-21) or later. Older lmconn answers `npm whoami` on a handle that has never been stored with `CREDENTIAL_POLICY` instead of `MISSING_KEY`, and lmauth then stops with `{"code":"login_check_failed"}` before showing any page.

## Publish and set the trusted publisher

Bump the version in package.json first; npm never accepts the same version twice. Then:

```sh
lmauth publish --package /abs/path/to/package-dir --access public --tag latest \
  --credential lmauth:npm-NPMUSER --login --expect-user NPMUSER \
  --trust-repo OWNER/REPO --trust-file release.yml \
  --lmconn-node "$T/node" --lmconn-entry "$T/lmconn/bin/lmconn.js" --lmconn-db "$D/creds.db"
```

- `--credential lmauth:NAME` is a name you choose. The first run stores the npm login under it, and later runs reuse it while npm still accepts it.
- `--login --expect-user NPMUSER` signs in through npm's web login when there is no working token, and refuses any account other than NPMUSER. The page is reachable by link, so this check is what stops someone else's login from being stored.
- `--trust-repo` and `--trust-file` name the GitHub repository and the workflow file (file name only, under .github/workflows) that npm will trust. The workflow needs `permissions: id-token: write` and npm 11.5.1 or newer.

## What you click

lmauth prints each page address on stderr as one JSON line, `{"approve":"https://lmctl.ai/r/.../npm-approve-N.html"}`. When an agent runs lmauth, it passes the address on to you. Open it in a browser where you are signed in to lmctl.ai. Each page holds one npm link; click it and approve on npm's own site.

A first run (worked example: `@lmctl-ai/lmwebtest` 0.1.73, 2026-11-21) showed two pages:

1. `npm-approve-1.html`: npm's web login. Approve as NPMUSER. lmauth stores the token, then continues by itself.
2. `npm-approve-2.html`: npm's 2FA approval for the publish. The same approval also covered setting the trusted publisher.

If a link is left unclicked until it expires, lmauth posts a fresh page and prints its address. The whole session ends after about 10 minutes without approval.

## The result

lmauth prints one JSON receipt per package on stdout and exits 0 only when every package is confirmed:

```json
{"results":[{"package":"@lmctl-ai/lmwebtest","version":"0.1.73","outcome":"published_confirmed",
  "integrity":"sha512-...","registryIntegrity":"sha512-...","trust":"configured","verified":true}]}
```

- `outcome`: `published_confirmed` (registry hash equals the file's), `already_published`, `conflict` (another file under the same version; the run stops), or `pending_verification` (check the registry later; never publish the same version again blindly).
- `trust`: `configured` (set now), `present` (it was already set), or `failed` (exit 1).

Right after publishing, `npm install NAME@VERSION` can answer `notarget` for a few minutes while the registry's package document catches up. The version document (`https://registry.npmjs.org/NAME/VERSION`) is already correct, and the tarball URL installs.

## Later versions: no lmauth, no click

Bump the version, push, and run the repository's workflow (for example `gh workflow run release.yml -R OWNER/REPO --ref main`). npm checks the workflow's OIDC identity against the trusted publisher. You need lmauth again only for a new package name or when the trusted publisher must change.

## Errors

| Error | Meaning and fix |
| --- | --- |
| `login_check_failed` | lmconn is older than `4f5b14e`; update the trusted lmconn copy. |
| `bridge_appkey_required` | `LMBRIDGE_APPKEY` is not set (setup step 4). |
| `store_not_private` | node, lmconn or a parent directory is writable by others, or the store is not a 700 directory directly under $HOME. |
| `ENEEDAUTH` in the GitHub workflow | npm has no trusted publisher for the package: run lmauth publish once with `--trust-repo` and `--trust-file`. |
| `E409 Cannot publish over previously staged version` | A publish waits for approval (staged). lmauth finds and approves it; do not publish the version again. |

Do not use an npm recovery code to get past a passkey prompt (the Chrome Password Manager PIN is the passkey's own check). A recovery code starts a 72-hour hold on publishing, tokens and settings.
