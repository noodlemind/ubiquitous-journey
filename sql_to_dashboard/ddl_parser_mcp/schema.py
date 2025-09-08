"""Schema definitions for DDL Parser MCP."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class InputFormat(str, Enum):
    """Supported input formats."""
    DDL = "ddl"
    MERMAID = "mermaid"


class RelationType(str, Enum):
    """Database relationship types."""
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_MANY = "N:M"


class ColumnInfo(BaseModel):
    """Information about a database column."""
    name: str
    data_type: str
    is_primary_key: bool = False
    is_foreign_key: bool = False
    is_nullable: bool = True
    default_value: Optional[str] = None
    references: Optional[Dict[str, str]] = None  # {"table": "...", "column": "..."}


class TableInfo(BaseModel):
    """Information about a database table."""
    name: str
    columns: List[ColumnInfo]
    primary_keys: List[str] = Field(default_factory=list)
    foreign_keys: List[Dict[str, Any]] = Field(default_factory=list)
    indexes: List[Dict[str, Any]] = Field(default_factory=list)


class Relationship(BaseModel):
    """Represents a relationship between tables."""
    from_table: str
    to_table: str
    from_column: str
    to_column: str
    type: RelationType
    label: Optional[str] = None


class DatabaseSchema(BaseModel):
    """Complete database schema representation."""
    tables: List[TableInfo]
    relationships: List[Relationship]
    database_type: Optional[str] = "generic"  # postgres, mysql, sqlite, etc.


class QuerySuggestion(BaseModel):
    """Suggested SQL query for visualization."""
    query: str
    description: str
    visualization_type: str  # bar, line, pie, scatter, heatmap, table
    expected_columns: List[str]
    parameters: Optional[List[str]] = None  # For parameterized queries


class DDLParserRequest(BaseModel):
    """Request schema for DDL Parser MCP."""
    task: Literal["parse_schema", "suggest_queries"]
    input: str = Field(..., description="DDL or Mermaid ER diagram text")
    format: InputFormat
    database_type: Optional[str] = "sqlite"  # Target database for SQL generation
    visualization_intents: Optional[List[str]] = None  # What user wants to visualize
    metadata: Optional[Dict[str, Any]] = None


class DDLParserResponse(BaseModel):
    """Response schema for DDL Parser MCP."""
    status: Literal["success", "error"]
    schema: Optional[DatabaseSchema] = None
    suggested_queries: Optional[List[QuerySuggestion]] = None
    sql_statements: Optional[List[str]] = None  # Ready-to-execute SQL
    instructions: Optional[str] = None  # Instructions for user
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
