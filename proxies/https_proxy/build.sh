#!/usr/bin/env bash
# Builds madeye/https_proxy (Rust) into proxies/bin/https_proxy.
# Requires Rust 1.70+ (https://rustup.rs).
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v cargo >/dev/null 2>&1; then
  echo "❌ Rust toolchain not installed. Install Rust 1.70+ first:"
  echo "   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
  exit 1
fi

SRC_DIR="$PWD/.src/https_proxy"
BIN_DIR="$PWD/../bin"

if [ ! -d "$SRC_DIR/.git" ]; then
  git clone https://github.com/madeye/https_proxy.git "$SRC_DIR"
fi

mkdir -p "$BIN_DIR"
cd "$SRC_DIR"
cargo build --release
cp -f target/release/https_proxy "$BIN_DIR/https_proxy"

echo "✅ Built proxies/bin/https_proxy"
echo "   Configure: cp proxies/https_proxy/config.example.yaml proxies/https_proxy/config.yaml"
echo "   Run:       proxies/bin/https_proxy run --config proxies/https_proxy/config.yaml"
