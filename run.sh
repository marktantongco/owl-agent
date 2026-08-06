#!/usr/bin/env bash
# 🦉 OWL-AGENT v4.3 — Unified launcher
set -euo pipefail

OWL_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$OWL_DIR/venv"
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
export CURL_CA_BUNDLE="${CURL_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"

# Ensure SSL cert env is set before any Python import
export PYTHONWARNINGS="ignore::DeprecationWarning"

usage() {
    cat <<EOF
🦉 OWL-AGENT v4.3 — Self-Optimising Proxy HTTP Client

USAGE:
  $0 server [--port 60000] [--metrics-port 9090] [--countries US GB PH]
  $0 fetch   <url> [--method GET] [--browser] [--geo US]
  $0 status
  $0 health
  $0 prox5   [-listen 127.0.0.1:42069] [-file proxies.txt]   # local SOCKS5 (prox5)

COMMANDS:
  server    Start the HTTP API + Prometheus metrics server (default)
  fetch     One-shot fetch a URL and print response
  status    Show proxy pool health
  health    Quick health check

EXAMPLES:
  $0 server
  $0 fetch https://api.github.com/users/octocat
  $0 fetch https://example.com --browser
  $0 fetch https://example.com --geo PH
  $0 status
EOF
    exit 0
}

# Default to server mode if no command
CMD="${1:-server}"
shift || true

case "$CMD" in
    server)
        exec "$VENV/bin/python" "$OWL_DIR/owl_server.py" "$@"
        ;;
    fetch)
        URL="${1:-}"
        if [ -z "$URL" ]; then
            echo "❌ Usage: $0 fetch <url> [options]"
            exit 1
        fi
        shift
        # Parse flags for the inline fetch
        METHOD="GET"
        BROWSER="false"
        while [ $# -gt 0 ]; do
            case "$1" in
                --method) METHOD="$2"; shift 2 ;;
                --browser) BROWSER="true"; shift ;;
                --geo) shift 2 ;;  # Currently ignored in one-shot; server handles it
                *) shift ;;
            esac
        done
        PAYLOAD=$(cat <<JSON
{
    "url": "$URL",
    "method": "$METHOD",
    "browser": $BROWSER
}
JSON
        )
        curl -s -X POST http://127.0.0.1:60000/fetch \
            -H 'Content-Type: application/json' \
            -d "$PAYLOAD" | python3 -m json.tool
        ;;
    status)
        curl -s http://127.0.0.1:60000/stats | python3 -m json.tool
        ;;
    health)
        curl -s http://127.0.0.1:60000/health | python3 -m json.tool
        ;;
    prox5)
        # Local prox5 SOCKS5 server (see proxies/). Requires a Go build.
        BIN="$OWL_DIR/proxies/bin/owl-prox5"
        if [ ! -x "$BIN" ]; then
            echo "❌ prox5 not built yet. Run: bash proxies/build.sh"
            exit 1
        fi
        exec "$BIN" "$@"
        ;;
    --help|-h)
        usage
        ;;
    *)
        echo "❌ Unknown command: $CMD"
        usage
        ;;
esac
