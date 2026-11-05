#!/usr/bin/env bash
# Prepare the pinned third-party pieces for `go test -tags integration ./...` inside ONE private prefix.
# Nothing is installed globally; nothing real is contacted except the public release/clone endpoints below.
#   usage: scripts/prepare-integration.sh /absolute/private/prefix   (prints `export ...` lines)
set -euo pipefail
prefix=${1:?absolute private prefix}
case $prefix in /*) ;; *) echo "prefix must be absolute" >&2; exit 2;; esac
mkdir -p "$prefix"
LMMOCK_TAG=v0.1.105
LMMOCK_COMMIT=e9d6d7ffe8bf68f42bbfa8438130f2f2aa538542
LMCONN_COMMIT=83cdec653e336167b55d5c1b4e5cd91f9572fce9
LMCTL_VERSION=0.2.462
arch=$(uname -m); os=$(uname -s)
case "$os-$arch" in
  Linux-x86_64)  asset=lmmock-linux-x64;   sum=50ad10f0918340b6d8a7db1d9eeaaf240566a5544de174eae9fa49aa929b97fe;;
  Linux-aarch64) asset=lmmock-linux-arm64; sum=4ebba138346aec018f4f1e3523f35a52b721043329e9cd82bbc46b1d1a95ee44;;
  Darwin-arm64)  asset=lmmock-macos-arm64; sum=e7bf169514f5fae2a9a8d16d7d81f97ef57155f90fdbc295f8472c66450566dc;;
  Darwin-x86_64) asset=lmmock-macos-x64;   sum=cb1284024b06e2a52ab2ab99d6fa4f983a325ad894f46c094e3af6cf5b432617;;
  *) echo "unsupported platform $os-$arch" >&2; exit 2;;
esac
# 1. lmmock release asset, digest pinned (the digests come from the release's SHA256SUMS).
if [ ! -x "$prefix/lmmock" ]; then
  mkdir -p "$prefix/dl"
  curl -fL "https://github.com/lmctl-ai/lmmock/releases/download/$LMMOCK_TAG/$asset" -o "$prefix/dl/$asset"
  echo "$sum  $prefix/dl/$asset" | sha256sum -c - >&2
  install -m 0755 "$prefix/dl/$asset" "$prefix/lmmock"
fi
# 2. lmmock source at the release commit (the fixture capture script), and a pinned lmscript compiler.
if [ ! -d "$prefix/lmmock-src" ]; then
  git clone -q --branch "$LMMOCK_TAG" https://github.com/lmctl-ai/lmmock.git "$prefix/lmmock-src"
  test "$(git -C "$prefix/lmmock-src" rev-parse HEAD)" = "$LMMOCK_COMMIT"
fi
if [ ! -x "$prefix/compiler/node_modules/.bin/lmscript" ]; then
  npm install --prefix "$prefix/compiler" "@lmctl-ai/lmctl@$LMCTL_VERSION" --no-audit --no-fund >&2
fi
mkdir -p "$prefix/build"
for n in github-device-flow; do
  LMSCRIPT_BIN="$prefix/compiler/node_modules/.bin/lmscript" \
    node "$prefix/lmmock-src/scripts/capture-fixture.mjs" "$prefix/lmmock-src/examples/auth/$n/server.lms" "$prefix/build/$n.lmcode" >&2
done
# 3. lmconn at the pinned commit, installed from the repository into the private prefix.
if [ ! -d "$prefix/lmconn-src" ]; then
  git clone -q https://github.com/lmctl-ai/lmconn.git "$prefix/lmconn-src"
  git -C "$prefix/lmconn-src" checkout -q "$LMCONN_COMMIT"
fi
test "$(git -C "$prefix/lmconn-src" rev-parse HEAD)" = "$LMCONN_COMMIT"
npm install --prefix "$prefix/lmconn" --install-links "$prefix/lmconn-src" --no-audit --no-fund >&2
cat <<OUT
export LMAUTH_NODE=$(command -v node)
export LMAUTH_LMCONN_ENTRY=$prefix/lmconn/node_modules/@lmctl-ai/lmconn/bin/lmconn.js
export LMAUTH_LMMOCK=$prefix/lmmock
export LMAUTH_LMMOCK_GITHUB=$prefix/build/github-device-flow.lmcode
export LMAUTH_LMMOCK_CONFIG=$prefix/lmmock-src/examples/auth/github-device-flow/config.json
OUT
