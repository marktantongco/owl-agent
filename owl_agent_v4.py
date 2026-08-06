#!/usr/bin/env python3
"""
🦉 OWL-AGENT v4 HYBRID — Unified Proxy Defense Stack
- ProxyBroker2-powered discovery (50+ sources, 7k+ proxies)
- Judge server validation (proactive health checks)
- owl-agent resilience (cache, dedup, rate-limit, single-strike ban, direct fallback)
- Production-ready with CLI + library modes
"""

import asyncio
import json
import time
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, AsyncGenerator, Callable, Awaitable
from pathlib import Path
from urllib.parse import urlparse

try:
    import aiohttp
    import aiofiles
    HTTP_CLIENT_OK = True
except ImportError:
    HTTP_CLIENT_OK = False
    logger = logging.getLogger("owl-agent")
    logger.error("Missing 'aiohttp' or 'aiofiles'. Install: pip install aiohttp aiofiles")

# ProxyBroker2 integration (optional, graceful fallback)
try:
    from proxybroker import Broker
    PROXYBROKER_OK = True
except (ImportError, RuntimeError):
    PROXYBROKER_OK = False

CACHE_DIR = Path.home() / ".owl-agent" / "cache" / "http"
CONFIG_DIR = Path.home() / ".owl-agent" / "config"
PROXY_SCORE_FILE = CONFIG_DIR / "proxy_scores.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TTL = 300
DEFAULT_RATE = 1.0
MAX_RETRIES = 2
JUDGE_SERVERS = [
    "http://httpbin.org/ip",
    "https://api.ipify.org?format=json",
    "http://ip.oxylabs.io/",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("owl-agent.v4")


@dataclass
class ProxyScore:
    url: str
    latency_ms: float = 9999.0
    success_count: int = 0
    fail_count: int = 0
    last_validated: float = 0.0
    ban_until: float = 0.0

    def score(self) -> float:
        """Proxy score: lower latency + higher success rate = higher score."""
        if self.is_banned():
            return 0.0
        success_rate = (
            self.success_count / (self.success_count + self.fail_count + 1)
        )
        return success_rate * (1000.0 / (self.latency_ms + 1))

    def is_banned(self) -> bool:
        return time.time() < self.ban_until

    def mark_failed(self):
        self.fail_count += 1
        self.ban_until = time.time() + 60  # Single-strike ban
        logger.warning(f"Proxy banned (60s): {self.url}")

    def mark_success(self, latency_ms: float):
        self.success_count += 1
        self.latency_ms = latency_ms
        self.last_validated = time.time()


@dataclass
class CachedResponse:
    status: int
    content: bytes
    headers: Dict[str, str]
    timestamp: float
    ttl: int
    protocol: str = "http/1.1"

    def is_fresh(self) -> bool:
        return time.time() - self.timestamp < self.ttl


@dataclass
class TokenBucket:
    rate: float
    capacity: float
    tokens: float = 0.0
    last_update: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def _replenish(self):
        now = time.time()
        elapsed = now - self.last_update
        async with self.lock:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

    async def acquire(self, tokens: float = 1.0) -> bool:
        await self._replenish()
        async with self.lock:
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
        wait_time = (tokens - self.tokens) / self.rate
        await asyncio.sleep(wait_time)
        return await self.acquire(tokens)


class ProxyScorer:
    """Load, persist, and rank proxies by performance."""

    def __init__(self, score_file: Path = PROXY_SCORE_FILE):
        self.score_file = score_file
        self.scores: Dict[str, ProxyScore] = {}
        self._lock = asyncio.Lock()
        self._load()

    def _load(self):
        if not self.score_file.exists():
            return
        try:
            with open(self.score_file) as f:
                data = json.load(f)
                for url, score_data in data.items():
                    ps = ProxyScore(
                        url=url,
                        latency_ms=score_data.get("latency_ms", 9999.0),
                        success_count=score_data.get("success_count", 0),
                        fail_count=score_data.get("fail_count", 0),
                        last_validated=score_data.get("last_validated", 0.0),
                        ban_until=score_data.get("ban_until", 0.0),
                    )
                    self.scores[url] = ps
        except Exception as e:
            logger.warning(f"Failed to load proxy scores: {e}")

    async def save(self):
        """Persist scores to disk."""
        async with self._lock:
            data = {
                url: {
                    "latency_ms": score.latency_ms,
                    "success_count": score.success_count,
                    "fail_count": score.fail_count,
                    "last_validated": score.last_validated,
                    "ban_until": score.ban_until,
                }
                for url, score in self.scores.items()
            }
        async with aiofiles.open(self.score_file, "w") as f:
            await f.write(json.dumps(data, indent=2))

    async def get_score(self, url: str) -> ProxyScore:
        async with self._lock:
            if url not in self.scores:
                self.scores[url] = ProxyScore(url=url)
            return self.scores[url]

    async def rank(self) -> List[ProxyScore]:
        """Return proxies ranked by score (highest first)."""
        async with self._lock:
            ranked = sorted(
                self.scores.values(), key=lambda p: p.score(), reverse=True
            )
        return [p for p in ranked if not p.is_banned()]


class ProxyDiscovery:
    """Discover proxies via ProxyBroker2 or fallback to manual sources."""

    def __init__(self, scorer: ProxyScorer):
        self.scorer = scorer
        self.discovered: set = set()

    async def discover_proxybroker2(
        self, limit: int = 100
    ) -> AsyncGenerator[str, None]:
        """Discover proxies from ProxyBroker2 (50+ sources)."""
        if not PROXYBROKER_OK:
            logger.warning("ProxyBroker2 not installed. Skipping auto-discovery.")
            return

        try:
            logger.info(f"ProxyBroker2: Discovering up to {limit} proxies...")
            proxies_queue = asyncio.Queue()
            broker = Broker(proxies_queue)

            async def collect_proxies():
                count = 0
                while count < limit:
                    try:
                        proxy = await asyncio.wait_for(
                            proxies_queue.get(), timeout=1.0
                        )
                        if proxy is None:
                            break
                        url = str(proxy)
                        if url not in self.discovered:
                            self.discovered.add(url)
                            yield url
                            count += 1
                    except asyncio.TimeoutError:
                        break

            # Run broker find in parallel
            find_task = asyncio.create_task(
                broker.find(
                    types=["HTTP", "HTTPS"],
                    limit=limit,
                    judge=JUDGE_SERVERS,
                    timeout=10,
                )
            )

            async for proxy_url in collect_proxies():
                yield proxy_url

            await find_task
        except Exception as e:
            logger.error(f"ProxyBroker2 discovery failed: {e}")

    async def discover_manual_sources(self) -> AsyncGenerator[str, None]:
        """Fallback: discover from GitHub, public APIs, and HTTPS-specific sources."""
        sources = [
            (
                "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/all/data.json",
                "json",
                True,
            ),
            (
                "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text&limit=100",
                "text",
                False,
            ),
            (
                "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
                "text",
                False,
            ),
            (
                "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
                "text",
                False,
            ),
            (
                "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
                "text",
                True,
            ),
            (
                "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
                "text",
                True,
            ),
        ]

        async with aiohttp.ClientSession() as session:
            for url, fmt, is_https in sources:
                try:
                    logger.info(f"Fetching proxies from: {url}")
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status != 200:
                            continue

                        if fmt == "json":
                            data = await resp.json()
                            items = (
                                data.get("data", [])
                                if isinstance(data, dict)
                                else data
                            )
                            for item in items[:50]:
                                ip = item.get("ip", item.get("host", ""))
                                port = item.get("port", "")
                                if ip and port:
                                    protocol = item.get("protocol", "http")
                                    scheme = "https" if protocol == "https" else "http"
                                    url = f"{scheme}://{ip}:{port}"
                                    if url not in self.discovered:
                                        self.discovered.add(url)
                                        yield url
                        else:
                            text = await resp.text()
                            for line in text.strip().split("\n")[:50]:
                                if ":" in line and not line.startswith("#"):
                                    url = f"{scheme}://{line.strip()}"
                                    if url not in self.discovered:
                                        self.discovered.add(url)
                                        yield url
                except Exception as e:
                    logger.warning(f"Manual discovery failed ({url}): {e}")

    async def discover_all(self, limit: int = 200) -> List[str]:
        """Discover proxies from all sources (ProxyBroker2 first, fallback to manual)."""
        proxies = []

        # Try ProxyBroker2 first
        if PROXYBROKER_OK:
            async for proxy_url in self.discover_proxybroker2(limit // 2):
                proxies.append(proxy_url)
                if len(proxies) >= limit:
                    return proxies

        # Fallback to manual sources
        async for proxy_url in self.discover_manual_sources():
            proxies.append(proxy_url)
            if len(proxies) >= limit:
                return proxies

        logger.info(f"Discovered {len(proxies)} total proxies")
        return proxies


class HTTPCache:
    """HTTP response caching (memory + disk)."""

    def __init__(self, ttl: int = DEFAULT_TTL):
        self.ttl = ttl
        self._memory: Dict[str, CachedResponse] = {}
        self._lock = asyncio.Lock()

    def _key(self, method: str, url: str, params: Optional[Dict] = None) -> str:
        return hashlib.sha256(
            f"{method}:{url}:{json.dumps(params or {}, sort_keys=True)}".encode()
        ).hexdigest()

    async def get(
        self, method: str, url: str, params: Optional[Dict] = None
    ) -> Optional[CachedResponse]:
        key = self._key(method, url, params)
        if key in self._memory and self._memory[key].is_fresh():
            return self._memory[key]
        path = CACHE_DIR / f"{key}.json"
        if path.exists():
            try:
                async with aiofiles.open(path, "r") as f:
                    data = json.loads(await f.read())
                cached = CachedResponse(
                    status=data["status"],
                    content=data["content"].encode("utf-8", errors="replace"),
                    headers=data["headers"],
                    timestamp=data["timestamp"],
                    ttl=data["ttl"],
                )
                if cached.is_fresh():
                    async with self._lock:
                        self._memory[key] = cached
                    return cached
                else:
                    path.unlink()
            except Exception:
                pass
        return None

    async def set(
        self, method: str, url: str, response: CachedResponse, params: Optional[Dict] = None
    ):
        key = self._key(method, url, params)
        async with self._lock:
            self._memory[key] = response
        path = CACHE_DIR / f"{key}.json"
        data = {
            "status": response.status,
            "content": response.content.decode("utf-8", errors="replace"),
            "headers": response.headers,
            "timestamp": response.timestamp,
            "ttl": response.ttl,
        }
        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(data))


class DomainRateLimiter:
    """Per-domain token bucket rate limiting."""

    def __init__(self, default_rate: float = DEFAULT_RATE):
        self.default_rate = default_rate
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, url: str, tokens: float = 1.0):
        domain = urlparse(url).netloc or url
        async with self._lock:
            if domain not in self._buckets:
                self._buckets[domain] = TokenBucket(
                    rate=self.default_rate, capacity=5.0, tokens=5.0
                )
        await self._buckets[domain].acquire(tokens)


class RequestDeduplicator:
    """Deduplicate in-flight requests."""

    def __init__(self):
        self._in_flight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    def _key(self, method: str, url: str, params: Optional[Dict] = None) -> str:
        return hashlib.sha256(
            f"{method}:{url}:{json.dumps(params or {}, sort_keys=True)}".encode()
        ).hexdigest()

    async def execute(
        self,
        method: str,
        url: str,
        params: Optional[Dict],
        factory: Callable[[], Awaitable[CachedResponse]],
    ) -> CachedResponse:
        key = self._key(method, url, params)
        async with self._lock:
            if key in self._in_flight:
                return await self._in_flight[key]
            future = asyncio.Future()
            self._in_flight[key] = future
        try:
            result = await factory()
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            async with self._lock:
                self._in_flight.pop(key, None)


class ResilientClient:
    """Main resilient HTTP client with proxy rotation, caching, and fallback."""

    def __init__(
        self,
        cache_ttl: int = DEFAULT_TTL,
        rate_limit: float = DEFAULT_RATE,
        max_retries: int = MAX_RETRIES,
    ):
        self.cache = HTTPCache(cache_ttl)
        self.dedup = RequestDeduplicator()
        self.limiter = DomainRateLimiter(rate_limit)
        self.scorer = ProxyScorer()
        self.discovery = ProxyDiscovery(self.scorer)
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
        self.proxies: List[str] = []

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            force_close=True, enable_cleanup_closed=True, limit=10
        )
        self._session = aiohttp.ClientSession(connector=connector)
        await self.discover_proxies()
        return self

    async def __aexit__(self, *args):
        await self.scorer.save()
        if self._session:
            await self._session.close()

    async def discover_proxies(self, limit: int = 200):
        """Auto-discover proxies."""
        self.proxies = await self.discovery.discover_all(limit)
        logger.info(f"Loaded {len(self.proxies)} proxies into rotation pool")

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs,
    ) -> CachedResponse:
        """Make HTTP request with caching, deduplication, and proxy rotation."""
        cached = await self.cache.get(method, url, params)
        if cached:
            logger.debug(f"Cache hit: {method} {url}")
            return cached

        async def factory():
            return await self._execute_with_retry(method, url, params, headers, **kwargs)

        return await self.dedup.execute(method, url, params, factory)

    async def _execute_with_retry(self, method, url, params, headers, **kwargs):
        """Execute request with proxy rotation and fallback to direct."""
        ranked_proxies = await self.scorer.rank()

        # Try ranked proxies first
        for attempt, proxy_score in enumerate(ranked_proxies):
            if attempt >= self.max_retries:
                break
            await self.limiter.acquire(url)
            try:
                start = time.time()
                async with self._session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    proxy=proxy_score.url,
                    timeout=aiohttp.ClientTimeout(total=30),
                    **kwargs,
                ) as resp:
                    content = await resp.read()
                latency = (time.time() - start) * 1000
                response = CachedResponse(
                    status=resp.status,
                    content=content,
                    headers=dict(resp.headers),
                    timestamp=time.time(),
                    ttl=self.cache.ttl,
                )
                await proxy_score.mark_success(latency)
                await self.cache.set(method, url, response, params)

                if resp.status in (429, 403, 407):
                    proxy_score.mark_failed()
                    logger.warning(f"Proxy rate limited: {proxy_score.url}")
                    continue

                return response
            except Exception as e:
                proxy_score.mark_failed()
                logger.warning(
                    f"Proxy failed ({proxy_score.url}): {e}, retry {attempt + 1}"
                )
                continue

        # Try unranked proxies (first time seeing them)
        unranked = [p for p in self.proxies if p not in [s.url for s in ranked_proxies]]
        for attempt, proxy_url in enumerate(unranked):
            if attempt >= self.max_retries:
                break
            await self.limiter.acquire(url)
            try:
                start = time.time()
                async with self._session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=30),
                    **kwargs,
                ) as resp:
                    content = await resp.read()
                latency = (time.time() - start) * 1000
                response = CachedResponse(
                    status=resp.status,
                    content=content,
                    headers=dict(resp.headers),
                    timestamp=time.time(),
                    ttl=self.cache.ttl,
                )
                score = await self.scorer.get_score(proxy_url)
                await score.mark_success(latency)
                await self.cache.set(method, url, response, params)
                return response
            except Exception as e:
                score = await self.scorer.get_score(proxy_url)
                score.mark_failed()
                logger.warning(f"Proxy failed ({proxy_url}): {e}")
                continue

        # All proxies failed → direct connection fallback
        logger.info("All proxies exhausted, attempting direct connection...")
        try:
            async with self._session.request(
                method,
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
                **kwargs,
            ) as resp:
                content = await resp.read()
            response = CachedResponse(
                status=resp.status,
                content=content,
                headers=dict(resp.headers),
                timestamp=time.time(),
                ttl=self.cache.ttl,
            )
            await self.cache.set(method, url, response, params)
            return response
        except Exception as e:
            raise RuntimeError(f"Direct connection also failed: {e}")

    async def get_stats(self):
        """Return proxy pool statistics."""
        ranked = await self.scorer.rank()
        healthy = len(ranked)
        return {
            "proxies_total": len(self.proxies),
            "proxies_healthy": healthy,
            "proxies_banned": len(self.proxies) - healthy,
        }


async def main():
    """Demo: fetch GitHub API with proxy rotation."""
    print("🦉 OWL-AGENT v4 HYBRID — Proxy Defense Stack")
    print("=" * 50)

    async with ResilientClient() as client:
        stats = await client.get_stats()
        print(f"Proxy pool: {stats['proxies_total']} total, {stats['proxies_healthy']} healthy")
        print()

        try:
            url = "https://api.github.com/users/octocat"
            print(f"Fetching: {url}")
            resp = await client.request("GET", url)
            print(f"✅ Status: {resp.status}")
            if resp.status == 200:
                data = json.loads(resp.content)
                print(f"   User: {data.get('login')} - {data.get('name')}")
            print()

            # Second request (should hit cache)
            print(f"Fetching again (should hit cache): {url}")
            resp2 = await client.request("GET", url)
            print(f"✅ Status: {resp2.status} (cached)")
        except Exception as e:
            print(f"❌ Request failed: {e}")

        # Final stats
        stats = await client.get_stats()
        print()
        print(f"Final stats: {stats['proxies_healthy']}/{stats['proxies_total']} proxies healthy")


if __name__ == "__main__":
    asyncio.run(main())
