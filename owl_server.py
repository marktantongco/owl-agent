#!/usr/bin/env python3
"""
🦉 OWL-AGENT v4.5 - HTTP API Server
====================================
Wraps ResilientClient in a production async HTTP server.
- /fetch   POST   Fetch a URL through the intelligent proxy pool
- /browser POST   Fetch via agent-browser headless browser
- /health  GET    Health check
- /stats   GET    Proxy pool stats
- /metrics GET    Prometheus metrics (port 9090)
"""

import asyncio
import json
import os
import time
import logging
from typing import Optional

from aiohttp import web

# Prometheus metrics
from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY, CONTENT_TYPE_LATEST

from proxy_defense import ResilientClient, CachedResponse, logger


# ─── Environment helpers (module-level so they are testable) ─────
def _env_bool(name: str, default: bool = False, getenv=os.getenv) -> bool:
    value = getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on", "enabled")


def _env_list(name: str, default=None, getenv=os.getenv):
    value = getenv(name)
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


def _collect_extra_proxies(environ=None) -> list:
    """Merge OWL_EXTRA_PROXIES / OWL_PROX5_SOCKS5 / OWL_HTTPS_PROXY into
    one list of proxy URLs to seed into the pool."""
    getenv = environ.get if environ is not None else os.getenv
    proxies = _env_list("OWL_EXTRA_PROXIES", getenv=getenv)
    for env_name, default_scheme in (("OWL_PROX5_SOCKS5", "socks5"), ("OWL_HTTPS_PROXY", "https")):
        value = getenv(env_name)
        if value:
            proxies.append(value if "://" in value else f"{default_scheme}://{value}")
    return proxies


# ─── Prometheus Metrics ──────────────────────────────────────────
REQUESTS_TOTAL = Counter(
    "owl_requests_total", "Total requests processed", ["method", "status"]
)
PROXY_POOL_SIZE = Gauge("owl_proxy_pool_size", "Number of proxies in pool")
PROXY_HEALTHY = Gauge("owl_proxy_healthy", "Number of healthy proxies")
REQUEST_LATENCY = Histogram(
    "owl_request_latency_seconds", "Request latency in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)
CACHE_HITS = Counter("owl_cache_hits_total", "Cache hit count")
CACHE_MISSES = Counter("owl_cache_misses_total", "Cache miss count")
POOL_REFRESH_COUNT = Counter("owl_pool_refresh_total", "Proxy pool refresh cycles")

# ─── HTTP API Handlers ──────────────────────────────────────────

class OwlServer:
    def __init__(self, host: str = "0.0.0.0", api_port: int = 60000,
                 metrics_port: int = 9090, **client_kwargs):
        self.host = host
        self.api_port = api_port
        self.metrics_port = metrics_port
        self.client_kwargs = client_kwargs
        self.client: Optional[ResilientClient] = None
        self._api_runner: Optional[web.AppRunner] = None
        self._metrics_site: Optional[asyncio.AbstractServer] = None

    async def start(self):
        """Start the API server and metrics endpoint."""
        self.client = ResilientClient(**self.client_kwargs)
        await self.client.__aenter__()

        # Start plugin loader discovery
        if self.client.plugin_loader:
            await self.client.plugin_loader.start()
            stats = self.client.plugin_loader.get_stats()
            logger.info(f"🔌 Plugins loaded: {stats['total']} ({', '.join(stats['plugins'].keys()) if stats['plugins'] else 'none'})")

        # API server (port 60000)
        app = web.Application()
        app.router.add_post("/fetch", self.handle_fetch)
        app.router.add_post("/browser", self.handle_browser)
        app.router.add_get("/health", self.handle_health)
        app.router.add_get("/stats", self.handle_stats)
        app.on_shutdown.append(self._on_shutdown)

        self._api_runner = web.AppRunner(app)
        await self._api_runner.setup()
        site = web.TCPSite(self._api_runner, self.host, self.api_port)
        await site.start()
        logger.info(f"🦉 OWL-AGENT API listening on http://{self.host}:{self.api_port}")

        # Metrics server (port 9090)
        metrics_app = web.Application()
        metrics_app.router.add_get("/metrics", self.handle_metrics)
        self._metrics_runner = web.AppRunner(metrics_app)
        await self._metrics_runner.setup()
        metrics_site = web.TCPSite(self._metrics_runner, self.host, self.metrics_port)
        await metrics_site.start()
        logger.info(f"📊 Prometheus metrics at http://{self.host}:{self.metrics_port}/metrics")

        # Background proxy pool metrics updater
        asyncio.create_task(self._update_metrics_loop())

    async def stop(self):
        """Graceful shutdown."""
        if self._api_runner:
            await self._api_runner.cleanup()
        if self._metrics_runner:
            await self._metrics_runner.cleanup()
        if self.client:
            await self.client.__aexit__(None, None, None)

    async def _on_shutdown(self, app):
        logger.info("Shutting down...")

    async def _update_metrics_loop(self):
        """Periodically update Gauge metrics from the proxy pool."""
        while True:
            try:
                if self.client:
                    PROXY_POOL_SIZE.set(len(self.client.pool_manager._proxies))
                    PROXY_HEALTHY.set(
                        sum(1 for p in self.client.pool_manager._proxies
                            if p.healthy and not p.is_banned())
                    )
            except Exception:
                pass
            await asyncio.sleep(15)

    async def handle_fetch(self, request: web.Request) -> web.Response:
        """POST /fetch — Fetch a URL through the proxy pool.

        Body (JSON):
        {
            "url": "https://example.com",
            "method": "GET",          # optional, default GET
            "headers": {},            # optional
            "browser": false,         # optional, use agent-browser
            "wait_for": ".selector",  # optional, for browser mode
            "timeout": 30             # optional
        }
        """
        start = time.time()
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        url = body.get("url")
        if not url:
            return web.json_response({"error": "Missing 'url' field"}, status=400)

        method = body.get("method", "GET").upper()
        headers = body.get("headers") or {}
        browser = body.get("browser", False)
        wait_for = body.get("wait_for")
        timeout = body.get("timeout", 30)

        try:
            resp: CachedResponse = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                browser=browser,
                wait_for=wait_for,
                timeout=timeout,
            )
            latency = time.time() - start
            REQUESTS_TOTAL.labels(method=method, status=str(resp.status)).inc()
            REQUEST_LATENCY.observe(latency)

            return web.json_response(
                {
                    "status": resp.status,
                    "headers": resp.headers,
                    "content_length": len(resp.content),
                    "content": resp.content.decode("utf-8", errors="replace"),
                    "latency_seconds": round(latency, 3),
                    "from_cache": resp.is_fresh() and (time.time() - resp.timestamp) < resp.ttl,
                }
            )
        except Exception as e:
            REQUESTS_TOTAL.labels(method=method, status="error").inc()
            return web.json_response({"error": str(e)}, status=502)

    async def handle_browser(self, request: web.Request) -> web.Response:
        """POST /browser — Fetch via agent-browser (JS rendering)."""
        body = await request.json()
        url = body.get("url")
        if not url:
            return web.json_response({"error": "Missing 'url' field"}, status=400)
        wait_for = body.get("wait_for")
        timeout = body.get("timeout", 30)
        try:
            content = await self.client.request(
                "GET", url, browser=True, wait_for=wait_for, timeout=timeout
            )
            return web.json_response(
                {
                    "status": content.status,
                    "content_length": len(content.content),
                    "content": content.content.decode("utf-8", errors="replace"),
                }
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=502)

    async def handle_health(self, request: web.Request) -> web.Response:
        """GET /health — Health check."""
        if not self.client:
            return web.json_response({"status": "not_ready"}, status=503)
        stats = await self.client.get_stats()
        return web.json_response({
            "status": "ok",
            "proxies_total": stats["proxies_total"],
            "proxies_healthy": stats["proxies_healthy"],
            "uptime": time.time() - self._start_time if hasattr(self, '_start_time') else 0,
        })

    async def handle_stats(self, request: web.Request) -> web.Response:
        """GET /stats — Detailed proxy pool and rate limiter stats."""
        if not self.client:
            return web.json_response({"status": "not_ready"}, status=503)
        stats = await self.client.get_stats()
        return web.json_response(stats)

    async def handle_metrics(self, request: web.Request) -> web.Response:
        """GET /metrics — Prometheus metrics."""
        return web.Response(
            body=generate_latest(REGISTRY),
            content_type="text/plain; version=0.0.4",
        )


# ─── Main ────────────────────────────────────────────────────────
async def main():
    import argparse

    parser = argparse.ArgumentParser(description="🦉 OWL-AGENT v4.5 Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--api-port", type=int, default=60000, help="API port")
    parser.add_argument("--metrics-port", type=int, default=9090, help="Prometheus port")
    parser.add_argument("--countries", nargs="+", default=_env_list("OWL_PROXY_COUNTRIES", ["US", "GB", "PH"]),
                        help="Preferred proxy countries (or OWL_PROXY_COUNTRIES)")
    parser.add_argument("--redis", action="store_true", default=_env_bool("OWL_REDIS_ENABLED"),
                        help="Enable Redis state sharing (or OWL_REDIS_ENABLED)")
    parser.add_argument("--redis-url", default=os.getenv("OWL_REDIS_URL", "redis://localhost:6379"),
                        help="Redis URL (or OWL_REDIS_URL)")

    # Self-hosted proxy endpoints: prox5 SOCKS5 server, madeye/https_proxy.
    # All are merged into the pool via --extra-proxies / OWL_EXTRA_PROXIES.
    parser.add_argument("--extra-proxies", default=",".join(_collect_extra_proxies()),
                        help="Comma-separated proxy URLs to seed into the pool "
                             "(or OWL_EXTRA_PROXIES / OWL_PROX5_SOCKS5 / OWL_HTTPS_PROXY)")
    parser.add_argument("--no-curl-cffi", action="store_true", help="Disable curl_cffi")
    parser.add_argument("--ab-test", action="store_true", help="Enable A/B testing for proxy strategies")
    parser.add_argument("--ml", action="store_true", help="Enable ML predictor for proxy selection")
    parser.add_argument("--ml-model", default="auto", choices=["auto", "logistic", "xgboost", "mlp"],
                        help="ML model type (default: auto)")
    parser.add_argument("--plugin-dir", default="~/.owl-agent/plugins",
                        help="Plugin directory for auto-discovery")
    args = parser.parse_args()

    server = OwlServer(
        host=args.host,
        api_port=args.api_port,
        metrics_port=args.metrics_port,
        use_curl_cffi=not args.no_curl_cffi,
        enable_ab_test=args.ab_test,
        enable_ml=args.ml,
        ml_model=args.ml_model,
        plugin_dir=args.plugin_dir,
        countries=args.countries,
        use_redis=args.redis,
        redis_url=args.redis_url,
        extra_proxies=[p for p in args.extra_proxies.split(",") if p],
    )
    server._start_time = time.time()

    _extra_display = " ".join(p for p in args.extra_proxies.split(",") if p) or "none"
    print(f"""
🦉 OWL-AGENT v4.5 Server
{'=' * 55}
  API:       http://{args.host}:{args.api_port}
  Metrics:   http://{args.host}:{args.metrics_port}/metrics
  Countries: {', '.join(args.countries)}
  Redis:     {'enabled' if args.redis else 'disabled'}
  curl_cffi:  {'enabled' if not args.no_curl_cffi else 'disabled'}
  A/B Test:  {'enabled' if args.ab_test else 'disabled'}
  ML:        {'enabled' if args.ml else 'disabled'}
  Extra:     {_extra_display}
{'=' * 55}
    """)

    await server.start()

    try:
        # Keep running until SIGINT/SIGTERM
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


def cli():
    """Console-script entry point for the `owl-server` command."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
