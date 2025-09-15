"""Custom error classes for SQL-to-Dashboard MCP tools."""

from typing import Optional, Dict, Any


class MCPError(Exception):
    """Base exception for all MCP-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(MCPError):
    """Raised when input validation fails."""
    pass


class ParsingError(MCPError):
    """Raised when DDL/Mermaid parsing fails."""
    
    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None, **kwargs):
        details = kwargs.copy()
        if line is not None:
            details['line'] = line
        if column is not None:
            details['column'] = column
        super().__init__(message, details)


class ExecutionError(MCPError):
    """Raised when query execution fails."""
    
    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        details = kwargs.copy()
        if query:
            # Truncate long queries for error messages
            details['query'] = query[:500] + '...' if len(query) > 500 else query
        super().__init__(message, details)


class GenerationError(MCPError):
    """Raised when dashboard generation fails."""
    pass


class ConnectionError(MCPError):
    """Raised when database connection fails."""
    pass


class TimeoutError(ExecutionError):
    """Raised when query execution times out."""
    pass


class SecurityError(MCPError):
    """Raised when security constraints are violated."""
    pass
