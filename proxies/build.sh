#!/usr/bin/env bash
# 🦉 Builds all bundled OWL-AGENT proxy integrations.
# Requires: Go 1.21+ (prox5) and Rust 1.70+ (https_proxy).
set -euo pipefail
cd "$(dirname "$0")"

# Version stamping: VERSION env wins, else nearest git tag, else "dev".
export VERSION="${VERSION:-$(git describe --tags --always 2>/dev/null || echo dev)}"

echo "🦉 Building OWL-AGENT proxy integrations (version $VERSION)"
echo "─────────────────────────────────────────"
"$PWD/prox5/build.sh"
"$PWD/https_proxy_go/build.sh"
"$PWD/https_proxy/build.sh"
echo ""
echo "✅ All integrations built."
echo "   See proxies/README.md for how to wire them into OWL-AGENT."
