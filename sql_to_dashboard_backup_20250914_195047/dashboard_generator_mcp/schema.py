"""Schema definitions for Dashboard Generator MCP."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal, Union
from enum import Enum


class ChartType(str, Enum):
    """Supported chart types."""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    TABLE = "table"


class ThemeType(str, Enum):
    """Dashboard theme options."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class DataPoint(BaseModel):
    """Generic data point for charts."""
    x: Union[str, float, int]
    y: Union[float, int]
    label: Optional[str] = None
    category: Optional[str] = None


class ChartConfig(BaseModel):
    """Configuration for a single chart."""
    type: ChartType
    title: str
    data: Union[List[Dict[str, Any]], Dict[str, Any]]
    x_column: Optional[str] = None  # Column name for X axis
    y_column: Optional[str] = None  # Column name for Y axis
    group_by: Optional[str] = None  # Column for grouping/categorization
    width: Optional[int] = 600
    height: Optional[int] = 400
    color_scheme: Optional[List[str]] = None


class DashboardConfig(BaseModel):
    """Configuration for the entire dashboard."""
    title: str = "Data Dashboard"
    theme: ThemeType = ThemeType.LIGHT
    responsive: bool = True
    charts: List[ChartConfig]
    layout: Literal["grid", "vertical", "horizontal"] = "grid"
    export_formats: Optional[List[str]] = Field(default_factory=lambda: ["html"])


class DashboardGeneratorRequest(BaseModel):
    """Request schema for Dashboard Generator MCP."""
    task: Literal["generate_dashboard", "preview_chart"]
    data: Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]  # Raw data or multiple datasets
    config: Optional[DashboardConfig] = None
    charts: Optional[List[ChartConfig]] = None  # Individual chart configs
    auto_detect: bool = False  # Auto-detect best visualizations from data
    metadata: Optional[Dict[str, Any]] = None


class DashboardAssets(BaseModel):
    """Generated dashboard assets."""
    html: str  # Main HTML content
    css: Optional[str] = None  # Custom CSS
    javascript: Optional[str] = None  # Custom JavaScript
    dependencies: List[str] = Field(default_factory=lambda: ["d3.v7.min.js"])


class DashboardGeneratorResponse(BaseModel):
    """Response schema for Dashboard Generator MCP."""
    status: Literal["success", "error"]
    dashboard: Optional[DashboardAssets] = None
    preview_url: Optional[str] = None  # For preview mode
    download_url: Optional[str] = None  # For download
    instructions: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
