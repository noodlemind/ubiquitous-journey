#!/usr/bin/env python3
"""Test script for SQL-to-Dashboard workflow."""

import json
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from ddl_parser_mcp.server import DDLParserMCPServer
from ddl_parser_mcp.schema import DDLParserRequest, InputFormat
from dashboard_generator_mcp.server import DashboardGeneratorMCPServer
from dashboard_generator_mcp.schema import (
    DashboardGeneratorRequest,
    ChartConfig,
    ChartType,
    DashboardConfig,
    ThemeType
)


def test_workflow():
    """Test the complete workflow."""
    
    print("🚀 Testing SQL-to-Dashboard Workflow\n")
    
    # Step 1: Test DDL Parser
    print("Step 1: Testing DDL Parser...")
    
    # Read example schema
    with open("examples/ecommerce_schema.sql", "r") as f:
        ddl_content = f.read()
    
    # Create parser server
    parser_server = DDLParserMCPServer()
    
    # Create request
    parse_request = DDLParserRequest(
        task="parse_schema",
        input=ddl_content,
        format=InputFormat.DDL,
        database_type="sqlite",
        visualization_intents=["overview", "distributions", "relationships"]
    )
    
    # Process request
    parse_response = parser_server.handle_request(parse_request)
    
    if parse_response.status == "success":
        print(f"✅ Parsed {len(parse_response.schema.tables)} tables")
        print(f"✅ Generated {len(parse_response.suggested_queries)} SQL queries")
        
        # Show first few queries
        print("\n📝 Sample SQL Queries:")
        for i, query in enumerate(parse_response.suggested_queries[:3], 1):
            print(f"\n{i}. {query.description}")
            print(f"   Type: {query.visualization_type}")
            print(f"   SQL: {query.query[:100]}...")
    else:
        print(f"❌ Parser failed: {parse_response.error}")
        return
    
    print("\n" + "="*50 + "\n")
    
    # Step 2: Test Dashboard Generator with Quality Charts
    print("Step 2: Testing Dashboard Generator with Quality Visualizations...")
    
    # Read sample data files
    with open("examples/time_series_data.json", "r") as f:
        time_series_data = json.load(f)
    
    with open("examples/customer_distribution.json", "r") as f:
        customer_data = json.load(f)
    
    with open("examples/product_performance.json", "r") as f:
        product_data = json.load(f)
    
    # Create dashboard server
    dashboard_server = DashboardGeneratorMCPServer()
    
    # Create focused, high-quality chart configurations
    charts = [
        # 1. Line chart for time series - showcasing trend analysis
        ChartConfig(
            type=ChartType.LINE,
            title="Daily Revenue Trend - January 2024",
            data=time_series_data,
            x_column="date",
            y_column="daily_revenue",
            width=700,
            height=350
        ),
        # 2. Pie chart for customer distribution - showcasing market share
        ChartConfig(
            type=ChartType.PIE,
            title="Customer Distribution by Country",
            data=customer_data,
            x_column="country",
            y_column="customer_count",
            width=450,
            height=400
        ),
        # 3. Scatter plot for product analysis - showcasing correlations
        ChartConfig(
            type=ChartType.SCATTER,
            title="Product Performance: Price vs Sales Volume",
            data=product_data,
            x_column="price",
            y_column="units_sold",
            group_by="category",
            width=700,
            height=400
        )
    ]
    
    # Create dashboard configuration with quality focus
    dashboard_config = DashboardConfig(
        title="Analytics Dashboard Demo",
        theme=ThemeType.LIGHT,
        responsive=True,
        charts=charts,
        layout="grid"
    )
    
    # Create request with organized datasets
    dashboard_request = DashboardGeneratorRequest(
        task="generate_dashboard",
        data={
            "time_series": time_series_data,
            "customers": customer_data,
            "products": product_data
        },
        config=dashboard_config,
        charts=charts,
        auto_detect=False  # Use our explicit chart configurations
    )
    
    # Process request
    dashboard_response = dashboard_server.handle_request(dashboard_request)
    
    if dashboard_response.status == "success":
        print("✅ Dashboard generated successfully")
        
        # Save to file
        output_file = "test_dashboard.html"
        with open(output_file, "w") as f:
            f.write(dashboard_response.dashboard.html)
        
        print(f"✅ Saved to: {output_file}")
        print(f"\n📊 Dashboard Info:")
        print(f"   Total Charts: {len(charts)}")
        print(f"   Theme: {dashboard_config.theme}")
        print(f"   Layout: {dashboard_config.layout}")
        print(f"   Responsive: {dashboard_config.responsive}")
        
        print(f"\n📈 Generated Visualizations:")
        for i, chart in enumerate(charts, 1):
            print(f"   {i}. {chart.title}")
            print(f"      • Type: {chart.type.value}")
            print(f"      • Dimensions: {chart.width}x{chart.height}px")
            if chart.x_column and chart.y_column:
                print(f"      • Data: {chart.x_column} vs {chart.y_column}")
            if chart.group_by:
                print(f"      • Grouped by: {chart.group_by}")
        
        print(f"\n✨ Key Features Demonstrated:")
        print(f"   • Interactive tooltips on hover")
        print(f"   • Responsive grid layout")
        print(f"   • Clean, professional styling")
        print(f"   • D3.js-powered visualizations")
        
        print(f"\n🎉 Success! Open {output_file} in your browser to view the dashboard.")
    else:
        print(f"❌ Dashboard generation failed: {dashboard_response.error}")
    
    print("\n" + "="*50)
    print("\n✨ Workflow test completed!")


if __name__ == "__main__":
    test_workflow()
