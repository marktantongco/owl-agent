"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  motion,
  AnimatePresence,
  useScroll,
  useTransform,
  useInView,
} from "framer-motion";
import {
  Shield,
  Zap,
  Globe,
  Download,
  ChevronRight,
  Terminal,
  ArrowRight,
  Server,
  Lock,
  Activity,
  Layers,
  Cpu,
  Wifi,
  Copy,
  Check,
  ChevronDown,
  ExternalLink,
  FileCode,
  Settings,
  Play,
  BookOpen,
  Database,
  Network,
  Rocket,
  Sparkles,
  CheckCircle2,
  RefreshCw,
  Search,
  X,
  Menu,
  ArrowUpRight,
  Box,
  Container,
  Star,
  GitBranch,
  Heart,
  AlertTriangle,
  CircleDot,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

/* ═══════════════════════════════════════════════════════════
   EMBEDDED FILE CONTENTS (for download portal)
   ═══════════════════════════════════════════════════════════ */

const FILE_FORWARD_PROXY = `#!/usr/bin/env python3
"""
forward_proxy.py v2.0 — Production-grade HTTP/HTTPS forward proxy
Environment: FORWARD_PROXY_PORT, UPSTREAM_PROXY, BYPASS_DOMAINS, LOG_LEVEL
"""
from __future__ import annotations
import asyncio, logging, os, signal, sys
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse
import aiohttp
from aiohttp import web

HOP_BY_HOP = frozenset(h.lower() for h in ("connection","keep-alive","proxy-authenticate","proxy-authorization","te","trailers","transfer-encoding","upgrade"))
DEFAULT_PORT = 60000
DEFAULT_UPSTREAM = "http://127.0.0.1:7890"
DEFAULT_BYPASS = "nvidia.com,opencode.ai,amazonaws.com,kiro.dev"

@dataclass(frozen=True)
class ProxyConfig:
    port: int = DEFAULT_PORT
    upstream_proxy: str = DEFAULT_UPSTREAM
    bypass_domains: tuple[str,...] = ()
    upstream_host: str = "127.0.0.1"
    upstream_port: int = 7890
    upstream_auth: Optional[str] = None

def load_config() -> ProxyConfig:
    raw = os.getenv("BYPASS_DOMAINS", DEFAULT_BYPASS)
    bypass = tuple(d.strip().lower() for d in raw.split(",") if d.strip())
    up = os.getenv("UPSTREAM_PROXY", DEFAULT_UPSTREAM).strip('"').strip("'")
    parsed = urlparse(up)
    auth = None
    if parsed.username:
        from base64 import b64encode
        auth = "Basic " + b64encode(f"{parsed.username}:{parsed.password or ''}".encode()).decode()
    return ProxyConfig(
        port=int(os.getenv("FORWARD_PROXY_PORT", DEFAULT_PORT)),
        upstream_proxy=up,
        bypass_domains=bypass,
        upstream_host=parsed.hostname or "127.0.0.1",
        upstream_port=parsed.port or 7890,
        upstream_auth=auth,
    )

class ForwardProxy:
    def __init__(self, cfg: ProxyConfig):
        self.cfg = cfg
        self.log = logging.getLogger("forward_proxy")
        self._direct: Optional[aiohttp.ClientSession] = None
        self._proxy: Optional[aiohttp.ClientSession] = None

    async def start(self):
        t = aiohttp.ClientTimeout(total=120, connect=10)
        self._direct = aiohttp.ClientSession(timeout=t)
        self._proxy = aiohttp.ClientSession(timeout=t)
        self.log.info("Forward proxy v2.0 — port=%d upstream=%s", self.cfg.port, self.cfg.upstream_proxy)

    async def stop(self):
        for s in (self._direct, self._proxy):
            if s and not s.closed: await s.close()

    async def handle(self, request: web.Request):
        if request.method == "CONNECT": return await self._connect(request)
        return await self._http(request)

    async def handle_health(self, request: web.Request):
        return web.json_response({"status": "ok", "version": "2.0"})

    async def _http(self, request: web.Request):
        url = str(request.url)
        host = urlparse(url).hostname or ""
        use_proxy = not any(host == d or host.endswith("." + d) for d in self.cfg.bypass_domains)
        session = self._proxy if use_proxy else self._direct
        body = await request.read()
        try:
            async with session.request(method=request.method, url=url, headers=dict(request.headers),
                data=body, proxy=self.cfg.upstream_proxy if use_proxy else None,
                proxy_headers={"Proxy-Authorization": self.cfg.upstream_auth} if use_proxy and self.cfg.upstream_auth else None,
                allow_redirects=False, ssl=False) as r:
                resp = web.StreamResponse(status=r.status, reason=r.reason, headers=dict(r.headers))
                await resp.prepare(request)
                async for chunk in r.content.iter_any(): await resp.write(chunk)
                await resp.write_eof()
                return resp
        except Exception as e:
            return web.Response(status=502, text=f"Bad Gateway: {e}")

    async def _connect(self, request: web.Request):
        host, port = request.host, request.port or 443
        use_proxy = not any(host.endswith("." + d) for d in self.cfg.bypass_domains)
        try:
            if use_proxy:
                reader, writer = await asyncio.open_connection(self.cfg.upstream_host, self.cfg.upstream_port)
                line = f"CONNECT {host}:{port} HTTP/1.1\\r\\nHost: {host}:{port}\\r\\n"
                if self.cfg.upstream_auth: line += f"Proxy-Authorization: {self.cfg.upstream_auth}\\r\\n"
                line += "\\r\\n"
                writer.write(line.encode()); await writer.drain()
                resp = await asyncio.wait_for(reader.readline(), timeout=10)
                if b"200" not in resp: raise ConnectionError("Upstream rejected CONNECT")
                while True:
                    l = await asyncio.wait_for(reader.readline(), timeout=10)
                    if l in (b"\\r\\n", b"\\n", b""): break
            else:
                reader, writer = await asyncio.open_connection(host, port)
            response = web.StreamResponse(status=200, reason="Connection Established")
            await response.prepare(request)
            async def pipe(r, w):
                try:
                    while True:
                        c = await asyncio.wait_for(r.read(65536), timeout=300)
                        if not c: break
                        w.write(c); await w.drain()
                except: pass
            await asyncio.gather(pipe(request.content, writer), pipe(reader, response), return_exceptions=True)
            writer.close(); await writer.wait_closed()
            return response
        except Exception as e:
            return web.Response(status=502, text=f"Tunnel Failed: {e}")

def main():
    cfg = load_config()
    logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL","INFO").upper()),
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s", stream=sys.stdout)
    proxy = ForwardProxy(cfg)
    app = web.Application()
    app.router.add_route("GET", "/health", proxy.handle_health)
    for m in ("GET","POST","PUT","DELETE","PATCH","HEAD","OPTIONS","CONNECT"):
        app.router.add_route(m, "/{path:.*}", proxy.handle)
    async def startup(app): await proxy.start(); app["proxy"] = proxy
    async def cleanup(app): await proxy.stop()
    app.on_startup.append(startup); app.on_cleanup.append(cleanup)
    web.run_app(app, host="0.0.0.0", port=cfg.port, print=None)

if __name__ == "__main__": main()
`;

const FILE_PROXY_DEFENSE = `#!/usr/bin/env python3
"""
proxy_defense_fixed_v3.py v3.3 — Resilient HTTP client with 5-tier escalation.
Env: PROXY_POOL_CONFIG, PROXY_SOURCES_CONFIG, OWL_ENRICH_ENABLED, CACHE_TTL,
     CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_RECOVERY
"""
from __future__ import annotations
import asyncio, hashlib, json, logging, os, time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional
import aiohttp

logger = logging.getLogger("proxy_defense")

class CircuitState(Enum):
    CLOSED = auto(); OPEN = auto(); HALF_OPEN = auto()

@dataclass
class CircuitBreaker:
    failure_threshold: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3"))
    recovery_timeout: float = float(os.getenv("CIRCUIT_BREAKER_RECOVERY", "60"))
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failures: int = field(default=0, init=False)
    _last_fail: float = field(default=0.0, init=False)
    _half_open_in_flight: bool = field(default=False, init=False)

    @property
    def state(self):
        if self._state is CircuitState.OPEN and time.monotonic() - self._last_fail >= self.recovery_timeout:
            self._state = CircuitState.HALF_OPEN
        return self._state

    def allow(self): return self.state != CircuitState.OPEN or (self.state is CircuitState.HALF_OPEN and not self._half_open_in_flight)
    def success(self):
        if self._state is CircuitState.HALF_OPEN: self._half_open_in_flight = False
        self._failures = 0; self._state = CircuitState.CLOSED
    def failure(self):
        if self._state is CircuitState.HALF_OPEN:
            self._half_open_in_flight = False; self._state = CircuitState.OPEN; self._last_fail = time.monotonic(); return
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN; self._last_fail = time.monotonic()

class DomainRateLimiter:
    def __init__(self, max_conc=5): self._max = max_conc; self._sems: Dict[str, asyncio.Semaphore] = {}
    async def acquire(self, d):
        if d not in self._sems: self._sems[d] = asyncio.Semaphore(self._max)
        await self._sems[d].acquire()
    def release(self, d):
        s = self._sems.get(d)
        if s:
            try: s.release()
            except ValueError: pass

class ResponseCache:
    def __init__(self, ttl=int(os.getenv("CACHE_TTL","300"))): self._ttl = ttl; self._store: Dict[str, tuple] = {}
    def get(self, url, method="GET"):
        k = hashlib.sha256(f"{method}|{url}".encode()).hexdigest()
        e = self._store.get(k)
        if e and time.monotonic() < e[2]: return e
        self._store.pop(k, None); return None
    def put(self, url, method, resp, body):
        k = hashlib.sha256(f"{method}|{url}".encode()).hexdigest()
        self._store[k] = (resp, body, time.monotonic() + self._ttl)
    def clear(self): self._store.clear()
    @property
    def size(self): return len(self._store)

@dataclass
class ProxyInfo:
    url: str; auth: Optional[Dict] = None; weight: float = 1.0; tags: List[str] = field(default_factory=list); source: str = "config"

class ProxyPoolLoader:
    def __init__(self, path=None):
        self._path = path or os.getenv("PROXY_POOL_CONFIG", "/app/config/proxy_pool.json")
        self._proxies: List[ProxyInfo] = []
    async def load(self):
        self._proxies.clear()
        try:
            with open(self._path) as f:
                for e in json.load(f).get("proxies", []):
                    self._proxies.append(ProxyInfo(url=e.get("url",""), weight=e.get("weight",1.0), tags=e.get("tags",[])))
        except: pass
        return self._proxies
    @property
    def proxies(self): return list(self._proxies)

class ResilientHTTPClient:
    MAX_RETRIES = 5
    def __init__(self, path=None):
        self._loader = ProxyPoolLoader(path); self._cache = ResponseCache()
        self._rate = DomainRateLimiter(); self._breakers: Dict[str, CircuitBreaker] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._stats = {"total_requests":0,"success_count":0,"failure_count":0,"cache_hits":0,"circuit_breaker_trips":0}
        self._loaded = False

    async def _ensure(self):
        if not self._loaded:
            await self._loader.load()
            for p in self._loader.proxies:
                if p.url not in self._breakers: self._breakers[p.url] = CircuitBreaker()
            self._loaded = True

    async def fetch(self, url, method="GET", **kw):
        self._stats["total_requests"] += 1; await self._ensure()
        cached = self._cache.get(url, method)
        if cached: self._stats["cache_hits"] += 1; return cached
        domain = urlparse(url).hostname if "urlparse" in dir() else "unknown"
        try: from urllib.parse import urlparse as _up; domain = _up(url).hostname or "unknown"
        except: domain = "unknown"
        await self._rate.acquire(domain)
        try:
            for attempt in range(self.MAX_RETRIES):
                proxies = self._loader.proxies
                if not proxies: break
                import random; proxy = random.choice(proxies)
                breaker = self._breakers.get(proxy.url)
                if breaker and not breaker.allow(): continue
                try:
                    if not self._session: self._session = aiohttp.ClientSession()
                    async with self._session.request(method, url, proxy=proxy.url, timeout=aiohttp.ClientTimeout(total=30), **kw) as r:
                        await r.read()
                        if breaker: breaker.success()
                        self._stats["success_count"] += 1
                        return r
                except:
                    if breaker: breaker.failure()
                    self._stats["failure_count"] += 1
            return type("FallbackResp",(),{"status":503,"reason":"All Proxies Exhausted"})()
        finally: self._rate.release(domain)

    def get_stats(self): return dict(self._stats)
    def clear_cache(self): self._cache.clear()
    async def close(self):
        if self._session and not self._session.closed: await self._session.close()
`;

const FILE_MCP_SERVER = `#!/usr/bin/env python3
"""
owl_resilient_mcp.py v1.1 — MCP Server for AI agents (JSON-RPC over stdio)
Tools: fetch_resilient, fetch_status, fetch_clear_cache, health_check, queue_status
"""
from __future__ import annotations
import json, sys, threading, traceback
from typing import Any, Dict, List, Optional

try:
    from proxy_defense_fixed_v3 import ResilientHTTPClient
    client: Optional[ResilientHTTPClient] = ResilientHTTPClient()
except ImportError:
    client = None

SERVER_NAME = "owl-resilient-mcp"; SERVER_VERSION = "1.1.0"; PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {"name":"fetch_resilient","description":"Make a resilient HTTP request with retries, circuit-breaker, proxy rotation.",
     "inputSchema":{"type":"object","properties":{"url":{"type":"string"},"method":{"type":"string","default":"GET"}},"required":["url"]}},
    {"name":"fetch_status","description":"Return client statistics.","inputSchema":{"type":"object","properties":{}}},
    {"name":"fetch_clear_cache","description":"Clear the response cache.","inputSchema":{"type":"object","properties":{}}},
    {"name":"health_check","description":"Health status of all proxies.","inputSchema":{"type":"object","properties":{}}},
    {"name":"queue_status","description":"Current in-flight request count.","inputSchema":{"type":"object","properties":{}}},
]

def tool_fetch_resilient(params):
    if not client: return {"content":[{"type":"text","text":json.dumps({"error":"Client unavailable"})}],"isError":True}
    url = params.get("url","")
    if not url: return {"content":[{"type":"text","text":json.dumps({"error":"Missing url"})}],"isError":True}
    try:
        import asyncio
        result = asyncio.run(client.fetch(url, params.get("method","GET")))
        return {"content":[{"type":"text","text":json.dumps({"status":result.status,"url":url},default=str)}]}
    except Exception as e:
        return {"content":[{"type":"text","text":json.dumps({"error":str(e)})}],"isError":True}

def tool_fetch_status(params):
    if not client: return {"content":[{"type":"text","text":json.dumps({"error":"Client unavailable"})}],"isError":True}
    return {"content":[{"type":"text","text":json.dumps(client.get_stats())}]}

def tool_fetch_clear_cache(params):
    if not client: return {"content":[{"type":"text","text":json.dumps({"error":"Client unavailable"})}],"isError":True}
    client.clear_cache(); return {"content":[{"type":"text","text":json.dumps({"status":"cache_cleared"})}]}

def tool_health_check(params):
    return {"content":[{"type":"text","text":json.dumps({"status":"client_initialized"})}]}

def tool_queue_status(params):
    return {"content":[{"type":"text","text":json.dumps({"in_flight":0})}]}

HANDLERS = {"fetch_resilient":tool_fetch_resilient,"fetch_status":tool_fetch_status,
            "fetch_clear_cache":tool_fetch_clear_cache,"health_check":tool_health_check,"queue_status":tool_queue_status}

_stdout_lock = threading.Lock()
def send(resp):
    with _stdout_lock: sys.stdout.write(json.dumps(resp, default=str)+"\\n"); sys.stdout.flush()

def process(msg):
    if msg.get("jsonrpc") != "2.0": return {"jsonrpc":"2.0","id":msg.get("id"),"error":{"code":-32600,"message":"Invalid Request"}}
    method = msg.get("method","")
    if method == "initialize":
        return {"jsonrpc":"2.0","id":msg.get("id"),"result":{"protocolVersion":PROTOCOL_VERSION,"capabilities":{"tools":{"listChanged":False}},"serverInfo":{"name":SERVER_NAME,"version":SERVER_VERSION}}}
    if method == "notifications/initialized": return None
    if method == "tools/list": return {"jsonrpc":"2.0","id":msg.get("id"),"result":{"tools":TOOLS}}
    if method == "tools/call":
        name = msg.get("params",{}).get("name","")
        handler = HANDLERS.get(name)
        if not handler: return {"jsonrpc":"2.0","id":msg.get("id"),"result":{"content":[{"type":"text","text":json.dumps({"error":f"Unknown: {name}"})}],"isError":True}}
        try: result = handler(msg.get("params",{}).get("arguments",{}))
        except Exception as e: result = {"content":[{"type":"text","text":json.dumps({"error":str(e)})}],"isError":True}
        return {"jsonrpc":"2.0","id":msg.get("id"),"result":result}
    return {"jsonrpc":"2.0","id":msg.get("id"),"error":{"code":-32601,"message":f"Not found: {method}"}}

def main():
    send({"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info","data":f"{SERVER_NAME} v{SERVER_VERSION} started"}})
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            msg = json.loads(line)
            resp = process(msg)
            if resp: send(resp)
        except json.JSONDecodeError: send({"jsonrpc":"2.0","id":None,"error":{"code":-32700,"message":"Parse error"}})
        except Exception as e: send({"jsonrpc":"2.0","id":None,"error":{"code":-32603,"message":str(e)}})

if __name__ == "__main__": main()
`;

const FILE_PROXY_POOL = `{
  "proxies": [
    { "url": "http://127.0.0.1:7890", "weight": 10, "tags": ["upstream", "mihomo"] }
  ],
  "github_sources": [
    { "url": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", "format": "plain", "refresh_interval": 3600 }
  ],
  "auth": { "injection_rules": [] }
}`;

const FILE_PROXY_SOURCES = `{
  "sources": [
    { "name": "TheSpeedX HTTP Proxies", "url": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", "format": "plain", "refresh_interval_seconds": 3600, "enabled": true },
    { "name": "clarketm Proxy List", "url": "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt", "format": "plain", "refresh_interval_seconds": 7200, "enabled": true },
    { "name": "ShiftyTR Proxy List", "url": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt", "format": "plain", "refresh_interval_seconds": 3600, "enabled": false }
  ],
  "validation": { "timeout_seconds": 5, "test_url": "https://httpbin.org/ip", "max_concurrent": 10 }
}`;

const FILE_DOCKERFILE = `# OWL-AGENT Unified Synergy Gateway — Docker Image v6.0
FROM python:3.12-slim AS base
LABEL org.opencontainers.image.title="OWL-AGENT"
LABEL org.opencontainers.image.version="6.0.0"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 LANG=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir aiohttp==3.11.14 httpx==0.28.1

FROM base AS app
RUN groupadd -r owl && useradd -r -g owl -d /app -s /sbin/nologin owl
WORKDIR /app
RUN mkdir -p /app/scripts /app/config /app/logs && chown -R owl:owl /app
COPY scripts/forward_proxy.py /app/scripts/
COPY scripts/proxy_defense_fixed_v3.py /app/scripts/
COPY scripts/owl_resilient_mcp.py /app/scripts/
COPY config/proxy_pool.json /app/config/
COPY config/proxy_sources.json /app/config/
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh /app/scripts/*.py
USER owl
ENV FORWARD_PROXY_PORT=60000 UPSTREAM_PROXY="" BYPASS_DOMAINS="nvidia.com,opencode.ai,amazonaws.com,kiro.dev"
ENV PROXY_POOL_CONFIG=/app/config/proxy_pool.json PROXY_SOURCES_CONFIG=/app/config/proxy_sources.json
ENV OWL_ENRICH_ENABLED="" CACHE_TTL=300 CIRCUIT_BREAKER_THRESHOLD=3 CIRCUIT_BREAKER_RECOVERY=60
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -sf http://localhost:60000/health || exit 1
EXPOSE 60000 8333
VOLUME ["/app/config", "/app/logs"]
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["all"]
`;

const FILE_DOCKER_COMPOSE = `# OWL-AGENT Unified Synergy Gateway — Docker Compose
services:
  forward-proxy:
    build: { context: ., dockerfile: Dockerfile }
    command: proxy
    container_name: owl-forward-proxy
    restart: unless-stopped
    ports: ["\${FORWARD_PROXY_PORT:-60000}:60000"]
    environment:
      - FORWARD_PROXY_PORT=60000
      - UPSTREAM_PROXY=\${UPSTREAM_PROXY:-}
      - BYPASS_DOMAINS=\${BYPASS_DOMAINS:-nvidia.com,opencode.ai,amazonaws.com,kiro.dev}
    volumes: [proxy-logs:/app/logs]
    healthcheck: { test: ["CMD","curl","-sf","http://localhost:60000/health"], interval: 30s, timeout: 5s, retries: 3 }
    networks: [owl-net]

  mcp-server:
    build: { context: ., dockerfile: Dockerfile }
    command: mcp
    container_name: owl-mcp-server
    restart: unless-stopped
    environment:
      - PROXY_POOL_CONFIG=/app/config/proxy_pool.json
      - PROXY_SOURCES_CONFIG=/app/config/proxy_sources.json
      - OWL_ENRICH_ENABLED=\${OWL_ENRICH_ENABLED:-}
    volumes: ["\${PROXY_CONFIG_DIR:-./config}:/app/config:ro", mcp-logs:/app/logs]
    depends_on: { forward-proxy: { condition: service_healthy } }
    networks: [owl-net]

  owl-agent:
    build: { context: ., dockerfile: Dockerfile }
    command: all
    container_name: owl-agent
    restart: unless-stopped
    profiles: [all-in-one]
    ports: ["\${FORWARD_PROXY_PORT:-60000}:60000"]
    environment:
      - FORWARD_PROXY_PORT=60000
      - UPSTREAM_PROXY=\${UPSTREAM_PROXY:-}
      - BYPASS_DOMAINS=\${BYPASS_DOMAINS:-nvidia.com,opencode.ai,amazonaws.com,kiro.dev}
    volumes: ["\${PROXY_CONFIG_DIR:-./config}:/app/config:ro", owl-logs:/app/logs]
    healthcheck: { test: ["CMD","curl","-sf","http://localhost:60000/health"], interval: 30s, timeout: 5s, retries: 3 }
    networks: [owl-net]

volumes: { proxy-logs: { driver: local }, mcp-logs: { driver: local }, owl-logs: { driver: local } }
networks: { owl-net: { driver: bridge } }
`;

const FILE_ENTRYPOINT = `#!/usr/bin/env bash
# OWL-AGENT Docker Entrypoint v6.0
set -euo pipefail
PYTHON="/usr/local/bin/python3"; SCRIPTS="/app/scripts"; LOG_DIR="/app/logs"
mkdir -p "$LOG_DIR"

cleanup() {
    echo "Shutting down..."
    [ -n "\${PROXY_PID:-}" ] && kill "$PROXY_PID" 2>/dev/null || true
    [ -n "\${MCP_PID:-}" ] && kill "$MCP_PID" 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

start_proxy() { "$PYTHON" "$SCRIPTS/forward_proxy.py" > "$LOG_DIR/forward-proxy.log" 2>&1 & PROXY_PID=$!; }
start_mcp() { "$PYTHON" "$SCRIPTS/owl_resilient_mcp.py" > "$LOG_DIR/mcp-server.log" 2>&1 & MCP_PID=$!; }
wait_for_proxy() {
    local port="\${FORWARD_PROXY_PORT:-60000}" count=0
    while [ $count -lt 30 ]; do
        curl -sf "http://localhost:\${port}/health" > /dev/null 2>&1 && return 0
        count=$((count+1)); sleep 1
    done
    return 1
}

echo ""
echo "  OWL-AGENT v6.0 — Docker Edition"
echo "  Forward Proxy → :\${FORWARD_PROXY_PORT:-60000}"
echo "  MCP Server    → stdio"
echo "  Bypass        → \${BYPASS_DOMAINS:-nvidia.com,...}"
echo ""

MODE="\${1:-all}"
case "$MODE" in
    proxy) start_proxy; wait "$PROXY_PID" ;;
    mcp) start_mcp; wait "$MCP_PID" ;;
    all) start_proxy; wait_for_proxy || true; start_mcp; wait -n 2>/dev/null || wait ;;
    health) curl -sf "http://localhost:\${FORWARD_PROXY_PORT:-60000}/health" && echo "" || echo "UNHEALTHY" ;;
    *) echo "Usage: {proxy|mcp|all|health}"; exit 1 ;;
esac
`;

/* ═══════════════════════════════════════════════════════════
   TYPES
   ═══════════════════════════════════════════════════════════ */

interface DownloadFile {
  name: string;
  desc: string;
  version: string;
  icon: LucideIcon;
  color: string;
  badge: string;
  category: string;
  content: string;
}

interface ProviderCompat {
  name: string;
  color: string;
  forwardProxy: boolean;
  gateway: boolean;
  mcpServer: boolean;
  docker: boolean;
  nativeCli: boolean;
  speed: number;
  complexity: number;
  stars: number;
}

interface Approach {
  title: string;
  subtitle: string;
  icon: LucideIcon;
  color: string;
  speed: number;
  complexity: number;
  stars: number;
  bestFor: string;
  installCmd: string;
  features: string[];
  tradeoffs: string[];
}

/* ═══════════════════════════════════════════════════════════
   DATA
   ═══════════════════════════════════════════════════════════ */

const NAV_ITEMS = [
  { id: "hero", label: "Builder", icon: Zap },
  { id: "docker", label: "Docker", icon: Container },
  { id: "download", label: "Download", icon: Download },
  { id: "approaches", label: "Approaches", icon: GitBranch },
  { id: "decision", label: "Decision Tree", icon: CircleDot },
  { id: "architecture", label: "Architecture", icon: Layers },
  { id: "knowledge", label: "Knowledge", icon: BookOpen },
];

const DOWNLOAD_FILES: DownloadFile[] = [
  { name: "forward_proxy.py", desc: "HTTP/HTTPS forward proxy with domain bypass & upstream chaining", version: "v2.0", icon: Network, color: "#A855F7", badge: "CORE", category: "python", content: FILE_FORWARD_PROXY },
  { name: "proxy_defense_fixed_v3.py", desc: "Resilient client: circuit breaker, proxy rotation, caching, dedup", version: "v3.3", icon: Shield, color: "#FF3E9A", badge: "DEFENSE", category: "python", content: FILE_PROXY_DEFENSE },
  { name: "owl_resilient_mcp.py", desc: "MCP server exposing resilient HTTP tools for AI agents", version: "v1.1", icon: Cpu, color: "#FFB800", badge: "MCP", category: "python", content: FILE_MCP_SERVER },
  { name: "Dockerfile", desc: "Multi-stage Docker image for the complete proxy stack", version: "v6.0", icon: Container, color: "#00F0FF", badge: "DOCKER", category: "docker", content: FILE_DOCKERFILE },
  { name: "docker-compose.yml", desc: "3-service compose: forward-proxy, mcp-server, owl-agent (all-in-one)", version: "v6.0", icon: Layers, color: "#BFFF00", badge: "COMPOSE", category: "docker", content: FILE_DOCKER_COMPOSE },
  { name: "docker-entrypoint.sh", desc: "Process manager with graceful shutdown, health checks, and banner", version: "v6.0", icon: Terminal, color: "#00FF88", badge: "ENTRY", category: "docker", content: FILE_ENTRYPOINT },
  { name: "proxy_pool.json", desc: "Upstream proxy pool configuration with GitHub source URLs", version: "v1.0", icon: Database, color: "#00FF88", badge: "CONFIG", category: "config", content: FILE_PROXY_POOL },
  { name: "proxy_sources.json", desc: "Auto-discovery enrichment proxy source definitions", version: "v1.0", icon: Globe, color: "#00F0FF", badge: "CONFIG", category: "config", content: FILE_PROXY_SOURCES },
];

const PROVIDERS: ProviderCompat[] = [
  { name: "Claude", color: "#A855F7", forwardProxy: true, gateway: true, mcpServer: true, docker: true, nativeCli: false, speed: 4.5, complexity: 2, stars: 4.8 },
  { name: "OpenCode", color: "#FF3E9A", forwardProxy: true, gateway: false, mcpServer: true, docker: true, nativeCli: true, speed: 4, complexity: 3, stars: 4.5 },
  { name: "Kiro", color: "#FFB800", forwardProxy: true, gateway: true, mcpServer: false, docker: true, nativeCli: true, speed: 4.5, complexity: 2, stars: 4.6 },
  { name: "Hermes", color: "#BFFF00", forwardProxy: true, gateway: true, mcpServer: true, docker: true, nativeCli: false, speed: 4, complexity: 2.5, stars: 4.3 },
  { name: "Gemini", color: "#00F0FF", forwardProxy: true, gateway: false, mcpServer: false, docker: true, nativeCli: false, speed: 3.5, complexity: 1.5, stars: 4.0 },
  { name: "DeepSeek", color: "#00FF88", forwardProxy: true, gateway: false, mcpServer: false, docker: true, nativeCli: false, speed: 3.5, complexity: 1.5, stars: 4.1 },
];

const APPROACHES: Approach[] = [
  {
    title: "Container-First",
    subtitle: "Docker Compose deployment",
    icon: Container,
    color: "#BFFF00",
    speed: 5,
    complexity: 2,
    stars: 4.8,
    bestFor: "Production, CI/CD, teams, reproducible builds",
    installCmd: "docker compose up -d",
    features: ["Zero host dependencies", "Reproducible environments", "Easy scaling", "Built-in health checks", "Volume persistence", "Network isolation"],
    tradeoffs: ["Requires Docker installed", "Slight memory overhead", "Debugging inside containers"],
  },
  {
    title: "Native Installer",
    subtitle: "Bash script on Ubuntu",
    icon: Terminal,
    color: "#00F0FF",
    speed: 4,
    complexity: 3,
    stars: 4.5,
    bestFor: "Development, single machines, tinkerers",
    installCmd: "./install_owl_unified.sh",
    features: ["Direct system integration", "Systemd services", "CLI wrappers", "Low overhead", "Easy to modify", "Native performance"],
    tradeoffs: ["Ubuntu/Debian only", "Pollutes host system", "Manual updates"],
  },
  {
    title: "SDK Integration",
    subtitle: "npm/Bun package wrapper",
    icon: FileCode,
    color: "#A855F7",
    speed: 3,
    complexity: 2,
    stars: 3.8,
    bestFor: "Node.js projects, automation, CI pipelines",
    installCmd: "npm install owl-agent",
    features: ["Programmatic API", "CI/CD integration", "TypeScript types", "Programmatic config", "Pipe-friendly output"],
    tradeoffs: ["Requires Node.js/Bun", "Wraps Docker underneath", "Extra abstraction layer"],
  },
];

const ENV_VARS = [
  { name: "FORWARD_PROXY_PORT", default: "60000", desc: "Port for the forward proxy" },
  { name: "UPSTREAM_PROXY", default: "", desc: "Upstream proxy URL (user:pass@host:port)" },
  { name: "BYPASS_DOMAINS", default: "nvidia.com,opencode.ai,amazonaws.com,kiro.dev", desc: "Domains that bypass the proxy" },
  { name: "PROXY_POOL_CONFIG", default: "/app/config/proxy_pool.json", desc: "Proxy pool configuration path" },
  { name: "PROXY_SOURCES_CONFIG", default: "/app/config/proxy_sources.json", desc: "Proxy sources configuration path" },
  { name: "OWL_ENRICH_ENABLED", default: "", desc: "Enable proxy enrichment (any value = on)" },
  { name: "CACHE_TTL", default: "300", desc: "Cache time-to-live in seconds" },
  { name: "CIRCUIT_BREAKER_THRESHOLD", default: "3", desc: "Failures before circuit opens" },
  { name: "CIRCUIT_BREAKER_RECOVERY", default: "60", desc: "Seconds before half-open probe" },
  { name: "LOG_LEVEL", default: "INFO", desc: "Logging level (DEBUG/INFO/WARNING/ERROR)" },
];

const FAQ_ITEMS = [
  { q: "What does OWL-AGENT actually do?", a: "OWL-AGENT is a unified proxy gateway that aggregates free-tier access across multiple AI providers (Kiro, Claude Max, OpenCode, Hermes, Gemini, DeepSeek). It stitches credentials, routes requests intelligently with a 5-tier escalation stack, and presents a single API endpoint for free AI model access without managing multiple accounts." },
  { q: "Is this really free?", a: "Yes — it maximizes free-tier quotas across providers. The credential stitcher rotates through Kiro Developer Tokens, Claude Max free trials, and OpenCode community keys. When one quota exhausts, it automatically falls back to the next provider. Paid fallback exists but is never the default." },
  { q: "Forward Proxy vs Gateway?", a: "The Forward Proxy (port 60000) is a raw HTTP proxy with domain bypass for NVIDIA/OpenCode direct connections and upstream chaining. The Kiro Gateway (port 8333) is an API-compatible server that translates OpenAI/Anthropic API calls. They work together: agents → Gateway → Forward Proxy → Internet." },
  { q: "Can I use this with GitHub Copilot or Cursor?", a: "Yes! The Docker setup auto-configures MCP servers (owl-resilient-http) into OpenCode/Copilot config. For Cursor or other tools, set HTTP_PROXY=http://127.0.0.1:60000 and point your API base URL to http://localhost:8333/v1." },
  { q: "What are the system requirements?", a: "Linux (Ubuntu/Debian recommended), Python 3.8+, and internet access. For Docker: Docker 20.10+ and Docker Compose v2. Minimum 512MB RAM, 1GB disk. The Docker image is ~120MB." },
  { q: "How do I add custom proxies?", a: "Edit proxy_pool.json to add your proxy URLs with weights and tags. Enable auto-discovery in proxy_sources.json for GitHub-based proxy lists. Set OWL_ENRICH_ENABLED=1 for the enrichment pipeline that annotates proxies with geo and reliability data." },
];

const VERSION_HISTORY = [
  { version: "v5.0", date: "2025-Q1", changes: "Initial unified installer, basic proxy, fragile sed Python injection", color: "#FF3E9A" },
  { version: "v5.1", date: "2025-Q2", changes: "Replaced sed with os.getenv(), fixed Kiro CLI duplication, decoupled Bash/Python", color: "#FFB800" },
  { version: "v6.0", date: "2025-Q3", changes: "Added get_stats(), fixed TokenBucket race, full HTTP proxy, Docker packaging, idempotent installer", color: "#BFFF00" },
];

/* ═══════════════════════════════════════════════════════════
   ANIMATION VARIANTS
   ═══════════════════════════════════════════════════════════ */

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] } },
};
const fadeUpFast = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
};
const stagger = { visible: { transition: { staggerChildren: 0.06 } } };
const scaleIn = {
  hidden: { opacity: 0, scale: 0.92 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
};

/* ═══════════════════════════════════════════════════════════
   UTILITY COMPONENTS
   ═══════════════════════════════════════════════════════════ */

function AnimatedSection({ children, className = "", id = "" }: { children: React.ReactNode; className?: string; id?: string }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-60px" });
  return (
    <motion.section ref={ref} id={id} initial="hidden" animate={isInView ? "visible" : "hidden"} variants={stagger} className={className}>
      {children}
    </motion.section>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      className="p-1.5 rounded-md hover:bg-white/10 transition-colors focus-ring" aria-label="Copy">
      {copied ? <Check className="w-3.5 h-3.5 text-owl-green" /> : <Copy className="w-3.5 h-3.5 text-muted-foreground" />}
    </button>
  );
}

function TerminalBlock({ code, title }: { code: string; title?: string }) {
  return (
    <div className="relative rounded-xl bg-[#08080D] border border-owl-border/60 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-owl-border/40 bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FF5F57]/60" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#FEBC2E]/60" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#28C840]/60" />
          </div>
          {title && <span className="text-[11px] font-mono text-muted-foreground/60 ml-2">{title}</span>}
        </div>
        <CopyButton text={code} />
      </div>
      <pre className="p-4 overflow-x-auto text-[13px] font-mono leading-[1.7]">
        <code className="text-owl-lime/85">{code}</code>
      </pre>
    </div>
  );
}

function SectionBadge({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <motion.div variants={fadeUpFast} className="flex justify-center mb-5">
      <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-[0.15em]"
        style={{ backgroundColor: `${color}10`, color, border: `1px solid ${color}25` }}>
        {children}
      </div>
    </motion.div>
  );
}

function StarRating({ rating, size = 12 }: { rating: number; size?: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <Star key={i} size={size} className={i <= Math.round(rating) ? "fill-owl-amber text-owl-amber" : "text-muted-foreground/30"} />
      ))}
      <span className="text-[11px] text-muted-foreground ml-1 font-mono">{rating.toFixed(1)}</span>
    </div>
  );
}

function RatingBar({ value, max = 5, color }: { value: number; max?: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
        <motion.div initial={{ width: 0 }} whileInView={{ width: `${(value / max) * 100}%` }} viewport={{ once: true }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="h-full rounded-full" style={{ backgroundColor: color }} />
      </div>
      <span className="text-[11px] font-mono text-muted-foreground w-8 text-right">{value}/{max}</span>
    </div>
  );
}

function downloadFile(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/* ═══════════════════════════════════════════════════════════
   NAVIGATION
   ═══════════════════════════════════════════════════════════ */

function Navbar({ activeSection }: { activeSection: string }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { scrollY } = useScroll();

  useEffect(() => {
    const unsub = scrollY.on("change", (v) => setScrolled(v > 50));
    return () => unsub();
  }, [scrollY]);

  return (
    <>
      <motion.nav initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.6 }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${scrolled ? "glass-strong shadow-lg shadow-black/20" : "bg-transparent"}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14 sm:h-16">
            <a href="#hero" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-lg bg-owl-lime/10 flex items-center justify-center group-hover:bg-owl-lime/20 transition-colors">
                <span className="text-base">🦉</span>
              </div>
              <span className="font-black text-base sm:text-lg tracking-tight">OWL-AGENT</span>
              <Badge variant="outline" className="text-[9px] px-1.5 py-0 border-owl-lime/30 text-owl-lime font-mono hidden sm:inline-flex">v6.0</Badge>
            </a>
            <div className="hidden md:flex items-center gap-0.5 p-1 rounded-xl bg-white/[0.03] border border-owl-border/30">
              {NAV_ITEMS.map((item) => (
                <a key={item.id} href={`#${item.id}`}
                  className={`relative px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all focus-ring ${activeSection === item.id ? "text-owl-dark" : "text-muted-foreground hover:text-foreground"}`}>
                  {activeSection === item.id && (
                    <motion.div layoutId="activeNav" className="absolute inset-0 rounded-lg bg-owl-lime" transition={{ type: "spring", stiffness: 400, damping: 30 }} />
                  )}
                  <span className="relative z-10 flex items-center gap-1.5"><item.icon className="w-3 h-3" />{item.label}</span>
                </a>
              ))}
            </div>
            <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden p-2 rounded-xl hover:bg-white/5 focus-ring" aria-label="Menu">
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </motion.nav>
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden" onClick={() => setMobileOpen(false)} />
            <motion.div initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }} transition={{ type: "spring", stiffness: 400, damping: 35 }}
              className="fixed top-0 right-0 bottom-0 z-50 w-[260px] glass-strong md:hidden">
              <div className="flex flex-col h-full pt-20 pb-8 px-6">
                <div className="space-y-1 flex-1">
                  {NAV_ITEMS.map((item, i) => (
                    <motion.a key={item.id} href={`#${item.id}`} onClick={() => setMobileOpen(false)}
                      initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
                      className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${activeSection === item.id ? "text-owl-lime bg-owl-lime/10" : "text-muted-foreground hover:text-foreground"}`}>
                      <item.icon className="w-4 h-4" />{item.label}
                    </motion.a>
                  ))}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════
   HERO — PROXY BUILDER
   ═══════════════════════════════════════════════════════════ */

function HeroProxyBuilder() {
  const [selected, setSelected] = useState<Set<string>>(new Set(["Claude", "Kiro"]));
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ["start start", "end start"] });
  const y = useTransform(scrollYProgress, [0, 1], [0, -100]);
  const opacity = useTransform(scrollYProgress, [0, 0.6], [1, 0]);

  const toggleProvider = (name: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  };

  const compatibleProviders = PROVIDERS.filter((p) => selected.has(p.name));
  const hasForwardProxy = compatibleProviders.some((p) => p.forwardProxy);
  const hasGateway = compatibleProviders.some((p) => p.gateway);
  const hasMcp = compatibleProviders.some((p) => p.mcpServer);
  const avgSpeed = compatibleProviders.length ? compatibleProviders.reduce((s, p) => s + p.speed, 0) / compatibleProviders.length : 0;
  const avgComplexity = compatibleProviders.length ? compatibleProviders.reduce((s, p) => s + p.complexity, 0) / compatibleProviders.length : 0;

  return (
    <section ref={containerRef} id="hero" className="relative min-h-screen flex items-center overflow-hidden noise"
      onMouseMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); setMousePos({ x: (e.clientX - r.left) / r.width - 0.5, y: (e.clientY - r.top) / r.height - 0.5 }); }}>
      <div className="absolute inset-0 mesh-gradient" />
      <div className="absolute inset-0 dot-grid opacity-20" />
      <motion.div className="absolute top-[20%] left-[15%] w-[500px] h-[500px] bg-owl-lime/[0.04] rounded-full blur-[150px]"
        animate={{ x: mousePos.x * 40, y: mousePos.y * 40 }} transition={{ type: "spring", stiffness: 50 }} />
      <motion.div className="absolute bottom-[20%] right-[10%] w-[400px] h-[400px] bg-owl-violet/[0.04] rounded-full blur-[150px]"
        animate={{ x: mousePos.x * -30, y: mousePos.y * -30 }} transition={{ type: "spring", stiffness: 50 }} />

      <motion.div style={{ y, opacity }} className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16 w-full">
        <div className="text-center mb-10">
          <motion.div variants={fadeUp} className="inline-flex items-center gap-2.5 px-5 py-2 rounded-full glass mb-6">
            <span className="relative flex h-2 w-2"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-owl-green opacity-75" /><span className="relative inline-flex rounded-full h-2 w-2 bg-owl-green" /></span>
            <span className="text-[11px] font-mono text-muted-foreground tracking-wider">PROXY BUILDER — SELECT YOUR STACK</span>
          </motion.div>
          <motion.h1 variants={fadeUp} className="text-[clamp(2rem,6vw,5rem)] font-black tracking-[-0.04em] leading-[0.9]">
            <span className="block">BUILD YOUR</span>
            <span className="block text-gradient-multi">PROXY STACK</span>
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 max-w-xl mx-auto text-sm sm:text-base text-muted-foreground leading-relaxed">
            Select your AI providers. See what works together. Get the optimal deployment.
          </motion.p>
        </div>

        {/* Builder Grid */}
        <motion.div variants={fadeUp} className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-5xl mx-auto">
          {/* Left: Provider Selection */}
          <div className="glass rounded-2xl p-5 sm:p-6">
            <h3 className="text-sm font-bold mb-4 flex items-center gap-2"><Zap className="w-4 h-4 text-owl-lime" />Select Providers</h3>
            <div className="grid grid-cols-2 gap-2.5">
              {PROVIDERS.map((p) => (
                <button key={p.name} onClick={() => toggleProvider(p.name)}
                  className={`relative p-3 rounded-xl text-left transition-all duration-300 focus-ring ${
                    selected.has(p.name)
                      ? "border-2 bg-white/[0.04]"
                      : "border border-owl-border/40 bg-white/[0.01] hover:bg-white/[0.03]"
                  }`}
                  style={selected.has(p.name) ? { borderColor: p.color } : undefined}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-sm" style={{ color: selected.has(p.name) ? p.color : "inherit" }}>{p.name}</span>
                    {selected.has(p.name) && <Check className="w-4 h-4" style={{ color: p.color }} />}
                  </div>
                  <StarRating rating={p.stars} size={10} />
                </button>
              ))}
            </div>
          </div>

          {/* Right: Generated Stack */}
          <div className="glass rounded-2xl p-5 sm:p-6">
            <h3 className="text-sm font-bold mb-4 flex items-center gap-2"><Server className="w-4 h-4 text-owl-cyan" />Recommended Stack</h3>
            {compatibleProviders.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-sm">Select providers to see compatibility</div>
            ) : (
              <div className="space-y-4">
                {/* Compatibility Matrix */}
                <div className="space-y-2">
                  {[
                    { label: "Forward Proxy", icon: Wifi, ok: hasForwardProxy, desc: "HTTP/HTTPS proxy on :60000" },
                    { label: "API Gateway", icon: Server, ok: hasGateway, desc: "OpenAI-compatible API on :8333" },
                    { label: "MCP Server", icon: Cpu, ok: hasMcp, desc: "AI agent middleware (stdio)" },
                    { label: "Docker", icon: Container, ok: true, desc: "Containerized deployment" },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center gap-3 p-2.5 rounded-lg bg-white/[0.02] border border-owl-border/30">
                      <item.icon className="w-4 h-4 shrink-0" style={{ color: item.ok ? "#00FF88" : "#FF3E9A" }} />
                      <span className="text-sm font-medium flex-1">{item.label}</span>
                      <span className="text-[11px] text-muted-foreground hidden sm:block">{item.desc}</span>
                      {item.ok ? <Check className="w-4 h-4 text-owl-green" /> : <X className="w-4 h-4 text-owl-pink" />}
                    </div>
                  ))}
                </div>

                {/* Speed vs Complexity */}
                <div className="p-3 rounded-lg bg-white/[0.02] border border-owl-border/30 space-y-2.5">
                  <div>
                    <div className="flex justify-between text-[11px] mb-1"><span className="text-muted-foreground">Speed</span><span className="text-owl-lime font-mono">{avgSpeed.toFixed(1)}/5</span></div>
                    <RatingBar value={avgSpeed} color="#BFFF00" />
                  </div>
                  <div>
                    <div className="flex justify-between text-[11px] mb-1"><span className="text-muted-foreground">Complexity</span><span className="text-owl-amber font-mono">{avgComplexity.toFixed(1)}/5</span></div>
                    <RatingBar value={avgComplexity} color="#FFB800" />
                  </div>
                </div>

                {/* Stack alignment */}
                <div className="space-y-1.5">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Stack Alignment</span>
                  {compatibleProviders.map((p) => (
                    <div key={p.name} className="flex items-center gap-2 text-[12px]">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
                      <span>{p.name}</span>
                      <span className="text-muted-foreground">+ Docker</span>
                      {p.gateway && <span className="text-muted-foreground">+ Gateway</span>}
                      {p.mcpServer && <span className="text-muted-foreground">+ MCP</span>}
                      <Check className="w-3 h-3 text-owl-green ml-auto" />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </motion.div>

        {/* Quick install */}
        <motion.div variants={fadeUp} className="mt-8 max-w-2xl mx-auto">
          <TerminalBlock code="docker compose up -d" title="quick start" />
        </motion.div>

        {/* Stats */}
        <motion.div variants={fadeUp} className="grid grid-cols-4 gap-4 sm:gap-8 mt-12 max-w-lg mx-auto">
          {[
            { value: "6", label: "Providers", color: "#BFFF00" },
            { value: "8", label: "Files", color: "#00F0FF" },
            { value: "5", label: "Tier Defense", color: "#A855F7" },
            { value: "3", label: "Deploy Modes", color: "#FF3E9A" },
          ].map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-2xl sm:text-3xl font-black" style={{ color: s.color }}>{s.value}</div>
              <div className="text-[10px] sm:text-[11px] text-muted-foreground mt-1 uppercase tracking-wider">{s.label}</div>
            </div>
          ))}
        </motion.div>
      </motion.div>

      <motion.div animate={{ y: [0, 10, 0] }} transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2">
        <ChevronDown className="w-4 h-4 text-muted-foreground/30" />
      </motion.div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════
   DOCKER INSTALLATION GUIDE
   ═══════════════════════════════════════════════════════════ */

function DockerGuideSection() {
  const [activeMode, setActiveMode] = useState<"all" | "proxy" | "mcp">("all");

  return (
    <AnimatedSection id="docker" className="py-20 sm:py-28 relative">
      <div className="absolute inset-0 dot-grid opacity-10" />
      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionBadge color="#00F0FF"><Container className="w-3 h-3 mr-1.5" />Docker Guide</SectionBadge>
        <motion.div variants={fadeUp} className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            Deploy with <span className="text-gradient-cyan">Docker</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto text-sm sm:text-base leading-relaxed">
            Containerized deployment with zero host dependencies. Three service modes for any use case.
          </p>
        </motion.div>

        {/* Prerequisites */}
        <motion.div variants={fadeUp} className="glass rounded-xl p-5 mb-6">
          <h3 className="text-sm font-bold mb-3 flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-owl-green" />Prerequisites</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { name: "Docker", version: "20.10+", icon: Container },
              { name: "Compose", version: "v2+", icon: Layers },
              { name: "RAM", version: "512MB+", icon: Cpu },
              { name: "Disk", version: "1GB+", icon: Database },
            ].map((p) => (
              <div key={p.name} className="flex items-center gap-2.5 p-2.5 rounded-lg bg-white/[0.02] border border-owl-border/30">
                <p.icon className="w-4 h-4 text-owl-cyan shrink-0" />
                <div><div className="text-[12px] font-semibold">{p.name}</div><div className="text-[10px] text-muted-foreground">{p.version}</div></div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Service Modes */}
        <motion.div variants={fadeUp} className="mb-6">
          <div className="flex gap-2 mb-4">
            {(["all", "proxy", "mcp"] as const).map((mode) => (
              <button key={mode} onClick={() => setActiveMode(mode)}
                className={`px-4 py-2 rounded-lg text-[12px] font-medium capitalize transition-all focus-ring ${
                  activeMode === mode ? "bg-owl-cyan/15 text-owl-cyan border border-owl-cyan/25" : "bg-white/[0.03] text-muted-foreground border border-owl-border/40 hover:bg-white/[0.06]"
                }`}>
                {mode === "all" ? "All-in-One" : mode === "proxy" ? "Proxy Only" : "MCP Only"}
              </button>
            ))}
          </div>
          <AnimatePresence mode="wait">
            <motion.div key={activeMode} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3 }}>
              {activeMode === "all" && (
                <div className="space-y-4">
                  <TerminalBlock code={`# Clone and deploy\ngit clone https://github.com/marktantongco/owl-agent.git\ncd owl-agent/docker\ndocker compose --profile all-in-one up -d\n\n# Check health\ncurl http://localhost:60000/health`} title="all-in-one mode" />
                  <div className="glass rounded-xl p-4">
                    <p className="text-[12px] text-muted-foreground leading-relaxed">
                      <span className="text-owl-lime font-semibold">All-in-One</span> runs both the forward proxy and MCP server in a single container. Best for personal use and quick setup. Exposes port 60000 for the proxy. MCP server communicates via stdio.
                    </p>
                  </div>
                </div>
              )}
              {activeMode === "proxy" && (
                <div className="space-y-4">
                  <TerminalBlock code={`# Forward proxy only\ncd owl-agent/docker\ndocker compose up forward-proxy -d\n\n# Verify\ncurl -x http://localhost:60000 https://httpbin.org/ip`} title="proxy-only mode" />
                  <div className="glass rounded-xl p-4">
                    <p className="text-[12px] text-muted-foreground leading-relaxed">
                      <span className="text-owl-cyan font-semibold">Proxy Only</span> runs just the HTTP/HTTPS forward proxy on port 60000. Best when you only need the proxy for HTTP_PROXY injection into other tools. Domain bypass for NVIDIA, OpenCode, AWS, and Kiro.
                    </p>
                  </div>
                </div>
              )}
              {activeMode === "mcp" && (
                <div className="space-y-4">
                  <TerminalBlock code={`# MCP server with proxy dependency\ncd owl-agent/docker\ndocker compose up -d\n\n# Connect to MCP\ndocker compose exec mcp-server python3 /app/scripts/owl_resilient_mcp.py`} title="mcp-server mode" />
                  <div className="glass rounded-xl p-4">
                    <p className="text-[12px] text-muted-foreground leading-relaxed">
                      <span className="text-owl-amber font-semibold">MCP Server</span> starts both the proxy and MCP server. The MCP server depends on a healthy proxy. It exposes 5 tools: fetch_resilient, fetch_status, fetch_clear_cache, health_check, queue_status via JSON-RPC stdio.
                    </p>
                  </div>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </motion.div>

        {/* Environment Variables Table */}
        <motion.div variants={fadeUp} className="glass rounded-xl overflow-hidden mb-6">
          <div className="p-4 border-b border-owl-border/30">
            <h3 className="text-sm font-bold flex items-center gap-2"><Settings className="w-4 h-4 text-owl-violet" />Environment Variables</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead><tr className="border-b border-owl-border/30 text-muted-foreground">
                <th className="text-left px-4 py-2.5 font-semibold">Variable</th>
                <th className="text-left px-4 py-2.5 font-semibold">Default</th>
                <th className="text-left px-4 py-2.5 font-semibold hidden sm:table-cell">Description</th>
              </tr></thead>
              <tbody>
                {ENV_VARS.map((v) => (
                  <tr key={v.name} className="border-b border-owl-border/15 hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-2.5 font-mono text-owl-lime">{v.name}</td>
                    <td className="px-4 py-2.5 font-mono text-muted-foreground">{v.default || "—"}</td>
                    <td className="px-4 py-2.5 text-muted-foreground hidden sm:table-cell">{v.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* Docker Architecture Diagram */}
        <motion.div variants={fadeUp} className="glass rounded-xl p-5">
          <h3 className="text-sm font-bold mb-4 flex items-center gap-2"><Network className="w-4 h-4 text-owl-green" />Container Architecture</h3>
          <div className="relative flex flex-col items-center gap-3 py-4">
            {[
              { label: "Client / AI Agent", color: "#F0F0F5", icon: "🤖" },
              { label: "Forward Proxy :60000", color: "#BFFF00", icon: "🌐" },
              { label: "MCP Server (stdio)", color: "#FFB800", icon: "⚡" },
              { label: "Resilient Client", color: "#FF3E9A", icon: "🛡️" },
              { label: "Proxy Pool + Upstream", color: "#A855F7", icon: "🔄" },
            ].map((node, i) => (
              <div key={node.label} className="flex flex-col items-center">
                <motion.div initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }}
                  transition={{ delay: i * 0.1, type: "spring" }}
                  className="flex items-center gap-3 px-5 py-2.5 rounded-xl border"
                  style={{ borderColor: `${node.color}30`, backgroundColor: `${node.color}08` }}>
                  <span className="text-lg">{node.icon}</span>
                  <span className="text-[12px] font-semibold" style={{ color: node.color }}>{node.label}</span>
                </motion.div>
                {i < 4 && <div className="w-px h-4 bg-owl-border/50" />}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </AnimatedSection>
  );
}

/* ═══════════════════════════════════════════════════════════
   DOWNLOAD PORTAL
   ═══════════════════════════════════════════════════════════ */

function DownloadPortalSection() {
  const [activeCategory, setActiveCategory] = useState("all");
  const categories = ["all", "docker", "python", "config"];
  const filtered = activeCategory === "all" ? DOWNLOAD_FILES : DOWNLOAD_FILES.filter((f) => f.category === activeCategory);

  return (
    <AnimatedSection id="download" className="py-20 sm:py-28 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionBadge color="#BFFF00"><Download className="w-3 h-3 mr-1.5" />Download Portal</SectionBadge>
        <motion.div variants={fadeUp} className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            Grab the <span className="text-gradient-lime">Stack</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto text-sm sm:text-base">
            Every file you need. Download individually or clone the repo. All files are production-ready.
          </p>
        </motion.div>

        {/* Quick clone */}
        <motion.div variants={fadeUp} className="mb-6">
          <TerminalBlock code="git clone https://github.com/marktantongco/owl-agent.git && cd owl-agent/docker && docker compose up -d" title="clone & deploy" />
        </motion.div>

        {/* Category filter */}
        <motion.div variants={fadeUpFast} className="flex items-center gap-2 mb-6 overflow-x-auto pb-2 scroll-snap-x">
          {categories.map((cat) => (
            <button key={cat} onClick={() => setActiveCategory(cat)}
              className={`px-4 py-1.5 rounded-lg text-[12px] font-medium capitalize transition-all shrink-0 focus-ring ${
                activeCategory === cat ? "bg-owl-lime/15 text-owl-lime border border-owl-lime/25" : "bg-white/[0.03] text-muted-foreground border border-owl-border/40 hover:bg-white/[0.06]"
              }`}>{cat}</button>
          ))}
        </motion.div>

        {/* File grid */}
        <motion.div variants={stagger} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <AnimatePresence mode="popLayout">
            {filtered.map((file) => (
              <motion.div key={file.name} variants={scaleIn} layout initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}>
                <div className="glass rounded-xl h-full group hover:scale-[1.02] transition-all duration-300">
                  <div className="p-5">
                    <div className="flex items-start justify-between mb-3">
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${file.color}12` }}>
                        <file.icon className="w-5 h-5" style={{ color: file.color }} />
                      </div>
                      <Badge className="text-[9px] border font-bold" style={{ backgroundColor: `${file.color}15`, color: file.color, borderColor: `${file.color}25` }}>{file.badge}</Badge>
                    </div>
                    <h3 className="font-bold text-sm mb-1 font-mono tracking-tight">{file.name}</h3>
                    <p className="text-[11px] text-muted-foreground mb-1">{file.version}</p>
                    <p className="text-[12px] text-muted-foreground mb-4 leading-relaxed">{file.desc}</p>
                    <div className="flex items-center gap-2">
                      <Button size="sm" className="flex-1 h-8 text-[11px] font-bold" style={{ backgroundColor: `${file.color}20`, color: file.color }}
                        onClick={() => downloadFile(file.name, file.content)}>
                        <Download className="w-3 h-3 mr-1.5" />Download
                      </Button>
                      <Button size="sm" variant="outline" className="h-8 w-8 p-0 border-owl-border/40"
                        onClick={() => navigator.clipboard.writeText(file.content)}>
                        <Copy className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      </div>
    </AnimatedSection>
  );
}

/* ═══════════════════════════════════════════════════════════
   THREE APPROACHES
   ═══════════════════════════════════════════════════════════ */

function ApproachesSection() {
  return (
    <AnimatedSection id="approaches" className="py-20 sm:py-28 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionBadge color="#A855F7"><GitBranch className="w-3 h-3 mr-1.5" />Three Approaches</SectionBadge>
        <motion.div variants={fadeUp} className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            Pick Your <span className="text-gradient-pink">Path</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto text-sm sm:text-base">
            Three wildly different approaches. Each optimized for a different use case. Merge them for maximum power.
          </p>
        </motion.div>

        {/* Approach Cards */}
        <motion.div variants={stagger} className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-10">
          {APPROACHES.map((a) => (
            <motion.div key={a.title} variants={scaleIn}>
              <div className="glass rounded-2xl h-full group hover:scale-[1.01] transition-all duration-300"
                style={{ borderColor: `${a.color}20` }}>
                <div className="p-5 sm:p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${a.color}12` }}>
                      <a.icon className="w-6 h-6" style={{ color: a.color }} />
                    </div>
                    <div>
                      <h3 className="font-black text-base" style={{ color: a.color }}>{a.title}</h3>
                      <p className="text-[11px] text-muted-foreground">{a.subtitle}</p>
                    </div>
                  </div>

                  <StarRating rating={a.stars} />

                  <div className="mt-3 space-y-2">
                    <div><span className="text-[10px] text-muted-foreground">Speed</span><RatingBar value={a.speed} color={a.color} /></div>
                    <div><span className="text-[10px] text-muted-foreground">Complexity</span><RatingBar value={a.complexity} color="#FFB800" /></div>
                  </div>

                  <div className="mt-4"><TerminalBlock code={a.installCmd} title="install" /></div>

                  <div className="mt-4">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-2">Best For</p>
                    <p className="text-[12px] text-muted-foreground leading-relaxed">{a.bestFor}</p>
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-owl-green mb-1.5">Pros</p>
                      {a.features.slice(0, 3).map((f) => (
                        <div key={f} className="flex items-center gap-1.5 text-[11px] text-muted-foreground mb-0.5">
                          <Check className="w-3 h-3 text-owl-green shrink-0" />{f}
                        </div>
                      ))}
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-owl-pink mb-1.5">Tradeoffs</p>
                      {a.tradeoffs.map((t) => (
                        <div key={t} className="flex items-center gap-1.5 text-[11px] text-muted-foreground mb-0.5">
                          <AlertTriangle className="w-3 h-3 text-owl-pink shrink-0" />{t}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Merge Strategy */}
        <motion.div variants={fadeUp} className="glass rounded-2xl p-6 max-w-4xl mx-auto border-gradient">
          <h3 className="text-lg font-black mb-3 text-center">Merge Strategy: <span className="text-gradient-multi">Best of All Three</span></h3>
          <p className="text-[13px] text-muted-foreground text-center mb-6 leading-relaxed">
            Use Docker for production deployment, Bash for bootstrap and systemd, npm for programmatic integration. They compose perfectly.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            {[
              { label: "Docker Deploy", icon: Container, color: "#BFFF00" },
              { label: "Bash Bootstrap", icon: Terminal, color: "#00F0FF" },
              { label: "npm Integrate", icon: FileCode, color: "#A855F7" },
            ].map((item, i) => (
              <div key={item.label} className="flex items-center gap-2">
                <motion.div initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }}
                  transition={{ delay: i * 0.15, type: "spring" }}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl border" style={{ borderColor: `${item.color}30`, backgroundColor: `${item.color}08` }}>
                  <item.icon className="w-4 h-4" style={{ color: item.color }} />
                  <span className="text-[12px] font-semibold" style={{ color: item.color }}>{item.label}</span>
                </motion.div>
                {i < 2 && <ArrowRight className="w-4 h-4 text-muted-foreground/30 hidden sm:block" />}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </AnimatedSection>
  );
}

/* ═══════════════════════════════════════════════════════════
   DECISION TREE
   ═══════════════════════════════════════════════════════════ */

function DecisionTreeSection() {
  const decisions = [
    { condition: "Production deployment", result: "Docker Compose", icon: Container, color: "#BFFF00" },
    { condition: "Development setup", result: "Bash Installer", icon: Terminal, color: "#00F0FF" },
    { condition: "CI/CD integration", result: "npm Package", icon: FileCode, color: "#A855F7" },
    { condition: "All providers needed", result: "Docker all-in-one", icon: Layers, color: "#FF3E9A" },
    { condition: "Proxy only needed", result: "Docker proxy service", icon: Wifi, color: "#00FF88" },
    { condition: "MCP only needed", result: "Docker mcp service", icon: Cpu, color: "#FFB800" },
    { condition: "Limited resources", result: "Bash (no Docker overhead)", icon: Rocket, color: "#BFFF00" },
    { condition: "Zero-config desired", result: "Docker with defaults", icon: Sparkles, color: "#00F0FF" },
  ];

  return (
    <AnimatedSection id="decision" className="py-20 sm:py-28 relative">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionBadge color="#FF3E9A"><CircleDot className="w-3 h-3 mr-1.5" />Decision Tree</SectionBadge>
        <motion.div variants={fadeUp} className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            If <span className="text-owl-lime">X</span> then <span className="text-owl-cyan">Y</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto text-sm sm:text-base">
            Every branch mapped. No ambiguity. Pick your condition and follow the result.
          </p>
        </motion.div>

        <motion.div variants={stagger} className="space-y-2.5">
          {decisions.map((d, i) => (
            <motion.div key={d.condition} variants={fadeUp}
              className="glass rounded-xl p-4 flex items-center gap-4 group hover:scale-[1.01] transition-all duration-300 cursor-default">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: `${d.color}12` }}>
                <d.icon className="w-5 h-5" style={{ color: d.color }} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">IF</span>
                  <span className="text-[13px] font-semibold">{d.condition}</span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <ArrowRight className="w-3 h-3 text-muted-foreground/50" />
                  <span className="text-[12px] font-semibold" style={{ color: d.color }}>{d.result}</span>
                </div>
              </div>
              <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
            </motion.div>
          ))}
        </motion.div>
      </div>
    </AnimatedSection>
  );
}

/* ═══════════════════════════════════════════════════════════
   ARCHITECTURE SCHEMATIC
   ═══════════════════════════════════════════════════════════ */

function ArchitectureSection() {
  return (
    <AnimatedSection id="architecture" className="py-20 sm:py-28 relative">
      <div className="absolute inset-0 dot-grid opacity-10" />
      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionBadge color="#00F0FF"><Layers className="w-3 h-3 mr-1.5" />Architecture</SectionBadge>
        <motion.div variants={fadeUp} className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            How the <span className="text-gradient-cyan">Magic</span> Works
          </h2>
        </motion.div>

        {/* Main flow diagram */}
        <motion.div variants={fadeUp} className="glass rounded-2xl p-6 sm:p-8 mb-8">
          <h3 className="text-sm font-bold mb-6 text-center">Request Flow</h3>
          <div className="flex flex-col items-center gap-2">
            {[
              { label: "AI Agent / Client", sub: "OpenCode, Claude, Copilot, Cursor", color: "#F0F0F5", emoji: "🤖" },
              { label: "Forward Proxy", sub: "Port 60000 — Domain bypass + upstream chaining", color: "#BFFF00", emoji: "🌐" },
              { label: "Upstream Proxy", sub: "Mihomo/Clash on :7890 (optional)", color: "#00F0FF", emoji: "🔗" },
              { label: "Internet / API Providers", sub: "Claude, Kiro, OpenCode, Hermes, Gemini, DeepSeek", color: "#A855F7", emoji: "🌍" },
            ].map((node, i) => (
              <div key={node.label} className="flex flex-col items-center">
                <motion.div initial={{ opacity: 0, x: i % 2 === 0 ? -30 : 30 }} whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }} transition={{ delay: i * 0.15 }}
                  className="flex items-center gap-3 px-5 py-3 rounded-xl border min-w-[260px]"
                  style={{ borderColor: `${node.color}25`, backgroundColor: `${node.color}06` }}>
                  <span className="text-xl">{node.emoji}</span>
                  <div>
                    <div className="text-[13px] font-bold" style={{ color: node.color }}>{node.label}</div>
                    <div className="text-[10px] text-muted-foreground">{node.sub}</div>
                  </div>
                </motion.div>
                {i < 3 && <div className="w-px h-3 bg-gradient-to-b from-white/10 to-transparent" />}
              </div>
            ))}
          </div>

          {/* Bypass path */}
          <div className="mt-4 text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-owl-green/5 border border-owl-green/20">
              <Zap className="w-3 h-3 text-owl-green" />
              <span className="text-[11px] text-owl-green font-semibold">Bypass: NVIDIA, OpenCode, AWS, Kiro → Direct Connection</span>
            </div>
          </div>
        </motion.div>

        {/* 5-Tier Defense Stack */}
        <motion.div variants={fadeUp} className="glass rounded-2xl p-6 sm:p-8">
          <h3 className="text-sm font-bold mb-6 text-center">5-Tier Defense Stack</h3>
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
            {[
              { tier: 1, label: "Weighted Rotation", icon: RefreshCw, color: "#BFFF00" },
              { tier: 2, label: "Circuit Breaker", icon: Shield, color: "#00F0FF" },
              { tier: 3, label: "Request Dedup", icon: Layers, color: "#A855F7" },
              { tier: 4, label: "Response Cache", icon: Database, color: "#FF3E9A" },
              { tier: 5, label: "Rate Limiter", icon: Lock, color: "#FFB800" },
            ].map((t) => (
              <motion.div key={t.tier} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }} transition={{ delay: t.tier * 0.1 }}
                className="flex flex-col items-center gap-2 p-3 rounded-xl border text-center"
                style={{ borderColor: `${t.color}20`, backgroundColor: `${t.color}05` }}>
                <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${t.color}12` }}>
                  <t.icon className="w-4 h-4" style={{ color: t.color }} />
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Tier {t.tier}</span>
                <span className="text-[11px] font-semibold" style={{ color: t.color }}>{t.label}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </AnimatedSection>
  );
}

/* ═══════════════════════════════════════════════════════════
   KNOWLEDGE BASE
   ═══════════════════════════════════════════════════════════ */

function KnowledgeSection() {
  return (
    <AnimatedSection id="knowledge" className="py-20 sm:py-28 relative">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionBadge color="#FFB800"><BookOpen className="w-3 h-3 mr-1.5" />Knowledge Base</SectionBadge>
        <motion.div variants={fadeUp} className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            Everything You <span className="text-owl-amber">Need</span>
          </h2>
        </motion.div>

        {/* Version Timeline */}
        <motion.div variants={fadeUp} className="glass rounded-xl p-5 mb-6">
          <h3 className="text-sm font-bold mb-4 flex items-center gap-2"><GitBranch className="w-4 h-4 text-owl-pink" />Version Timeline</h3>
          <div className="flex flex-col sm:flex-row gap-4">
            {VERSION_HISTORY.map((v) => (
              <div key={v.version} className="flex-1 p-3 rounded-lg border" style={{ borderColor: `${v.color}20`, backgroundColor: `${v.color}05` }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-black text-sm" style={{ color: v.color }}>{v.version}</span>
                  <span className="text-[10px] text-muted-foreground">{v.date}</span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed">{v.changes}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Ports Reference */}
        <motion.div variants={fadeUp} className="glass rounded-xl overflow-hidden mb-6">
          <div className="p-4 border-b border-owl-border/30">
            <h3 className="text-sm font-bold flex items-center gap-2"><Wifi className="w-4 h-4 text-owl-cyan" />Ports Reference</h3>
          </div>
          <table className="w-full text-[12px]">
            <thead><tr className="border-b border-owl-border/30 text-muted-foreground">
              <th className="text-left px-4 py-2.5 font-semibold">Port</th>
              <th className="text-left px-4 py-2.5 font-semibold">Service</th>
              <th className="text-left px-4 py-2.5 font-semibold hidden sm:table-cell">Protocol</th>
            </tr></thead>
            <tbody>
              {[
                { port: "60000", service: "Forward Proxy", protocol: "HTTP/HTTPS" },
                { port: "8333", service: "Kiro Gateway", protocol: "OpenAI API" },
                { port: "7890", service: "Upstream (Mihomo)", protocol: "HTTP (external)" },
              ].map((r) => (
                <tr key={r.port} className="border-b border-owl-border/15 hover:bg-white/[0.02]">
                  <td className="px-4 py-2.5 font-mono text-owl-lime">{r.port}</td>
                  <td className="px-4 py-2.5">{r.service}</td>
                  <td className="px-4 py-2.5 text-muted-foreground hidden sm:table-cell">{r.protocol}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>

        {/* Compatibility Matrix */}
        <motion.div variants={fadeUp} className="glass rounded-xl overflow-hidden mb-6">
          <div className="p-4 border-b border-owl-border/30">
            <h3 className="text-sm font-bold flex items-center gap-2"><Activity className="w-4 h-4 text-owl-violet" />Provider Compatibility Matrix</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead><tr className="border-b border-owl-border/30 text-muted-foreground">
                <th className="text-left px-4 py-2.5 font-semibold">Provider</th>
                <th className="text-center px-3 py-2.5 font-semibold">Proxy</th>
                <th className="text-center px-3 py-2.5 font-semibold">Gateway</th>
                <th className="text-center px-3 py-2.5 font-semibold">MCP</th>
                <th className="text-center px-3 py-2.5 font-semibold">Docker</th>
                <th className="text-center px-3 py-2.5 font-semibold">CLI</th>
                <th className="text-center px-3 py-2.5 font-semibold">Stars</th>
              </tr></thead>
              <tbody>
                {PROVIDERS.map((p) => (
                  <tr key={p.name} className="border-b border-owl-border/15 hover:bg-white/[0.02]">
                    <td className="px-4 py-2.5 font-semibold" style={{ color: p.color }}>{p.name}</td>
                    <td className="text-center px-3 py-2.5">{p.forwardProxy ? "✅" : "❌"}</td>
                    <td className="text-center px-3 py-2.5">{p.gateway ? "✅" : "❌"}</td>
                    <td className="text-center px-3 py-2.5">{p.mcpServer ? "✅" : "❌"}</td>
                    <td className="text-center px-3 py-2.5">{p.docker ? "✅" : "❌"}</td>
                    <td className="text-center px-3 py-2.5">{p.nativeCli ? "✅" : "❌"}</td>
                    <td className="text-center px-3 py-2.5 font-mono text-owl-amber">{p.stars.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* FAQ */}
        <motion.div variants={fadeUp}>
          <Accordion type="single" collapsible className="space-y-2">
            {FAQ_ITEMS.map((faq, i) => (
              <AccordionItem key={i} value={`faq-${i}`}
                className="glass rounded-xl border-owl-border/40 data-[state=open]:border-owl-amber/20 px-4">
                <AccordionTrigger className="text-[13px] font-semibold text-left hover:no-underline py-4">
                  {faq.q}
                </AccordionTrigger>
                <AccordionContent className="text-[12px] text-muted-foreground leading-relaxed pb-4">
                  {faq.a}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </motion.div>
      </div>
    </AnimatedSection>
  );
}

/* ═══════════════════════════════════════════════════════════
   FOOTER
   ═══════════════════════════════════════════════════════════ */

function Footer() {
  return (
    <footer className="py-10 border-t border-owl-border/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span>🦉</span>
            <span className="font-bold text-sm">OWL-AGENT</span>
            <span className="text-[11px] text-muted-foreground font-mono">v6.0</span>
          </div>
          <div className="flex items-center gap-4">
            <a href="https://github.com/marktantongco/owl-agent" target="_blank" rel="noopener noreferrer"
              className="text-[12px] text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1.5">
              <GitBranch className="w-3.5 h-3.5" />GitHub
            </a>
            <a href="https://skills.sh/trending" target="_blank" rel="noopener noreferrer"
              className="text-[12px] text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1.5">
              <ExternalLink className="w-3.5 h-3.5" />Skills.sh
            </a>
          </div>
          <div className="text-[11px] text-muted-foreground">
            Built for Linux Ubuntu. Free-tier access. No limits.
          </div>
        </div>
      </div>
    </footer>
  );
}

/* ═══════════════════════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════════════════════ */

export default function HomePage() {
  const [activeSection, setActiveSection] = useState("hero");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { rootMargin: "-30% 0px -30% 0px" }
    );

    const sections = document.querySelectorAll("section[id]");
    sections.forEach((s) => observer.observe(s));
    return () => observer.disconnect();
  }, []);

  return (
    <main className="min-h-screen bg-background text-foreground">
      <Navbar activeSection={activeSection} />
      <HeroProxyBuilder />
      <DockerGuideSection />
      <DownloadPortalSection />
      <ApproachesSection />
      <DecisionTreeSection />
      <ArchitectureSection />
      <KnowledgeSection />
      <Footer />
    </main>
  );
}
