#!/usr/bin/env python3
"""
proxy_defense_fixed_v3.py — Production-grade resilient HTTP client.

v3.3 with v6.0 bug fixes.

Features:
  - 5-tier escalation: weighted proxy rotation, circuit breaker,
    request deduplication, response caching with TTL, domain rate limiting.
  - ProxyPoolLoader: JSON config, auth injection, GitHub list fetching,
    config-based enrichment (OWL_ENRICH_ENABLED).
  - CircuitBreaker: CLOSED / OPEN / HALF_OPEN with configurable threshold
    and recovery timeout.
  - DomainRateLimiter: asyncio.Semaphore per domain (fixes v6.0 race
    condition from recursive TokenBucket acquire).
  - v6.0 fix: added get_stats() so callers no longer reference a
    non-existent self._stats attribute.

Environment variables:
  PROXY_POOL_CONFIG       Default proxy pool JSON path  (/app/config/proxy_pool.json)
  PROXY_SOURCES_CONFIG    Proxy sources JSON path       (/app/config/proxy_sources.json)
  OWL_ENRICH_ENABLED      Enable config enrichment      ("")
  CACHE_TTL               Cache time-to-live in seconds (300)
  CIRCUIT_BREAKER_THRESHOLD  Failures before opening    (3)
  CIRCUIT_BREAKER_RECOVERY   Seconds before half-open   (60)

Dependencies: aiohttp (plus stdlib)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("proxy_defense")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(_handler)

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------
ENV_PROXY_POOL_CONFIG: str = os.getenv("PROXY_POOL_CONFIG", "/app/config/proxy_pool.json")
ENV_PROXY_SOURCES_CONFIG: str = os.getenv("PROXY_SOURCES_CONFIG", "/app/config/proxy_sources.json")
ENV_OWL_ENRICH_ENABLED: str = os.getenv("OWL_ENRICH_ENABLED", "")
ENV_CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))
ENV_CB_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3"))
ENV_CB_RECOVERY: int = int(os.getenv("CIRCUIT_BREAKER_RECOVERY", "60"))


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------
class CircuitState(Enum):
    """Possible states for a circuit breaker."""

    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


@dataclass
class CircuitBreaker:
    """Thread-safe (asyncio-safe) circuit breaker per proxy.

    - CLOSED: requests pass through normally.
    - OPEN: all requests are rejected immediately.
    - HALF_OPEN: one test request is allowed; success closes the circuit,
      failure re-opens it.
    """

    failure_threshold: int = ENV_CB_THRESHOLD
    recovery_timeout: float = ENV_CB_RECOVERY

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _half_open_in_flight: bool = field(default=False, init=False)

    # -- public interface ----------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Return current state, transitioning OPEN -> HALF_OPEN if recovery
        timeout has elapsed."""
        if self._state is CircuitState.OPEN:
            if (time.monotonic() - self._last_failure_time) >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.debug("Circuit breaker transitioning OPEN -> HALF_OPEN")
        return self._state

    def allow_request(self) -> bool:
        """Decide whether a new request may proceed."""
        current = self.state
        if current is CircuitState.CLOSED:
            return True
        if current is CircuitState.HALF_OPEN:
            # Only one probe request at a time in half-open state.
            if not self._half_open_in_flight:
                self._half_open_in_flight = True
                return True
            return False
        # OPEN
        return False

    def record_success(self) -> None:
        """Record a successful request; resets failure count."""
        if self._state is CircuitState.HALF_OPEN:
            self._half_open_in_flight = False
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed request; may open the circuit."""
        if self._state is CircuitState.HALF_OPEN:
            # Probe failed — back to OPEN.
            self._half_open_in_flight = False
            self._state = CircuitState.OPEN
            self._last_failure_time = time.monotonic()
            return
        self._failure_count += 1
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._last_failure_time = time.monotonic()
            logger.warning(
                "Circuit breaker OPENED after %d failures", self._failure_count
            )


# ---------------------------------------------------------------------------
# DomainRateLimiter (Semaphore-based — v6.0 race-condition fix)
# ---------------------------------------------------------------------------
class DomainRateLimiter:
    """Per-domain concurrency limiter using ``asyncio.Semaphore``.

    The v6.0 TokenBucket implementation could dead-lock when ``acquire``
    was called recursively from within a task that already held the token.
    Replacing it with a semaphore eliminates the recursive-acquire problem
    entirely: ``Semaphore.acquire`` is non-recursive by design and will
    correctly queue waiters without risking a dead-lock.
    """

    DEFAULT_MAX_CONCURRENCY: int = 5

    def __init__(self, max_concurrency: int = DEFAULT_MAX_CONCURRENCY) -> None:
        self._max_concurrency: int = max_concurrency
        self._semaphores: Dict[str, asyncio.Semaphore] = {}

    def _get_semaphore(self, domain: str) -> asyncio.Semaphore:
        """Return (or lazily create) the semaphore for *domain*."""
        sem = self._semaphores.get(domain)
        if sem is None:
            sem = asyncio.Semaphore(self._max_concurrency)
            self._semaphores[domain] = sem
        return sem

    async def acquire(self, domain: str) -> None:
        """Acquire a permit for *domain*.  Waits if at capacity."""
        await self._get_semaphore(domain).acquire()

    def release(self, domain: str) -> None:
        """Release a permit for *domain*."""
        sem = self._semaphores.get(domain)
        if sem is not None:
            try:
                sem.release()
            except ValueError:
                # Semaphore was already at zero; ignore.
                logger.debug("Semaphore release overflow for domain=%s", domain)


# ---------------------------------------------------------------------------
# ResponseCache
# ---------------------------------------------------------------------------
@dataclass
class _CacheEntry:
    response: aiohttp.ClientResponse
    body: bytes
    expires_at: float


class ResponseCache:
    """Simple in-memory TTL cache keyed by request fingerprint."""

    def __init__(self, ttl: int = ENV_CACHE_TTL) -> None:
        self._ttl: int = ttl
        self._store: Dict[str, _CacheEntry] = {}

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _fingerprint(url: str, method: str, **kwargs: Any) -> str:
        """Deterministic hash identifying a request."""
        h = hashlib.sha256()
        h.update(f"{method.upper()}|{url}".encode())
        # Sort kwargs so fingerprint is stable.
        for k in sorted(kwargs):
            h.update(f"|{k}={kwargs[k]}".encode())
        return h.hexdigest()

    # -- public interface ----------------------------------------------------

    def get(self, url: str, method: str = "GET", **kwargs: Any) -> Optional[_CacheEntry]:
        """Return cached entry if present and not expired, else ``None``."""
        key = self._fingerprint(url, method, **kwargs)
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() >= entry.expires_at:
            del self._store[key]
            return None
        return entry

    def put(
        self,
        url: str,
        method: str,
        response: aiohttp.ClientResponse,
        body: bytes,
        **kwargs: Any,
    ) -> None:
        """Store a response in the cache."""
        key = self._fingerprint(url, method, **kwargs)
        self._store[key] = _CacheEntry(
            response=response,
            body=body,
            expires_at=time.monotonic() + self._ttl,
        )

    def clear(self) -> None:
        """Remove all cached entries."""
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)


# ---------------------------------------------------------------------------
# ProxyPoolLoader
# ---------------------------------------------------------------------------
@dataclass
class ProxyInfo:
    """Metadata for a single proxy."""

    url: str
    auth: Optional[Dict[str, str]] = None
    weight: float = 1.0
    tags: List[str] = field(default_factory=list)
    source: str = "config"


class ProxyPoolLoader:
    """Load and manage a pool of HTTP proxies.

    Sources (in priority order):
      1. Local JSON config (``PROXY_POOL_CONFIG``).
      2. Proxy-sources config (``PROXY_SOURCES_CONFIG``) — may contain
         GitHub raw URLs to fetch additional proxy lists.
      3. OWL enrichment (when ``OWL_ENRICH_ENABLED`` is set).
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._config_path: str = config_path or ENV_PROXY_POOL_CONFIG
        self._proxies: List[ProxyInfo] = []
        self._loaded: bool = False

    # -- loading -------------------------------------------------------------

    async def load(self) -> List[ProxyInfo]:
        """Load proxies from all configured sources."""
        self._proxies.clear()

        # Tier 1: local JSON config
        await self._load_from_config()

        # Tier 2: proxy sources (GitHub lists, etc.)
        await self._load_from_sources()

        # Tier 3: OWL enrichment
        if ENV_OWL_ENRICH_ENABLED:
            await self._enrich_from_owl()

        self._loaded = True
        logger.info(
            "ProxyPoolLoader: loaded %d proxy(es) from %s",
            len(self._proxies),
            self._config_path,
        )
        return self._proxies

    async def _load_from_config(self) -> None:
        """Load proxies from the primary JSON config file."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            logger.warning("Proxy config not found: %s", self._config_path)
            return
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in %s: %s", self._config_path, exc)
            return

        entries = data if isinstance(data, list) else data.get("proxies", [])
        for entry in entries:
            info = ProxyInfo(
                url=entry.get("url", entry.get("host", "")),
                auth=self._extract_auth(entry),
                weight=float(entry.get("weight", 1.0)),
                tags=entry.get("tags", []),
                source="config",
            )
            if info.url:
                self._proxies.append(info)

    async def _load_from_sources(self) -> None:
        """Fetch additional proxies from sources config (GitHub lists, etc.)."""
        try:
            with open(ENV_PROXY_SOURCES_CONFIG, "r", encoding="utf-8") as fh:
                sources = json.load(fh)
        except FileNotFoundError:
            logger.debug("Proxy sources config not found: %s", ENV_PROXY_SOURCES_CONFIG)
            return
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in %s: %s", ENV_PROXY_SOURCES_CONFIG, exc)
            return

        source_list = sources if isinstance(sources, list) else sources.get("sources", [])
        for src in source_list:
            url = src.get("url", "")
            if not url:
                continue
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status != 200:
                            logger.warning("Source %s returned HTTP %d", url, resp.status)
                            continue
                        text = await resp.text()
                for line in text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Accept formats: host:port, http://host:port, etc.
                    proxy_url = line if "://" in line else f"http://{line}"
                    self._proxies.append(
                        ProxyInfo(
                            url=proxy_url,
                            weight=float(src.get("weight", 0.5)),
                            tags=src.get("tags", []),
                            source="github",
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to fetch proxy source %s: %s", url, exc)

    async def _enrich_from_owl(self) -> None:
        """Enrich proxy metadata when OWL_ENRICH_ENABLED is set.

        This is a placeholder for integration with the OWL enrichment
        pipeline.  In production it would call an internal API to annotate
        proxies with geo, latency, and reliability data.
        """
        logger.info("OWL enrichment enabled — annotating %d proxies", len(self._proxies))
        for proxy in self._proxies:
            # Placeholder: in real usage, call OWL enrichment API here.
            proxy.tags.append("owl-enriched")

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _extract_auth(entry: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract username/password from a proxy config entry."""
        username = entry.get("username") or entry.get("user")
        password = entry.get("password") or entry.get("pass")
        if username and password:
            return {"username": username, "password": password}
        return None

    # -- public interface ----------------------------------------------------

    @property
    def proxies(self) -> List[ProxyInfo]:
        """Return current proxy list (may be empty if not yet loaded)."""
        return list(self._proxies)

    async def reload(self) -> List[ProxyInfo]:
        """Force a full reload of the proxy pool."""
        return await self.load()


# ---------------------------------------------------------------------------
# Weighted proxy selector
# ---------------------------------------------------------------------------
class WeightedProxySelector:
    """Select proxies with weighted random distribution, preferring ones
    whose circuit breaker is CLOSED and that have a higher weight."""

    def __init__(self, proxies: List[ProxyInfo], breakers: Dict[str, CircuitBreaker]) -> None:
        self._proxies: List[ProxyInfo] = proxies
        self._breakers: Dict[str, CircuitBreaker] = breakers

    def select(self) -> Optional[ProxyInfo]:
        """Return a proxy selected by weighted random choice.

        Proxies with an OPEN circuit breaker receive zero weight.  HALF_OPEN
        proxies receive a reduced weight so the probe request is tried but
        not flooded.
        """
        if not self._proxies:
            return None

        weights: List[float] = []
        for p in self._proxies:
            breaker = self._breakers.get(p.url)
            if breaker is None:
                weights.append(p.weight)
                continue
            state = breaker.state
            if state is CircuitState.OPEN:
                weights.append(0.0)
            elif state is CircuitState.HALF_OPEN:
                weights.append(p.weight * 0.1)
            else:
                weights.append(p.weight)

        total = sum(weights)
        if total <= 0:
            # All circuits open — fall back to round-robin so we don't
            # permanently block.
            return self._proxies[0]

        # Weighted random selection.
        import random

        r = random.uniform(0, total)
        cumulative = 0.0
        for proxy, w in zip(self._proxies, weights):
            cumulative += w
            if r <= cumulative:
                return proxy

        return self._proxies[-1]


# ---------------------------------------------------------------------------
# Deduplication middleware (in-flight request coalescing)
# ---------------------------------------------------------------------------
class RequestDeduplicator:
    """Coalesce duplicate in-flight requests for the same resource.

    When multiple callers request the same URL+method+kwargs concurrently,
    only one actual HTTP request is made; all callers share the result.
    """

    def __init__(self) -> None:
        self._in_flight: Dict[str, asyncio.Event] = {}
        self._results: Dict[str, Any] = {}

    def _key(self, url: str, method: str, **kwargs: Any) -> str:
        h = hashlib.sha256()
        h.update(f"{method.upper()}|{url}".encode())
        for k in sorted(kwargs):
            h.update(f"|{k}={kwargs[k]}".encode())
        return h.hexdigest()

    async def deduplicate(
        self,
        url: str,
        method: str,
        factory,  # Callable[[], Awaitable[Response]]
        **kwargs: Any,
    ):
        """If a request for *url/method* is already in flight, wait for it;
        otherwise, start a new one via *factory*."""
        key = self._key(url, method, **kwargs)

        # Check if already in flight.
        if key in self._in_flight:
            logger.debug("Dedup: coalescing request for %s %s", method, url)
            await self._in_flight[key].wait()
            return self._results.get(key)

        # New request — register the event.
        event = asyncio.Event()
        self._in_flight[key] = event
        try:
            result = await factory()
            self._results[key] = result
            return result
        finally:
            event.set()
            # Clean up after a short grace period so late waiters can
            # still read the result.
            asyncio.get_event_loop().call_later(
                1.0, self._cleanup, key
            )

    def _cleanup(self, key: str) -> None:
        self._in_flight.pop(key, None)
        self._results.pop(key, None)


# ---------------------------------------------------------------------------
# Fallback response for when everything fails
# ---------------------------------------------------------------------------
class _FallbackResponse:
    """Minimal response-like object returned when all retries are exhausted."""

    def __init__(self, url: str, status: int = 503) -> None:
        self.url = url
        self.status = status
        self.reason = "All Proxies Exhausted"
        self._body: bytes = b""
        self.headers: Dict[str, str] = {}

    async def read(self) -> bytes:
        return self._body

    async def text(self) -> str:
        return self._body.decode("utf-8", errors="replace")

    async def json(self) -> Any:
        return {}

    def release(self) -> None:
        pass


# ---------------------------------------------------------------------------
# ResilientHTTPClient
# ---------------------------------------------------------------------------
class ResilientHTTPClient:
    """Production-grade resilient HTTP client with 5-tier escalation.

    Tier 1 — Weighted proxy rotation (prefer working proxies)
    Tier 2 — Circuit breaker (3 failures → OPEN for 60 s, then HALF_OPEN)
    Tier 3 — Request deduplication (in-flight coalescing)
    Tier 4 — Response caching with TTL (300 s default)
    Tier 5 — Domain rate limiting (asyncio.Semaphore, not recursive acquire)
    """

    MAX_PROXY_RETRIES: int = 5

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._pool_loader = ProxyPoolLoader(config_path=config_path)
        self._cache = ResponseCache(ttl=ENV_CACHE_TTL)
        self._dedup = RequestDeduplicator()
        self._rate_limiter = DomainRateLimiter()
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._session: Optional[aiohttp.ClientSession] = None

        # v6.0 bug fix — stats are now tracked properly via get_stats().
        self._stats: Dict[str, int] = {
            "total_requests": 0,
            "success_count": 0,
            "failure_count": 0,
            "cache_hits": 0,
            "circuit_breaker_trips": 0,
        }

        self._proxies_loaded: bool = False

    # -- lifecycle -----------------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Lazily create (or return existing) aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _ensure_proxies(self) -> None:
        """Load the proxy pool on first use."""
        if not self._proxies_loaded:
            await self._pool_loader.load()
            # Pre-create circuit breakers for each proxy.
            for proxy in self._pool_loader.proxies:
                if proxy.url not in self._circuit_breakers:
                    self._circuit_breakers[proxy.url] = CircuitBreaker()
            self._proxies_loaded = True

    async def close(self) -> None:
        """Close the underlying aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # -- Tier 4: caching -----------------------------------------------------

    def _cache_hit(self, url: str, method: str, **kwargs: Any) -> Optional[Any]:
        """Return cached response if available, else ``None``."""
        entry = self._cache.get(url, method, **kwargs)
        if entry is not None:
            self._stats["cache_hits"] += 1
            logger.debug("Cache HIT for %s %s", method, url)
        return entry

    # -- Tier 5: domain rate limiting ----------------------------------------

    async def _rate_limit_acquire(self, domain: str) -> None:
        """Acquire a rate-limit permit for *domain*."""
        await self._rate_limiter.acquire(domain)

    def _rate_limit_release(self, domain: str) -> None:
        """Release a rate-limit permit for *domain*."""
        self._rate_limiter.release(domain)

    # -- Domain extraction ---------------------------------------------------

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract the hostname from *url* for rate-limiting purposes."""
        try:
            from urllib.parse import urlparse

            return urlparse(url).hostname or "unknown"
        except Exception:  # noqa: BLE001
            return "unknown"

    # -- Tier 1 + Tier 2: proxy selection with circuit breaker ---------------

    def _select_proxy(self) -> Optional[ProxyInfo]:
        """Weighted proxy selection that respects circuit-breaker state."""
        selector = WeightedProxySelector(
            self._pool_loader.proxies, self._circuit_breakers
        )
        return selector.select()

    # -- Core fetch ----------------------------------------------------------

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        **kwargs: Any,
    ):
        """Main entry point — execute a resilient HTTP request.

        Escalation order:
          1. Check cache (Tier 4).
          2. Check deduplication (Tier 3).
          3. Acquire domain rate-limit permit (Tier 5).
          4. Select proxy via weighted rotation (Tier 1), respecting circuit
             breaker state (Tier 2).
          5. Execute the request; on failure, rotate proxy and retry.

        Returns:
            An ``aiohttp.ClientResponse``-like object.
        """
        self._stats["total_requests"] += 1
        await self._ensure_proxies()

        # --- Tier 4: cache ---
        cached = self._cache_hit(url, method, **kwargs)
        if cached is not None:
            return cached

        # --- Tier 3: deduplication ---
        async def _do_fetch():
            return await self._fetch_inner(url, method, **kwargs)

        result = await self._dedup.deduplicate(url, method, _do_fetch, **kwargs)
        return result

    async def _fetch_inner(self, url: str, method: str, **kwargs: Any):
        """Inner fetch logic, called after cache miss and dedup check."""
        domain = self._extract_domain(url)

        # --- Tier 5: rate limiting ---
        await self._rate_limit_acquire(domain)
        try:
            return await self._fetch_with_proxy_rotation(url, method, **kwargs)
        finally:
            self._rate_limit_release(domain)

    async def _fetch_with_proxy_rotation(
        self, url: str, method: str, **kwargs: Any
    ):
        """Try up to ``MAX_PROXY_RETRIES`` different proxies."""
        last_exception: Optional[Exception] = None
        tried: set[str] = set()

        for attempt in range(self.MAX_PROXY_RETRIES):
            proxy = self._select_proxy()

            # No proxies available at all.
            if proxy is None:
                logger.warning("No proxies available — making direct request")
                return await self._direct_request(url, method, **kwargs)

            # All unique proxies exhausted.
            if proxy.url in tried:
                # If we've tried every proxy once, allow repeats but log it.
                logger.warning(
                    "All %d unique proxies exhausted, retrying with %s",
                    len(tried),
                    proxy.url,
                )
            tried.add(proxy.url)

            # --- Tier 2: circuit breaker check ---
            breaker = self._circuit_breakers.get(proxy.url)
            if breaker and not breaker.allow_request():
                self._stats["circuit_breaker_trips"] += 1
                logger.debug("Circuit OPEN for proxy %s, skipping", proxy.url)
                continue

            try:
                response = await self._execute_via_proxy(proxy, url, method, **kwargs)
                # Success — record it.
                if breaker:
                    breaker.record_success()
                self._stats["success_count"] += 1

                # Tier 4: cache the response for non-mutating methods.
                if method.upper() in ("GET", "HEAD", "OPTIONS"):
                    body = await response.read()
                    self._cache.put(url, method, response, body, **kwargs)

                return response

            except Exception as exc:  # noqa: BLE001
                last_exception = exc
                if breaker:
                    breaker.record_failure()
                self._stats["failure_count"] += 1
                logger.warning(
                    "Proxy %s failed (attempt %d/%d): %s",
                    proxy.url,
                    attempt + 1,
                    self.MAX_PROXY_RETRIES,
                    exc,
                )

        # All retries exhausted.
        logger.error(
            "All proxy retries exhausted for %s %s: %s",
            method,
            url,
            last_exception,
        )
        return _FallbackResponse(url)

    async def _execute_via_proxy(
        self,
        proxy: ProxyInfo,
        url: str,
        method: str,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        """Execute a single HTTP request through *proxy*."""
        session = await self._ensure_session()

        proxy_url = proxy.url
        proxy_auth = None
        if proxy.auth:
            proxy_auth = aiohttp.BasicAuth(
                login=proxy.auth["username"],
                password=proxy.auth["password"],
            )

        # Merge timeout with a sensible default.
        timeout = kwargs.pop("timeout", aiohttp.ClientTimeout(total=30))

        async with session.request(
            method,
            url,
            proxy=proxy_url,
            proxy_auth=proxy_auth,
            timeout=timeout,
            **kwargs,
        ) as resp:
            # Read the body so it is available after the context manager
            # exits (needed for caching).
            await resp.read()
            return resp

    async def _direct_request(
        self, url: str, method: str, **kwargs: Any
    ) -> aiohttp.ClientResponse:
        """Make a direct request without any proxy."""
        session = await self._ensure_session()
        timeout = kwargs.pop("timeout", aiohttp.ClientTimeout(total=30))

        async with session.request(method, url, timeout=timeout, **kwargs) as resp:
            await resp.read()
            self._stats["success_count"] += 1
            return resp

    # -- v6.0 bug fix: get_stats() ------------------------------------------

    def get_stats(self) -> dict:
        """Return operational statistics.

        v6.0 bug fix: ``owl_resilient_mcp.py`` previously referenced
        ``self._stats`` on the client which did not exist.  This method
        provides the canonical stats interface.
        """
        return dict(self._stats)

    # -- cache management ----------------------------------------------------

    def clear_cache(self) -> None:
        """Clear the entire response cache."""
        self._cache.clear()
        logger.info("Response cache cleared")

    # -- health check --------------------------------------------------------

    async def health(self) -> dict:
        """Return health status of all known proxies.

        Each proxy is probed with a lightweight HEAD request and its
        circuit-breaker state is reported.
        """
        await self._ensure_proxies()
        results: Dict[str, Any] = {}

        for proxy in self._pool_loader.proxies:
            breaker = self._circuit_breakers.get(proxy.url)
            cb_state = breaker.state.name if breaker else "UNKNOWN"
            healthy = cb_state in ("CLOSED", "HALF_OPEN")

            # Attempt a lightweight probe.
            probe_ok = False
            if healthy:
                try:
                    session = await self._ensure_session()
                    async with session.head(
                        "https://httpbin.org/status/200",
                        proxy=proxy.url,
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        probe_ok = resp.status < 500
                except Exception:  # noqa: BLE001
                    probe_ok = False

            results[proxy.url] = {
                "circuit_breaker": cb_state,
                "healthy": healthy and probe_ok,
                "weight": proxy.weight,
                "tags": proxy.tags,
                "source": proxy.source,
            }

        return results


# ---------------------------------------------------------------------------
# Standalone CLI (optional)
# ---------------------------------------------------------------------------
async def _main() -> None:
    """Quick smoke-test when run as a script."""
    client = ResilientHTTPClient()
    try:
        resp = await client.fetch("https://httpbin.org/get")
        print(f"Status : {resp.status}")
        body = await resp.text()
        print(f"Body   : {body[:200]}...")
        print(f"Stats  : {client.get_stats()}")
        print(f"Health : {await client.health()}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(_main())
