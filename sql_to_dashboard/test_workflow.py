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
from dashboard_generator_mcp.schema import DashboardGeneratorRequest


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
    
    # Step 2: Test Dashboard Generator
    print("Step 2: Testing Dashboard Generator...")
    
    # Read sample data
    with open("examples/sample_data.json", "r") as f:
        sample_data = json.load(f)
    
    # Create dashboard server
    dashboard_server = DashboardGeneratorMCPServer()
    
    # Create request
    dashboard_request = DashboardGeneratorRequest(
        task="generate_dashboard",
        data=sample_data,
        auto_detect=True
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
        print(f"   Charts: {dashboard_response.metadata.get('chart_count', 0)}")
        print(f"   Theme: {dashboard_response.metadata.get('theme', 'unknown')}")
        print(f"   Responsive: {dashboard_response.metadata.get('responsive', False)}")
        
        print(f"\n🎉 Success! Open {output_file} in your browser to view the dashboard.")
    else:
        print(f"❌ Dashboard generation failed: {dashboard_response.error}")
    
    print("\n" + "="*50)
    print("\n✨ Workflow test completed!")


if __name__ == "__main__":
    test_workflow()
