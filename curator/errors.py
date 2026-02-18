"""Curator-specific exceptions."""


class CuratorError(Exception):
    """Base exception for curator operations."""


class ConfigError(CuratorError):
    """Curator configuration missing or invalid."""


class FetchError(CuratorError):
    """fetch_data.py failed."""

    def __init__(self, message: str, exit_code: int | None = None, stderr: str = ""):
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr


class ValidationError(CuratorError):
    """fetched_data.json schema validation failed."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


class ImportError_(CuratorError):
    """MCP bulk import failed. Named ImportError_ to avoid shadowing builtin."""

    def __init__(self, message: str, mcp_response: dict | None = None):
        super().__init__(message)
        self.mcp_response = mcp_response


class MCPError(CuratorError):
    """MCP server communication failed."""
