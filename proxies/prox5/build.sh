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

# Init module if missing, then pull prox5 and build.
go mod init owl-prox5 2>/dev/null || true
go mod tidy
go build -trimpath -o ../bin/owl-prox5 .

echo "✅ Built proxies/bin/owl-prox5"
echo "   Run: bash run.sh prox5 -listen 127.0.0.1:42069 -file proxies.txt"
