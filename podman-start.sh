#!/bin/bash
# 🦉 OWL-AGENT v4.2 – Podman Quick-Start
# Run: bash podman-start.sh [up|down|logs|status]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/podman-compose.yml"

case "${1:-up}" in
  up)
    echo "🚀 Starting OWL-AGENT stack with podman..."
    podman-compose -f "$COMPOSE_FILE" up -d
    echo ""
    echo "✅ Stack is running:"
    echo "   OWL-AGENT:   http://localhost:8000/metrics"
    echo "   Prometheus:  http://localhost:9090"
    echo "   Grafana:     http://localhost:3000 (admin/admin)"
    echo ""
    echo "📊 Test metrics: curl http://localhost:8000/metrics"
    ;;
  down)
    echo "🛑 Stopping OWL-AGENT stack..."
    podman-compose -f "$COMPOSE_FILE" down
    ;;
  logs)
    podman-compose -f "$COMPOSE_FILE" logs -f ${2:-}
    ;;
  status)
    podman-compose -f "$COMPOSE_FILE" ps
    ;;
  build)
    echo "🔨 Building OWL-AGENT image..."
    podman-compose -f "$COMPOSE_FILE" build owl-agent
    ;;
  *)
    echo "Usage: $0 {up|down|logs|status|build}"
    exit 1
    ;;
esac
