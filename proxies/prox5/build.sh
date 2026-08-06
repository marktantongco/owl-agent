#!/usr/bin/env bash
# Builds the prox5 SOCKS5 wrapper into proxies/bin/owl-prox5.
# Requires Go 1.21+ (https://go.dev/dl/).
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v go >/dev/null 2>&1; then
  echo "❌ Go not installed. Install Go 1.21+ first: https://go.dev/dl/"
  exit 1
fi

mkdir -p ../bin

# Version stamping: VERSION env wins, else nearest git tag, else "dev".
VERSION="${VERSION:-$(git describe --tags --always 2>/dev/null || echo dev)}"

go mod tidy
go build -trimpath -ldflags="-s -w -X main.version=$VERSION" -o ../bin/owl-prox5 .

echo "✅ Built proxies/bin/owl-prox5 (version $VERSION)"
echo "   Run: bash run.sh prox5 -listen 127.0.0.1:42069 -file proxies.txt"
