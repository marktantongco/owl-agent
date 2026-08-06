#!/usr/bin/env python3
"""
🦉 OWL-AGENT v4.5 — Self-Healing Plugin Loader
Automatically discovers, loads, and reloads plugins from a designated directory.
"""

import importlib
import importlib.util
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Callable, Optional

logger = logging.getLogger("owl-agent.plugin")


class PluginLoader:
    """Auto-discovers and hot-reloads plugins from a directory.

    Plugins are Python files in the plugin directory that define
    hook functions: on_request, on_response, on_error, on_start, on_complete.

    Features:
    - Automatic discovery on startup
    - Hot-reload when files change (periodic scan)
    - Self-healing: disables failed plugins, retries later
    - Isolation: plugin errors don't crash the engine
    """

    HOOK_TYPES = ["start", "request", "response", "error", "complete"]

    def __init__(self, plugin_dir: str = "~/.owl-agent/plugins",
                 watch_interval: int = 10):
        self.plugin_dir = Path(plugin_dir).expanduser()
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.watch_interval = watch_interval
        self._loaded_plugins: Dict[str, Dict[str, Callable]] = {}
        self._enabled: Dict[str, bool] = {}
        self._failed: Dict[str, int] = {}  # name -> fail count
        self._last_modified: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._watch_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the plugin loader: scan once, then watch."""
        self._running = True
        self._scan_all_plugins()
        self._watch_task = asyncio.create_task(self._watch_loop())
        logger.info(f"🔌 Plugin loader started (dir: {self.plugin_dir})")

    async def stop(self):
        """Stop the plugin loader."""
        self._running = False
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass

    async def _watch_loop(self):
        """Periodically scan for new/changed plugins."""
        while self._running:
            try:
                await asyncio.sleep(self.watch_interval)
                await self._scan_and_reload()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Plugin watch error: {e}")
                await asyncio.sleep(self.watch_interval)

    def _scan_all_plugins(self):
        """Initial scan of all plugins."""
        for file_path in self.plugin_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue  # Skip private files
            try:
                self._load_plugin_file(file_path)
            except Exception as e:
                logger.error(f"Failed to load plugin {file_path.name}: {e}")

    async def _scan_and_reload(self):
        """Scan for changed plugins and reload them."""
        for file_path in self.plugin_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            try:
                mod_time = file_path.stat().st_mtime
                if self._last_modified.get(str(file_path), 0) < mod_time:
                    await self._reload_plugin_file(file_path)
            except Exception as e:
                logger.debug(f"Error checking plugin {file_path.name}: {e}")

    def _load_plugin_file(self, file_path: Path):
        """Load a plugin file and register its hooks."""
        try:
            spec = importlib.util.spec_from_file_location(
                file_path.stem, file_path
            )
            if spec is None or spec.loader is None:
                logger.warning(f"Cannot load plugin spec: {file_path.name}")
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            hooks = self._extract_hooks(module)
            if hooks:
                self._loaded_plugins[file_path.stem] = hooks
                self._enabled[file_path.stem] = True
                self._failed[file_path.stem] = 0
                self._last_modified[str(file_path)] = file_path.stat().st_mtime
                logger.info(f"🔌 Loaded plugin: {file_path.stem} "
                          f"({', '.join(hooks.keys())})")
            else:
                logger.debug(f"Plugin {file_path.stem} has no hook functions")
        except Exception as e:
            logger.error(f"Failed to load plugin {file_path.name}: {e}")
            self._failed[file_path.stem] = self._failed.get(file_path.stem, 0) + 1

    async def _reload_plugin_file(self, file_path: Path):
        """Hot-reload a changed plugin file."""
        name = file_path.stem
        logger.info(f"🔄 Reloading plugin: {name}")
        try:
            # Remove from sys.modules if previously loaded
            if name in sys.modules:
                del sys.modules[name]

            spec = importlib.util.spec_from_file_location(name, file_path)
            if spec is None or spec.loader is None:
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            hooks = self._extract_hooks(module)
            async with self._lock:
                if hooks:
                    self._loaded_plugins[name] = hooks
                    self._enabled[name] = True
                    self._failed[name] = 0
                    self._last_modified[str(file_path)] = file_path.stat().st_mtime
                    logger.info(f"✅ Reloaded plugin: {name} "
                              f"({', '.join(hooks.keys())})")
                else:
                    # Plugin lost its hooks - disable it
                    self._enabled[name] = False
                    logger.warning(f"Plugin {name} lost hooks after reload, disabled")
        except Exception as e:
            logger.error(f"Failed to reload plugin {name}: {e}")
            self._failed[name] = self._failed.get(name, 0) + 1
            # Self-healing: disable after 3 consecutive failures
            if self._failed[name] >= 3:
                self._enabled[name] = False
                logger.warning(f"Plugin {name} disabled after 3 failures")

    def _extract_hooks(self, module) -> Dict[str, Callable]:
        """Extract hook functions from a module."""
        hooks = {}
        for hook_type in self.HOOK_TYPES:
            func = getattr(module, f"on_{hook_type}", None)
            if func and callable(func):
                hooks[hook_type] = func
        return hooks

    def get_hooks(self, hook_type: str) -> List[Callable]:
        """Return all enabled hook functions for a given type."""
        funcs = []
        for name, hooks in self._loaded_plugins.items():
            if self._enabled.get(name, False) and hook_type in hooks:
                funcs.append(hooks[hook_type])
        return funcs

    def disable_plugin(self, name: str):
        """Manually disable a plugin."""
        self._enabled[name] = False
        logger.info(f"Plugin {name} disabled")

    def enable_plugin(self, name: str):
        """Manually enable a plugin."""
        if name in self._loaded_plugins:
            self._enabled[name] = True
            self._failed[name] = 0
            logger.info(f"Plugin {name} enabled")

    def get_stats(self) -> Dict:
        """Return plugin statistics."""
        return {
            "total": len(self._loaded_plugins),
            "enabled": sum(1 for v in self._enabled.values() if v),
            "failed": sum(1 for v in self._failed.values() if v >= 3),
            "plugins": {
                name: {
                    "enabled": self._enabled.get(name, False),
                    "hooks": list(hooks.keys()),
                    "failures": self._failed.get(name, 0),
                }
                for name, hooks in self._loaded_plugins.items()
            }
        }
