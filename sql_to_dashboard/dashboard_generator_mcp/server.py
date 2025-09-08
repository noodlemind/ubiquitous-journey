"""Dashboard Generator MCP Server - Creates D3.js dashboards from data."""

import json
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path
import base64

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dashboard_generator_mcp.schema import (
    DashboardGeneratorRequest,
    DashboardGeneratorResponse,
    DashboardAssets,
    DashboardConfig,
    ChartConfig,
    ChartType,
    ThemeType
)
from dashboard_generator_mcp.generators.dashboard_template import DashboardTemplate
from shared.validators import validate_json_data, validate_visualization_spec
from shared.errors import ValidationError, GenerationError


class DashboardGeneratorMCPServer:
    """MCP Server for Dashboard Generation."""
    
    def __init__(self):
        """Initialize the Dashboard Generator MCP Server."""
        self.max_data_rows = 1000000  # 1M rows max
        self.template_generator = DashboardTemplate()
        
    def handle_request(self, request: DashboardGeneratorRequest) -> DashboardGeneratorResponse:
        """
        Handle dashboard generation request.
        
        Args:
            request: DashboardGeneratorRequest object
            
        Returns:
            DashboardGeneratorResponse object
        """
        try:
            # Validate data
            validate_json_data(request.data, self.max_data_rows)
            
            if request.task == "generate_dashboard":
                return self._generate_dashboard(request)
            elif request.task == "preview_chart":
                return self._preview_chart(request)
            else:
                return DashboardGeneratorResponse(
                    status="error",
                    error=f"Unknown task: {request.task}"
                )
                
        except ValidationError as e:
            return DashboardGeneratorResponse(
                status="error",
                error=f"Validation error: {e.message}",
                metadata={"details": e.details}
            )
        except GenerationError as e:
            return DashboardGeneratorResponse(
                status="error",
                error=f"Generation error: {e.message}",
                metadata={"details": e.details}
            )
        except Exception as e:
            return DashboardGeneratorResponse(
                status="error",
                error=f"Server error: {str(e)}"
            )
    
    def _generate_dashboard(self, request: DashboardGeneratorRequest) -> DashboardGeneratorResponse:
        """Generate complete dashboard from data."""
        
        # Create config if not provided
        if request.config:
            config = request.config
        else:
            # Auto-detect configuration from data
            config = self._auto_detect_config(request.data, request.charts)
        
        # Prepare data for each chart
        chart_data = self._prepare_chart_data(config, request.data)
        
        # Generate HTML dashboard
        html_content = self.template_generator.generate_html(config, chart_data)
        
        # Create dashboard assets
        assets = DashboardAssets(
            html=html_content,
            dependencies=["d3.v7.min.js"]
        )
        
        # Create instructions
        instructions = self._create_instructions(config, len(chart_data))
        
        return DashboardGeneratorResponse(
            status="success",
            dashboard=assets,
            instructions=instructions,
            metadata={
                "chart_count": len(config.charts),
                "theme": config.theme.value,
                "responsive": config.responsive
            }
        )
    
    def _preview_chart(self, request: DashboardGeneratorRequest) -> DashboardGeneratorResponse:
        """Generate a preview of a single chart."""
        
        if not request.charts or len(request.charts) == 0:
            return DashboardGeneratorResponse(
                status="error",
                error="No chart configuration provided for preview"
            )
        
        # Use first chart for preview
        chart_config = request.charts[0]
        
        # Create minimal dashboard config
        config = DashboardConfig(
            title="Chart Preview",
            charts=[chart_config],
            theme=ThemeType.LIGHT
        )
        
        # Prepare data
        chart_data = self._prepare_chart_data(config, request.data)
        
        # Generate HTML
        html_content = self.template_generator.generate_html(config, chart_data)
        
        assets = DashboardAssets(html=html_content)
        
        return DashboardGeneratorResponse(
            status="success",
            dashboard=assets,
            instructions="Preview generated successfully. Save the HTML to view.",
            metadata={"preview": True}
        )
    
    def _auto_detect_config(self, data: Any, charts: Optional[List[ChartConfig]] = None) -> DashboardConfig:
        """Auto-detect dashboard configuration from data structure."""
        
        # If charts are provided, use them
        if charts:
            return DashboardConfig(
                title="Data Dashboard",
                charts=charts
            )
        
        # Otherwise, analyze data and suggest charts
        suggested_charts = []
        
        # Normalize data to list format
        if isinstance(data, dict):
            # Multiple datasets
            for key, dataset in data.items():
                if isinstance(dataset, list) and dataset:
                    chart = self._suggest_chart_for_data(dataset, key)
                    if chart:
                        suggested_charts.append(chart)
        elif isinstance(data, list) and data:
            # Single dataset
            chart = self._suggest_chart_for_data(data, "Data")
            if chart:
                suggested_charts.append(chart)
        
        if not suggested_charts:
            # Default to table view
            suggested_charts.append(ChartConfig(
                type=ChartType.TABLE,
                title="Data Table",
                data=data
            ))
        
        return DashboardConfig(
            title="Auto-Generated Dashboard",
            charts=suggested_charts
        )
    
    def _suggest_chart_for_data(self, data: List[Dict], title: str) -> Optional[ChartConfig]:
        """Suggest appropriate chart type based on data structure."""
        
        if not data or not isinstance(data[0], dict):
            return None
        
        columns = list(data[0].keys())
        
        # Analyze column types
        has_numeric = False
        has_categorical = False
        has_date = False
        
        for col in columns:
            sample_value = data[0].get(col)
            if sample_value is not None:
                if isinstance(sample_value, (int, float)):
                    has_numeric = True
                elif isinstance(sample_value, str):
                    # Check if it looks like a date
                    if any(pattern in sample_value for pattern in ['-', '/', '2020', '2021', '2022', '2023', '2024']):
                        has_date = True
                    else:
                        has_categorical = True
        
        # Suggest chart based on data types
        if has_date and has_numeric:
            # Time series - use line chart
            date_col = next((col for col in columns if self._is_date_column(data, col)), None)
            numeric_col = next((col for col in columns if self._is_numeric_column(data, col)), None)
            
            return ChartConfig(
                type=ChartType.LINE,
                title=f"{title} - Time Series",
                data=data,
                x_column=date_col,
                y_column=numeric_col
            )
        elif has_categorical and has_numeric:
            # Category vs value - use bar chart
            cat_col = next((col for col in columns if self._is_categorical_column(data, col)), None)
            num_col = next((col for col in columns if self._is_numeric_column(data, col)), None)
            
            # Check if pie chart is more appropriate (few categories)
            unique_categories = len(set(row.get(cat_col) for row in data[:100]))
            
            if unique_categories <= 8:
                return ChartConfig(
                    type=ChartType.PIE,
                    title=f"{title} - Distribution",
                    data=data,
                    x_column=cat_col,
                    y_column=num_col
                )
            else:
                return ChartConfig(
                    type=ChartType.BAR,
                    title=f"{title} - by Category",
                    data=data,
                    x_column=cat_col,
                    y_column=num_col
                )
        elif has_numeric and len(columns) >= 2:
            # Multiple numeric columns - could be scatter
            numeric_cols = [col for col in columns if self._is_numeric_column(data, col)]
            if len(numeric_cols) >= 2:
                return ChartConfig(
                    type=ChartType.SCATTER,
                    title=f"{title} - Correlation",
                    data=data,
                    x_column=numeric_cols[0],
                    y_column=numeric_cols[1]
                )
        
        # Default to table
        return ChartConfig(
            type=ChartType.TABLE,
            title=f"{title} - Table View",
            data=data
        )
    
    def _is_numeric_column(self, data: List[Dict], column: str) -> bool:
        """Check if column contains numeric data."""
        try:
            for row in data[:10]:  # Check first 10 rows
                val = row.get(column)
                if val is not None and not isinstance(val, (int, float)):
                    float(val)  # Try to convert
            return True
        except:
            return False
    
    def _is_categorical_column(self, data: List[Dict], column: str) -> bool:
        """Check if column contains categorical data."""
        for row in data[:10]:
            val = row.get(column)
            if val is not None and isinstance(val, str):
                return True
        return False
    
    def _is_date_column(self, data: List[Dict], column: str) -> bool:
        """Check if column contains date data."""
        for row in data[:10]:
            val = row.get(column)
            if val is not None and isinstance(val, str):
                if any(pattern in str(val) for pattern in ['-', '/', '2020', '2021', '2022', '2023', '2024']):
                    return True
        return False
    
    def _prepare_chart_data(self, config: DashboardConfig, raw_data: Any) -> List[Any]:
        """Prepare data for each chart in the configuration."""
        chart_data = []
        
        for chart in config.charts:
            if chart.data is not None:
                # Use chart-specific data if provided
                chart_data.append(chart.data)
            elif isinstance(raw_data, dict):
                # Try to find matching dataset by title
                matching_key = None
                for key in raw_data.keys():
                    if key.lower() in chart.title.lower() or chart.title.lower() in key.lower():
                        matching_key = key
                        break
                
                if matching_key:
                    chart_data.append(raw_data[matching_key])
                else:
                    # Use first available dataset
                    chart_data.append(list(raw_data.values())[0] if raw_data else [])
            else:
                # Use the raw data for all charts
                chart_data.append(raw_data)
        
        return chart_data
    
    def _create_instructions(self, config: DashboardConfig, chart_count: int) -> str:
        """Create user instructions for the generated dashboard."""
        return f"""
📊 Dashboard Generated Successfully!

Created {chart_count} visualization(s) with theme: {config.theme.value}

📝 Next Steps:
1. Save the HTML content to a file (e.g., dashboard.html)
2. Open the file in a web browser
3. Interact with the visualizations (hover for tooltips, etc.)

✨ Features:
- Responsive layout: {'Yes' if config.responsive else 'No'}
- Interactive tooltips on hover
- Clean, modern design
- Standalone file (no server required)

💡 Tips:
- The dashboard works offline once saved
- You can edit the HTML/CSS for customization
- Print or save as PDF from your browser
- Share the HTML file with others

Enjoy your dashboard!
"""
    
    def process_json_request(self, json_str: str) -> str:
        """
        Process a JSON string request and return JSON response.
        
        Args:
            json_str: JSON string containing request
            
        Returns:
            JSON string containing response
        """
        try:
            # Parse request
            request_data = json.loads(json_str)
            request = DashboardGeneratorRequest(**request_data)
            
            # Handle request
            response = self.handle_request(request)
            
            # Return JSON response
            return response.model_dump_json(indent=2)
            
        except json.JSONDecodeError as e:
            error_response = DashboardGeneratorResponse(
                status="error",
                error=f"Invalid JSON: {str(e)}"
            )
            return error_response.model_dump_json(indent=2)
        except Exception as e:
            error_response = DashboardGeneratorResponse(
                status="error",
                error=f"Request processing failed: {str(e)}"
            )
            return error_response.model_dump_json(indent=2)


# Example usage
if __name__ == "__main__":
    server = DashboardGeneratorMCPServer()
    
    # Example data
    example_data = [
        {"category": "Sales", "value": 45000, "month": "2024-01"},
        {"category": "Marketing", "value": 32000, "month": "2024-01"},
        {"category": "Development", "value": 67000, "month": "2024-01"},
        {"category": "Sales", "value": 48000, "month": "2024-02"},
        {"category": "Marketing", "value": 35000, "month": "2024-02"},
        {"category": "Development", "value": 71000, "month": "2024-02"},
    ]
    
    # Create request
    request = DashboardGeneratorRequest(
        task="generate_dashboard",
        data=example_data,
        auto_detect=True
    )
    
    # Generate dashboard
    response = server.handle_request(request)
    
    if response.status == "success":
        # Save HTML to file
        with open("example_dashboard.html", "w") as f:
            f.write(response.dashboard.html)
        print("Dashboard saved to example_dashboard.html")
        print(response.instructions)
