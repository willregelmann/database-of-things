"""Lightweight MCP JSON-RPC client over stdio."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from curator.errors import MCPError

# Project root (parent of curator/ package)
DEFAULT_PROJECT_ROOT = Path(__file__).parent.parent

ENV_TO_SERVER = {
    "local": "database-of-things-local",
    "prod": "database-of-things-prod",
}


def _load_server_config(
    env: str, project_root: Path | None = None
) -> dict:
    """Load MCP server config from .mcp.json for the given environment.

    Args:
        env: "local" or "prod".
        project_root: Override project root path.

    Returns:
        Server config dict with command, args, env keys.

    Raises:
        MCPError: If .mcp.json missing or env not found.
    """
    root = project_root or DEFAULT_PROJECT_ROOT
    mcp_path = root / ".mcp.json"

    if not mcp_path.exists():
        raise MCPError(f".mcp.json not found at {mcp_path}")

    mcp_config = json.loads(mcp_path.read_text())
    servers = mcp_config.get("mcpServers", {})

    server_name = ENV_TO_SERVER.get(env)
    if not server_name or server_name not in servers:
        raise MCPError(
            f"No MCP server configured for env '{env}'. "
            f"Available: {list(servers.keys())}"
        )

    return servers[server_name]


class MCPClient:
    """Spawn MCP server as subprocess, communicate via JSON-RPC over stdio."""

    def __init__(self, env: str = "local", project_root: Path | None = None):
        self._root = project_root or DEFAULT_PROJECT_ROOT
        self._request_id = 0
        self._server_config = _load_server_config(env, self._root)
        self._process: subprocess.Popen | None = None

    def __enter__(self):
        self._start()
        return self

    def __exit__(self, *exc):
        self.close()

    def _start(self):
        """Spawn the MCP server and perform initialize handshake."""
        config = self._server_config
        cmd = [config["command"]] + config.get("args", [])

        # Resolve relative paths against project root
        resolved_args = []
        for arg in cmd[1:]:
            p = self._root / arg
            resolved_args.append(str(p) if p.exists() else arg)
        cmd = [cmd[0]] + resolved_args

        env = {**dict(__import__("os").environ), **config.get("env", {})}

        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(self._root),
        )

        # MCP initialize handshake
        self._send_raw(
            self._build_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "curator-cli", "version": "0.1.0"},
            })
        )
        self._read_response()  # Read initialize result (we don't need it)

        # Send initialized notification (no id, no response expected)
        notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self._send_raw(notification)

    def call_tool(self, name: str, arguments: dict | None = None) -> dict | str:
        """Call an MCP tool and return the parsed response.

        Args:
            name: Tool name (e.g., "bulk_import_curator_batch").
            arguments: Tool arguments dict.

        Returns:
            Parsed JSON dict if response is JSON, raw text otherwise.

        Raises:
            MCPError: If server not running, JSON-RPC error, or communication failure.
        """
        if not self._process:
            raise MCPError("MCP server not started. Use as context manager.")

        request = self._build_request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })
        self._send_raw(request)
        response = self._read_response()
        return self._parse_tool_response(response)

    def close(self):
        """Terminate the MCP server subprocess."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

    def _build_request(self, method: str, params: dict) -> dict:
        """Build a JSON-RPC 2.0 request."""
        self._request_id += 1
        return {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

    def _send_raw(self, message: dict):
        """Send a JSON-RPC message to the server's stdin."""
        if not self._process or not self._process.stdin:
            raise MCPError("MCP server stdin not available")
        data = json.dumps(message)
        # MCP uses Content-Length header framing
        frame = f"Content-Length: {len(data)}\r\n\r\n{data}"
        self._process.stdin.write(frame.encode())
        self._process.stdin.flush()

    def _read_response(self) -> dict:
        """Read a JSON-RPC response from the server's stdout."""
        if not self._process or not self._process.stdout:
            raise MCPError("MCP server stdout not available")

        # Read Content-Length header
        headers = {}
        while True:
            line = self._process.stdout.readline().decode()
            if line == "\r\n" or line == "\n" or line == "":
                break
            if ":" in line:
                key, _, value = line.partition(":")
                headers[key.strip().lower()] = value.strip()

        content_length = int(headers.get("content-length", 0))
        if content_length == 0:
            raise MCPError("Empty response from MCP server")

        data = self._process.stdout.read(content_length).decode()
        return json.loads(data)

    def _parse_tool_response(self, raw: dict) -> dict | str:
        """Parse a JSON-RPC response into the tool's result.

        Args:
            raw: Full JSON-RPC response dict.

        Returns:
            Parsed JSON dict if content is JSON, raw text otherwise.

        Raises:
            MCPError: If response contains a JSON-RPC error.
        """
        if "error" in raw:
            err = raw["error"]
            raise MCPError(f"MCP error {err.get('code')}: {err.get('message')}")

        result = raw.get("result", {})
        content = result.get("content", [])

        if not content:
            return {}

        text = content[0].get("text", "")

        # Try to parse as JSON, fall back to raw text
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text
