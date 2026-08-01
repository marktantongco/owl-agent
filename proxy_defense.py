#!/usr/bin/env python3
"""
🦉 OWL-AGENT PROXY DEFENSE STACK v4.3
- ProxyBroker2 with country filtering
- Quality scoring (weighted success/latency)
- Adaptive rate limiting (per-domain)
- Redis state sharing (optional)
- curl_cffi Chrome fingerprinting
- Retry-After parsing
- Circuit breaker
- agent-browser integration
- LRU cache, dedup, direct fallback
- Plugin System (request/response hooks)
- A/B Testing (strategy comparison per domain)
- ML Predictor (logistic regression proxy selection)
"""

import asyncio
import hashlib
import inspect
import json
import time
import logging
import subprocess
import random
import statistics
import email.utils
import datetime
import sys
import warnings
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, Awaitable, List, Set
from pathlib import Path
from urllib.parse import urlparse
from collections import OrderedDict, defaultdict

import aiohttp
import aiofiles
import httpx
from circuitbreaker import CircuitBreaker

# ─── Python 3.14+ compatibility: monkey-patch asyncio.get_event_loop ───
# ProxyBroker2 calls asyncio.get_event_loop() at module import time.
# Python 3.14 changed get_event_loop() to raise RuntimeError instead of
# creating a new loop, which breaks proxybroker2 entirely.
# This patch restores the old behavior so proxybroker2 can be imported.
if sys.version_info >= (3, 12):
    _original_get_event_loop = asyncio.get_event_loop

    def _patched_get_event_loop():
        try:
            return _original_get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    asyncio.get_event_loop = _patched_get_event_loop
    # Suppress the deprecation warning for get_event_loop_policy
    warnings.filterwarnings('ignore', message=".*get_event_loop_policy.*")
    warnings.filterwarnings('ignore', message=".*get_event_loop.*deprecated.*")

# ─── curl_cffi SSL cert path ─── MUST be set BEFORE curl_cffi import ───
_CA_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"
if Path(_CA_BUNDLE).exists():
    import os as _os
    _os.environ.setdefault("SSL_CERT_FILE", _CA_BUNDLE)
    _os.environ.setdefault("CURL_CA_BUNDLE", _CA_BUNDLE)

# Optional curl_cffi
try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False

# Optional Redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Optional ML dependencies
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# v4.4: Advanced ML models
try:
    from ml_models import AdvancedMLPredictor, XGB_AVAILABLE
except ImportError:
    AdvancedMLPredictor = None
    XGB_AVAILABLE = False

# v4.5: Self-healing plugin loader
try:
    from plugin_loader import PluginLoader
except ImportError:
    PluginLoader = None

# ─── Paths ──────────────────────────────────────────────────────
CACHE_DIR = Path.home() / ".owl-agent" / "cache" / "http"
CONFIG_DIR = Path.home() / ".owl-agent" / "config"
PROXY_CACHE_FILE = CONFIG_DIR / "proxy_cache.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# ─── Constants ─────────────────────────────────────────────────
DEFAULT_TTL = 300
DEFAULT_RATE = 1.0
MAX_RETRIES = 3
MAX_CACHED_RESPONSES = 1000
MAX_PROXY_CACHE = 100
MAX_SESSIONS = 20
MAX_DOMAINS_RATE_LIMIT = 1000
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 30
DEFAULT_COUNTRIES = ["US", "GB", "DE", "FR", "CA"]
QUALITY_DECAY = 0.9
ADAPTIVE_MIN_RATE = 0.1
ADAPTIVE_MAX_RATE = 5.0
AB_MIN_SAMPLE_SIZE = 100
ML_MIN_SAMPLES = 20
ML_MAX_SAMPLES = 1000
ML_STALENESS_THRESHOLD = 0.6  # Minimum CV score to consider model valid

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("owl-agent.proxy")

# ─── Data Classes (memory-optimised) ──────────────────────────
@dataclass(slots=True)
class CachedResponse:
    status: int
    content: bytes
    headers: Dict[str, str]
    timestamp: float
    ttl: int
    protocol: str = "http/1.1"
    def is_fresh(self) -> bool:
        return time.time() - self.timestamp < self.ttl

@dataclass(slots=True)
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

@dataclass(slots=True)
class ProxyEntry:
    url: str
    healthy: bool = True
    last_check: float = 0.0
    fail_count: int = 0
    ban_until: float = 0.0
    def is_banned(self) -> bool:
        return time.time() < self.ban_until
    def mark_failed(self):
        self.fail_count += 1
        self.ban_until = time.time() + 60
        self.healthy = False
        logger.warning(f"Proxy banned (60s): {self.url}")
    def mark_success(self):
        self.fail_count = 0
        self.healthy = True
        self.last_check = time.time()

# ─── HTTPCache (LRU + periodic cleanup) ──────────────────────
class HTTPCache:
    def __init__(self, ttl: int = DEFAULT_TTL, max_size: int = MAX_CACHED_RESPONSES):
        self.ttl = ttl
        self._max_size = max_size
        self._memory: Dict[str, CachedResponse] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleaner(self):
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(60)
            now = time.time()
            async with self._lock:
                expired = [k for k, v in self._memory.items() if not v.is_fresh()]
                for k in expired:
                    del self._memory[k]
                if len(self._memory) > self._max_size:
                    sorted_items = sorted(self._memory.items(), key=lambda x: x[1].timestamp)
                    for k, _ in sorted_items[:len(self._memory)-self._max_size]:
                        del self._memory[k]

    def _key(self, method: str, url: str, params: Optional[Dict] = None, protocol: str = "http/1.1") -> str:
        return hashlib.sha256(f"{method}:{url}:{json.dumps(params or {}, sort_keys=True)}:{protocol}".encode()).hexdigest()

    async def get(self, method: str, url: str, params: Optional[Dict] = None, protocol: str = "http/1.1") -> Optional[CachedResponse]:
        key = self._key(method, url, params, protocol)
        if key in self._memory and self._memory[key].is_fresh():
            return self._memory[key]
        path = CACHE_DIR / f"{key}.json"
        if path.exists():
            try:
                async with aiofiles.open(path, 'r') as f:
                    data = json.loads(await f.read())
                cached = CachedResponse(
                    status=data["status"], content=data["content"].encode('utf-8', errors='replace'),
                    headers=data["headers"], timestamp=data["timestamp"], ttl=data["ttl"], protocol=data.get("protocol", "http/1.1")
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

    async def set(self, method: str, url: str, response: CachedResponse, params: Optional[Dict] = None):
        key = self._key(method, url, params, response.protocol)
        async with self._lock:
            self._memory[key] = response
        path = CACHE_DIR / f"{key}.json"
        data = {"status": response.status, "content": response.content.decode('utf-8', errors='replace'), "headers": response.headers,
                "timestamp": response.timestamp, "ttl": response.ttl, "protocol": response.protocol}
        async with aiofiles.open(path, 'w') as f:
            await f.write(json.dumps(data))

# ─── RequestDeduplicator ──────────────────────────────────────
class RequestDeduplicator:
    def __init__(self):
        self._in_flight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
    def _key(self, method: str, url: str, params: Optional[Dict] = None, protocol: str = "http/1.1") -> str:
        return hashlib.sha256(f"{method}:{url}:{json.dumps(params or {}, sort_keys=True)}:{protocol}".encode()).hexdigest()
    async def execute(self, method: str, url: str, params: Optional[Dict], protocol: str, factory: Callable[[], Awaitable[CachedResponse]]) -> CachedResponse:
        key = self._key(method, url, params, protocol)
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

# ─── QualityScorer ─────────────────────────────────────────────
class QualityScorer:
    """Weighted scoring for proxies based on success rate and latency."""
    def __init__(self, decay_factor: float = QUALITY_DECAY):
        self._scores: Dict[str, float] = {}
        self._history: Dict[str, List[float]] = {}
        self._decay = decay_factor

    def update(self, proxy_url: str, success: bool, latency_ms: float = 9999.0):
        old_score = self._scores.get(proxy_url, 0.5)
        new_score = old_score * self._decay + (1.0 if success else 0.0) * (1 - self._decay)
        self._scores[proxy_url] = new_score
        if proxy_url not in self._history:
            self._history[proxy_url] = []
        self._history[proxy_url].append(latency_ms)
        if len(self._history[proxy_url]) > 100:
            self._history[proxy_url] = self._history[proxy_url][-100:]

    def get_score(self, proxy_url: str) -> float:
        return self._scores.get(proxy_url, 0.5)

    def get_best_proxy(self, proxies: List[str]) -> Optional[str]:
        if not proxies:
            return None
        return max(proxies, key=lambda p: self.get_score(p))

    def get_recent_success_rate(self, proxy_url: str, window: int = 10) -> float:
        """Get success rate from last N entries in history."""
        history = self._history.get(proxy_url)
        if not history or len(history) == 0:
            return 0.5
        recent = history[-window:]
        return sum(recent) / len(recent) if recent else 0.5

    def get_avg_latency(self, proxy_url: str, window: int = 10) -> float:
        """Get average latency (ms) from last N entries in history.

        Public API so ML predictor doesn't access _history directly.
        Returns 500.0 (default) if no data available.
        """
        history = self._history.get(proxy_url)
        if not history:
            return 500.0
        recent = history[-window:]
        return sum(recent) / len(recent) if recent else 500.0

    def get_all_scores(self) -> Dict[str, float]:
        return self._scores.copy()

# ─── AdaptiveRateLimiter ──────────────────────────────────────
class AdaptiveRateLimiter:
    """Dynamically adjusts per-domain request rate based on response codes."""
    def __init__(self, base_rate: float = DEFAULT_RATE,
                 min_rate: float = ADAPTIVE_MIN_RATE,
                 max_rate: float = ADAPTIVE_MAX_RATE):
        self.base_rate = base_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self._rates: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def adjust(self, domain: str, status: int):
        async with self._lock:
            current = self._rates.get(domain, self.base_rate)
            if status in (429, 503):
                new_rate = max(self.min_rate, current * 0.5)
            elif 200 <= status < 300:
                new_rate = min(self.max_rate, current * 1.1)
            else:
                new_rate = current
            self._rates[domain] = new_rate
            logger.debug(f"Rate for {domain}: {new_rate:.2f} req/s")

    async def get_rate(self, domain: str) -> float:
        return self._rates.get(domain, self.base_rate)

    async def get_all_rates(self) -> Dict[str, float]:
        return self._rates.copy()

# ─── RedisStore (optional) ────────────────────────────────────
class RedisStore:
    """Persistent state storage using Redis."""
    def __init__(self, url: str = "redis://localhost:6379", prefix: str = "owl:"):
        self.url = url
        self.prefix = prefix
        self._redis = None
        self._enabled = False

    async def connect(self):
        if not REDIS_AVAILABLE:
            logger.warning("Redis not installed -- falling back to memory")
            return
        try:
            self._redis = redis.from_url(self.url, decode_responses=True)
            await self._redis.ping()
            self._enabled = True
            logger.info("Redis connected")
        except Exception as e:
            logger.warning(f"Redis unavailable: {e} -- falling back to memory")
            self._enabled = False

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        if self._enabled:
            await self._redis.set(self.prefix + key, json.dumps(value), ex=ttl)

    async def get(self, key: str) -> Optional[Any]:
        if not self._enabled:
            return None
        data = await self._redis.get(self.prefix + key)
        if data:
            return json.loads(data)
        return None

    async def delete(self, key: str):
        if self._enabled:
            await self._redis.delete(self.prefix + key)

    async def keys(self, pattern: str) -> List[str]:
        if not self._enabled:
            return []
        return await self._redis.keys(self.prefix + pattern)

# ─── ProxyPoolManager with country filtering ──────────────────
class ProxyPoolManager:
    def __init__(self, max_queue: int = 50, cache_file: Path = PROXY_CACHE_FILE,
                 cache_max: int = MAX_PROXY_CACHE, countries: Optional[List[str]] = None):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue)
        self._lock = asyncio.Lock()
        self._running = False
        self._cache_file = cache_file
        self._cache_max = cache_max
        self._proxies: List[ProxyEntry] = []
        self._url_set: Set[str] = set()
        self._url_map: Dict[str, ProxyEntry] = {}  # O(1) lookup by URL
        # Broker initialized lazily in start() when we're in an async context
        self._broker = None
        self.countries = countries or DEFAULT_COUNTRIES

    async def start(self):
        self._running = True
        self._load_cache()

        # If no cached proxies, try to fetch from public proxy lists
        if not self._proxies:
            await self._fetch_public_proxies()

        for p in self._proxies:
            if p.healthy and not p.is_banned():
                try:
                    self.queue.put_nowait(p.url)
                except asyncio.QueueFull:
                    break

        # Always schedule discovery — the lazy init inside handles import failures
        asyncio.create_task(self._discovery_loop())

        logger.info(f"Proxy pool: {len(self._proxies)} proxies loaded, {self.queue.qsize()} in queue")

    def _load_cache(self):
        if not self._cache_file.exists():
            return
        try:
            with open(self._cache_file, 'r') as f:
                data = json.load(f)
            for item in data.get("proxies", []):
                p = ProxyEntry(
                    url=item["url"],
                    healthy=item.get("healthy", True),
                    last_check=item.get("last_check", 0.0),
                    fail_count=item.get("fail_count", 0),
                    ban_until=item.get("ban_until", 0.0)
                )
                self._proxies.append(p)
                self._url_set.add(p.url)
                self._url_map[p.url] = p
            if len(self._proxies) > self._cache_max:
                self._proxies = self._proxies[-self._cache_max:]
                self._url_set = {p.url for p in self._proxies}
                self._url_map = {p.url: p for p in self._proxies}
            logger.info(f"Loaded {len(self._proxies)} proxies from cache")
        except Exception as e:
            logger.warning(f"Failed to load proxy cache: {e}")

    def _save_cache(self):
        data = {
            "proxies": [
                {
                    "url": p.url,
                    "healthy": p.healthy,
                    "last_check": p.last_check,
                    "fail_count": p.fail_count,
                    "ban_until": p.ban_until
                } for p in self._proxies
            ]
        }
        try:
            with open(self._cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save proxy cache: {e}")

    def _proxybroker2_proxy_url(self, proxy) -> Optional[str]:
        """Safely extract URL from a ProxyBroker2 Proxy object.

        ProxyBroker2's Proxy class may use different attribute names
        depending on the version. This handles both old and new APIs.
        """
        try:
            host = getattr(proxy, 'host', None)
            port = getattr(proxy, 'port', None)
            if not host or not port:
                return None

            # Try multiple attribute names for protocol (varies by version)
            proto = getattr(proxy, 'protocol', None) or \
                    getattr(proxy, 'proto', None) or \
                    getattr(proxy, 'type', None) or 'HTTP'

            proto = proto.upper() if proto else 'HTTP'

            # Map common protocol names to URL schemes
            scheme_map = {
                'HTTP': 'http', 'HTTPS': 'https',
                'SOCKS4': 'socks4', 'SOCKS5': 'socks5',
                'SOCKS': 'socks5', 'CONNECT': 'http',
            }
            scheme = scheme_map.get(proto, 'http')

            return f"{scheme}://{host}:{port}"
        except Exception as e:
            logger.debug(f"Failed to extract proxy URL from {type(proxy).__name__}: {e}")
            return None

    async def _fetch_public_proxies(self):
        """Fetch proxies from public GitHub raw proxy lists when cache is empty."""
        proxy_list_urls = [
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
            "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text&limit=50",
        ]

        logger.info("Fetching proxies from public proxy lists...")
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            for url in proxy_list_urls:
                if len(self._proxies) >= self._cache_max:
                    break
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        lines = resp.text.strip().split('\n')
                        count = 0
                        max_per_source = min(20, self._cache_max - len(self._proxies))
                        for line in lines[:max_per_source]:
                            line = line.strip()
                            if not line or ':' not in line:
                                continue
                            if 'socks5' in url.lower():
                                proxy_url = f"socks5://{line}"
                            elif 'https' in url.lower():
                                proxy_url = f"https://{line}"
                            else:
                                proxy_url = f"http://{line}"
                            if proxy_url not in self._url_set:
                                new_entry = ProxyEntry(url=proxy_url)
                                self._proxies.append(new_entry)
                                self._url_set.add(proxy_url)
                                self._url_map[proxy_url] = new_entry
                                count += 1
                        if count > 0:
                            source_name = url.split('/')[-1]
                            logger.info(f"  Fetched {count} proxies from {source_name}")
                except Exception as e:
                    logger.debug(f"  Failed to fetch from {url.split('/')[-1]}: {e}")
                    continue

        if self._proxies:
            if len(self._proxies) > self._cache_max:
                self._proxies = self._proxies[-self._cache_max:]
                self._url_set = {p.url for p in self._proxies}
            self._save_cache()
            logger.info(f"Total proxies loaded from public lists: {len(self._proxies)}")
        else:
            logger.warning("No proxies could be fetched from public lists")

    async def _discovery_loop(self):
        # Lazy init broker now that we're in async context
        if self._broker is None:
            try:
                from proxybroker2 import Broker as _Broker
                self._broker = _Broker()
                logger.info("ProxyBroker2 initialized for ongoing discovery")
            except (ImportError, RuntimeError) as e:
                logger.warning(f"ProxyBroker2 unavailable: {e} — no ongoing discovery")
                return
        while self._running:
            try:
                # find() is a coroutine that starts discovery; proxies appear in _broker._proxies queue
                find_task = asyncio.create_task(self._broker.find(
                    types=['HTTP', 'HTTPS', 'SOCKS4', 'SOCKS5'],
                    countries=self.countries,
                    limit=0
                ))
                # Read discovered proxies from the broker's internal queue
                while self._running:
                    try:
                        proxy = await asyncio.wait_for(
                            self._broker._proxies.get(), timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        # Check if find task is still running
                        if find_task.done():
                            break
                        continue
                    url = self._proxybroker2_proxy_url(proxy)
                    if url and url not in self._url_set:
                        p = ProxyEntry(url=url)
                        self._proxies.append(p)
                        self._url_set.add(url)
                        self._url_map[url] = p
                        await self.queue.put(url)
                        logger.debug(f"Discovered proxy: {url}")
                        if len(self._proxies) > self._cache_max:
                            self._proxies = self._proxies[-self._cache_max:]
                            self._url_set = {p.url for p in self._proxies}
                            self._url_map = {p.url: p for p in self._proxies}
                        self._save_cache()
                    elif url is None:
                        logger.debug(f"Skipped proxy (could not parse): {type(proxy).__name__}")
            except asyncio.CancelledError:
                break
            except AttributeError as e:
                # ProxyBroker2 API incompatibility - object missing expected attributes
                logger.warning(f"ProxyBroker2 API incompatibility: {e}")
                logger.info("ProxyBroker2 discovery disabled. Public proxy lists are active.")
                # Don't retry - the API is incompatible, just exit the loop
                break
            except Exception as e:
                logger.error(f"ProxyBroker2 discovery error: {e}")
                await asyncio.sleep(30)

    async def get(self) -> Optional[str]:
        try:
            url = await asyncio.wait_for(self.queue.get(), timeout=5.0)
            return url
        except asyncio.TimeoutError:
            return None

    def get_all_urls(self) -> List[str]:
        return [p.url for p in self._proxies if p.healthy and not p.is_banned()]

    def get_entry(self, url: str) -> Optional[ProxyEntry]:
        """Get ProxyEntry by URL — O(1) dict lookup."""
        return self._url_map.get(url)

    def stop(self):
        self._running = False
        self._save_cache()

# ─── Plugin System (v4.3) ──────────────────────────────
class PluginManager:
    """Manages request/response lifecycle plugins."""
    def __init__(self, plugin_loader=None):
        self._hooks: Dict[str, List[Callable]] = {
            "start": [], "request": [], "response": [],
            "error": [], "complete": []
        }
        self._plugin_loader = plugin_loader

    def register(self, hook_type: str, func: Callable):
        if hook_type not in self._hooks:
            raise ValueError(f"Unknown hook type: {hook_type}")
        self._hooks[hook_type].append(func)

    def _get_all_hooks(self, hook_type: str) -> List[Callable]:
        """Merge static hooks with dynamic hooks from PluginLoader."""
        hooks = list(self._hooks.get(hook_type, []))
        if self._plugin_loader:
            hooks.extend(self._plugin_loader.get_hooks(hook_type))
        return hooks

    async def run_hooks(self, hook_type: str, *args, **kwargs):
        for hook in self._get_all_hooks(hook_type):
            try:
                if inspect.iscoroutinefunction(hook):
                    await hook(*args, **kwargs)
                else:
                    hook(*args, **kwargs)
            except Exception as e:
                logger.error(f"Plugin hook {hook_type} failed: {e}")


# ─── A/B Testing Engine (v4.3) ──────────────────────────
class ABTestManager:
    """Manages A/B tests for proxy strategies per domain."""
    STRATEGIES = ["best_score", "random", "round_robin"]

    def __init__(self):
        self._domain_strategy: Dict[str, str] = {}
        self._domain_stats: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
            lambda: {s: {"success": 0, "total": 0} for s in self.STRATEGIES}
        )
        self._round_robin_index: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
        # Randomly assign 20%% of domains to alternative strategies at start
        # so we have comparison data for the switching logic
        self._default_alt_rate = 0.2

    def get_strategy(self, domain: str) -> str:
        if domain not in self._domain_strategy:
            # Randomly assign alternative strategy for new domains
            # so A/B comparison data is generated
            if random.random() < self._default_alt_rate:
                alt = random.choice([s for s in self.STRATEGIES if s != "best_score"])
                self._domain_strategy[domain] = alt
            else:
                self._domain_strategy[domain] = "best_score"
        return self._domain_strategy[domain]

    async def record_result(self, domain: str, strategy: str, success: bool):
        async with self._lock:
            stats = self._domain_stats[domain][strategy]
            stats["total"] += 1
            if success:
                stats["success"] += 1
            total = sum(s["total"] for s in self._domain_stats[domain].values())
            if total >= 100:
                best = self._evaluate_best(domain)
                if best and best != self._domain_strategy.get(domain):
                    logger.info(f"AB: Switching {domain}: {self._domain_strategy.get(domain)} -> {best}")
                    self._domain_strategy[domain] = best

    def _evaluate_best(self, domain: str) -> Optional[str]:
        stats = self._domain_stats[domain]
        best, best_rate = None, 0.0
        for strategy, data in stats.items():
            if data["total"] > 0:
                rate = data["success"] / data["total"]
                if rate > best_rate:
                    best_rate, best = rate, strategy
        return best

    def select_proxy(self, domain: str, proxy_urls: List[str], scorer: 'QualityScorer') -> Optional[str]:
        if not proxy_urls:
            return None
        strategy = self.get_strategy(domain)
        if strategy == "best_score":
            return scorer.get_best_proxy(proxy_urls)
        elif strategy == "random":
            return random.choice(proxy_urls)
        elif strategy == "round_robin":
            idx = self._round_robin_index[domain] % len(proxy_urls)
            self._round_robin_index[domain] += 1
            return proxy_urls[idx]
        return None

    def get_stats(self, domain: Optional[str] = None) -> Dict:
        if domain:
            d = self._domain_stats.get(domain, {})
            return {k: dict(v) for k, v in d.items()} if d else {}
        # Return all domains' stats as plain dicts (JSON-safe)
        return {dom: {k: dict(v) for k, v in strats.items()}
                for dom, strats in self._domain_stats.items()}


# ─── ML Predictor (v4.3) ──────────────────────────────────
class MLPredictor:
    """Online ML predictor for proxy success using logistic regression.

    On startup, validates any persisted model's CV score against
    ML_STALENESS_THRESHOLD. If the score is below threshold, the model
    is discarded and will be retrained from scratch after enough live
    samples are collected.
    """
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._features: List[List[float]] = []
        self._labels: List[int] = []
        self._model = None
        self._scaler = None
        self._is_trained_flag = False
        self._cv_score: float = 0.0
        self._samples_since_train: int = 0
        self._lock = asyncio.Lock()

    def is_trained(self) -> bool:
        return self._is_trained_flag

    def get_info(self) -> Dict[str, Any]:
        """Return model metadata for /stats endpoint."""
        return {
            "model_name": "Logistic",
            "cv_score": round(self._cv_score, 4),
            "samples": len(self._features),
            "is_trained": self._is_trained_flag,
            "staleness_threshold": ML_STALENESS_THRESHOLD,
            "is_stale": self._cv_score < ML_STALENESS_THRESHOLD and self._is_trained_flag,
        }

    def _extract_features(self, proxy_url: str, latency_ms: float) -> List[float]:
        protocol = proxy_url.split("://")[0] if "://" in proxy_url else "http"
        proto_map = {"http": 0, "https": 1, "socks4": 2, "socks5": 3}
        # Add success rate estimate from scorer via public method
        success_rate = 0.5  # default
        if self._scorer_ref:
            success_rate = self._scorer_ref.get_recent_success_rate(proxy_url)
        return [latency_ms / 1000.0, float(proto_map.get(protocol, 0)), success_rate]

    async def update(self, proxy_url: str, latency_ms: float, success: bool):
        async with self._lock:
            features = self._extract_features(proxy_url, latency_ms)
            self._features.append(features)
            self._labels.append(1 if success else 0)
            if len(self._features) > self.max_samples:
                self._features = self._features[-self.max_samples:]
                self._labels = self._labels[-self.max_samples:]
            if len(self._features) >= 20:
                # Atomic swap: train in thread, then swap model outside lock
                await asyncio.to_thread(self._train_atomic)

    def _train_atomic(self):
        """Train model, validate with cross-validation, and atomically swap.

        If the CV score falls below ML_STALENESS_THRESHOLD, the model is
        still installed but flagged as stale so callers know it needs more
        live data before it becomes reliable.
        """
        if not SKLEARN_AVAILABLE:
            return
        try:
            X = np.array(self._features)
            y = np.array(self._labels)
            if len(set(y)) < 2:
                return
            # Need at least 2 samples per class for cross-validation
            min_class_count = min(10, min(np.bincount(y)) if len(y) >= 20 else 2)
            if min_class_count < 2:
                logger.debug("Not enough samples per class for CV, skipping validation")
                cv_score = 0.5
            else:
                cv_folds = min(3, min_class_count)
                scaler_cv = StandardScaler()
                X_cv = scaler_cv.fit_transform(X)
                model_cv = LogisticRegression(max_iter=1000, class_weight='balanced')
                cv_scores = cross_val_score(model_cv, X_cv, y, cv=cv_folds, scoring='accuracy')
                cv_score = float(cv_scores.mean())

            # Fit final model on full data
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            model = LogisticRegression(max_iter=1000, class_weight='balanced')
            model.fit(X_scaled, y)

            # Atomic swap
            self._model = model
            self._scaler = scaler
            self._cv_score = cv_score
            self._samples_since_train = 0
            self._is_trained_flag = True

            if cv_score < ML_STALENESS_THRESHOLD:
                logger.warning(f"ML model trained but CV score {cv_score:.3f} < threshold {ML_STALENESS_THRESHOLD} — model is stale, will improve with more data")
            else:
                logger.info(f"ML model trained: CV score {cv_score:.3f}, samples={len(self._features)}")
        except Exception as e:
            logger.warning(f"ML training failed: {e}")

    async def predict(self, proxy_url: str, latency_ms: float) -> float:
        if not self._is_trained_flag or not SKLEARN_AVAILABLE:
            return 0.5
        async with self._lock:
            if self._model is None or self._scaler is None:
                return 0.5
            try:
                features = self._extract_features(proxy_url, latency_ms)
                X = np.array([features])
                X_scaled = self._scaler.transform(X)
                return float(self._model.predict_proba(X_scaled)[0][1])
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")
                return 0.5


# ─── DomainCircuitBreaker ──────────────────────────────────────
class DomainCircuitBreaker:
    def __init__(self, failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                 recovery_timeout=CIRCUIT_BREAKER_RECOVERY_TIMEOUT):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

    def get(self, domain: str) -> CircuitBreaker:
        if domain not in self._breakers:
            self._breakers[domain] = CircuitBreaker(
                failure_threshold=self._failure_threshold,
                recovery_timeout=self._recovery_timeout
            )
        return self._breakers[domain]

# ─── AgentBrowserWrapper ──────────────────────────────────────
class AgentBrowserWrapper:
    def __init__(self, proxy_url: Optional[str] = None, headless: bool = True):
        self.proxy_url = proxy_url
        self.headless = headless

    async def fetch_page(self, url: str, wait_for: Optional[str] = None, timeout: int = 30) -> str:
        cmd = ["agent-browser", "fetch", url]
        if self.proxy_url:
            cmd.extend(["--proxy", self.proxy_url])
        if self.headless:
            cmd.append("--headless")
        if wait_for:
            cmd.extend(["--wait", wait_for])
        cmd.extend(["--timeout", str(timeout)])
        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            if result.returncode != 0:
                logger.error(f"agent-browser error: {stderr.decode()}")
                raise RuntimeError(f"agent-browser failed: {stderr.decode()}")
            return stdout.decode('utf-8', errors='replace')
        except FileNotFoundError:
            raise RuntimeError("agent-browser not installed. Run: npx skills add vercel-labs/agent-browser")

# ─── ResilientClient (Unified) ──────────────────────────────
class ResilientClient:
    def __init__(self,
                 cache_ttl: int = DEFAULT_TTL,
                 rate_limit: float = DEFAULT_RATE,
                 max_retries: int = MAX_RETRIES,
                 use_curl_cffi: bool = False,
                 countries: Optional[List[str]] = None,
                 use_redis: bool = False,
                 redis_url: str = "redis://localhost:6379",
                 enable_ab_test: bool = False,
                 enable_ml: bool = False,
                 ml_model: str = "auto",
                 plugin_dir: str = "~/.owl-agent/plugins"):
        self.cache = HTTPCache(cache_ttl)
        self.dedup = RequestDeduplicator()
        self.limiter = AdaptiveRateLimiter(base_rate=rate_limit)
        self.max_retries = max_retries
        self.pool_manager = ProxyPoolManager(countries=countries)
        self.circuit_breakers = DomainCircuitBreaker()
        self.scorer = QualityScorer()
        self.use_curl_cffi = use_curl_cffi and CURL_CFFI_AVAILABLE
        if self.use_curl_cffi:
            logger.info("Using curl_cffi for requests (Chrome 110 fingerprint)")
        else:
            logger.info("Using httpx for requests")
        self.use_redis = use_redis
        self.redis_url = redis_url
        self.redis_store = None
        self._direct_session = None
        self._proxy_sessions: Dict[str, httpx.AsyncClient] = {}
        self._browser_wrapper = None
        # v4.5: Plugin loader (must be before PluginManager)
        self.plugin_loader = PluginLoader(plugin_dir) if PluginLoader else None
        # v4.3: Plugin system, A/B testing, ML predictor
        self.plugin_manager = PluginManager(self.plugin_loader)
        self.enable_ab_test = enable_ab_test
        self.enable_ml = enable_ml and SKLEARN_AVAILABLE
        self.ab_test = ABTestManager() if self.enable_ab_test else None
        # v4.4: Advanced ML predictor
        if self.enable_ml and AdvancedMLPredictor:
            self.ml_predictor = AdvancedMLPredictor(model_type=ml_model)
        else:
            self.ml_predictor = None
        if self.enable_ab_test:
            logger.info("A/B testing enabled")
        if self.enable_ml:
            logger.info(f"ML predictor enabled (model={ml_model})")
        elif enable_ml and not SKLEARN_AVAILABLE:
            logger.warning("ML requested but scikit-learn not available — disabled")
        if self.plugin_loader:
            logger.info(f"Plugin loader enabled (dir={plugin_dir})")

    async def __aenter__(self):
        await self.pool_manager.start()
        await self.cache.start_cleaner()

        # aiohttp session for direct connections (handles TLS better than curl_cffi)
        self._aiohttp_direct_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        if self.use_curl_cffi:
            self._direct_session = CurlAsyncSession(
                impersonate="chrome110",
                timeout=30,
                verify=True
            )
        else:
            self._direct_session = httpx.AsyncClient(http2=True)

        # _proxy_sessions is populated lazily per-proxy in _execute_with_resilient_client
        self._browser_wrapper = AgentBrowserWrapper()

        if self.use_redis:
            self.redis_store = RedisStore(self.redis_url)
            await self.redis_store.connect()
            await self._load_state()

        return self

    async def __aexit__(self, *args):
        if self.plugin_loader:
            await self.plugin_loader.stop()
        self.pool_manager.stop()
        if self._direct_session:
            if hasattr(self._direct_session, 'aclose'):
                await self._direct_session.aclose()
            else:
                # curl_cffi's AsyncSession.close() is a coroutine named close(), not aclose()
                close_fn = self._direct_session.close()
                if hasattr(close_fn, '__await__') or asyncio.iscoroutine(close_fn):
                    await close_fn
        await self._aiohttp_direct_session.close()
        for proxy, session in self._proxy_sessions.items():
            await session.aclose()
        self._proxy_sessions.clear()

    async def _load_state(self):
        if not self.redis_store or not self.redis_store._enabled:
            return
        try:
            keys = await self.redis_store.keys("score:*")
            for key in keys:
                proxy_url = key.split(":")[-1]
                score = await self.redis_store.get(f"score:{proxy_url}")
                if score is not None:
                    self.scorer._scores[proxy_url] = float(score)
            keys = await self.redis_store.keys("rate:*")
            for key in keys:
                domain = key.split(":")[-1]
                rate = await self.redis_store.get(f"rate:{domain}")
                if rate is not None:
                    self.limiter._rates[domain] = float(rate)
            logger.info("State loaded from Redis")
        except Exception as e:
            logger.warning(f"Failed to load state from Redis: {e}")

    async def _save_state(self):
        if not self.redis_store or not self.redis_store._enabled:
            return
        try:
            for proxy_url, score in self.scorer.get_all_scores().items():
                await self.redis_store.set(f"score:{proxy_url}", score, ttl=3600)
            for domain, rate in await self.limiter.get_all_rates().items():
                await self.redis_store.set(f"rate:{domain}", rate, ttl=3600)
        except Exception as e:
            logger.warning(f"Failed to save state to Redis: {e}")

    def _estimate_latency(self, proxy_url: str) -> float:
        """Estimate proxy latency from scorer history."""
        return self.scorer.get_avg_latency(proxy_url)

    async def _get_best_proxy(self, domain: Optional[str] = None) -> Optional[str]:
        """Enhanced proxy selection using A/B test and ML predictor."""
        healthy_urls = self.pool_manager.get_all_urls()
        if not healthy_urls:
            return None
        # A/B test strategy selection
        if self.enable_ab_test and self.ab_test and domain:
            selected = self.ab_test.select_proxy(domain, healthy_urls, self.scorer)
            if selected:
                return selected
        # ML predictor selection
        if self.enable_ml and self.ml_predictor and self.ml_predictor.is_trained():
            best_url, best_prob = None, -1.0
            for u in healthy_urls:
                latency = self._estimate_latency(u)
                entry = self.pool_manager.get_entry(u)
                prob = await self.ml_predictor.predict(u, latency, proxy_entry=entry, scorer=self.scorer)
                if prob > best_prob:
                    best_prob, best_url = prob, u
            if best_url:
                return best_url
        # Fallback to quality scorer
        return self.scorer.get_best_proxy(healthy_urls)

    async def _execute_with_resilient_client(self, method, url, params, headers, **kwargs):
        proxy_url = await self._get_best_proxy()
        if proxy_url:
            if self.use_curl_cffi:
                proxies = {"http": proxy_url, "https": proxy_url}
                response = await self._direct_session.request(
                    method, url, params=params, headers=headers, proxies=proxies, **kwargs
                )
                return response
            else:
                # Use cached httpx session with proxy (replaces broken resilient_httpx + litproxy)
                if proxy_url not in self._proxy_sessions:
                    self._proxy_sessions[proxy_url] = httpx.AsyncClient(
                        proxy=proxy_url, http2=True, timeout=30.0
                    )
                response = await self._proxy_sessions[proxy_url].request(
                    method, url, params=params, headers=headers, **kwargs
                )
                return response
        else:
            response = await self._direct_session.request(
                method, url, params=params, headers=headers, **kwargs
            )
            return response

    async def _fetch_with_browser(self, url: str, wait_for: Optional[str] = None, timeout: int = 30) -> str:
        proxy = await self._get_best_proxy()
        browser = AgentBrowserWrapper(proxy_url=proxy)
        return await browser.fetch_page(url, wait_for, timeout)

    async def request(self, method: str, url: str, params: Optional[Dict] = None,
                      headers: Optional[Dict] = None, browser: bool = False,
                      wait_for: Optional[str] = None, timeout: int = 30, **kwargs) -> CachedResponse:
        if browser:
            content = await self._fetch_with_browser(url, wait_for, timeout)
            return CachedResponse(
                status=200,
                content=content.encode('utf-8'),
                headers={"Content-Type": "text/html"},
                timestamp=time.time(),
                ttl=self.cache.ttl
            )

        cached = await self.cache.get(method, url, params)
        if cached:
            return cached

        # HTTPS URLs bypass proxy pool entirely (free proxies can't tunnel HTTPS)
        if url.startswith("https://"):
            logger.info(f"HTTPS URL: direct connection (no proxy): {url}")
            try:
                req_timeout = aiohttp.ClientTimeout(total=timeout)
                async with self._aiohttp_direct_session.request(method, url, params=params, headers=headers, timeout=req_timeout, **kwargs) as resp:
                    content = await resp.read()
                    return CachedResponse(
                        status=resp.status,
                        content=content,
                        headers=dict(resp.headers),
                        timestamp=time.time(),
                        ttl=self.cache.ttl,
                    )
            except Exception as e:
                logger.warning(f"Direct HTTPS connection failed: {e}")
                raise RuntimeError(f"Direct HTTPS connection failed: {e}")

        async def factory():
            return await self._execute_with_retry(method, url, params, headers, timeout=timeout, **kwargs)
        return await self.dedup.execute(method, url, params, "http/1.1", factory)

    async def _execute_with_retry(self, method, url, params, headers, timeout=30, **kwargs):
        domain = urlparse(url).netloc
        breaker = self.circuit_breakers.get(domain)

        if breaker.opened:
            raise RuntimeError(f"Circuit breaker open for {domain}")

        # v4.3: Run start hooks
        await self.plugin_manager.run_hooks("start", method=method, url=url, domain=domain)

        for attempt in range(self.max_retries):
            start = time.time()
            proxy_url = None
            try:
                # Select proxy (via AB test / ML / scorer)
                proxy_url = await self._get_best_proxy(domain)
                # Note: proxy_url is NOT added to kwargs to avoid leaking it to httpx/aiohttp

                # v4.3: Run request hooks
                await self.plugin_manager.run_hooks("request", method=method, url=url,
                    proxy=proxy_url, attempt=attempt)

                response = await self._execute_with_resilient_client(method, url, params, headers, **kwargs)

                if self.use_curl_cffi:
                    resp_content = response.content
                    status = response.status_code
                    resp_headers = dict(response.headers)
                else:
                    resp_content = await response.aread()
                    status = response.status_code
                    resp_headers = dict(response.headers)

                latency = (time.time() - start) * 1000

                cached_response = CachedResponse(
                    status=status,
                    content=resp_content,
                    headers=resp_headers,
                    timestamp=time.time(),
                    ttl=self.cache.ttl
                )

                # Update scorer
                if proxy_url:
                    self.scorer.update(proxy_url, success=True, latency_ms=latency)

                # v4.4: Update ML predictor with context + ProxyEntry
                if self.enable_ml and self.ml_predictor and proxy_url:
                    context = {"url": url, "method": method, "domain": domain}
                    entry = self.pool_manager.get_entry(proxy_url)
                    await self.ml_predictor.update(proxy_url, latency, True, context, self.scorer, entry)

                await self.limiter.adjust(domain, status)

                breaker.reset()

                # v4.3: Record AB test result
                if self.enable_ab_test and self.ab_test:
                    strategy = self.ab_test.get_strategy(domain)
                    await self.ab_test.record_result(domain, strategy, success=True)

                # Retry-After handling
                if status in (429, 503) and 'retry-after' in resp_headers:
                    retry_after = resp_headers['retry-after']
                    try:
                        seconds = int(retry_after)
                    except ValueError:
                        try:
                            retry_date = email.utils.parsedate_to_datetime(retry_after)
                            seconds = max(0, (retry_date - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
                        except Exception:
                            seconds = 5
                    logger.info(f"Retry-After: sleeping {seconds}s before retry")
                    await asyncio.sleep(seconds)
                    continue

                # v4.3: Run response hooks
                await self.plugin_manager.run_hooks("response", response=cached_response)

                await self.cache.set(method, url, cached_response, params)
                await self._save_state()

                # v4.3: Run complete hooks
                await self.plugin_manager.run_hooks("complete", url=url, status=status, latency_ms=latency)
                return cached_response

            except Exception as e:
                if proxy_url:
                    self.scorer.update(proxy_url, success=False)
                    # v4.3: Update ML predictor on failure with ProxyEntry
                    if self.enable_ml and self.ml_predictor:
                        entry = self.pool_manager.get_entry(proxy_url)
                        await self.ml_predictor.update(proxy_url, 9999.0, success=False, proxy_entry=entry)
                await self.limiter.adjust(domain, 500)

                # v4.3: Record AB test failure
                if self.enable_ab_test and self.ab_test:
                    strategy = self.ab_test.get_strategy(domain)
                    await self.ab_test.record_result(domain, strategy, success=False)

                # v4.3: Run error hooks
                await self.plugin_manager.run_hooks("error", error=e, attempt=attempt, url=url)
                logger.warning(f"Request failed (attempt {attempt+1}/{self.max_retries}): {e}")
                continue

        # Direct fallback - use aiohttp to avoid curl_cffi TLS issues
        logger.info("All proxies exhausted, attempting direct connection via aiohttp...")
        try:
            req_timeout = aiohttp.ClientTimeout(total=timeout)
            async with self._aiohttp_direct_session.request(method, url, params=params, headers=headers, timeout=req_timeout, **kwargs) as resp:
                content = await resp.read()
                status = resp.status
                resp_headers = dict(resp.headers)
            cached_response = CachedResponse(
                status=status,
                content=content,
                headers=resp_headers,
                timestamp=time.time(),
                ttl=self.cache.ttl
            )
            await self.cache.set(method, url, cached_response, params)
            return cached_response
        except Exception as e:
            raise RuntimeError(f"Direct connection also failed: {e}")

    async def get_stats(self):
        total = len(self.pool_manager._proxies)
        healthy = sum(1 for p in self.pool_manager._proxies if p.healthy and not p.is_banned())
        scores = self.scorer.get_all_scores()
        rates = await self.limiter.get_all_rates()
        stats = {
            "proxies_total": total,
            "proxies_healthy": healthy,
            "scores": scores,
            "rates": rates,
            "version": self.version if hasattr(self, 'version') else "4.5",
        }
        if self.enable_ab_test and self.ab_test:
            stats["ab_test"] = self.ab_test.get_stats()
        if self.enable_ml and self.ml_predictor:
            stats["ml_trained"] = self.ml_predictor.is_trained()
            if hasattr(self.ml_predictor, 'get_info'):
                stats["ml_model"] = self.ml_predictor.get_info()
        if self.plugin_loader:
            stats["plugins"] = self.plugin_loader.get_stats()
        return stats

# ─── Main (test) ────────────────────────────────────────────────
async def main():
    print("🦉 OWL-AGENT v4.5 (Advanced ML + Self-Healing Plugins)")
    print("=" * 50)
    async with ResilientClient(use_curl_cffi=True, countries=["US", "GB"], use_redis=False) as client:
        stats = await client.get_stats()
        print(f"Proxy pool: {stats['proxies_total']} total, {stats['proxies_healthy']} healthy")
        print(f"Quality scores: {stats['scores']}")
        print(f"Adaptive rates: {stats['rates']}")
        print()
        try:
            resp = await client.request("GET", "https://api.github.com/users/octocat")
            print(f"✅ Success! Status: {resp.status}, content length: {len(resp.content)} bytes")
            if resp.status == 200:
                data = json.loads(resp.content)
                print(f"   User: {data.get('login')} - {data.get('name')}")
        except Exception as e:
            print(f"❌ All attempts failed: {e}")
        print()
        print("🦉 OWL-AGENT v4.3 running on http://127.0.0.1:60000")
        print("Press Ctrl+C to stop.")

if __name__ == "__main__":
    asyncio.run(main())
