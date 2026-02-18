"""Tests for MCP JSON-RPC client."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from curator.mcp import MCPClient, _load_server_config
from curator.errors import MCPError


class TestLoadServerConfig:
    def test_loads_local_config(self, tmp_path):
        mcp_json = {
            "mcpServers": {
                "database-of-things-local": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["mcp-server/build/index.js"],
                    "env": {"SUPABASE_URL": "http://localhost:54321"},
                },
                "database-of-things-prod": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["mcp-server/build/index.js"],
                    "env": {"SUPABASE_URL": "https://prod.supabase.co"},
                },
            }
        }
        mcp_path = tmp_path / ".mcp.json"
        mcp_path.write_text(json.dumps(mcp_json))

        config = _load_server_config("local", project_root=tmp_path)
        assert config["command"] == "node"
        assert config["env"]["SUPABASE_URL"] == "http://localhost:54321"

    def test_loads_prod_config(self, tmp_path):
        mcp_json = {
            "mcpServers": {
                "database-of-things-local": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["mcp-server/build/index.js"],
                    "env": {"SUPABASE_URL": "http://localhost:54321"},
                },
                "database-of-things-prod": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["mcp-server/build/index.js"],
                    "env": {"SUPABASE_URL": "https://prod.supabase.co"},
                },
            }
        }
        mcp_path = tmp_path / ".mcp.json"
        mcp_path.write_text(json.dumps(mcp_json))

        config = _load_server_config("prod", project_root=tmp_path)
        assert config["env"]["SUPABASE_URL"] == "https://prod.supabase.co"

    def test_raises_on_missing_mcp_json(self, tmp_path):
        with pytest.raises(MCPError, match=".mcp.json"):
            _load_server_config("local", project_root=tmp_path)

    def test_raises_on_unknown_env(self, tmp_path):
        mcp_json = {"mcpServers": {"database-of-things-local": {"type": "stdio", "command": "node", "args": [], "env": {}}}}
        (tmp_path / ".mcp.json").write_text(json.dumps(mcp_json))
        with pytest.raises(MCPError, match="staging"):
            _load_server_config("staging", project_root=tmp_path)


class TestMCPClientProtocol:
    def test_builds_jsonrpc_request(self):
        """Verify the JSON-RPC request format without spawning a server."""
        client = MCPClient.__new__(MCPClient)
        client._request_id = 0
        request = client._build_request("tools/call", {
            "name": "get_curator_stats",
            "arguments": {"name": "Pokemon TCG"},
        })
        assert request["jsonrpc"] == "2.0"
        assert request["method"] == "tools/call"
        assert request["id"] == 1
        assert request["params"]["name"] == "get_curator_stats"

    def test_parses_success_response(self):
        """Verify parsing of a successful MCP tool response."""
        client = MCPClient.__new__(MCPClient)
        raw = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [{"type": "text", "text": '{"success": true, "total_items": 42}'}],
            },
        }
        result = client._parse_tool_response(raw)
        assert result["success"] is True
        assert result["total_items"] == 42

    def test_parses_plain_text_response(self):
        """Some MCP tools return markdown, not JSON."""
        client = MCPClient.__new__(MCPClient)
        raw = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [{"type": "text", "text": "Found 5 results"}],
            },
        }
        result = client._parse_tool_response(raw)
        assert result == "Found 5 results"

    def test_raises_on_jsonrpc_error(self):
        """JSON-RPC errors should raise MCPError."""
        client = MCPClient.__new__(MCPClient)
        raw = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32601, "message": "Method not found"},
        }
        with pytest.raises(MCPError, match="Method not found"):
            client._parse_tool_response(raw)
