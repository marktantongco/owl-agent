#!/usr/bin/env python3
"""
🦉 OWL-AGENT MCP Server
Model Context Protocol server for Cline integration
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

# MCP Protocol implementation
class MCPServer:
    def __init__(self):
        self.tools = {}
        self.resources = {}

    def tool(self, name: str, description: str):
        def decorator(func):
            self.tools[name] = {
                "name": name,
                "description": description,
                "handler": func
            }
            return func
        return decorator

    def resource(self, uri: str, name: str, description: str):
        def decorator(func):
            self.resources[uri] = {
                "uri": uri,
                "name": name,
                "description": description,
                "handler": func
            }
            return func
        return decorator

    async def handle_request(self, request: Dict) -> Dict:
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id", 1)

        if method == "initialize":
            return await self._handle_initialize(req_id, params)
        elif method == "tools/list":
            return await self._handle_tools_list(req_id)
        elif method == "tools/call":
            return await self._handle_tool_call(req_id, params)
        elif method == "resources/list":
            return await self._handle_resources_list(req_id)
        elif method == "resources/read":
            return await self._handle_resource_read(req_id, params)
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}

    async def _handle_initialize(self, req_id: int, params: Dict) -> Dict:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "serverInfo": {
                    "name": "owl-agent",
                    "version": "4.2.0"
                }
            }
        }

    async def _handle_tools_list(self, req_id: int) -> Dict:
        tools = []
        for name, tool in self.tools.items():
            tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            })
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

    async def _handle_tool_call(self, req_id: int, params: Dict) -> Dict:
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": f"Tool not found: {tool_name}"}}

        try:
            result = await self.tools[tool_name]["handler"](arguments)
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result)}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}

    async def _handle_resources_list(self, req_id: int) -> Dict:
        resources = []
        for uri, resource in self.resources.items():
            resources.append({
                "uri": uri,
                "name": resource["name"],
                "description": resource["description"],
                "mimeType": "application/json"
            })
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": resources}}

    async def _handle_resource_read(self, req_id: int, params: Dict) -> Dict:
        uri = params.get("uri", "")
        if uri not in self.resources:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": f"Resource not found: {uri}"}}

        try:
            content = await self.resources[uri]["handler"]()
            return {"jsonrpc": "2.0", "id": req_id, "result": {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(content)}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}

# Initialize server
server = MCPServer()

# Import OWL-AGENT
sys.path.insert(0, "/home/ubuntu/.owl-agent")
from proxy_defense import ResilientClient

# Client instance
_client = None

async def get_client():
    global _client
    if _client is None:
        _client = ResilientClient(use_curl_cffi=True)
        await _client.__aenter__()
    return _client

# Register tools
@server.tool("owl_fetch", "Fetch a URL via the resilient client with proxy rotation and quality scoring")
async def handle_fetch(args: Dict) -> Any:
    url = args.get("url")
    if not url:
        return {"error": "Missing url parameter"}

    client = await get_client()
    resp = await client.request("GET", url)
    return {
        "status": resp.status,
        "content_length": len(resp.content),
        "content": resp.content.decode('utf-8', errors='replace')[:5000],
        "headers": resp.headers
    }

@server.tool("owl_stats", "Get proxy pool statistics including healthy proxy count and quality scores")
async def handle_stats(args: Dict) -> Any:
    client = await get_client()
    return await client.get_stats()

@server.tool("owl_fetch_browser", "Fetch a URL using headless browser for JavaScript-rendered content")
async def handle_fetch_browser(args: Dict) -> Any:
    url = args.get("url")
    if not url:
        return {"error": "Missing url parameter"}

    client = await get_client()
    resp = await client.request("GET", url, browser=True)
    return {
        "status": resp.status,
        "content_length": len(resp.content),
        "content": resp.content.decode('utf-8', errors='replace')[:5000]
    }

# Register resources
@server.resource("owl://proxy-pool", "Proxy Pool", "Current proxy pool status and health")
async def get_proxy_pool():
    client = await get_client()
    stats = await client.get_stats()
    return {
        "total": stats["proxies_total"],
        "healthy": stats["proxies_healthy"],
        "scores": stats["scores"]
    }

@server.resource("owl://config", "Configuration", "OWL-AGENT configuration")
async def get_config():
    return {
        "version": "4.2.0",
        "curl_cffi": True,
        "redis": False,
        "countries": ["US", "GB", "DE", "FR", "CA"],
        "ttl": 300,
        "rate": 1.0
    }

# Main
async def main():
    """Run MCP server via stdio"""
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin.buffer)

    while True:
        line = await reader.readline()
        if not line:
            break

        try:
            request = json.loads(line.decode().strip())
            response = await server.handle_request(request)
            print(json.dumps(response), flush=True)
        except Exception as e:
            print(json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32603, "message": str(e)}}), flush=True)

if __name__ == "__main__":
    asyncio.run(main())
