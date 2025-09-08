"""Dashboard HTML template generator."""

from typing import List, Dict, Any, Optional
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))

from dashboard_generator_mcp.schema import ChartConfig, DashboardConfig, ThemeType
from shared.validators import sanitize_html


class DashboardTemplate:
    """Generate complete HTML dashboard with D3.js visualizations."""
    
    @staticmethod
    def generate_html(config: DashboardConfig, chart_data: List[Dict[str, Any]]) -> str:
        """
        Generate complete standalone HTML dashboard.
        
        Args:
            config: Dashboard configuration
            chart_data: List of data for each chart
            
        Returns:
            Complete HTML string
        """
        theme_css = DashboardTemplate._get_theme_css(config.theme)
        charts_html = ""
        charts_js = ""
        
        for i, (chart_config, data) in enumerate(zip(config.charts, chart_data)):
            chart_id = f"chart-{i}"
            charts_html += f'<div id="{chart_id}" class="chart-container"></div>\n'
            charts_js += DashboardTemplate._generate_chart_js(chart_id, chart_config, data)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{sanitize_html(config.title)}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        {theme_css}
        {DashboardTemplate._get_base_css()}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <h1 class="dashboard-title">{sanitize_html(config.title)}</h1>
        <div class="charts-grid {'responsive' if config.responsive else ''}">
            {charts_html}
        </div>
    </div>
    
    <script>
        // Chart rendering code
        {charts_js}
        
        // Initialize all charts
        window.addEventListener('DOMContentLoaded', function() {{
            console.log('Dashboard initialized with {len(config.charts)} charts');
        }});
    </script>
</body>
</html>"""
        
        return html
    
    @staticmethod
    def _get_base_css() -> str:
        """Get base CSS styles for dashboard."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            padding: 20px;
        }
        
        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .dashboard-title {
            margin-bottom: 30px;
            font-size: 2em;
            font-weight: 600;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
        }
        
        .charts-grid.responsive {
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        }
        
        .chart-container {
            background: var(--chart-bg);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-height: 400px;
        }
        
        .chart-title {
            font-size: 1.2em;
            font-weight: 500;
            margin-bottom: 15px;
            color: var(--text-primary);
        }
        
        .axis {
            font-size: 12px;
        }
        
        .axis-label {
            font-size: 14px;
            font-weight: 500;
        }
        
        .bar {
            transition: opacity 0.3s;
        }
        
        .bar:hover {
            opacity: 0.8;
        }
        
        .line {
            fill: none;
            stroke-width: 2;
        }
        
        .dot {
            transition: r 0.3s;
        }
        
        .dot:hover {
            r: 6;
        }
        
        .tooltip {
            position: absolute;
            padding: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 4px;
            pointer-events: none;
            font-size: 12px;
            z-index: 1000;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        th {
            background: var(--table-header-bg);
            font-weight: 600;
        }
        
        tr:hover {
            background: var(--table-hover-bg);
        }
        """
    
    @staticmethod
    def _get_theme_css(theme: ThemeType) -> str:
        """Get theme-specific CSS variables."""
        if theme == ThemeType.DARK:
            return """
            :root {
                --bg-primary: #1a1a1a;
                --bg-secondary: #2d2d2d;
                --text-primary: #ffffff;
                --text-secondary: #b0b0b0;
                --chart-bg: #2d2d2d;
                --border-color: #404040;
                --table-header-bg: #333333;
                --table-hover-bg: #3a3a3a;
                --color-1: #4fc3f7;
                --color-2: #81c784;
                --color-3: #ffb74d;
                --color-4: #f06292;
                --color-5: #ba68c8;
            }
            
            body {
                background: var(--bg-primary);
                color: var(--text-primary);
            }
            """
        else:  # Light theme
            return """
            :root {
                --bg-primary: #ffffff;
                --bg-secondary: #f5f5f5;
                --text-primary: #333333;
                --text-secondary: #666666;
                --chart-bg: #ffffff;
                --border-color: #e0e0e0;
                --table-header-bg: #f5f5f5;
                --table-hover-bg: #fafafa;
                --color-1: #2196f3;
                --color-2: #4caf50;
                --color-3: #ff9800;
                --color-4: #e91e63;
                --color-5: #9c27b0;
            }
            
            body {
                background: var(--bg-secondary);
                color: var(--text-primary);
            }
            """
    
    @staticmethod
    def _generate_chart_js(chart_id: str, config: ChartConfig, data: Any) -> str:
        """Generate JavaScript code for a specific chart."""
        
        # Convert data to JSON string for embedding
        data_json = json.dumps(data, indent=2)
        
        if config.type.value == "bar":
            return DashboardTemplate._generate_bar_chart_js(chart_id, config, data_json)
        elif config.type.value == "line":
            return DashboardTemplate._generate_line_chart_js(chart_id, config, data_json)
        elif config.type.value == "pie":
            return DashboardTemplate._generate_pie_chart_js(chart_id, config, data_json)
        elif config.type.value == "table":
            return DashboardTemplate._generate_table_js(chart_id, config, data_json)
        else:
            return f"// Chart type '{config.type}' not yet implemented\\n"
    
    @staticmethod
    def _generate_bar_chart_js(chart_id: str, config: ChartConfig, data_json: str) -> str:
        """Generate D3.js bar chart code."""
        return f"""
        // Bar chart for {chart_id}
        (function() {{
            const data = {data_json};
            const containerId = "{chart_id}";
            const title = "{sanitize_html(config.title)}";
            
            // Get container dimensions
            const container = d3.select("#" + containerId);
            const width = {config.width or 600};
            const height = {config.height or 400};
            const margin = {{top: 40, right: 30, bottom: 60, left: 60}};
            const innerWidth = width - margin.left - margin.right;
            const innerHeight = height - margin.top - margin.bottom;
            
            // Clear any existing content
            container.html("");
            
            // Add title
            container.append("h3")
                .attr("class", "chart-title")
                .text(title);
            
            // Create SVG
            const svg = container.append("svg")
                .attr("width", width)
                .attr("height", height)
                .attr("viewBox", `0 0 ${{width}} ${{height}}`);
            
            const g = svg.append("g")
                .attr("transform", `translate(${{margin.left}},${{margin.top}})`);
            
            // Determine X and Y columns
            const xColumn = "{config.x_column or 'category' or 'x'}";
            const yColumn = "{config.y_column or 'value' or 'count' or 'y'}";
            
            // Ensure data is in the right format
            const chartData = Array.isArray(data) ? data : [data];
            
            // Create scales
            const xScale = d3.scaleBand()
                .domain(chartData.map(d => d[xColumn]))
                .range([0, innerWidth])
                .padding(0.1);
            
            const yScale = d3.scaleLinear()
                .domain([0, d3.max(chartData, d => +d[yColumn])])
                .nice()
                .range([innerHeight, 0]);
            
            // Add axes
            g.append("g")
                .attr("class", "axis x-axis")
                .attr("transform", `translate(0,${{innerHeight}})`)
                .call(d3.axisBottom(xScale))
                .selectAll("text")
                .attr("transform", "rotate(-45)")
                .style("text-anchor", "end");
            
            g.append("g")
                .attr("class", "axis y-axis")
                .call(d3.axisLeft(yScale));
            
            // Add bars
            const bars = g.selectAll(".bar")
                .data(chartData)
                .enter().append("rect")
                .attr("class", "bar")
                .attr("x", d => xScale(d[xColumn]))
                .attr("y", d => yScale(+d[yColumn]))
                .attr("width", xScale.bandwidth())
                .attr("height", d => innerHeight - yScale(+d[yColumn]))
                .attr("fill", "var(--color-1)");
            
            // Add tooltip
            const tooltip = d3.select("body").append("div")
                .attr("class", "tooltip")
                .style("opacity", 0);
            
            bars.on("mouseover", function(event, d) {{
                tooltip.transition().duration(200).style("opacity", .9);
                tooltip.html(`${{d[xColumn]}}: ${{d[yColumn]}}`)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            }})
            .on("mouseout", function(d) {{
                tooltip.transition().duration(500).style("opacity", 0);
            }});
        }})();
        """
    
    @staticmethod
    def _generate_line_chart_js(chart_id: str, config: ChartConfig, data_json: str) -> str:
        """Generate D3.js line chart code."""
        return f"""
        // Line chart for {chart_id}
        (function() {{
            const data = {data_json};
            const containerId = "{chart_id}";
            const title = "{sanitize_html(config.title)}";
            
            // Similar setup as bar chart
            const container = d3.select("#" + containerId);
            const width = {config.width or 600};
            const height = {config.height or 400};
            const margin = {{top: 40, right: 30, bottom: 60, left: 60}};
            const innerWidth = width - margin.left - margin.right;
            const innerHeight = height - margin.top - margin.bottom;
            
            container.html("");
            container.append("h3").attr("class", "chart-title").text(title);
            
            const svg = container.append("svg")
                .attr("width", width)
                .attr("height", height);
            
            const g = svg.append("g")
                .attr("transform", `translate(${{margin.left}},${{margin.top}})`);
            
            const chartData = Array.isArray(data) ? data : [data];
            const xColumn = "{config.x_column or 'date' or 'x'}";
            const yColumn = "{config.y_column or 'value' or 'y'}";
            
            // Parse dates if x column contains date strings
            chartData.forEach(d => {{
                if (typeof d[xColumn] === 'string' && d[xColumn].match(/\\d{{4}}-\\d{{2}}-\\d{{2}}/)) {{
                    d[xColumn] = new Date(d[xColumn]);
                }}
            }});
            
            // Create scales
            const xScale = d3.scaleTime()
                .domain(d3.extent(chartData, d => d[xColumn]))
                .range([0, innerWidth]);
            
            const yScale = d3.scaleLinear()
                .domain([0, d3.max(chartData, d => +d[yColumn])])
                .nice()
                .range([innerHeight, 0]);
            
            // Create line generator
            const line = d3.line()
                .x(d => xScale(d[xColumn]))
                .y(d => yScale(+d[yColumn]));
            
            // Add axes
            g.append("g")
                .attr("class", "axis x-axis")
                .attr("transform", `translate(0,${{innerHeight}})`)
                .call(d3.axisBottom(xScale));
            
            g.append("g")
                .attr("class", "axis y-axis")
                .call(d3.axisLeft(yScale));
            
            // Add line
            g.append("path")
                .datum(chartData)
                .attr("class", "line")
                .attr("d", line)
                .attr("stroke", "var(--color-1)")
                .attr("stroke-width", 2)
                .attr("fill", "none");
            
            // Add dots
            g.selectAll(".dot")
                .data(chartData)
                .enter().append("circle")
                .attr("class", "dot")
                .attr("cx", d => xScale(d[xColumn]))
                .attr("cy", d => yScale(+d[yColumn]))
                .attr("r", 4)
                .attr("fill", "var(--color-1)");
        }})();
        """
    
    @staticmethod
    def _generate_pie_chart_js(chart_id: str, config: ChartConfig, data_json: str) -> str:
        """Generate D3.js pie chart code."""
        return f"""
        // Pie chart for {chart_id}
        (function() {{
            const data = {data_json};
            const containerId = "{chart_id}";
            const title = "{sanitize_html(config.title)}";
            
            const container = d3.select("#" + containerId);
            const width = {config.width or 400};
            const height = {config.height or 400};
            const radius = Math.min(width, height) / 2 - 40;
            
            container.html("");
            container.append("h3").attr("class", "chart-title").text(title);
            
            const svg = container.append("svg")
                .attr("width", width)
                .attr("height", height);
            
            const g = svg.append("g")
                .attr("transform", `translate(${{width/2}},${{height/2}})`);
            
            const chartData = Array.isArray(data) ? data : [data];
            const labelColumn = "{config.x_column or 'label' or 'category'}";
            const valueColumn = "{config.y_column or 'value' or 'count'}";
            
            const color = d3.scaleOrdinal()
                .domain(chartData.map(d => d[labelColumn]))
                .range(["var(--color-1)", "var(--color-2)", "var(--color-3)", "var(--color-4)", "var(--color-5)"]);
            
            const pie = d3.pie()
                .value(d => +d[valueColumn]);
            
            const arc = d3.arc()
                .innerRadius(0)
                .outerRadius(radius);
            
            const arcs = g.selectAll(".arc")
                .data(pie(chartData))
                .enter().append("g")
                .attr("class", "arc");
            
            arcs.append("path")
                .attr("d", arc)
                .attr("fill", d => color(d.data[labelColumn]));
            
            arcs.append("text")
                .attr("transform", d => `translate(${{arc.centroid(d)}})`)
                .attr("text-anchor", "middle")
                .text(d => d.data[labelColumn]);
        }})();
        """
    
    @staticmethod
    def _generate_table_js(chart_id: str, config: ChartConfig, data_json: str) -> str:
        """Generate HTML table from data."""
        return f"""
        // Table for {chart_id}
        (function() {{
            const data = {data_json};
            const containerId = "{chart_id}";
            const title = "{sanitize_html(config.title)}";
            
            const container = d3.select("#" + containerId);
            container.html("");
            container.append("h3").attr("class", "chart-title").text(title);
            
            const chartData = Array.isArray(data) ? data : [data];
            
            if (chartData.length > 0) {{
                const columns = Object.keys(chartData[0]);
                
                const table = container.append("table");
                const thead = table.append("thead");
                const tbody = table.append("tbody");
                
                // Add headers
                thead.append("tr")
                    .selectAll("th")
                    .data(columns)
                    .enter()
                    .append("th")
                    .text(d => d);
                
                // Add rows
                const rows = tbody.selectAll("tr")
                    .data(chartData)
                    .enter()
                    .append("tr");
                
                rows.selectAll("td")
                    .data(row => columns.map(col => row[col]))
                    .enter()
                    .append("td")
                    .text(d => d);
            }}
        }})();
        """
