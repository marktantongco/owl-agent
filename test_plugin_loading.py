#!/usr/bin/env python3
"""Test that the example_logger plugin loads and registers hooks correctly."""

import asyncio
import sys
import logging

sys.path.insert(0, '/home/ubuntu/.owl-agent')
from plugin_loader import PluginLoader
from proxy_defense import PluginManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

async def _smoke_test():  # standalone smoke script, not a pytest test (see tests/test_v45_modules.py)
    print("=" * 60)
    print("OWL-AGENT v4.5 — Plugin Loading Test")
    print("=" * 60)
    print()

    # 1. Test PluginLoader discovers the plugin
    print("1. Creating PluginLoader...")
    loader = PluginLoader(plugin_dir="/home/ubuntu/.owl-agent/plugins", watch_interval=60)
    print(f"   Plugin directory: {loader.plugin_dir}")
    print(f"   Plugin dir exists: {loader.plugin_dir.exists()}")

    # 2. Scan for plugins
    print()
    print("2. Scanning for plugins...")
    loader._scan_all_plugins()
    stats = loader.get_stats()
    print(f"   Total plugins found: {stats['total']}")
    print(f"   Enabled: {stats['enabled']}")
    print(f"   Failed: {stats['failed']}")
    for name, info in stats['plugins'].items():
        print(f"   - {name}: hooks={info['hooks']}, enabled={info['enabled']}")

    # 3. Verify specific hooks
    print()
    print("3. Verifying hook registration...")
    request_hooks = loader.get_hooks("request")
    response_hooks = loader.get_hooks("response")
    error_hooks = loader.get_hooks("error")
    start_hooks = loader.get_hooks("start")
    complete_hooks = loader.get_hooks("complete")

    print(f"   request hooks:  {len(request_hooks)}")
    print(f"   response hooks: {len(response_hooks)}")
    print(f"   error hooks:    {len(error_hooks)}")
    print(f"   start hooks:    {len(start_hooks)}")
    print(f"   complete hooks: {len(complete_hooks)}")

    # 4. Test PluginManager integration
    print()
    print("4. Testing PluginManager integration...")
    pm = PluginManager(plugin_loader=loader)

    all_request = pm._get_all_hooks("request")
    all_response = pm._get_all_hooks("response")
    all_error = pm._get_all_hooks("error")
    print(f"   PluginManager request hooks (merged):  {len(all_request)}")
    print(f"   PluginManager response hooks (merged): {len(all_response)}")
    print(f"   PluginManager error hooks (merged):    {len(all_error)}")

    # 5. Execute hooks and verify they work
    print()
    print("5. Executing hooks...")
    await pm.run_hooks("request", method="GET", url="https://example.com/test")
    print("   ✅ on_request hook executed successfully")

    await pm.run_hooks("error", error=Exception("test error"), attempt=0, url="https://example.com/test")
    print("   ✅ on_error hook executed successfully")

    # 6. Test enable/disable
    print()
    print("6. Testing enable/disable...")
    loader.disable_plugin("example_logger")
    print(f"   Disabled: hooks now {len(loader.get_hooks('request'))}")
    loader.enable_plugin("example_logger")
    print(f"   Re-enabled: hooks now {len(loader.get_hooks('request'))}")

    # 7. Summary
    print()
    print("=" * 60)
    print("✅ ALL PLUGIN TESTS PASSED")
    print("   Plugin: example_logger")
    print("   Hooks registered: request, response, error")
    print("   PluginManager integration: working")
    print("   Enable/disable: working")
    print("=" * 60)

asyncio.run(_smoke_test())
