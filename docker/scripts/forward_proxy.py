#!/usr/bin/env python3
"""
forward_proxy.py v2.0 — Production-grade HTTP/HTTPS forward proxy

Features:
  - Full HTTP method handling (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
  - HTTPS via CONNECT tunneling
  - Domain bypass (direct connection for whitelisted domains)
  - Upstream proxy chaining with auth support (user:pass@host:port)
  - Asyncio + aiohttp with connection pooling & timeouts
  - Graceful shutdown on SIGINT / SIGTERM
  - Health check on /health
  - Structured logging to stdout

Environment variables:
  FORWARD_PROXY_PORT  (default: 60000)
  UPSTREAM_PROXY      (default: http://127.0.0.1:7890)
  BYPASS_DOMAINS      (default: nvidia.com,opencode.ai,amazonaws.com,kiro.dev)
  LOG_LEVEL           (default: INFO)
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from aiohttp import web

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOP_BY_HOP_HEADERS = frozenset(
    h.lower() for h in (
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    )
)

# Headers that the proxy itself manages — never forward these from the client.
PROXY_MANAGED_HEADERS = frozenset(
    h.lower() for h in (
        "proxy-connection",
        "proxy-authenticate",
        "proxy-authorization",
    )
)

DEFAULT_PORT = 60000
DEFAULT_UPSTREAM = "http://127.0.0.1:7890"
DEFAULT_BYPASS = "nvidia.com,opencode.ai,amazonaws.com,kiro.dev"
DEFAULT_LOG_LEVEL = "INFO"

CONNECT_TIMEOUT = 10  # seconds – tunnel establishment
REQUEST_TIMEOUT = 120  # seconds – full request/response cycle
TUNNEL_RW_TIMEOUT = 300  # seconds – idle timeout on tunnel pipes

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProxyConfig:
    port: int = DEFAULT_PORT
    upstream_proxy: str = DEFAULT_UPSTREAM
    bypass_domains: tuple[str, ...] = ()
    log_level: str = DEFAULT_LOG_LEVEL

    # Parsed upstream fields (populated in __post_init__)
    upstream_scheme: str = "http"
    upstream_host: str = "127.0.0.1"
    upstream_port: int = 7890
    upstream_auth: Optional[str] = None  # Basic auth "user:pass"

    def __post_init__(self) -> None:
        # Allow frozen dataclass to set computed fields via object.__setattr__
        parsed = urlparse(self.upstream_proxy)
        scheme = parsed.scheme or "http"
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (7890 if scheme == "http" else 443)
        auth: Optional[str] = None
        if parsed.username:
            from base64 import b64encode
            user = parsed.username
            pw = parsed.password or ""
            auth = "Basic " + b64encode(f"{user}:{pw}".encode()).decode()
        object.__setattr__(self, "upstream_scheme", scheme)
        object.__setattr__(self, "upstream_host", host)
        object.__setattr__(self, "upstream_port", port)
        object.__setattr__(self, "upstream_auth", auth)


def load_config() -> ProxyConfig:
    raw_bypass = os.getenv("BYPASS_DOMAINS", DEFAULT_BYPASS)
    bypass = tuple(d.strip().lower() for d in raw_bypass.split(",") if d.strip())
    upstream = os.getenv("UPSTREAM_PROXY", DEFAULT_UPSTREAM)
    # Strip surrounding quotes (Docker / docker-compose often injects them)
    if upstream.startswith('"') and upstream.endswith('"'):
        upstream = upstream[1:-1]
    if upstream.startswith("'") and upstream.endswith("'"):
        upstream = upstream[1:-1]

    return ProxyConfig(
        port=int(os.getenv("FORWARD_PROXY_PORT", DEFAULT_PORT)),
        upstream_proxy=upstream,
        bypass_domains=bypass,
        log_level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def domain_matches_bypass(hostname: str, bypass_domains: tuple[str, ...]) -> bool:
    """Return True if *hostname* matches any bypass domain (exact or subdomain)."""
    hostname = hostname.lower()
    for domain in bypass_domains:
        if hostname == domain or hostname.endswith("." + domain):
            return True
    return False


def clean_headers(headers: dict) -> dict:
    """Strip hop-by-hop and proxy-managed headers, return a plain dict."""
    out: dict[str, str] = {}
    for k, v in headers.items():
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS or lk in PROXY_MANAGED_HEADERS:
            continue
        out[k] = v
    return out


def build_upstream_connect_url(host: str, port: int, cfg: ProxyConfig) -> str:
    """Build the URL used when sending CONNECT through the upstream proxy."""
    return f"{cfg.upstream_scheme}://{cfg.upstream_host}:{cfg.upstream_port}"


# ---------------------------------------------------------------------------
# Proxy handler
# ---------------------------------------------------------------------------


class ForwardProxy:
    """Stateful proxy: owns the outgoing ClientSession and routing logic."""

    def __init__(self, cfg: ProxyConfig) -> None:
        self.cfg = cfg
        self.log = logging.getLogger("forward_proxy")
        self._direct_session: Optional[aiohttp.ClientSession] = None
        self._proxy_session: Optional[aiohttp.ClientSession] = None

    # -- session lifecycle ---------------------------------------------------

    async def start(self) -> None:
        timeout = aiohttp.ClientTimeout(
            total=REQUEST_TIMEOUT,
            connect=CONNECT_TIMEOUT,
        )
        self._direct_session = aiohttp.ClientSession(timeout=timeout)
        # The proxy session doesn't need its own proxy kwarg — we handle
        # proxy routing manually so we can inject auth per-request.
        self._proxy_session = aiohttp.ClientSession(timeout=timeout)
        self.log.info(
            "Forward proxy v2.0 initialised — port=%d upstream=%s bypass=%s",
            self.cfg.port,
            self.cfg.upstream_proxy,
            ", ".join(self.cfg.bypass_domains),
        )

    async def stop(self) -> None:
        for sess in (self._direct_session, self._proxy_session):
            if sess and not sess.closed:
                await sess.close()
        self.log.info("Proxy sessions closed.")

    # -- request dispatch ----------------------------------------------------

    async def handle(self, request: web.Request) -> web.StreamResponse:
        """Main entry point for every incoming request."""
        if request.method == "CONNECT":
            return await self._handle_connect(request)
        return await self._handle_http(request)

    # -- health check --------------------------------------------------------

    async def handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "version": "2.0"})

    # -- HTTP (non-CONNECT) --------------------------------------------------

    async def _handle_http(self, request: web.Request) -> web.StreamResponse:
        """Forward plain HTTP requests (GET, POST, PUT, DELETE, PATCH, …)."""
        url = str(request.url)
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        use_proxy = not domain_matches_bypass(hostname, self.cfg.bypass_domains)
        session = self._proxy_session if use_proxy else self._direct_session

        # Build outgoing headers
        fwd_headers = clean_headers(dict(request.headers))
        # Ensure Host is set correctly
        if "Host" not in fwd_headers and parsed.netloc:
            fwd_headers["Host"] = parsed.netloc

        # Read the full body from the client
        body = await request.read()

        proxy_url: Optional[str] = None
        proxy_headers: Optional[dict[str, str]] = None
        if use_proxy:
            proxy_url = self.cfg.upstream_proxy
            if self.cfg.upstream_auth:
                proxy_headers = {"Proxy-Authorization": self.cfg.upstream_auth}

        self.log.debug(
            "HTTP %s %s → upstream=%s proxy=%s",
            request.method, url, use_proxy, proxy_url,
        )

        try:
            async with session.request(
                method=request.method,
                url=url,
                headers=fwd_headers,
                data=body,
                proxy=proxy_url,
                proxy_headers=proxy_headers,
                allow_redirects=False,  # let the client decide
                ssl=False,  # don't verify upstream certs inside the tunnel
            ) as upstream_resp:
                # Build the downstream response
                resp_headers = clean_headers(dict(upstream_resp.headers))
                # Re-add content-length if the upstream set it (after cleaning)
                if "Content-Length" in upstream_resp.headers and "Content-Length" not in resp_headers:
                    resp_headers["Content-Length"] = upstream_resp.headers["Content-Length"]

                response = web.StreamResponse(
                    status=upstream_resp.status,
                    reason=upstream_resp.reason,
                    headers=resp_headers,
                )
                await response.prepare(request)

                # Stream the body back to the client in chunks
                async for chunk in upstream_resp.content.iter_any():
                    await response.write(chunk)

                await response.write_eof()
                return response

        except aiohttp.ClientError as exc:
            self.log.error("Upstream error for %s %s: %s", request.method, url, exc)
            return web.Response(status=502, text=f"Bad Gateway: {exc}")
        except asyncio.TimeoutError:
            self.log.error("Timeout for %s %s", request.method, url)
            return web.Response(status=504, text="Gateway Timeout")
        except Exception as exc:
            self.log.exception("Unexpected error for %s %s", request.method, url)
            return web.Response(status=500, text=f"Internal Proxy Error: {exc}")

    # -- HTTPS (CONNECT) -----------------------------------------------------

    async def _handle_connect(self, request: web.Request) -> web.StreamResponse:
        """Handle CONNECT method — establish a bidirectional TCP tunnel."""
        host = request.host  # aiohttp parses "host:port" from the request line
        port = request.port or 443
        hostname = host.split(":")[0] if ":" in host else host

        use_proxy = not domain_matches_bypass(hostname, self.cfg.bypass_domains)

        self.log.debug("CONNECT %s:%d → upstream=%s", host, port, use_proxy)

        try:
            if use_proxy:
                upstream_reader, upstream_writer = await self._connect_via_upstream(
                    host, port,
                )
            else:
                upstream_reader, upstream_writer = await self._connect_direct(
                    host, port,
                )
        except Exception as exc:
            self.log.error("CONNECT tunnel failed %s:%d: %s", host, port, exc)
            return web.Response(status=502, text=f"Tunnel Connection Failed: {exc}")

        # Acknowledge the CONNECT to the client
        response = web.StreamResponse(status=200, reason="Connection Established")
        response.force_close = False
        try:
            await response.prepare(request)
        except Exception as exc:
            self.log.warning("Failed to send 200 to client for CONNECT %s:%d: %s", host, port, exc)
            upstream_writer.close()
            await upstream_writer.wait_closed()
            return response

        # Bidirectional piping
        try:
            await self._pipe_bidirectional(
                request, response, upstream_reader, upstream_writer,
            )
        except Exception:
            self.log.debug("Tunnel pipe closed for %s:%d", host, port)
        finally:
            upstream_writer.close()
            try:
                await upstream_writer.wait_closed()
            except Exception:
                pass

        return response

    async def _connect_direct(
        self, host: str, port: int,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open a direct TCP connection (bypass path)."""
        return await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=CONNECT_TIMEOUT,
        )

    async def _connect_via_upstream(
        self, host: str, port: int,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open a TCP connection through the upstream HTTP proxy using CONNECT."""
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                self.cfg.upstream_host, self.cfg.upstream_port,
            ),
            timeout=CONNECT_TIMEOUT,
        )

        # Send CONNECT request to upstream proxy
        connect_line = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n"
        if self.cfg.upstream_auth:
            connect_line += f"Proxy-Authorization: {self.cfg.upstream_auth}\r\n"
        connect_line += "\r\n"

        writer.write(connect_line.encode())
        await writer.drain()

        # Read the upstream proxy's response
        response_line = await asyncio.wait_for(
            reader.readline(), timeout=CONNECT_TIMEOUT,
        )
        if not response_line:
            writer.close()
            await writer.wait_closed()
            raise ConnectionError("Upstream proxy closed connection during CONNECT")

        # Parse HTTP status from response line, e.g. "HTTP/1.1 200 Connection established"
        parts = response_line.decode(errors="replace").strip().split(" ", 2)
        if len(parts) < 2 or parts[1] != "200":
            status = parts[1] if len(parts) >= 2 else "???"
            reason = parts[2] if len(parts) >= 3 else ""
            writer.close()
            await writer.wait_closed()
            raise ConnectionError(
                f"Upstream proxy rejected CONNECT: {status} {reason}"
            )

        # Consume remaining headers from the proxy response
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=CONNECT_TIMEOUT)
            if line in (b"\r\n", b"\n", b""):
                break

        return reader, writer

    async def _pipe_bidirectional(
        self,
        request: web.Request,
        response: web.StreamResponse,
        upstream_reader: asyncio.StreamReader,
        upstream_writer: asyncio.StreamWriter,
    ) -> None:
        """Copy data between the client and the upstream in both directions."""

        async def client_to_upstream() -> None:
            try:
                while True:
                    chunk = await asyncio.wait_for(
                        request.content.read(65536),
                        timeout=TUNNEL_RW_TIMEOUT,
                    )
                    if not chunk:
                        break
                    upstream_writer.write(chunk)
                    await upstream_writer.drain()
            except (asyncio.TimeoutError, ConnectionError, OSError):
                pass
            finally:
                try:
                    if not upstream_writer.is_closing():
                        upstream_writer.write_eof()
                except Exception:
                    pass

        async def upstream_to_client() -> None:
            try:
                while True:
                    chunk = await asyncio.wait_for(
                        upstream_reader.read(65536),
                        timeout=TUNNEL_RW_TIMEOUT,
                    )
                    if not chunk:
                        break
                    await response.write(chunk)
            except (asyncio.TimeoutError, ConnectionError, OSError):
                pass
            finally:
                try:
                    await response.write_eof()
                except Exception:
                    pass

        # Run both directions concurrently; stop when either side closes.
        await asyncio.gather(
            client_to_upstream(),
            upstream_to_client(),
            return_exceptions=True,
        )


# ---------------------------------------------------------------------------
# Application factory & lifecycle
# ---------------------------------------------------------------------------


def create_app(cfg: ProxyConfig) -> web.Application:
    proxy = ForwardProxy(cfg)

    app = web.Application()

    # Health check — must be registered BEFORE the catch-all
    app.router.add_route("GET", "/health", proxy.handle_health)

    # Catch-all proxy handler — every method & path
    for method in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "CONNECT"):
        app.router.add_route(method, "/{path_info:.*}", proxy.handle)

    app.on_startup.append(on_startup(proxy))
    app.on_cleanup.append(on_cleanup(proxy))
    return app


def on_startup(proxy: ForwardProxy):
    async def _on_startup(app: web.Application) -> None:
        await proxy.start()
        app["proxy"] = proxy
    return _on_startup


def on_cleanup(proxy: ForwardProxy):
    async def _on_cleanup(app: web.Application) -> None:
        await proxy.stop()
    return _on_cleanup


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    cfg = load_config()

    logging.basicConfig(
        level=getattr(logging, cfg.log_level, logging.INFO),
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    log = logging.getLogger("forward_proxy")
    log.info("Starting forward proxy v2.0 on port %d", cfg.port)

    app = create_app(cfg)

    # Graceful shutdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.ensure_future(_shutdown(app, log)),
        )

    try:
        web.run_app(app, host="0.0.0.0", port=cfg.port, print=None)
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


async def _shutdown(app: web.Application, log: logging.Logger) -> None:
    log.info("Shutdown signal received — cleaning up")
    await app.shutdown()
    await app.cleanup()


if __name__ == "__main__":
    main()
