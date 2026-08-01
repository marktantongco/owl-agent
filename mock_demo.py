#!/usr/bin/env python3
"""
🦉 OWL-AGENT v4.2 - Mock Demo & Usage Guide
Simulates all tools with mock data to show how they work.
"""

import asyncio
import json
import time
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# MOCK DATA
# ═══════════════════════════════════════════════════════════════

MOCK_PROXIES = [
    {"url": "http://198.51.100.42:8080", "country": "US", "latency": 45, "success_rate": 0.95},
    {"url": "http://203.0.113.55:3128", "country": "GB", "latency": 78, "success_rate": 0.88},
    {"url": "socks5://192.0.2.100:1080", "country": "DE", "latency": 120, "success_rate": 0.72},
    {"url": "http://198.51.100.200:8888", "country": "FR", "latency": 95, "success_rate": 0.81},
    {"url": "http://203.0.113.75:9090", "country": "CA", "latency": 62, "success_rate": 0.91},
]

MOCK_GITHUB_USER = {
    "login": "octocat",
    "id": 583231,
    "name": "The Octocat",
    "company": "@github",
    "blog": "https://github.blog",
    "location": "San Francisco",
    "public_repos": 8,
    "followers": 23369,
    "following": 9,
}

MOCK_SCRAPE_RESULT = {
    "url": "https://example.com",
    "status": 200,
    "title": "Example Domain",
    "content_length": 1256,
    "proxy_used": "http://198.51.100.42:8080",
    "latency_ms": 45,
    "cached": False,
}

# ═══════════════════════════════════════════════════════════════
# ANSI COLORS
# ═══════════════════════════════════════════════════════════════

class C:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'

def header(text):
    print(f"\n{C.BOLD}{C.CYAN}{'═'*60}{C.END}")
    print(f"{C.BOLD}{C.CYAN}  {text}{C.END}")
    print(f"{C.BOLD}{C.CYAN}{'═'*60}{C.END}\n")

def success(text):
    print(f"{C.GREEN}✓{C.END} {text}")

def info(text):
    print(f"{C.BLUE}ℹ{C.END} {text}")

def warning(text):
    print(f"{C.YELLOW}⚠{C.END} {text}")

def error(text):
    print(f"{C.RED}✗{C.END} {text}")

def dim(text):
    print(f"{C.DIM}{text}{C.END}")

# ═══════════════════════════════════════════════════════════════
# MOCK TOOLS
# ═══════════════════════════════════════════════════════════════

class MockResilientClient:
    """Simulates the ResilientClient with mock responses."""
    
    def __init__(self):
        self.proxies = MOCK_PROXIES
        self.cache = {}
        self.scores = {}
        self.rates = {}
        self.request_count = 0
    
    async def get_stats(self):
        return {
            "proxies_total": len(self.proxies),
            "proxies_healthy": len(self.proxies),
            "scores": self.scores,
            "rates": self.rates,
        }
    
    async def request(self, method, url, **kwargs):
        self.request_count += 1
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Simulate GitHub API response
        if "github.com" in url and "octocat" in url:
            return MockResponse(200, json.dumps(MOCK_GITHUB_USER).encode())
        
        # Simulate general scrape
        return MockResponse(200, json.dumps(MOCK_SCRAPE_RESULT).encode())


class MockResponse:
    def __init__(self, status, content):
        self.status = status
        self.content = content
        self.headers = {"Content-Type": "application/json"}


# ═══════════════════════════════════════════════════════════════
# DEMO FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def demo_stats():
    header("1. PROXY POOL STATS")
    
    client = MockResilientClient()
    stats = await client.get_stats()
    
    success(f"Proxy pool: {stats['proxies_total']} total, {stats['proxies_healthy']} healthy")
    print()
    
    # Show proxy table
    print(f"  {'Proxy URL':<35} {'Country':<10} {'Latency':<10} {'Success':<10}")
    print(f"  {'─'*35} {'─'*10} {'─'*10} {'─'*10}")
    for p in MOCK_PROXIES:
        print(f"  {p['url']:<35} {p['country']:<10} {p['latency']}ms{'':<5} {p['success_rate']*100:.0f}%")


async def demo_fetch():
    header("2. FETCH URL (Direct Mode)")
    
    dim("Command: ~/.owl-agent/run.sh fetch https://api.github.com/users/octocat")
    print()
    
    client = MockResilientClient()
    resp = await client.request("GET", "https://api.github.com/users/octocat")
    data = json.loads(resp.content)
    
    success(f"Status: {resp.status}")
    info(f"Content-Length: {len(resp.content)} bytes")
    print()
    
    print(f"  {C.BOLD}User Data:{C.END}")
    print(f"  ├─ Login:    {data['login']}")
    print(f"  ├─ Name:     {data['name']}")
    print(f"  ├─ Company:  {data['company']}")
    print(f"  ├─ Location: {data['location']}")
    print(f"  ├─ Repos:    {data['public_repos']}")
    print(f"  └─ Followers: {data['followers']:,}")


async def demo_proxy_fetch():
    header("3. FETCH URL (Proxy Mode)")
    
    dim("Command: ~/.owl-agent/run.sh fetch --proxy https://httpbin.org/ip")
    print()
    
    client = MockResilientClient()
    proxy = MOCK_PROXIES[0]
    
    info(f"Selected proxy: {proxy['url']} (score: {proxy['success_rate']:.2f})")
    await asyncio.sleep(0.1)
    success(f"Request through proxy successful")
    info(f"Latency: {proxy['latency']}ms")
    print()
    
    # Simulate quality scoring
    client.scores[proxy['url']] = proxy['success_rate']
    client.rates["httpbin.org"] = 2.5
    
    print(f"  {C.BOLD}Quality Scores:{C.END}")
    for url, score in client.scores.items():
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"  {url:<35} [{bar}] {score:.2f}")
    
    print(f"\n  {C.BOLD}Adaptive Rates:{C.END}")
    for domain, rate in client.rates.items():
        print(f"  {domain:<35} {rate:.1f} req/s")


async def demo_scrape():
    header("4. SCRAPE WEBSITE (Browser Mode)")
    
    dim("Command: ~/.owl-agent/run.sh fetch --proxy https://example.com")
    dim("(With browser=True for JavaScript rendering)")
    print()
    
    info("Using curl_cffi Chrome 110 fingerprint...")
    await asyncio.sleep(0.15)
    success("Page rendered successfully")
    print()
    
    result = MOCK_SCRAPE_RESULT
    print(f"  {C.BOLD}Scrape Result:{C.END}")
    print(f"  ├─ URL:             {result['url']}")
    print(f"  ├─ Status:          {result['status']}")
    print(f"  ├─ Title:           {result['title']}")
    print(f"  ├─ Content Length:   {result['content_length']} bytes")
    print(f"  ├─ Proxy Used:      {result['proxy_used']}")
    print(f"  ├─ Latency:         {result['latency_ms']}ms")
    print(f"  └─ Cached:          {result['cached']}")


async def demo_mcp():
    header("5. MCP SERVER (Cline Integration)")
    
    dim("Config in Cline: ~/.owl-agent/mcp-server.py")
    print()
    
    tools = [
        ("owl_fetch", "Fetch URL via proxy pool", "GET /fetch?url=<url>"),
        ("owl_fetch_browser", "Fetch with JS rendering", "GET /fetch?url=<url>&browser=true"),
        ("owl_stats", "Get proxy statistics", "GET /stats"),
    ]
    
    print(f"  {C.BOLD}Available MCP Tools:{C.END}\n")
    for name, desc, endpoint in tools:
        print(f"  {C.GREEN}{name}{C.END}")
        print(f"    ├─ Description: {desc}")
        print(f"    └─ Endpoint:    {dim(endpoint)}")
        print()


async def demo_python_api():
    header("6. PYTHON API USAGE")
    
    code = '''
from proxy_defense import ResilientClient

async def main():
    # Basic usage
    async with ResilientClient() as client:
        resp = await client.request("GET", "https://api.github.com/users/octocat")
        print(f"Status: {resp.status}")
    
    # With options
    async with ResilientClient(
        use_curl_cffi=True,      # Chrome fingerprint
        countries=["US", "GB"],   # Country filter
        use_redis=True,           # State persistence
        cache_ttl=600,            # 10 min cache
        rate_limit=2.0,           # 2 req/s
    ) as client:
        resp = await client.request("GET", url)
'''
    
    print(f"  {C.BOLD}Example Code:{C.END}")
    for line in code.strip().split('\n'):
        print(f"  {C.DIM}{line}{C.END}")


async def demo_features():
    header("7. DEFENSE FEATURES STATUS")
    
    features = [
        ("Quality Scoring", "✓", "Picks best proxy for each target"),
        ("Adaptive Rate Limiting", "✓", "Reduces bans by 40-60%"),
        ("Circuit Breaker", "✓", "Stops hammering dead endpoints"),
        ("LRU Cache", "✓", "Memory + disk persistence"),
        ("Request Dedup", "✓", "In-flight coalescing"),
        ("curl_cffi Fingerprint", "✓", "Chrome 110 TLS handshake"),
        ("Retry-After Parsing", "✓", "Polite backoff compliance"),
        ("Redis State Sharing", "✓", "Optional persistence"),
    ]
    
    print(f"  {'Feature':<25} {'Status':<10} {'Description'}")
    print(f"  {'─'*25} {'─'*10} {'─'*40}")
    for name, status, desc in features:
        color = C.GREEN if status == "✓" else C.YELLOW
        print(f"  {name:<25} {color}{status}{C.END}{'':<7} {desc}")


async def demo_usage_guide():
    header("8. QUICK USAGE GUIDE")
    
    commands = [
        ("~/.owl-agent/run.sh stats", "Show proxy pool statistics"),
        ("~/.owl-agent/run.sh test", "Test GitHub API connection"),
        ("~/.owl-agent/run.sh fetch <url>", "Fetch URL (direct)"),
        ("~/.owl-agent/run.sh fetch --proxy <url>", "Fetch URL (via proxy)"),
        ("~/.owl-agent/run.sh serve", "Start HTTP API server"),
        ("~/.owl-agent/run.sh help", "Show all commands"),
    ]
    
    print(f"  {C.BOLD}CLI Commands:{C.END}\n")
    for cmd, desc in commands:
        print(f"  {C.GREEN}{cmd}{C.END}")
        print(f"    └─ {desc}")
        print()


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    print(f"""
{C.BOLD}{C.CYAN}
  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║   🦉 OWL-AGENT v4.2 - Mock Demo & Usage Guide           ║
  ║                                                           ║
  ║   Self-Optimising Scraping Engine                         ║
  ║   50+ Proxies | Quality Scoring | Chrome Fingerprint     ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝
{C.END}""")
    
    await demo_stats()
    await demo_fetch()
    await demo_proxy_fetch()
    await demo_scrape()
    await demo_mcp()
    await demo_python_api()
    await demo_features()
    await demo_usage_guide()
    
    print(f"""
{C.BOLD}{C.GREEN}
  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║   ✅ All tools simulated successfully!                   ║
  ║                                                           ║
  ║   To use with real proxies:                               ║
  ║   1. Add working proxies to proxy_cache.json             ║
  ║   2. Or buy proxy service (Bright Data, Oxylabs)         ║
  ║   3. Run: ~/.owl-agent/run.sh fetch --proxy <url>        ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝
{C.END}""")

if __name__ == "__main__":
    asyncio.run(main())
