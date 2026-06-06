#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# OWL-AGENT Docker Entrypoint
# Manages multiple processes: forward-proxy, mcp-server
# ═══════════════════════════════════════════════════════════
set -euo pipefail

PYTHON="/usr/local/bin/python3"
SCRIPTS="/app/scripts"
LOG_DIR="/app/logs"

mkdir -p "$LOG_DIR"

# ── Signal handler for graceful shutdown ──────────────────
cleanup() {
    echo "🦉 OWL-AGENT: Shutting down..."
    if [ -n "${PROXY_PID:-}" ]; then
        kill "$PROXY_PID" 2>/dev/null || true
        wait "$PROXY_PID" 2>/dev/null || true
    fi
    if [ -n "${MCP_PID:-}" ]; then
        kill "$MCP_PID" 2>/dev/null || true
        wait "$MCP_PID" 2>/dev/null || true
    fi
    echo "🦉 OWL-AGENT: All services stopped."
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── Service functions ─────────────────────────────────────

start_proxy() {
    echo "🦉 Starting Forward Proxy on :${FORWARD_PROXY_PORT:-60000}..."
    "$PYTHON" "$SCRIPTS/forward_proxy.py" > "$LOG_DIR/forward-proxy.log" 2>&1 &
    PROXY_PID=$!
    echo "   Forward Proxy PID: $PROXY_PID"
}

start_mcp() {
    echo "🦉 Starting MCP Resilient HTTP Server..."
    "$PYTHON" "$SCRIPTS/owl_resilient_mcp.py" > "$LOG_DIR/mcp-server.log" 2>&1 &
    MCP_PID=$!
    echo "   MCP Server PID: $MCP_PID"
}

wait_for_proxy() {
    local port="${FORWARD_PROXY_PORT:-60000}"
    local max_retries=30
    local count=0
    echo "🦉 Waiting for Forward Proxy on :${port}..."
    while [ $count -lt $max_retries ]; do
        if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1; then
            echo "   ✅ Forward Proxy is healthy!"
            return 0
        fi
        count=$((count + 1))
        sleep 1
    done
    echo "   ⚠️  Forward Proxy health check timed out after ${max_retries}s"
    return 1
}

print_banner() {
    echo ""
    echo "  ╔═══════════════════════════════════════════════════╗"
    echo "  ║          🦉  OWL-AGENT v6.0  🦉                  ║"
    echo "  ║     Unified Synergy Gateway — Docker Edition      ║"
    echo "  ╠═══════════════════════════════════════════════════╣"
    echo "  ║  Forward Proxy  →  :${FORWARD_PROXY_PORT:-60000}                       ║"
    echo "  ║  MCP Server     →  stdio                         ║"
    echo "  ║  Bypass Domains →  ${BYPASS_DOMAINS:-nvidia.com,...}     ║"
    echo "  ║  Upstream Proxy →  ${UPSTREAM_PROXY:-none}                ║"
    echo "  ║  Enrichment     →  ${OWL_ENRICH_ENABLED:-disabled}              ║"
    echo "  ╚═══════════════════════════════════════════════════╝"
    echo ""
}

# ── Main ──────────────────────────────────────────────────

print_banner

MODE="${1:-all}"

case "$MODE" in
    proxy)
        start_proxy
        wait "$PROXY_PID"
        ;;
    mcp)
        start_mcp
        wait "$MCP_PID"
        ;;
    all)
        start_proxy
        wait_for_proxy || true
        start_mcp
        echo "🦉 All services running. Press Ctrl+C to stop."
        # Wait for any child to exit
        wait -n 2>/dev/null || wait
        ;;
    health)
        echo "Checking Forward Proxy health..."
        curl -sf "http://localhost:${FORWARD_PROXY_PORT:-60000}/health" && echo "" || echo "UNHEALTHY"
        ;;
    *)
        echo "Usage: docker-entrypoint.sh {proxy|mcp|all|health}"
        echo ""
        echo "  proxy   — Run only the Forward Proxy"
        echo "  mcp     — Run only the MCP Server"
        echo "  all     — Run all services (default)"
        echo "  health  — Check service health"
        exit 1
        ;;
esac
