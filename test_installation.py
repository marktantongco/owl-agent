#!/usr/bin/env python3
"""
🦉 OWL-AGENT Installation Test
Verify that all components are properly installed and working.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add OWL-AGENT to path
sys.path.insert(0, str(Path.home() / ".owl-agent"))

def print_status(icon: str, message: str, status: str):
    """Print a status message with icon."""
    colors = {
        "ok": "\033[92m✓\033[0m",
        "warn": "\033[93m⚠\033[0m",
        "error": "\033[91m✗\033[0m",
        "info": "\033[94mℹ\033[0m"
    }
    print(f"{colors.get(status, ' ')} {message}")

def test_imports():
    """Test that all required modules can be imported."""
    print("\n📦 Testing Imports...")

    modules = [
        ("aiohttp", "aiohttp"),
        ("aiofiles", "aiofiles"),
        ("httpx", "httpx"),
        ("resilient_httpx", "resilient_httpx"),
        ("circuitbreaker", "circuitbreaker"),
    ]

    optional_modules = [
        ("proxybroker", "proxybroker (proxy discovery)"),
        ("litproxy", "litproxy (proxy rotation)"),
        ("curl_cffi", "curl_cffi (Chrome fingerprinting)"),
        ("redis", "redis (state sharing)"),
    ]

    all_ok = True
    for module, name in modules:
        try:
            __import__(module)
            print_status("ok", f"{name}: installed", "ok")
        except ImportError as e:
            print_status("error", f"{name}: MISSING - {e}", "error")
            all_ok = False

    for module, name in optional_modules:
        try:
            __import__(module)
            print_status("ok", f"{name}: installed (optional)", "ok")
        except ImportError:
            print_status("warn", f"{name}: not installed (optional)", "warn")

    return all_ok

def test_owl_agent_import():
    """Test that OWL-AGENT modules can be imported."""
    print("\n🦉 Testing OWL-AGENT Import...")

    try:
        from proxy_defense import (  # noqa: F401  (import-existence check: names intentionally unused)
            ResilientClient,
            HTTPCache,
            RequestDeduplicator,
            QualityScorer,
            AdaptiveRateLimiter,
            RedisStore,
            ProxyPoolManager,
            DomainCircuitBreaker,
            AgentBrowserWrapper
        )
        print_status("ok", "All classes imported successfully", "ok")
        return True
    except ImportError as e:
        print_status("error", f"Import failed: {e}", "error")
        return False

def test_directories():
    """Test that required directories exist."""
    print("\n📁 Testing Directories...")

    dirs = [
        (Path.home() / ".owl-agent", "OWL-AGENT home"),
        (Path.home() / ".owl-agent" / "cache", "Cache directory"),
        (Path.home() / ".owl-agent" / "cache" / "http", "HTTP cache"),
        (Path.home() / ".owl-agent" / "config", "Config directory"),
    ]

    all_ok = True
    for path, name in dirs:
        if path.exists():
            print_status("ok", f"{name}: {path}", "ok")
        else:
            print_status("error", f"{name}: MISSING", "error")
            all_ok = False

    return all_ok

def test_files():
    """Test that required files exist."""
    print("\n📄 Testing Files...")

    files = [
        (Path.home() / ".owl-agent" / "proxy_defense.py", "Main script"),
        (Path.home() / ".owl-agent" / "run.sh", "CLI wrapper"),
        (Path.home() / ".owl-agent" / "mcp-server.py", "MCP server"),
        (Path.home() / ".owl-agent" / "commands.json", "Cursor commands"),
        (Path.home() / ".owl-agent" / "warp-agent.yaml", "Warp agent"),
        (Path.home() / ".owl-agent" / "owl-agent.skill.json", "OpenCode skill"),
        (Path.home() / ".owl-agent" / "package.json", "Package metadata"),
        (Path.home() / ".owl-agent" / "README.md", "Documentation"),
        (Path.home() / ".owl-agent" / "DOCUMENTATION.md", "Full documentation"),
        (Path.home() / ".owl-agent" / "LICENSE", "License"),
        (Path.home() / ".owl-agent" / "CONTRIBUTING.md", "Contributing guide"),
    ]

    all_ok = True
    for path, name in files:
        if path.exists():
            print_status("ok", f"{name}: exists", "ok")
        else:
            print_status("error", f"{name}: MISSING", "error")
            all_ok = False

    return all_ok

def test_executable():
    """Test that run.sh is executable."""
    print("\n🔧 Testing Executable...")

    run_sh = Path.home() / ".owl-agent" / "run.sh"
    if run_sh.exists() and os.access(run_sh, os.X_OK):
        print_status("ok", "run.sh is executable", "ok")
        return True
    else:
        print_status("error", "run.sh is not executable", "error")
        return False

async def test_basic_functionality():
    """Test basic functionality of ResilientClient."""
    print("\n⚡ Testing Basic Functionality...")

    try:
        from proxy_defense import ResilientClient

        async with ResilientClient(
            use_curl_cffi=False,  # Use httpx for testing
            countries=["US"],
            use_redis=False
        ) as client:
            stats = await client.get_stats()
            print_status("ok", f"Proxy pool initialized: {stats['proxies_total']} proxies", "ok")
            return True
    except Exception as e:
        print_status("error", f"Functionality test failed: {e}", "error")
        return False

async def main():
    """Run all tests."""
    print("=" * 60)
    print("🦉 OWL-AGENT v4.2 Installation Test")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("OWL-AGENT Import", test_owl_agent_import()))
    results.append(("Directories", test_directories()))
    results.append(("Files", test_files()))
    results.append(("Executable", test_executable()))
    results.append(("Basic Functionality", await test_basic_functionality()))

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")

    print(f"\n{'✓' if passed == total else '⚠'} {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 Installation test PASSED! OWL-AGENT is ready to use.")
        print("\n🚀 Quick start:")
        print("   ~/.owl-agent/run.sh test")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("\n📖 Documentation: ~/.owl-agent/DOCUMENTATION.md")

    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
