#!/usr/bin/env python3
"""
OWL-AGENT Validation Suite — Docker Edition
Runs 8 checks to verify the Docker deployment is healthy.
"""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

SCRIPTS_DIR = Path("/app/scripts")
CONFIG_DIR = Path("/app/config")
PROXY_PORT = 60000

PASSED = 0
FAILED = 0

def check(name: str, condition: bool, detail: str = ""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✅ {name}")
    else:
        FAILED += 1
        print(f"  ❌ {name} — {detail}")

def main():
    print("🦉 OWL-AGENT Validation Suite — Docker Edition")
    print("=" * 55)

    # Test 1: File existence
    print("\n[1/8] File Existence")
    for f in [
        "forward_proxy.py",
        "proxy_defense_fixed_v3.py",
        "owl_resilient_mcp.py",
    ]:
        check(f, (SCRIPTS_DIR / f).exists(), f"Missing {SCRIPTS_DIR / f}")

    # Test 2: Config files
    print("\n[2/8] Config Files")
    for f in ["proxy_pool.json", "proxy_sources.json"]:
        check(f, (CONFIG_DIR / f).exists(), f"Missing {CONFIG_DIR / f}")

    # Test 3: Python syntax
    print("\n[3/8] Python Syntax Validation")
    for f in SCRIPTS_DIR.glob("*.py"):
        import ast
        try:
            ast.parse((SCRIPTS_DIR / f.name).read_text())
            check(f.name, True)
        except SyntaxError as e:
            check(f.name, False, str(e))

    # Test 4: JSON validity
    print("\n[4/8] JSON Config Validity")
    for f in CONFIG_DIR.glob("*.json"):
        try:
            json.loads((CONFIG_DIR / f.name).read_text())
            check(f.name, True)
        except json.JSONDecodeError as e:
            check(f.name, False, str(e))

    # Test 5: Forward proxy health
    print("\n[5/8] Forward Proxy Health Check")
    try:
        resp = urllib.request.urlopen(f"http://localhost:{PROXY_PORT}/health", timeout=5)
        data = json.loads(resp.read())
        check("Proxy /health", data.get("status") == "ok", f"Got: {data}")
    except Exception as e:
        check("Proxy /health", False, str(e))

    # Test 6: Bypass domain logic
    print("\n[6/8] Bypass Domain Logic")
    try:
        from importlib.machinery import SourceFileLoader
        fp = SourceFileLoader("forward_proxy", str(SCRIPTS_DIR / "forward_proxy.py")).load_module()
        check("bypass module loaded", True)
        if hasattr(fp, "should_bypass"):
            check("nvidia.com bypass", fp.should_bypass("api.nvidia.com"))
            check("opencode.ai bypass", fp.should_bypass("cdn.opencode.ai"))
            check("random.com no bypass", not fp.should_bypass("example.com"))
        else:
            check("should_bypass function", False, "Function not found in module")
    except Exception as e:
        check("Bypass logic import", False, str(e))

    # Test 7: MCP protocol
    print("\n[7/8] MCP Protocol Handshake")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "owl_resilient_mcp.py")],
            input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            capture_output=True, text=True, timeout=10,
        )
        if result.stdout.strip():
            resp = json.loads(result.stdout.strip())
            check("MCP initialize", resp.get("result", {}).get("protocolVersion") is not None, f"Got: {resp}")
        else:
            check("MCP initialize", False, "No stdout output")
    except Exception as e:
        check("MCP initialize", False, str(e))

    # Test 8: Dependencies
    print("\n[8/8] Python Dependencies")
    for mod in ["aiohttp", "httpx", "json", "asyncio", "hashlib"]:
        try:
            __import__(mod)
            check(mod, True)
        except ImportError as e:
            check(mod, False, str(e))

    # Summary
    print("\n" + "=" * 55)
    total = PASSED + FAILED
    if FAILED == 0:
        print(f"🦉 ALL {total} TESTS PASSED!")
        return 0
    else:
        print(f"⚠️  {PASSED}/{total} passed, {FAILED} failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
