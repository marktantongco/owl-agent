#!/usr/bin/env bash
# 🦉 OWL-AGENT v4.5 - Self-Optimising Scraping Engine Installer
# This script installs OWL-AGENT v4.5 and all its dependencies.
# v4.5 adds: Advanced ML (XGBoost/MLP), Self-Healing Plugins, A/B Testing

set -euo pipefail

# --- Configuration ---
OWL_HOME="${HOME}/.owl-agent"
OWL_BIN="${OWL_HOME}/run.sh"
OWL_PYTHON="${OWL_HOME}/proxy_defense.py"
OWL_SERVER="${OWL_HOME}/owl_server.py"
VENV_DIR="${OWL_HOME}/venv"
PYTHON_CMD="${VENV_DIR}/bin/python"
PIP_CMD="${VENV_DIR}/bin/pip"

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Helper functions ---
log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
log_step()  { echo -e "${BLUE}[STEP]${NC} $1"; }

echo -e "${GREEN}"
echo "  🦉 OWL-AGENT v4.5 Installer"
echo "  ════════════════════════════"
echo "  Advanced ML + Self-Healing Plugins + A/B Testing"
echo -e "${NC}"

# --- Check system requirements ---
log_step "Checking system requirements..."
if ! command -v python3 &>/dev/null; then
    log_error "Python3 is required but not installed."
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ "$(printf '%s\n' "3.10" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.10" ]]; then
    log_error "Python 3.10+ is required (found $PYTHON_VERSION)."
fi
log_info "Python $PYTHON_VERSION found ✓"

# --- Create directories ---
log_step "Creating OWL-AGENT home directory: $OWL_HOME"
mkdir -p "$OWL_HOME/cache/http"
mkdir -p "$OWL_HOME/config"
mkdir -p "$OWL_HOME/cache/proxy"
mkdir -p "$OWL_HOME/cache/models"
mkdir -p "$OWL_HOME/plugins"

# --- Create Python virtual environment ---
log_step "Creating Python virtual environment..."
if [ -d "$VENV_DIR" ]; then
    log_info "Virtual environment already exists, reusing..."
else
    python3 -m venv "$VENV_DIR"
fi
# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"

# --- Install Python dependencies ---
log_step "Installing Python dependencies (this may take a moment)..."
$PIP_CMD install --upgrade pip wheel setuptools 2>&1 | tail -1

log_info "Installing core dependencies..."
$PIP_CMD install --quiet \
    httpx[socks] \
    aiohttp \
    aiofiles \
    proxybroker2 \
    litproxy \
    resilient-httpx \
    circuitbreaker \
    curl_cffi \
    redis \
    prometheus-client

log_info "Installing v4.5 ML dependencies..."
$PIP_CMD install --quiet \
    scikit-learn \
    numpy \
    xgboost \
    joblib

log_info "Installing v4.5 plugin dependencies..."
$PIP_CMD install --quiet \
    watchdog

log_info "✅ All dependencies installed"

# --- Verify critical imports ---
log_step "Verifying critical imports..."
python3 -c "
import aiohttp, httpx, curl_cffi, circuitbreaker, proxybroker
print('  Core imports OK ✓')
" 2>/dev/null || log_warn "Some core imports failed (non-fatal)"

python3 -c "
import sklearn, numpy
print(f'  ML imports OK ✓ (scikit-learn {sklearn.__version__}, numpy {numpy.__version__})')
" 2>/dev/null || log_warn "ML imports failed - ML predictor will be disabled"

python3 -c "
try:
    import xgboost
    print(f'  XGBoost OK ✓ ({xgboost.__version__})')
except ImportError:
    print('  XGBoost not installed (optional)')
" 2>/dev/null || true

python3 -c "
try:
    import joblib
    print(f'  Joblib OK ✓ ({joblib.__version__})')
except ImportError:
    print('  Joblib not installed (optional)')
" 2>/dev/null || true

# --- Create the wrapper run.sh script ---
log_step "Creating run.sh wrapper..."
cat > "$OWL_BIN" << 'RUNEOF'
#!/usr/bin/env bash
# 🦉 OWL-AGENT v4.5 — Unified launcher
set -euo pipefail

OWL_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$OWL_DIR/venv"
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
export CURL_CA_BUNDLE="${CURL_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"
export PYTHONWARNINGS="ignore::DeprecationWarning"

usage() {
    cat <<EOF
🦉 OWL-AGENT v4.5 — Self-Optimising Proxy HTTP Client

USAGE:
  $0 server [--port 60000] [--metrics-port 9090] [--countries US GB PH] [--ab-test] [--ml] [--ml-model auto] [--plugin-dir ~/.owl-agent/plugins]
  $0 fetch   <url> [--method GET] [--browser] [--geo US]
  $0 status
  $0 health
  $0 stats

COMMANDS:
  server    Start the HTTP API + Prometheus metrics server (default)
  fetch     One-shot fetch a URL and print response
  status    Show proxy pool health
  health    Quick health check
  stats     Detailed stats including A/B test and ML data

SERVER OPTIONS:
  --ab-test         Enable A/B testing for proxy strategies
  --ml              Enable ML predictor for proxy selection
  --ml-model TYPE   ML model type: auto, logistic, xgboost, mlp (default: auto)
  --plugin-dir DIR  Plugin directory for auto-discovery (default: ~/.owl-agent/plugins)
  --no-curl-cffi    Disable curl_cffi (use httpx instead)
  --redis           Enable Redis state sharing

EXAMPLES:
  $0 server --ab-test --ml --ml-model auto
  $0 fetch https://api.github.com/users/octocat
  $0 fetch https://example.com --browser
  $0 stats
EOF
    exit 0
}

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
        METHOD="GET"
        BROWSER="false"
        while [ $# -gt 0 ]; do
            case "$1" in
                --method) METHOD="$2"; shift 2 ;;
                --browser) BROWSER="true"; shift ;;
                --geo) shift 2 ;;
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
    status|health|stats)
        curl -s "http://127.0.0.1:60000/$CMD" | python3 -m json.tool
        ;;
    --help|-h)
        usage
        ;;
    *)
        echo "❌ Unknown command: $CMD"
        usage
        ;;
esac
RUNEOF
chmod +x "$OWL_BIN"

# --- Create default config ---
log_step "Creating default config (config.json)..."
cat > "$OWL_HOME/config/config.json" << 'CFGEOF'
{
    "cache_ttl": 300,
    "rate_limit": 1.0,
    "max_retries": 3,
    "countries": ["US", "GB", "DE", "FR", "CA"],
    "use_curl_cffi": true,
    "use_redis": false,
    "redis_url": "redis://localhost:6379",
    "enable_ab_test": true,
    "enable_ml": true,
    "ml_model": "auto",
    "plugin_dir": "~/.owl-agent/plugins"
}
CFGEOF

# --- Create sample plugin ---
log_step "Creating sample plugin..."
cat > "$OWL_HOME/plugins/example_logger.py" << 'PLUGEOF'
"""Example plugin: logs all requests and responses."""
import logging

logger = logging.getLogger("owl-agent.plugin.example")

def on_request(method, url, **kwargs):
    logger.info(f"[Plugin] Request: {method} {url}")

def on_response(response, **kwargs):
    logger.info(f"[Plugin] Response: status={response.status}")

def on_error(error, attempt, url, **kwargs):
    logger.warning(f"[Plugin] Error on {url} (attempt {attempt}): {error}")
PLUGEOF
log_info "Sample plugin created at $OWL_HOME/plugins/example_logger.py"

# --- Create systemd service ---
log_step "Creating systemd service..."
cat > "$OWL_HOME/owl-agent.service" << SVCEOF
[Unit]
Description=🦉 OWL-AGENT v4.5 — Advanced ML + Self-Healing Plugins
Documentation=https://github.com/your-org/owl-agent
After=network.target
Wants=redis.service

[Service]
Type=simple
User=$(whoami)
Group=$(id -gn)
WorkingDirectory=$OWL_HOME

Environment=SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
Environment=CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
Environment=PYTHONWARNINGS=ignore::DeprecationWarning
Environment=OWL_USE_REDIS=false

ExecStart=$VENV_DIR/bin/python $OWL_SERVER \\
    --host 0.0.0.0 \\
    --api-port 60000 \\
    --metrics-port 9091 \\
    --countries US GB PH \\
    --ab-test \\
    --ml \\
    --ml-model auto \\
    --plugin-dir $OWL_HOME/plugins

Restart=always
RestartSec=10

ProtectHome=false
NoNewPrivileges=true
PrivateDevices=true
ProtectSystem=full
CapabilityBoundingSet=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
SVCEOF
log_info "Service file created at $OWL_HOME/owl-agent.service"
log_info "To install: sudo cp $OWL_HOME/owl-agent.service /etc/systemd/system/ && sudo systemctl daemon-reload"

# --- Install agent-browser (Node.js) ---
log_step "Installing agent-browser (optional)..."
if command -v npm &>/dev/null; then
    npm install -g @anthropic-ai/agent-browser 2>/dev/null && \
        log_info "agent-browser installed ✓" || \
        log_warn "agent-browser install failed (non-fatal)"
else
    log_warn "npm not found; agent-browser skipped (non-fatal)"
fi

# --- Test the installation ---
log_step "Testing OWL-AGENT installation..."
if "$PYTHON_CMD" -c "
from proxy_defense import PluginManager, ABTestManager
print('  PluginManager: OK')
print('  ABTestManager: OK')
try:
    from ml_models import AdvancedMLPredictor, XGB_AVAILABLE
    print(f'  AdvancedMLPredictor: OK (xgboost={XGB_AVAILABLE})')
except ImportError:
    print('  AdvancedMLPredictor: not available')
try:
    from plugin_loader import PluginLoader
    print(f'  PluginLoader: OK')
except ImportError:
    print('  PluginLoader: not available')
" 2>/dev/null; then
    log_info "✅ OWL-AGENT v4.5 installed successfully!"
else
    log_warn "Import test had issues; try running manually"
fi

# --- Summary ---
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  🦉 OWL-AGENT v4.5 Installation Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
echo "  Location:    $OWL_HOME"
echo "  Binary:      $OWL_BIN"
echo "  Python:      $PYTHON_CMD"
echo "  Config:      $OWL_HOME/config/config.json"
echo "  Plugins:     $OWL_HOME/plugins/"
echo "  Service:     $OWL_HOME/owl-agent.service"
echo ""
echo "  Quick start:"
echo "    $OWL_BIN server --ab-test --ml --ml-model auto"
echo "    $OWL_BIN fetch https://api.github.com/users/octocat"
echo "    $OWL_BIN stats"
echo ""
echo "  Install systemd service:"
echo "    sudo cp $OWL_HOME/owl-agent.service /etc/systemd/system/"
echo "    sudo systemctl daemon-reload"
echo "    sudo systemctl enable --now owl-agent"
echo ""
echo "  Add to PATH (optional):"
echo "    echo 'export PATH=\"\$PATH:$OWL_HOME\"' >> ~/.bashrc"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
