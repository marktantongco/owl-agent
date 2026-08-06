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
go mod tidy
go build -trimpath -ldflags="-s -w" -o ../bin/https_proxy_go .

echo "✅ Built proxies/bin/https_proxy_go"
echo "   Configure: cp proxies/https_proxy_go/config.example.yaml config.yaml"
echo "   Run:       proxies/bin/https_proxy_go run --config config.yaml"
