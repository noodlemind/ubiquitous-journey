"""Minimal schemas for SQL to Dashboard - Version 2.0"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request to generate SQL query and dashboard from DDL."""
    ddl: str = Field(..., description="DDL schema definition")
    intents: List[str] = Field(..., description="What insights the user wants")
    database: str = Field(default="sqlite", description="Target database type")
    

class GenerateResponse(BaseModel):
    """Response containing generated SQL and dashboard HTML."""
    query: str = Field(..., description="Master SQL query joining all tables")
    dashboard_html: str = Field(..., description="Complete dashboard HTML with D3.js")
    execution_script: str = Field(..., description="Script to execute the query")
    instructions: str = Field(..., description="Simple instructions for the user")
    

class DashboardConfig(BaseModel):
    """Optional configuration for dashboard customization."""
    title: str = Field(default="Data Dashboard", description="Dashboard title")
    theme: str = Field(default="light", description="Dashboard theme")
    auto_refresh: bool = Field(default=True, description="Auto-refresh when data.json changes")