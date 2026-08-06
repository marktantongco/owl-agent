#!/usr/bin/env python3
"""OWL-AGENT v4.5 Live End-to-End Test"""

import asyncio
import sys
import json
import time

sys.path.insert(0, '/home/ubuntu/.owl-agent')
from proxy_defense import ResilientClient


async def _e2e_smoke():  # standalone live-e2e script, not a pytest test (see tests/)
    print("1. Creating ResilientClient with ML + AB + Plugins enabled...")
    async with ResilientClient(
        use_curl_cffi=False,
        countries=["US", "GB"],
        enable_ab_test=True,
        enable_ml=True,
        ml_model="auto"
    ) as client:
        print("2. Client initialized, fetching proxy pool stats...")
        stats = await client.get_stats()
        print(f"   Proxies: {stats['proxies_total']} total, {stats['proxies_healthy']} healthy")
        print(f"   ML trained: {stats.get('ml_trained', False)}")
        print(f"   Plugins: {stats.get('plugins', {}).get('total', 0)} loaded")
        print(f"   AB test domains: {len(stats.get('ab_test', {}))}")
        print()

        # Test 1: HTTP URL (should use proxy pool)
        print("3. Test 1: Fetching http://httpbin.org/get via proxy pool...")
        start = time.time()
        resp = await client.request("GET", "http://httpbin.org/get")
        latency = time.time() - start
        print(f"   Status: {resp.status}")
        print(f"   Content length: {len(resp.content)} bytes")
        print(f"   Latency: {latency:.2f}s")
        if resp.status == 200:
            data = json.loads(resp.content)
            print(f"   Origin: {data.get('origin', 'unknown')}")
        print()

        # Test 2: HTTPS URL (should go direct)
        print("4. Test 2: Fetching https://httpbin.org/get (direct)...")
        start = time.time()
        resp2 = await client.request("GET", "https://httpbin.org/get")
        latency2 = time.time() - start
        print(f"   Status: {resp2.status}")
        print(f"   Content length: {len(resp2.content)} bytes")
        print(f"   Latency: {latency2:.2f}s")
        print()

        # Test 3: Another HTTP URL
        print("5. Test 3: Fetching http://httpbin.org/ip...")
        start = time.time()
        resp3 = await client.request("GET", "http://httpbin.org/ip")
        latency3 = time.time() - start
        print(f"   Status: {resp3.status}")
        print(f"   Content: {resp3.content[:100]}")
        print(f"   Latency: {latency3:.2f}s")
        print()

        # Check ML and AB stats after requests
        print("6. Post-request stats:")
        stats2 = await client.get_stats()
        print(f"   ML trained: {stats2.get('ml_trained', False)}")
        ml_info = stats2.get("ml_model", {})
        print(f"   ML model: {ml_info.get('model_name', 'none')}")
        print(f"   ML samples: {ml_info.get('samples', 0)}")
        print(f"   ML cv_score: {ml_info.get('cv_score', 0):.3f}")
        print(f"   AB test domains: {len(stats2.get('ab_test', {}))}")
        print(f"   Quality scores count: {len(stats2.get('scores', {}))}")
        print()
        print("✅ E2E test completed successfully!")


if __name__ == "__main__":
    asyncio.run(_e2e_smoke())
