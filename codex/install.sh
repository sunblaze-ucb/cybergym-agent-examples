#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CODEX_REPO="$SCRIPT_DIR/codex-repo"

# clone repo
if [ ! -d "$CODEX_REPO" ]; then
    git clone -b cybergym git@github.com:sunblaze-ucb/cybergym-codex.git $CODEX_REPO
fi

# Build the Codex image. package.json requires Node.js 22 or newer.
node_major="$(node --version | sed -E 's/^v([0-9]+).*/\1/')"
if [[ ! "$node_major" =~ ^[0-9]+$ ]] || (( node_major < 22 )); then
  echo "Codex requires Node.js >= 22; found $(node --version)." >&2
  exit 1
fi
if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm is required. Install it with: corepack enable && corepack prepare pnpm@latest --activate" >&2
  exit 1
fi

CODEX_CLI_DIR="$CODEX_REPO/codex-cli"
pushd "$CODEX_CLI_DIR" >/dev/null || {
  echo "Error: Failed to change directory to $CODEX_CLI_DIR"
  exit 1
}
pnpm install
pnpm run build

pack_dir="$(mktemp -d /tmp/cybergym-codex-pack.XXXXXX)"
cleanup() {
  rm -rf "$pack_dir"
  popd >/dev/null || true
}
trap cleanup EXIT

mkdir -p ./dist
rm -f ./dist/codex.tgz
pnpm pack --pack-destination "$pack_dir"
mapfile -t packages < <(find "$pack_dir" -maxdepth 1 -type f -name '*.tgz' -print)
if (( ${#packages[@]} != 1 )); then
  echo "Expected exactly one packed Codex archive in $pack_dir, found ${#packages[@]}." >&2
  exit 1
fi
mv "${packages[0]}" ./dist/codex.tgz
test -s ./dist/codex.tgz || {
  echo "Failed to prepare $CODEX_CLI_DIR/dist/codex.tgz" >&2
  exit 1
}

echo "Prepared $(pwd)/dist/codex.tgz"
docker build -t cybergym/codex -f "./Dockerfile.cybergym" .
