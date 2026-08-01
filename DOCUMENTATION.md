# 🦉 OWL-AGENT v4.2 — Complete Documentation & AI Integration Guide

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Installation](#installation)
4. [CLI Reference](#cli-reference)
5. [Python API Reference](#python-api-reference)
6. [AI Tool Integrations](#ai-tool-integrations)
7. [Configuration](#configuration)
8. [Advanced Usage](#advanced-usage)
9. [Troubleshooting](#troubleshooting)

---

## Executive Summary

OWL-AGENT v4.2 is a **production-grade, self-optimising HTTP client** that combines:

- **50+ proxy sources** via ProxyBroker2
- **Quality scoring** (weighted success/latency metrics)
- **Adaptive rate limiting** (per-domain dynamic adjustment)
- **Redis state sharing** (optional persistence across restarts)
- **curl_cffi Chrome fingerprinting** (bypasses TLS detection)
- **Retry-After parsing** (polite backoff compliance)
- **Circuit breaker** (stops hammering dead endpoints)
- **Headless browser** (JavaScript SPA rendering)
- **LRU cache** (memory + disk persistence)
- **Request deduplication** (in-flight coalescing)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      USER LAYER                             │
│  OpenCode | Cline | Cursor | Warp | Claude Code | Codex    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   UNIFIED API                               │
│  CLI (run.sh) | Python Class | MCP Server | HTTP API        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 RESILIENT CLIENT                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │  Cache  │ │  Dedup  │ │ Limiter │ │ Breaker │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ Scorer  │ │  Proxy  │ │ Redis   │ │ curl_   │          │
│  │         │ │  Pool   │ │ Store   │ │ cffi    │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               EXTERNAL DEPENDENCIES                        │
│  ProxyBroker2 | LitProxy | agent-browser | aiohttp         │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Python 3.9+
- pip

### Quick Install

```bash
# Clone or download OWL-AGENT
cd ~/.owl-agent

# Install Python dependencies
pip install proxybroker2 litproxy resilient-httpx circuitbreaker curl_cffi httpx aiohttp aiofiles redis

# Make scripts executable
chmod +x proxy_defense.py run.sh
```

### Full Installation

```bash
# Create directory structure
mkdir -p ~/.owl-agent/cache/http ~/.owl-agent/config

# Install all dependencies
pip install proxybroker2 litproxy resilient-httpx circuitbreaker curl_cffi httpx aiohttp aiofiles redis

# Verify installation
python3 ~/.owl-agent/proxy_defense.py
```

---

## CLI Reference

### Basic Commands

```bash
# Fetch a URL
~/.owl-agent/run.sh fetch https://api.github.com/users/octocat

# Show proxy pool statistics
~/.owl-agent/run.sh stats

# Run test request
~/.owl-agent/run.sh test

# Start HTTP API server
~/.owl-agent/run.sh serve
```

### Options

```bash
# Use curl_cffi for Chrome fingerprinting
~/.owl-agent/run.sh fetch --curl-cffi https://httpbin.org/get

# Enable Redis state sharing
~/.owl-agent/run.sh fetch --redis https://httpbin.org/get

# Filter proxies by country
~/.owl-agent/run.sh fetch --countries US,GB https://httpbin.org/get
```

### HTTP API Server

Start the server on port 8420:

```bash
~/.owl-agent/run.sh serve
```

Endpoints:
- `GET /fetch?url=<url>` - Fetch a URL
- `GET /stats` - Get proxy pool statistics

---

## Python API Reference

### Basic Usage

```python
import asyncio
from proxy_defense import ResilientClient

async def main():
    # Create client with default settings
    async with ResilientClient() as client:
        resp = await client.request("GET", "https://api.github.com/users/octocat")
        print(f"Status: {resp.status}")
        print(f"Content: {resp.content.decode()}")

asyncio.run(main())
```

### Advanced Configuration

```python
import asyncio
from proxy_defense import ResilientClient

async def main():
    async with ResilientClient(
        cache_ttl=600,           # Cache TTL in seconds
        rate_limit=2.0,          # Requests per second
        max_retries=5,           # Max retry attempts
        use_curl_cffi=True,      # Use Chrome fingerprinting
        countries=["US", "GB"],  # Country filter
        use_redis=True,          # Enable Redis
        redis_url="redis://localhost:6379"
    ) as client:
        resp = await client.request("GET", "https://httpbin.org/get")
        print(f"Status: {resp.status}")

asyncio.run(main())
```

### Browser Mode (JavaScript Rendering)

```python
async def fetch_with_browser():
    async with ResilientClient() as client:
        resp = await client.request(
            "GET",
            "https://spa-site.com",
            browser=True,
            wait_for="#content",
            timeout=60
        )
        print(f"Status: {resp.status}")
        print(f"Content: {resp.content.decode()[:500]}")
```

### Get Statistics

```python
async def get_stats():
    async with ResilientClient() as client:
        stats = await client.get_stats()
        print(f"Total proxies: {stats['proxies_total']}")
        print(f"Healthy proxies: {stats['proxies_healthy']}")
        print(f"Quality scores: {stats['scores']}")
        print(f"Adaptive rates: {stats['rates']}")
```

---

## AI Tool Integrations

### 1. OpenCode

Add to your OpenCode skills directory:

```bash
# Copy skill file
cp ~/.owl-agent/owl-agent.skill.json ~/.opencode/skills/

# Usage in OpenCode
> owl-agent fetch https://api.github.com/users/octocat
> owl-agent stats
```

### 2. Cline (MCP Server)

Add to your Cline MCP configuration:

```json
{
  "mcpServers": {
    "owl-agent": {
      "command": "python3",
      "args": ["~/.owl-agent/mcp-server.py"],
      "env": {}
    }
  }
}
```

Available MCP Tools:
- `owl_fetch` - Fetch a URL
- `owl_stats` - Get proxy statistics
- `owl_fetch_browser` - Fetch with JS rendering

### 3. Cursor Commands

Add to your Cursor commands:

```json
{
  "owl-fetch": {
    "command": "~/.owl-agent/run.sh fetch",
    "description": "Fetch URL via OWL-AGENT",
    "shortcut": "Cmd+Shift+O"
  }
}
```

### 4. Warp Agent

Add to your Warp agents:

```bash
# Copy agent config
cp ~/.owl-agent/warp-agent.yaml ~/.warp/agents/
```

Natural language triggers:
- "fetch <url>"
- "scrape <url>"
- "get proxy stats"

### 5. Claude Code

Add as a custom skill:

```bash
# Create skill directory
mkdir -p ~/.claude/skills/owl-agent

# Copy files
cp ~/.owl-agent/proxy_defense.py ~/.claude/skills/owl-agent/
cp ~/.owl-agent/run.sh ~/.claude/skills/owl-agent/

# Usage in Claude Code
> Use OWL-AGENT to fetch https://api.github.com/users/octocat
```

### 6. Codex CLI

Add as a custom tool:

```bash
# Create alias
alias owl-agent="~/.owl-agent/run.sh"

# Usage
owl-agent fetch https://httpbin.org/get
owl-agent stats
```

### 7. Hermes Agent

Add to Hermes skills:

```bash
# Create skill directory
mkdir -p ~/.hermes/skills/owl-agent

# Copy files
cp ~/.owl-agent/proxy_defense.py ~/.hermes/skills/owl-agent/

# Register in Hermes
hermes skill add owl-agent
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
```

### Config File

Create `~/.owl-agent/config/settings.json`:

```json
{
  "version": "4.2.0",
  "cache_ttl": 300,
  "rate_limit": 1.0,
  "max_retries": 3,
  "use_curl_cffi": true,
  "countries": ["US", "GB", "DE", "FR", "CA"],
  "redis": {
    "enabled": false,
    "url": "redis://localhost:6379"
  },
  "circuit_breaker": {
    "failure_threshold": 5,
    "recovery_timeout": 30
  }
}
```

---

## Advanced Usage

### Custom Proxy Sources

Extend the proxy discovery with custom sources:

```python
from proxy_defense import ProxyPoolManager

class CustomProxyPool(ProxyPoolManager):
    async def _discovery_loop(self):
        # Add custom proxy sources
        async for proxy in self._broker.find(...):
            # Custom logic here
            pass
```

### Custom Quality Scoring

Override the quality scorer:

```python
from proxy_defense import QualityScorer

class CustomScorer(QualityScorer):
    def update(self, proxy_url, success, latency_ms):
        # Custom scoring logic
        super().update(proxy_url, success, latency_ms)
```

### Middleware Pattern

Add request/response middleware:

```python
async def logging_middleware(client, request):
    print(f"Request: {request.method} {request.url}")
    response = await request()
    print(f"Response: {response.status}")
    return response
```

---

## Troubleshooting

### Common Issues

1. **Proxy discovery fails**
   - Check internet connection
   - Verify proxybroker2 is installed: `pip show proxybroker2`
   - Check logs for specific errors

2. **Redis connection fails**
   - Ensure Redis is running: `redis-cli ping`
   - Check Redis URL configuration
   - Redis is optional - system falls back to memory

3. **curl_cffi not available**
   - Install: `pip install curl_cffi`
   - Falls back to httpx if not available

4. **agent-browser not found**
   - Install: `npx skills add vercel-labs/agent-browser`
   - Or use httpx mode instead

### Debug Mode

```bash
# Enable debug logging
export OWL_LOG_LEVEL=DEBUG
~/.owl-agent/run.sh test
```

### Performance Tuning

```python
# Optimize for high throughput
async with ResilientClient(
    rate_limit=5.0,           # Higher rate limit
    max_retries=2,            # Faster failure detection
    cache_ttl=600,            # Longer cache
    countries=["US"]          # Focus on specific region
) as client:
    pass
```

---

## License

MIT License

## Support

- GitHub: https://github.com/owl-agent/owl-agent
- Issues: https://github.com/owl-agent/owl-agent/issues
- Documentation: https://docs.owl-agent.dev
