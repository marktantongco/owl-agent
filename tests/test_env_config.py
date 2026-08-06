#!/usr/bin/env python3
"""
Unit tests for OWL_* environment variable configuration and
extra_proxies seeding.

Covers:
1. proxy_defense._env_int / _env_float / _env_bool / _env_list helpers
2. Module constants reading env vars at import time (via subprocess, so the
   constants are computed against the target environment)
3. ProxyPoolManager extra_proxies seeding (incl. dedup with cached entries)
4. owl_server module-level env helpers + --extra-proxies collection
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# ─── Ensure the repo root is on sys.path ─────────────────────────
OWL_DIR = Path(__file__).resolve().parent.parent
if str(OWL_DIR) not in sys.path:
    sys.path.insert(0, str(OWL_DIR))

import proxy_defense as pd  # noqa: E402  (deliberate: repo-root sys.path bootstrap above)


# ═══════════════════════════════════════════════════════════════════
#  1. proxy_defense env helpers
# ═══════════════════════════════════════════════════════════════════

class TestEnvHelpers:
    def test_env_int_default(self, monkeypatch):
        monkeypatch.delenv("OWL_UNSET_INT", raising=False)
        assert pd._env_int("OWL_UNSET_INT", 42) == 42

    def test_env_int_parses(self, monkeypatch):
        monkeypatch.setenv("OWL_TEST_INT", "123")
        assert pd._env_int("OWL_TEST_INT", 42) == 123

    def test_env_int_invalid_falls_back(self, monkeypatch):
        monkeypatch.setenv("OWL_TEST_INT", "not-a-number")
        assert pd._env_int("OWL_TEST_INT", 42) == 42

    def test_env_float_parses(self, monkeypatch):
        monkeypatch.setenv("OWL_TEST_FLOAT", "2.5")
        assert pd._env_float("OWL_TEST_FLOAT", 1.0) == 2.5

    def test_env_float_invalid_falls_back(self, monkeypatch):
        monkeypatch.setenv("OWL_TEST_FLOAT", "abc")
        assert pd._env_float("OWL_TEST_FLOAT", 1.0) == 1.0

    @pytest.mark.parametrize("truthy", ["1", "true", "yes", "on", "enabled", "TRUE", " True "])
    def test_env_bool_truthy(self, monkeypatch, truthy):
        monkeypatch.setenv("OWL_TEST_BOOL", truthy)
        assert pd._env_bool("OWL_TEST_BOOL") is True

    @pytest.mark.parametrize("falsy", ["0", "false", "no", "off", "disable", ""])
    def test_env_bool_falsy(self, monkeypatch, falsy):
        monkeypatch.setenv("OWL_TEST_BOOL", falsy)
        assert pd._env_bool("OWL_TEST_BOOL") is False

    def test_env_bool_default(self, monkeypatch):
        monkeypatch.delenv("OWL_TEST_BOOL", raising=False)
        assert pd._env_bool("OWL_TEST_BOOL") is False
        assert pd._env_bool("OWL_TEST_BOOL", True) is True

    def test_env_list_parses_comma_separated(self, monkeypatch):
        monkeypatch.setenv("OWL_TEST_LIST", "US, GB,  DE ,")
        assert pd._env_list("OWL_TEST_LIST") == ["US", "GB", "DE"]

    def test_env_list_default(self, monkeypatch):
        monkeypatch.delenv("OWL_TEST_LIST", raising=False)
        assert pd._env_list("OWL_TEST_LIST", ["A", "B"]) == ["A", "B"]
        assert pd._env_list("OWL_TEST_LIST") == []


# ═══════════════════════════════════════════════════════════════════
#  2. Module constants reflect env vars at import time
# ═══════════════════════════════════════════════════════════════════

class TestConstantsFromEnv:
    """Constants are computed at import time, so we exercise them in a
    subprocess with the target environment. This avoids polluting the
    test-process module state with importlib.reload()."""

    _CODE = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(OWL_DIR)!r})\n"
        "import proxy_defense as pd\n"
        "print(json.dumps({\n"
        "  'countries': pd.DEFAULT_COUNTRIES,\n"
        "  'ttl': pd.DEFAULT_TTL,\n"
        "  'rate': pd.DEFAULT_RATE,\n"
        "  'min_rate': pd.ADAPTIVE_MIN_RATE,\n"
        "  'max_rate': pd.ADAPTIVE_MAX_RATE,\n"
        "  'cache_size': pd.MAX_PROXY_CACHE,\n"
        "  'cache_dir': str(pd.CACHE_DIR),\n"
        "}))\n"
    )

    def _run(self, env_overrides):
        env = {k: v for k, v in os.environ.items() if not k.startswith("OWL_")}
        env.update(env_overrides)
        proc = subprocess.run(
            [sys.executable, "-c", self._CODE],
            capture_output=True, text=True, env=env, cwd=str(OWL_DIR), timeout=120,
        )
        assert proc.returncode == 0, f"subprocess failed:\n{proc.stderr}"
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def test_constants_from_env(self):
        data = self._run({
            "OWL_PROXY_COUNTRIES": "US,PH",
            "OWL_CACHE_TTL": "123",
            "OWL_RATE_LIMIT": "2.5",
            "OWL_MIN_RATE": "0.05",
            "OWL_MAX_RATE": "9.5",
            "OWL_PROXY_CACHE_SIZE": "77",
            "OWL_CACHE_DIR": "/tmp/owl-env-test-cache",
        })
        assert data["countries"] == ["US", "PH"]
        assert data["ttl"] == 123
        assert data["rate"] == 2.5
        assert data["min_rate"] == 0.05
        assert data["max_rate"] == 9.5
        assert data["cache_size"] == 77
        assert data["cache_dir"] == "/tmp/owl-env-test-cache"

    def test_constants_defaults_when_unset(self):
        data = self._run({})
        assert data["countries"] == ["US", "GB", "DE", "FR", "CA"]
        assert data["ttl"] == 300
        assert data["rate"] == 1.0
        assert data["min_rate"] == 0.1
        assert data["max_rate"] == 5.0
        assert data["cache_size"] == 100


# ═══════════════════════════════════════════════════════════════════
#  3. ProxyPoolManager extra_proxies seeding
# ═══════════════════════════════════════════════════════════════════

class TestExtraProxiesSeeding:
    async def _make_pool(self, tmp_path, extra_proxies, cache_proxies=None):
        """Hermetic pool: no network fetch, no discovery loop."""
        cache_file = tmp_path / "proxy_cache.json"
        if cache_proxies is not None:
            cache_file.write_text(json.dumps({"proxies": cache_proxies}))
        pool = pd.ProxyPoolManager(cache_file=cache_file, extra_proxies=extra_proxies)
        pool._fetch_public_proxies = AsyncMock()
        pool._discovery_loop = AsyncMock()
        return pool

    @pytest.mark.asyncio
    async def test_extra_proxies_seeded_into_pool(self, tmp_path):
        pool = await self._make_pool(tmp_path, extra_proxies=[
            "socks5://127.0.0.1:42069",
            "https://user:pass@proxy.example.com:443",
        ])
        await pool.start()
        try:
            urls = pool.get_all_urls()
            assert "socks5://127.0.0.1:42069" in urls
            assert "https://user:pass@proxy.example.com:443" in urls
        finally:
            pool.stop()

    @pytest.mark.asyncio
    async def test_extra_proxies_dedup_with_cache(self, tmp_path):
        pool = await self._make_pool(tmp_path, extra_proxies=[
            "http://127.0.0.1:8080", "socks5://127.0.0.1:42069",
        ], cache_proxies=[
            {"url": "http://127.0.0.1:8080", "healthy": True,
             "last_check": 0.0, "fail_count": 0, "ban_until": 0.0},
        ])
        await pool.start()
        try:
            urls = pool.get_all_urls()
            assert urls.count("http://127.0.0.1:8080") == 1
            assert "socks5://127.0.0.1:42069" in urls
        finally:
            pool.stop()

    @pytest.mark.asyncio
    async def test_no_extra_proxies(self, tmp_path):
        pool = await self._make_pool(tmp_path, extra_proxies=None)
        await pool.start()
        try:
            assert pool.get_all_urls() == []
        finally:
            pool.stop()

    @pytest.mark.asyncio
    async def test_extra_proxies_filter_empty(self, tmp_path):
        pool = await self._make_pool(tmp_path, extra_proxies=["", "socks5://127.0.0.1:42069", "  "])
        await pool.start()
        try:
            assert pool.get_all_urls() == ["socks5://127.0.0.1:42069"]
        finally:
            pool.stop()


# ═══════════════════════════════════════════════════════════════════
#  4. owl_server env helpers + extra-proxies collection
# ═══════════════════════════════════════════════════════════════════

class TestOwlServerEnvHelpers:
    def test_env_bool(self, monkeypatch):
        import owl_server
        monkeypatch.setenv("OWL_SRV_BOOL", "true")
        assert owl_server._env_bool("OWL_SRV_BOOL") is True
        monkeypatch.setenv("OWL_SRV_BOOL", "0")
        assert owl_server._env_bool("OWL_SRV_BOOL") is False
        monkeypatch.delenv("OWL_SRV_BOOL", raising=False)
        assert owl_server._env_bool("OWL_SRV_BOOL", True) is True

    def test_env_list(self, monkeypatch):
        import owl_server
        monkeypatch.setenv("OWL_SRV_LIST", "a, b ,c")
        assert owl_server._env_list("OWL_SRV_LIST") == ["a", "b", "c"]
        monkeypatch.delenv("OWL_SRV_LIST", raising=False)
        assert owl_server._env_list("OWL_SRV_LIST", ["x"]) == ["x"]

    def test_collect_extra_proxies_empty(self):
        import owl_server
        assert owl_server._collect_extra_proxies({}) == []

    def test_collect_extra_proxies_from_all_sources(self):
        import owl_server
        environ = {
            "OWL_EXTRA_PROXIES": "http://127.0.0.1:8080,socks5://127.0.0.1:1080",
            "OWL_PROX5_SOCKS5": "127.0.0.1:42069",
            "OWL_HTTPS_PROXY": "https://alice:hunter2@proxy.example.com:443",
        }
        proxies = owl_server._collect_extra_proxies(environ)
        assert proxies == [
            "http://127.0.0.1:8080",
            "socks5://127.0.0.1:1080",
            "socks5://127.0.0.1:42069",          # scheme inferred
            "https://alice:hunter2@proxy.example.com:443",
        ]

    def test_collect_extra_proxies_full_url_not_prefixed(self):
        import owl_server
        environ = {"OWL_PROX5_SOCKS5": "socks5://127.0.0.1:42069"}  # already a URL
        assert owl_server._collect_extra_proxies(environ) == ["socks5://127.0.0.1:42069"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
