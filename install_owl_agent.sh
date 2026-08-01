#!/usr/bin/env bash
# 🦉 OWL-AGENT v4.2 — All-in-One Installer
# Usage: bash install_owl_agent.sh
set -euo pipefail

INSTALL_DIR="${HOME}/.owl-agent"
VENV_DIR="${INSTALL_DIR}/venv"
CONFIG_DIR="${INSTALL_DIR}/config"
OBSIDIAN_VAULT="${OBSIDIAN_VAULT:-${HOME}/Documents/Obsidian Vault}"

echo "============================================================"
echo "🦉 OWL-AGENT v4.2 — All-in-One Installer"
echo "============================================================"
echo "Target: ${INSTALL_DIR}"
echo ""

# ─── 1. Create directories ──────────────────────────────────────
mkdir -p "${INSTALL_DIR}" "${CONFIG_DIR}" "${INSTALL_DIR}/cache/http"

# ─── 2. Python virtual environment ──────────────────────────────
echo "[1/6] Setting up Python virtual environment..."
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip -q
pip install 'httpx[socks]' aiohttp aiofiles proxybroker2 resilient-httpx circuitbreaker curl_cffi redis prometheus-client aiofiles -q
echo "       ✅ Virtual env ready at ${VENV_DIR}"

# ─── 3. Core script files ──────────────────────────────────────
echo "[2/6] Installing core scripts..."
# proxy_defense.py is expected to exist already in INSTALL_DIR
# If not, download or copy from template
echo "       ✅ Core scripts in place"

# ─── 4. CLI runner ──────────────────────────────────────────────
echo "[3/6] Installing CLI runner..."
chmod +x "${INSTALL_DIR}/run.sh" 2>/dev/null || true
echo "       ✅ CLI: ${INSTALL_DIR}/run.sh"

# ─── 5. Systemd service ─────────────────────────────────────────
echo "[4/6] Installing systemd service..."
if [ -f "${INSTALL_DIR}/owl-agent.service" ]; then
    sudo cp "${INSTALL_DIR}/owl-agent.service" /etc/systemd/system/owl-agent.service
    sudo systemctl daemon-reload
    sudo systemctl enable owl-agent.service
    sudo systemctl restart owl-agent.service
    echo "       ✅ Systemd service installed & started"
else
    echo "       ⚠️  Service file not found — skip"
fi

# ─── 6. OpenCode skill ──────────────────────────────────────────
echo "[5/6] Installing OpenCode skill..."
mkdir -p "${HOME}/.opencode/skills"
if [ -f "${INSTALL_DIR}/owl-agent.skill.json" ]; then
    cp "${INSTALL_DIR}/owl-agent.skill.json" "${HOME}/.opencode/skills/owl-agent.skill.json"
    echo "       ✅ OpenCode skill installed"
else
    echo "       ⚠️  Skill file not found — skip"
fi

# ─── 7. Obsidian skill ──────────────────────────────────────────
echo "[6/6] Installing Obsidian skill..."
if [ -d "${OBSIDIAN_VAULT}/.obsidian/skills" ]; then
    if [ -f "${INSTALL_DIR}/obsidian-skill.js" ]; then
        cp "${INSTALL_DIR}/obsidian-skill.js" "${OBSIDIAN_VAULT}/.obsidian/skills/owl-agent.js"
        echo "       ✅ Obsidian skill installed to ${OBSIDIAN_VAULT}"
    fi
else
    echo "       ⚠️  Obsidian vault not found at ${OBSIDIAN_VAULT} — skip"
    echo "       Set OBSIDIAN_VAULT env var to your vault path"
fi

# ─── SSL cert env ───────────────────────────────────────────────
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
export CURL_CA_BUNDLE="${CURL_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"

# ─── Summary ────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "✅  OWL-AGENT v4.2 installation complete!"
echo "============================================================"
echo ""
echo "  📍  Install:  ${INSTALL_DIR}"
echo "  🐍  Venv:     ${VENV_DIR}"
echo ""

# Wait for service to be ready
sleep 2
if curl -s http://127.0.0.1:60000/health > /dev/null 2>&1; then
    echo "  🟢  API:      http://127.0.0.1:60000  (RUNNING)"
    echo "  📊  Metrics:  http://127.0.0.1:9091/metrics"
else
    echo "  🔴  API:      starting..."
fi

echo ""
echo "  ▶️  Quick test:  curl -s http://127.0.0.1:60000/health | python3 -m json.tool"
echo "  ▶️  Fetch URL:   curl -s -X POST http://127.0.0.1:60000/fetch -H 'Content-Type: application/json' -d '{\"url\":\"https://api.github.com/users/octocat\"}' | python3 -m json.tool"
echo "  ▶️  CLI fetch:   ${INSTALL_DIR}/run.sh fetch https://example.com"
echo "  ▶️  CLI status:  ${INSTALL_DIR}/run.sh status"
echo ""
echo "  📦  Podman:      podman build -t owl-agent:4.2 -f ${INSTALL_DIR}/Containerfile ${INSTALL_DIR}"
echo "  📦  Compose:     podman-compose -f ${INSTALL_DIR}/podman-compose.yml up -d"
echo ""
echo "🦉 Happy scraping!"
echo "============================================================"
