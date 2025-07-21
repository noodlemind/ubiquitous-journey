from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal


class MCPRequest(BaseModel):
    """Model Context Protocol Request schema"""
    task: Literal["nl_query"]
    query: str
    verbose: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """Model Context Protocol Response schema"""
    status: Literal["success", "error"]
    intent: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    natural: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None