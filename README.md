# 🦉 OWL-AGENT v4.5

**The Self-Optimising Scraping Engine with Advanced ML & Self-Healing Plugins**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-4.5.0-green.svg)](https://github.com/owl-agent/owl-agent)

---

## Quick Start

```bash
# Install
curl -sSL https://raw.githubusercontent.com/your-org/owl-agent/main/install.sh | bash

# Start server
~/.owl-agent/run.sh server --ab-test --ml --ml-model auto

# Fetch a URL
~/.owl-agent/run.sh fetch https://api.github.com/users/octocat

# Check stats
~/.owl-agent/run.sh stats
```

---

## Development (Makefile)

When working from a checkout (no `~/.owl-agent` install needed):

```bash
make setup         # create venv/ and install Python dependencies
make test          # run the full pytest suite
make server        # start the HTTP API server (binds 0.0.0.0, honors $PORT)
make fetch URL=https://example.com   # one-shot fetch via the running server
make stats         # show proxy pool stats
make go-test       # run Go tests for the https_proxy Go port
make go-build      # build the Go proxy binaries (prox5 + https_proxy_go)
make build-proxies # build all proxy integrations (needs Go 1.22+ and Rust 1.70+)
make lint          # ruff lint (Python)
make help          # list all targets
```

`make server` is equivalent to `bash run.sh server --host 0.0.0.0 --api-port $PORT`.

### Install as a Python package

OWL-AGENT is also a proper Python package (`pyproject.toml`, flat layout):

```bash
make install                 # pip install -e . into venv/
# or: pip install .          # anywhere — installs the owl-server console command
make wheel                   # build a distributable wheel into dist/
```

Once installed, start the server with the console script:

```bash
owl-server --host 0.0.0.0 --api-port 60000
```

The package installs `owl_server`, `proxy_defense`, `ml_models` and
`plugin_loader` as top-level importable modules (same flat layout as the repo,
so existing imports keep working). `mcp-server.py` is intentionally not
packaged (hyphenated filename) — run it as a plain script: `python mcp-server.py`.

---

## Features

| Feature | Description |
|---------|-------------|
| 🔀 **50+ Proxy Sources** | Automatic proxy discovery via ProxyBroker2 |
| 📊 **Quality Scoring** | Weighted metrics for optimal proxy selection |
| ⚡ **Adaptive Rate Limiting** | Dynamic per-domain request adjustment |
| 🧠 **Advanced ML** | XGBoost/MLP/Logistic auto-select with cross-validation |
| 🔌 **Self-Healing Plugins** | Auto-discovery, hot-reload, error isolation |
| 🧪 **A/B Testing** | Compare proxy strategies per domain |
| 💾 **Redis State Sharing** | Persistent state across restarts (optional) |
| 🌐 **Chrome Fingerprinting** | curl_cffi TLS handshake bypass |
| 🔄 **Retry-After Parsing** | Polite backoff compliance |
| 🛡️ **Circuit Breaker** | Stops hammering dead endpoints |
| 🎭 **Headless Browser** | JavaScript SPA rendering |
| 📦 **LRU Cache** | Memory + disk persistence |
| 🔗 **Request Deduplication** | In-flight coalescing |

---

## Installation

### Prerequisites

- Python 3.10+
- pip

### Quick Install

```bash
curl -sSL https://raw.githubusercontent.com/your-org/owl-agent/main/install.sh | bash
```

### Manual Install

```bash
# Create directory structure
mkdir -p ~/.owl-agent/{cache/http,cache/models,config,plugins}

# Install Python dependencies
pip install httpx[socks] aiohttp aiofiles proxybroker2 resilient-httpx \
    circuitbreaker curl_cffi redis prometheus-client \
    scikit-learn numpy xgboost joblib watchdog

# Copy files
cp proxy_defense.py ml_models.py plugin_loader.py owl_server.py ~/.owl-agent/
cp run.sh ~/.owl-agent/
chmod +x ~/.owl-agent/run.sh
```

### Verify Installation

```bash
~/.owl-agent/run.sh stats
```

---

## Usage

### CLI Commands

```bash
# Start HTTP API server
~/.owl-agent/run.sh server --ab-test --ml --ml-model auto

# Fetch a URL
~/.owl-agent/run.sh fetch https://api.github.com/users/octocat

# Show proxy pool statistics
~/.owl-agent/run.sh stats

# Quick health check
~/.owl-agent/run.sh health
```

### Server Options

```bash
~/.owl-agent/run.sh server \
    --ab-test           # Enable A/B testing
    --ml                # Enable ML predictor
    --ml-model auto     # ML model: auto, logistic, xgboost, mlp
    --plugin-dir ~/.owl-agent/plugins  # Plugin directory
    --no-curl-cffi      # Disable curl_cffi
    --redis             # Enable Redis state sharing
```

### Python API

```python
import asyncio
from proxy_defense import ResilientClient

async def main():
    async with ResilientClient(
        use_curl_cffi=True,
        countries=["US", "GB"],
        enable_ab_test=True,
        enable_ml=True,
        ml_model="auto",
        plugin_dir="~/.owl-agent/plugins"
    ) as client:
        resp = await client.request("GET", "https://api.github.com/users/octocat")
        print(f"Status: {resp.status}")
        print(f"Content: {resp.content.decode()[:100]}")

asyncio.run(main())
```

### HTTP API Server

Start the server on port 60000:

```bash
~/.owl-agent/run.sh server
```

Endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/fetch` | Fetch a URL through the proxy pool |
| POST | `/browser` | Fetch via agent-browser (JS rendering) |
| GET | `/health` | Health check |
| GET | `/stats` | Detailed proxy pool and ML stats |
| GET | `/metrics` | Prometheus metrics |

#### POST /fetch

**Request:**

```json
{
    "url": "https://example.com",
    "method": "GET",
    "headers": {},
    "browser": false,
    "timeout": 30
}
```

**Response:**

```json
{
    "status": 200,
    "content": "<!DOCTYPE html>...",
    "headers": {"Content-Type": "text/html"},
    "latency_seconds": 1.234,
    "cached": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | int | HTTP status code |
| `content` | string | Response body |
| `headers` | object | Response headers |
| `latency_seconds` | float | Request duration |
| `cached` | bool | Whether response was served from cache |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OWL-AGENT v4.5 Stack                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     PLUGIN SYSTEM (v4.5)                             │  │
│  │  • Auto-discovery from ~/.owl-agent/plugins/                         │  │
│  │  • Hot-reload on file change                                         │  │
│  │  • Self-healing: disable after 3 failures                            │  │
│  │  • Hooks: on_request, on_response, on_error, on_start, on_complete  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     A/B TESTING ENGINE                                │  │
│  │  • Multiple strategies per domain (best-score, random, round-robin)  │  │
│  │  • Track success rates per strategy                                  │  │
│  │  • Auto-switch to best strategy based on statistical significance    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                  ML PREDICTOR (v4.4)                                 │  │
│  │  • XGBoost / MLP / Logistic auto-select via cross-validation        │  │
│  │  • 12-feature vector (latency, success rate, protocol, country...)   │  │
│  │  • Online training (incrementally on each request)                   │  │
│  │  • Model persistence via joblib                                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      RESILIENTCLIENT CORE                            │  │
│  │  • Caching, dedup, rate limiting, circuit breaker, proxy pool       │  │
│  │  • Plugin hook integration                                           │  │
│  │  • A/B test and ML predictor integration                             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Plugin Authoring Guide

### Plugin Directory

Plugins live in `~/.owl-agent/plugins/`. Each `.py` file is a plugin.

### Available Hooks

| Hook | Signature | When Called |
|------|-----------|------------|
| `on_start` | `def on_start(method, url, domain, **kw)` | Before any request attempt |
| `on_request` | `def on_request(method, url, proxy, attempt, **kw)` | Before each proxy attempt |
| `on_response` | `def on_response(response, **kw)` | After successful response |
| `on_error` | `def on_error(error, attempt, url, **kw)` | On request failure |
| `on_complete` | `def on_complete(url, status, latency_ms, **kw)` | After request completes |

### Example Plugin

```python
# ~/.owl-agent/plugins/my_logger.py
"""Logs all requests with timing information."""
import logging

logger = logging.getLogger("owl-agent.plugin.my_logger")

def on_request(method, url, **kwargs):
    logger.info(f"Fetching {method} {url}")

def on_response(response, **kwargs):
    logger.info(f"Got status {response.status}")

def on_error(error, attempt, url, **kwargs):
    logger.warning(f"Error on {url} (attempt {attempt}): {error}")
```

### Hot-Reload

Edit any plugin file and changes take effect within seconds (no restart needed).

### Self-Healing

If a plugin fails to load 3 times, it's automatically disabled. Check logs for details.

### Disable/Enable Plugins

```python
from plugin_loader import PluginLoader
loader = PluginLoader("~/.owl-agent/plugins")
loader.disable_plugin("my_logger")
loader.enable_plugin("my_logger")
```

---

## Configuration

### Environment Variables

```bash
# Proxy settings
export OWL_PROXY_COUNTRIES="US,GB,DE,FR"
export OWL_PROXY_CACHE_SIZE=100

# Rate limiting
export OWL_RATE_LIMIT=1.0
export OWL_MIN_RATE=0.1
export OWL_MAX_RATE=5.0

# Caching
export OWL_CACHE_TTL=300
export OWL_CACHE_DIR=~/.owl-agent/cache

# Redis (optional)
export OWL_REDIS_URL="redis://localhost:6379"
export OWL_REDIS_ENABLED=false

# Logging
export OWL_LOG_LEVEL=INFO

# Self-hosted proxy integrations (prox5 SOCKS5 server, madeye/https_proxy)
export OWL_EXTRA_PROXIES="socks5://127.0.0.1:42069,https://user:pass@proxy.example.com:443"
# …or the convenience aliases:
export OWL_PROX5_SOCKS5="127.0.0.1:42069"
export OWL_HTTPS_PROXY="https://user:pass@proxy.example.com:443"
```

> These variables are read at startup and act as **defaults** — explicit CLI
> flags and constructor arguments always take precedence.

### Config File

`~/.owl-agent/config/config.json`:

```json
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
```

---

## Proxy Integrations (prox5 & https_proxy)

OWL-AGENT can use **self-hosted proxy servers** as first-class pool entries —
run your own rotating SOCKS5 exit ([prox5](https://github.com/yunginnanet/prox5))
and/or a stealth HTTPS forward proxy ([https_proxy](https://github.com/madeye/https_proxy))
and wire them in with one env var. See [`proxies/README.md`](proxies/README.md).

```bash
# Build (needs Go 1.22+ and Rust 1.70+ on your machine)
bash proxies/build.sh

# Run prox5 (SOCKS5 on 127.0.0.1:42069)
bash run.sh prox5 -listen 127.0.0.1:42069 -file proxies.txt

# Point OWL-AGENT at them
bash run.sh server --extra-proxies "socks5://127.0.0.1:42069,https://user:pass@proxy.example.com:443"
```

| Variable | Effect |
|---|---|
| `OWL_EXTRA_PROXIES` | Comma-separated proxy URLs seeded into the pool |
| `OWL_PROX5_SOCKS5` | Convenience alias → adds a `socks5://` entry |
| `OWL_HTTPS_PROXY` | Convenience alias → adds an `https://` entry |

Seeded proxies are quality-scored like any other pool entry, so HTTPS traffic
tunnels through them via CONNECT instead of falling back to a direct connection.

---

## v4.3 → v4.5 Diff Patch

### New Files

| File | Purpose |
|------|---------|
| `ml_models.py` | AdvancedMLPredictor with XGBoost/MLP/Logistic |
| `plugin_loader.py` | Self-healing plugin auto-discovery and hot-reload |
| `plugins/example_logger.py` | Sample plugin |

### Modified Files

#### `proxy_defense.py`

```diff
+ # v4.4: Advanced ML models
+ try:
+     from ml_models import AdvancedMLPredictor, XGB_AVAILABLE
+ except ImportError:
+     AdvancedMLPredictor = None
+     XGB_AVAILABLE = False
+
+ # v4.5: Self-healing plugin loader
+ try:
+     from plugin_loader import PluginLoader
+ except ImportError:
+     PluginLoader = None

  class ResilientClient:
-     def __init__(self, ..., enable_ml: bool = False):
+     def __init__(self, ..., enable_ml: bool = False,
+                  ml_model: str = "auto",
+                  plugin_dir: str = "~/.owl-agent/plugins"):
          ...
+         # v4.5: Plugin loader
+         self.plugin_loader = PluginLoader(plugin_dir) if PluginLoader else None
+         self.plugin_manager = PluginManager(self.plugin_loader)
+
+         # v4.4: Advanced ML predictor
+         if self.enable_ml and AdvancedMLPredictor:
+             self.ml_predictor = AdvancedMLPredictor(model_type=ml_model)

  class QualityScorer:
+     def get_avg_latency(self, proxy_url: str, window: int = 10) -> float:
+         """Public API for ML predictor."""
+         history = self._history.get(proxy_url)
+         if not history:
+             return 500.0
+         recent = history[-window:]
+         return sum(recent) / len(recent) if recent else 500.0

  class PluginManager:
-     def __init__(self):
+     def __init__(self, plugin_loader=None):
+         self._plugin_loader = plugin_loader

-     async def run_hooks(self, hook_type, *args, **kwargs):
-         for hook in self._hooks.get(hook_type, []):
+     def _get_all_hooks(self, hook_type):
+         """Merge static hooks with dynamic hooks from PluginLoader."""
+         hooks = list(self._hooks.get(hook_type, []))
+         if self._plugin_loader:
+             hooks.extend(self._plugin_loader.get_hooks(hook_type))
+         return hooks
+
+     async def run_hooks(self, hook_type, *args, **kwargs):
+         for hook in self._get_all_hooks(hook_type):
              ...

  class ProxyPoolManager:
+     def __init__(self, ...):
+         self._url_map: Dict[str, ProxyEntry] = {}  # O(1) lookup

+     def get_entry(self, url: str) -> Optional[ProxyEntry]:
+         """O(1) dict lookup instead of O(n) scan."""
+         return self._url_map.get(url)
```

#### `owl_server.py`

```diff
+     parser.add_argument("--ml-model", default="auto",
+                         choices=["auto", "logistic", "xgboost", "mlp"])
+     parser.add_argument("--plugin-dir", default="~/.owl-agent/plugins")
```

---

## Competitive Advantages

| Tool | OWL-AGENT Advantage |
|------|---------------------|
| OpenCode | Adds self-healing proxies + ML selection |
| Cline | Brings 50+ proxy sources + plugin system |
| Cursor | Adds adaptive rate limiting + A/B testing |
| Warp | Drop-in HTTP client with advanced ML |
| Codebuff | Adds quality scoring + advanced ML |
| Claude Code | Supports SOCKS5 + curl_cffi + plugins |
| Codex | Has LRU + disk cache + model persistence |
| Antigravity | Adds country filtering + feature engineering |
| Kiro-CLI | Integrates agent-browser + hot-reload |
| Hermes-Agent | Adds circuit breaker + self-healing |

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Support

- **GitHub**: https://github.com/owl-agent/owl-agent
- **Issues**: https://github.com/owl-agent/owl-agent/issues
- **Documentation**: https://docs.owl-agent.dev

---

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) first.

---

## Acknowledgments

- ProxyBroker2 for proxy discovery
- LitProxy for proxy rotation
- curl_cffi for Chrome fingerprinting
- Resilient-HTTPX for retry logic
- scikit-learn for ML models
- XGBoost for gradient boosting
