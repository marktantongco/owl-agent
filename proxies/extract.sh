#!/usr/bin/env bash
# Extracts the bundled Go modules into their standalone public repositories.
#
# The Freebuff-injected GitHub App credential can read/push existing repos but
# cannot CREATE repositories, so create the two empty repos first (30 seconds):
#
#   gh repo create marktantongco/owl-prox5 --public
#   gh repo create marktantongco/owl-https-proxy --public
#
# Then run this script:  bash proxies/extract.sh
#
# It copies each module to a temp dir, rewrites it for standalone use (own
# module path, bin/ build output), validates it (go vet/build/test), commits,
# and pushes to the canonical repo. The owl-agent tree is left untouched.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if ! command -v go >/dev/null 2>&1; then
  echo "❌ Go not installed (required to validate the modules before pushing)."
  exit 1
fi

# ─── owl-prox5 ────────────────────────────────────────────────────────────────
DIR="$TMP/owl-prox5"
mkdir -p "$DIR"
cp -r "$ROOT/proxies/prox5/." "$DIR/"
cd "$DIR"
sed -i 's|module github.com/marktantongco/owl-agent/proxies/prox5|module github.com/marktantongco/owl-prox5|' go.mod
sed -i 's|mkdir -p ../bin|mkdir -p bin|; s|-o ../bin/owl-prox5|-o bin/owl-prox5|; s|proxies/bin/owl-prox5|bin/owl-prox5|g; s|bash run.sh prox5 -listen|./bin/owl-prox5 -listen|g' build.sh
sed -i 's|bash proxies/build.sh|bash build.sh|; s|bash proxies/prox5/build.sh|bash build.sh|; s|bash run.sh prox5 -listen|./bin/owl-prox5 -listen|g' README.md
printf 'bin/\n' > .gitignore
go mod tidy
go vet ./...
go build -o /dev/null .
git init -b main -q
git add -A
git -c user.name="OWL-AGENT" -c user.email="owl-agent@users.noreply.github.com" commit -q -m "owl-prox5: rotating SOCKS5 proxy server (wrapper around yunginnanet/prox5)"
git remote add origin https://github.com/marktantongco/owl-prox5.git
echo "🦉 Pushing owl-prox5 → https://github.com/marktantongco/owl-prox5"
git push -u origin main

# ─── owl-https-proxy ──────────────────────────────────────────────────────────
DIR="$TMP/owl-https-proxy"
mkdir -p "$DIR"
cp -r "$ROOT/proxies/https_proxy_go/." "$DIR/"
cd "$DIR"
sed -i 's|module github.com/marktantongco/owl-agent/proxies/https_proxy_go|module github.com/marktantongco/owl-https-proxy|' go.mod
sed -i 's|mkdir -p ../bin|mkdir -p bin|; s|-o ../bin/https_proxy_go|-o bin/https_proxy_go|; s|proxies/bin/https_proxy_go|bin/https_proxy_go|g; s|cp proxies/https_proxy_go/config.example.yaml config.yaml|cp config.example.yaml config.yaml|' build.sh
sed -i 's|bash proxies/build.sh|bash build.sh|; s|bash proxies/https_proxy_go/build.sh|bash build.sh|; s|proxies/bin/https_proxy_go|bin/https_proxy_go|g; s|proxies/https_proxy_go/config.example.yaml|config.example.yaml|g' README.md
printf 'bin/\n' > .gitignore
go mod tidy
go vet ./...
go test ./...
go build -o /dev/null .
git init -b main -q
git add -A
git -c user.name="OWL-AGENT" -c user.email="owl-agent@users.noreply.github.com" commit -q -m "https_proxy_go: stealth HTTPS/HTTP forward proxy (Go port of madeye/https_proxy)"
git remote add origin https://github.com/marktantongco/owl-https-proxy.git
echo "🦉 Pushing owl-https-proxy → https://github.com/marktantongco/owl-https-proxy"
git push -u origin main

echo ""
echo "✅ Both modules extracted."
echo "   https://github.com/marktantongco/owl-prox5"
echo "   https://github.com/marktantongco/owl-https-proxy"
