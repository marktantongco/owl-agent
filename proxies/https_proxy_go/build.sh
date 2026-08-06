#!/usr/bin/env bash
# Builds the Go port of madeye/https_proxy into proxies/bin/https_proxy_go.
# Requires Go 1.22+ (https://go.dev/dl/).
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v go >/dev/null 2>&1; then
  echo "❌ Go not installed. Install Go 1.22+ first: https://go.dev/dl/"
  exit 1
fi

mkdir -p ../bin

# Version stamping: VERSION env wins, else nearest git tag, else "dev".
VERSION="${VERSION:-$(git describe --tags --always 2>/dev/null || echo dev)}"

# Platform-qualified asset name (e.g. https_proxy_go-darwin-arm64, https_proxy_go-windows-amd64.exe).
GOOS="$(go env GOOS)"; GOARCH="$(go env GOARCH)"
EXT=""; [ "$GOOS" = "windows" ] && EXT=".exe"
ASSET="https_proxy_go-$GOOS-$GOARCH$EXT"

go mod tidy
go build -trimpath -ldflags="-s -w -X main.version=$VERSION" -o "../bin/$ASSET" .

echo "✅ Built proxies/bin/$ASSET (version $VERSION)"
echo "   Configure: cp proxies/https_proxy_go/config.example.yaml config.yaml"
echo "   Run:       proxies/bin/$ASSET run --config config.yaml"
