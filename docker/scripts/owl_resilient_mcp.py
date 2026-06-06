#!/usr/bin/env python3
"""
owl_resilient_mcp.py v1.1 — MCP Server exposing resilient HTTP tools for AI agents.

Implements the Model Context Protocol (JSON-RPC over stdin/stdout) using threading
to avoid asyncio event-loop conflicts with proxy_defense_fixed_v3.

v6.0 Bug Fix: handle_tool_call no longer references self._stats (NameError).
              Instead, it calls client.get_stats() on the module-level client.
"""

from __future__ import annotations

import json
import sys
import threading
import traceback
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Import proxy_defense_fixed_v3 — the resilient HTTP client module
# ---------------------------------------------------------------------------
try:
    from proxy_defense_fixed_v3 import ResilientHTTPClient

    client: Optional[ResilientHTTPClient] = ResilientHTTPClient()
except ImportError:
    print(
        json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/message",
            "params": {
                "level": "warning",
                "data": (
                    "proxy_defense_fixed_v3 not found — running in stub mode. "
                    "All tool calls will return error responses."
                ),
            },
        }),
        flush=True,
    )
    client = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# MCP Protocol Constants
# ---------------------------------------------------------------------------
SERVER_NAME = "owl-resilient-mcp"
SERVER_VERSION = "1.1.0"
PROTOCOL_VERSION = "2024-11-05"

# ---------------------------------------------------------------------------
# Tool Definitions (JSON Schema)
# ---------------------------------------------------------------------------
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "fetch_resilient",
        "description": (
            "Make a resilient HTTP request with automatic retries, circuit-breaker "
            "protection, and proxy rotation via the ResilientHTTPClient."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to request (required).",
                },
                "method": {
                    "type": "string",
                    "description": "HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS).",
                    "default": "GET",
                },
                "headers": {
                    "type": "object",
                    "description": "Optional HTTP headers as key-value pairs.",
                    "additionalProperties": {"type": "string"},
                },
                "body": {
                    "type": "string",
                    "description": "Optional request body (sent as-is for non-JSON, "
                    "parsed as JSON when Content-Type is application/json).",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "fetch_status",
        "description": (
            "Return client statistics: total_requests, success_count, failure_count, "
            "cache_hits, and circuit_breaker_trips."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "fetch_clear_cache",
        "description": "Clear the internal response cache of the ResilientHTTPClient.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "health_check",
        "description": "Return health status of all configured proxy endpoints.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "queue_status",
        "description": "Return the current in-flight request count managed by the client.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]

# ---------------------------------------------------------------------------
# Tool Handlers
# ---------------------------------------------------------------------------

def _no_client_error() -> Dict[str, Any]:
    """Return a structured error when the ResilientHTTPClient is unavailable."""
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({
                    "error": "ResilientHTTPClient not available",
                    "detail": (
                        "proxy_defense_fixed_v3 could not be imported. "
                        "Ensure the module is on PYTHONPATH."
                    ),
                }),
            }
        ],
        "isError": True,
    }


def tool_fetch_resilient(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a resilient HTTP request through the client."""
    if client is None:
        return _no_client_error()

    url: str = params.get("url", "")
    method: str = params.get("method", "GET").upper()
    headers: Optional[Dict[str, str]] = params.get("headers")
    body: Optional[str] = params.get("body")

    if not url:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"error": "Missing required parameter: url"}),
                }
            ],
            "isError": True,
        }

    try:
        result = client.request(
            url=url,
            method=method,
            headers=headers,
            body=body,
        )

        # Normalize the result into MCP content format
        if isinstance(result, dict):
            text = json.dumps(result, default=str)
        elif isinstance(result, str):
            text = result
        else:
            text = str(result)

        return {
            "content": [
                {"type": "text", "text": text},
            ]
        }
    except Exception as exc:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }),
                }
            ],
            "isError": True,
        }


def tool_fetch_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return client statistics.

    v6.0 Bug Fix: Uses client.get_stats() instead of the broken self._stats
    reference that caused a NameError in the original module-level function.
    """
    if client is None:
        return _no_client_error()

    try:
        stats = client.get_stats()
        # Ensure all expected keys are present even if the client omits some
        normalized = {
            "total_requests": stats.get("total_requests", 0),
            "success_count": stats.get("success_count", 0),
            "failure_count": stats.get("failure_count", 0),
            "cache_hits": stats.get("cache_hits", 0),
            "circuit_breaker_trips": stats.get("circuit_breaker_trips", 0),
        }
        return {
            "content": [
                {"type": "text", "text": json.dumps(normalized, default=str)},
            ]
        }
    except Exception as exc:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }),
                }
            ],
            "isError": True,
        }


def tool_fetch_clear_cache(params: Dict[str, Any]) -> Dict[str, Any]:
    """Clear the response cache."""
    if client is None:
        return _no_client_error()

    try:
        client.clear_cache()
        return {
            "content": [
                {"type": "text", "text": json.dumps({"status": "cache_cleared"})},
            ]
        }
    except Exception as exc:
        # Fallback: try attribute-style access if clear_cache is not a method
        try:
            if hasattr(client, "_cache"):
                client._cache.clear()  # type: ignore[attr-defined]
                return {
                    "content": [
                        {"type": "text", "text": json.dumps({"status": "cache_cleared"})},
                    ]
                }
        except Exception:
            pass

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }),
                }
            ],
            "isError": True,
        }


def tool_health_check(params: Dict[str, Any]) -> Dict[str, Any]:
    """Check health of all configured proxies."""
    if client is None:
        return _no_client_error()

    try:
        if hasattr(client, "health_check"):
            result = client.health_check()
        elif hasattr(client, "check_proxies"):
            result = client.check_proxies()
        elif hasattr(client, "check_health"):
            result = client.check_health()
        else:
            # Best-effort: report client existence as healthy
            result = {"status": "client_initialized", "proxies": "unknown"}

        if isinstance(result, dict):
            text = json.dumps(result, default=str)
        else:
            text = str(result)

        return {
            "content": [
                {"type": "text", "text": text},
            ]
        }
    except Exception as exc:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }),
                }
            ],
            "isError": True,
        }


def tool_queue_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return current in-flight request count."""
    if client is None:
        return _no_client_error()

    try:
        if hasattr(client, "in_flight_count"):
            count = client.in_flight_count
        elif hasattr(client, "get_in_flight"):
            count = client.get_in_flight()
        elif hasattr(client, "queue_status"):
            result = client.queue_status()
            if isinstance(result, dict):
                return {
                    "content": [
                        {"type": "text", "text": json.dumps(result, default=str)},
                    ]
                }
            count = result
        elif hasattr(client, "_in_flight"):
            # Access the internal counter directly as a last resort
            count = client._in_flight  # type: ignore[attr-defined]
        else:
            count = 0

        return {
            "content": [
                {"type": "text", "text": json.dumps({"in_flight": count})},
            ]
        }
    except Exception as exc:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }),
                }
            ],
            "isError": True,
        }


# ---------------------------------------------------------------------------
# Tool Dispatch Table
# ---------------------------------------------------------------------------
TOOL_HANDLERS: Dict[str, Any] = {
    "fetch_resilient": tool_fetch_resilient,
    "fetch_status": tool_fetch_status,
    "fetch_clear_cache": tool_fetch_clear_cache,
    "health_check": tool_health_check,
    "queue_status": tool_queue_status,
}

# ---------------------------------------------------------------------------
# JSON-RPC / MCP Message Handling
# ---------------------------------------------------------------------------

def handle_initialize(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Respond to the MCP `initialize` request with server capabilities."""
    return {
        "jsonrpc": "2.0",
        "id": msg.get("id"),
        "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {
                    "listChanged": False,
                },
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
            },
        },
    }


def handle_tools_list(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Respond to `tools/list` with the available tool definitions."""
    return {
        "jsonrpc": "2.0",
        "id": msg.get("id"),
        "result": {
            "tools": TOOLS,
        },
    }


def handle_tools_call(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Execute a tool call and return the result.

    v6.0 Bug Fix: The original implementation was a module-level function that
    referenced `self._stats`, causing a NameError at runtime. This version uses
    `client.get_stats()` (the module-level ResilientHTTPClient instance) instead.
    """
    tool_name = ""
    try:
        params = msg.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        handler = TOOL_HANDLERS.get(tool_name)
        if handler is None:
            return {
                "jsonrpc": "2.0",
                "id": msg.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "error": f"Unknown tool: {tool_name}",
                                "available_tools": list(TOOL_HANDLERS.keys()),
                            }),
                        }
                    ],
                    "isError": True,
                },
            }

        result = handler(arguments)

        return {
            "jsonrpc": "2.0",
            "id": msg.get("id"),
            "result": result,
        }
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": msg.get("id"),
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "error": f"Tool execution failed: {exc}",
                            "tool": tool_name,
                            "traceback": traceback.format_exc(),
                        }),
                    }
                ],
                "isError": True,
            },
        }


# ---------------------------------------------------------------------------
# Request Router
# ---------------------------------------------------------------------------

def process_message(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Route an incoming JSON-RPC message to the appropriate handler.

    Returns the response dict, or None for notifications that require no reply.
    """
    # --- Validate JSON-RPC 2.0 structure first ---------------------------
    if msg.get("jsonrpc") != "2.0":
        msg_id = msg.get("id") if isinstance(msg, dict) else None
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32600,
                "message": "Invalid Request: missing or wrong 'jsonrpc' version",
            },
        }

    method = msg.get("method", "")

    # --- MCP lifecycle --------------------------------------------------
    if method == "initialize":
        return handle_initialize(msg)

    if method == "notifications/initialized":
        # Client confirmed initialization — no response required
        return None

    # --- Tool operations ------------------------------------------------
    if method == "tools/list":
        return handle_tools_list(msg)

    if method == "tools/call":
        return handle_tools_call(msg)

    # --- Unknown method -------------------------------------------------
    if "id" in msg:
        return {
            "jsonrpc": "2.0",
            "id": msg["id"],
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}",
            },
        }

    # Notification with unknown method — ignore per JSON-RPC spec
    return None


# ---------------------------------------------------------------------------
# Stdin Reader (threading-based, NOT asyncio)
# ---------------------------------------------------------------------------

def read_loop() -> None:
    """Read JSON-RPC messages from stdin, one per line, and dispatch them.

    Uses blocking I/O in a daemon thread so there are zero asyncio
    dependencies — this avoids the event-loop conflicts that arise when
    proxy_defense_fixed_v3 creates its own asyncio loop internally.
    """
    stdin_lock = threading.Lock()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        # --- Parse -------------------------------------------------------
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {exc}",
                },
            }
            _send(response)
            continue

        # --- Validate basic JSON-RPC structure ---------------------------
        if not isinstance(msg, dict) or "jsonrpc" not in msg:
            response = {
                "jsonrpc": "2.0",
                "id": msg.get("id") if isinstance(msg, dict) else None,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: missing 'jsonrpc' field",
                },
            }
            _send(response)
            continue

        # --- Process & respond -------------------------------------------
        try:
            response = process_message(msg)
            if response is not None:
                _send(response)
        except Exception as exc:
            error_response = {
                "jsonrpc": "2.0",
                "id": msg.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {exc}",
                    "data": traceback.format_exc(),
                },
            }
            _send(error_response)


def _send(response: Dict[str, Any]) -> None:
    """Write a JSON-RPC response to stdout in a thread-safe manner."""
    payload = json.dumps(response, default=str)
    with _stdout_lock:
        sys.stdout.write(payload + "\n")
        sys.stdout.flush()


_stdout_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    """Start the MCP server. Reads from stdin, writes to stdout."""
    # Emit a log notification so host processes know we started
    _send({
        "jsonrpc": "2.0",
        "method": "notifications/message",
        "params": {
            "level": "info",
            "data": f"{SERVER_NAME} v{SERVER_VERSION} started (protocol {PROTOCOL_VERSION})",
        },
    })

    try:
        read_loop()
    except KeyboardInterrupt:
        pass
    except Exception:
        # Last-ditch error log before exiting
        _send({
            "jsonrpc": "2.0",
            "method": "notifications/message",
            "params": {
                "level": "error",
                "data": f"{SERVER_NAME} crashed: {traceback.format_exc()}",
            },
        })
        raise


if __name__ == "__main__":
    main()
