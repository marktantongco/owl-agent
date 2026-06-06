<p align="center">
  <img src="https://img.shields.io/badge/OWL--AGENT-v6.0-BFFF00?style=for-the-badge&labelColor=050508&color=BFFF00" alt="OWL-AGENT v6.0" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&labelColor=050508&color=3776AB" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&labelColor=050508&color=2496ED" alt="Docker Ready" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge&labelColor=050508&color=00FF88" alt="MIT License" />
</p>

<h1 align="center">🦉 OWL-AGENT</h1>
<h3 align="center">Unified Free-Tier AI Proxy Gateway</h3>
<p align="center"><strong>One Gateway. All AI Models. Zero Cost.</strong></p>

---

## 🧭 Overview

**OWL-AGENT** is a production-grade proxy gateway that aggregates **free-tier access** across multiple AI providers. It stitches credentials, routes requests intelligently with a 5-tier escalation stack, and presents a single API endpoint — so you get free AI model access without managing multiple accounts or API keys.

### What It Does

| Feature | Description |
|---------|-------------|
| **Forward Proxy** | HTTP/HTTPS proxy on port 60000 with domain bypass and upstream chaining |
| **Resilient Client** | 5-tier defense: weighted rotation → circuit breaker → dedup → cache → rate limit |
| **MCP Server** | Model Context Protocol server exposing 5 tools for AI agents |
| **Docker Packaging** | Multi-stage Docker image with docker-compose for 3 service modes |
| **Credential Stitching** | Pool management and rotation for free-tier credentials |
| **Domain Bypass** | NVIDIA, OpenCode, AWS, Kiro domains go direct (no proxy overhead) |

---

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/marktantongco/owl-agent.git
cd owl-agent/docker

# Start all services
docker compose --profile all-in-one up -d

# Verify the proxy is running
curl http://localhost:60000/health
```

### Docker Service Modes

| Mode | Command | Description | Port |
|------|---------|-------------|------|
| **All-in-One** | `docker compose --profile all-in-one up -d` | Proxy + MCP in single container | 60000 |
| **Proxy Only** | `docker compose up forward-proxy -d` | Just the HTTP/HTTPS proxy | 60000 |
| **MCP + Proxy** | `docker compose up -d` | Both services, MCP depends on proxy | 60000 |

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌─────────────┐
│  AI Agent /  │────▶│  Forward Proxy   │────▶│  Upstream Proxy │────▶│  Internet   │
│  Client      │     │  Port 60000      │     │  Mihomo :7890   │     │  API APIs   │
└──────────────┘     └──────────────────┘     └─────────────────┘     └─────────────┘
                            │ bypass                                       │
                     ┌──────┴──────┐                              ┌─────┴─────┐
                     │ NVIDIA,     │                              │ Claude,   │
                     │ OpenCode,   │                              │ Kiro,     │
                     │ AWS, Kiro   │                              │ Hermes,   │
                     └─────────────┘                              │ Gemini    │
                                                                  └───────────┘
```

### 5-Tier Defense Stack

| Tier | Component | Purpose |
|------|-----------|---------|
| 1 | **Weighted Proxy Rotation** | Prefer working proxies with higher weight |
| 2 | **Circuit Breaker** | 3 failures → OPEN for 60s → HALF_OPEN probe |
| 3 | **Request Deduplication** | Coalesce duplicate in-flight requests |
| 4 | **Response Cache** | TTL-based cache (300s default) for GET/HEAD |
| 5 | **Domain Rate Limiter** | asyncio.Semaphore per domain (5 concurrent) |

---

## 📦 Provider Compatibility

| Provider | Forward Proxy | API Gateway | MCP Server | Docker | Native CLI | Stars |
|----------|:------------:|:-----------:|:----------:|:------:|:----------:|:-----:|
| Claude | ✅ | ✅ | ✅ | ✅ | ❌ | ⭐ 4.8 |
| OpenCode | ✅ | ❌ | ✅ | ✅ | ✅ | ⭐ 4.5 |
| Kiro | ✅ | ✅ | ❌ | ✅ | ✅ | ⭐ 4.6 |
| Hermes | ✅ | ✅ | ✅ | ✅ | ❌ | ⭐ 4.3 |
| Gemini | ✅ | ❌ | ❌ | ✅ | ❌ | ⭐ 4.0 |
| DeepSeek | ✅ | ❌ | ❌ | ✅ | ❌ | ⭐ 4.1 |

---

## 🗺️ Decision Tree

```
IF you need production deployment  → Docker Compose (all-in-one profile)
IF you need development setup      → Bash Installer (./install_owl_unified.sh)
IF you need CI/CD integration      → npm Package (npm install owl-agent)
IF you need all providers          → Docker with default config
IF you need proxy only             → Docker proxy service
IF you need MCP only               → Docker mcp service
IF you have limited resources      → Bash (no Docker overhead)
IF you want zero-config            → Docker Compose with defaults
```

---

## 🔧 Three Approaches Compared

| Aspect | 🐳 Container-First | 🖥️ Native Installer | 📦 SDK Integration |
|--------|:------------------:|:-------------------:|:------------------:|
| **Install** | `docker compose up -d` | `./install_owl_unified.sh` | `npm install owl-agent` |
| **Speed** | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| **Complexity** | ★★☆☆☆ | ★★★☆☆ | ★★☆☆☆ |
| **Rating** | ⭐ 4.8 | ⭐ 4.5 | ⭐ 3.8 |
| **Best For** | Production, CI/CD, teams | Dev, single machines, tinkerers | Node.js, automation, pipelines |
| **Host Deps** | Docker only | Python 3.8+, Ubuntu | Node.js/Bun |
| **Isolation** | Full container isolation | System-level | Wraps Docker |

### Merge Strategy: Best of All Three

Use **Docker** for production deployment, **Bash** for bootstrap and systemd, **npm** for programmatic integration. They compose perfectly:

```
Docker Deploy ──▶ Bash Bootstrap ──▶ npm Integrate
   (prod)           (setup)           (automation)
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FORWARD_PROXY_PORT` | `60000` | Port for the forward proxy |
| `UPSTREAM_PROXY` | `""` | Upstream proxy URL (user:pass@host:port) |
| `BYPASS_DOMAINS` | `nvidia.com,opencode.ai,amazonaws.com,kiro.dev` | Domains that bypass the proxy |
| `PROXY_POOL_CONFIG` | `/app/config/proxy_pool.json` | Proxy pool configuration path |
| `PROXY_SOURCES_CONFIG` | `/app/config/proxy_sources.json` | Proxy sources configuration path |
| `OWL_ENRICH_ENABLED` | `""` | Enable proxy enrichment (any value = on) |
| `CACHE_TTL` | `300` | Cache time-to-live in seconds |
| `CIRCUIT_BREAKER_THRESHOLD` | `3` | Failures before circuit opens |
| `CIRCUIT_BREAKER_RECOVERY` | `60` | Seconds before half-open probe |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |

---

## 📂 Project Structure

```
owl-agent/
├── docker/                          # 🐳 Docker-packaged backend
│   ├── Dockerfile                   # Multi-stage Python 3.12-slim image
│   ├── docker-compose.yml           # 3 services: proxy, mcp, all-in-one
│   ├── docker-entrypoint.sh         # Process manager with graceful shutdown
│   ├── scripts/                     # Python runtime scripts
│   │   ├── forward_proxy.py         # HTTP/HTTPS proxy (port 60000)
│   │   ├── proxy_defense_fixed_v3.py # 5-tier resilient HTTP client
│   │   └── owl_resilient_mcp.py     # MCP server (JSON-RPC stdio)
│   └── config/                      # Runtime configurations
│       ├── proxy_pool.json          # Upstream proxy + GitHub sources
│       └── proxy_sources.json       # Auto-discovery source definitions
├── src/                             # 🌐 Next.js web portal
│   ├── app/
│   │   ├── page.tsx                 # Main landing page
│   │   ├── layout.tsx               # Root layout with dark theme
│   │   └── globals.css              # Custom OWL theme
│   └── components/ui/               # shadcn/ui components
├── package.json                     # Next.js 16 + React 19
└── README.md                        # This file
```

---

## 🔌 MCP Server Tools

The MCP server exposes 5 tools for AI agents via JSON-RPC over stdio:

| Tool | Description |
|------|-------------|
| `fetch_resilient` | Make a resilient HTTP request with retries, circuit-breaker, proxy rotation |
| `fetch_status` | Return client statistics (requests, successes, failures, cache hits) |
| `fetch_clear_cache` | Clear the internal response cache |
| `health_check` | Health status of all configured proxies |
| `queue_status` | Current in-flight request count |

### Connect from OpenCode

```json
{
  "mcpServers": {
    "owl-resilient-http": {
      "command": "docker",
      "args": ["compose", "exec", "mcp-server", "python3", "/app/scripts/owl_resilient_mcp.py"]
    }
  }
}
```

---

## 🛡️ Ports Reference

| Port | Service | Protocol |
|------|---------|----------|
| 60000 | Forward Proxy | HTTP/HTTPS |
| 8333 | Kiro Gateway | OpenAI API |
| 7890 | Upstream (Mihomo) | HTTP (external) |

---

## 📜 Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| **v5.0** | 2025-Q1 | Initial unified installer, basic proxy, fragile sed injection |
| **v5.1** | 2025-Q2 | Replaced sed with os.getenv(), fixed Kiro CLI duplication |
| **v6.0** | 2025-Q3 | Added get_stats(), fixed TokenBucket race, full HTTP proxy, Docker packaging, idempotent installer |

---

## 🤝 Stack Alignment

### Works Well Together ✅

| Combination | Rating | Notes |
|-------------|--------|-------|
| Docker + MCP + Claude | ⭐⭐⭐⭐⭐ | Full-stack: proxy, API, agent tools |
| Docker + Kiro CLI + Gateway | ⭐⭐⭐⭐⭐ | Native CLI with API gateway |
| Bash + OpenCode + Proxy | ⭐⭐⭐⭐ | Solid development setup |
| Docker + All Providers | ⭐⭐⭐⭐⭐ | Maximum coverage |

### Partial Support ⚠️

| Combination | Rating | Notes |
|-------------|--------|-------|
| npm + Gateway + Gemini | ⭐⭐⭐ | No native Gemini gateway support |
| Bash + MCP + DeepSeek | ⭐⭐⭐ | MCP works, no DeepSeek-specific features |

---

## 📋 Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | v2+ | Multi-service orchestration |
| Python | 3.8+ | Runtime for scripts (inside container or native) |
| RAM | 512MB+ | Minimum for proxy services |
| Disk | 1GB+ | Docker image + logs |

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Proxy won't start | Check if port 60000 is free: `lsof -i :60000` |
| Health check fails | Wait 30s after start, check `docker compose logs` |
| MCP tools not found | Ensure MCP container is running: `docker compose ps` |
| Circuit breaker stuck | Send a GET request to trigger HALF_OPEN probe |
| Cache too aggressive | Lower `CACHE_TTL` env var or call `fetch_clear_cache` |

---

## 📄 License

MIT License — Free for personal and commercial use.

---

<p align="center">
  <strong>🦉 Built for Linux Ubuntu. Free-tier access. No limits.</strong>
</p>
