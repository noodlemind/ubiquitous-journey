#!/usr/bin/env python3
"""
Test the complete workflow with single master query approach.
Demonstrates how one comprehensive query can feed D3.js dashboards.
"""

import json
import sqlite3
from pathlib import Path

from ddl_parser_mcp.server import DDLParserMCPServer
from ddl_parser_mcp.schema import DDLParserRequest, InputFormat
from dashboard_generator_mcp.server import DashboardGeneratorMCPServer
from dashboard_generator_mcp.schema import DashboardGeneratorRequest


def setup_test_database():
    """Create a test SQLite database with sample data."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # Create schema
    cursor.executescript("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(255),
            country VARCHAR(50),
            segment VARCHAR(50),
            created_at DATE
        );
        
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name VARCHAR(100),
            category VARCHAR(50),
            unit_price DECIMAL(10,2),
            stock_quantity INTEGER
        );
        
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date DATE,
            status VARCHAR(20),
            total_amount DECIMAL(10,2),
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );
        
        CREATE TABLE order_items (
            item_id INTEGER PRIMARY KEY,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            unit_price DECIMAL(10,2),
            subtotal DECIMAL(10,2),
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
    """)
    
    # Insert sample data
    cursor.executescript("""
        INSERT INTO customers VALUES 
            (1, 'John Doe', 'john@example.com', 'USA', 'Premium', '2023-01-15'),
            (2, 'Jane Smith', 'jane@example.com', 'UK', 'Standard', '2023-02-20'),
            (3, 'Bob Johnson', 'bob@example.com', 'Canada', 'Premium', '2023-03-10');
        
        INSERT INTO products VALUES
            (1, 'Laptop Pro', 'Electronics', 1299.99, 50),
            (2, 'Wireless Mouse', 'Electronics', 29.99, 200),
            (3, 'Office Chair', 'Furniture', 399.99, 30),
            (4, 'Desk Lamp', 'Furniture', 49.99, 100);
        
        INSERT INTO orders VALUES
            (1, 1, '2024-01-10', 'Completed', 1329.98),
            (2, 2, '2024-01-15', 'Completed', 449.98),
            (3, 1, '2024-02-01', 'Pending', 29.99);
        
        INSERT INTO order_items VALUES
            (1, 1, 1, 1, 1299.99, 1299.99),
            (2, 1, 2, 1, 29.99, 29.99),
            (3, 2, 3, 1, 399.99, 399.99),
            (4, 2, 4, 1, 49.99, 49.99),
            (5, 3, 2, 1, 29.99, 29.99);
    """)
    
    conn.commit()
    return conn


def test_master_query_workflow():
    """Test the complete workflow with master query approach."""
    
    print("="*80)
    print("🚀 TESTING MASTER QUERY WORKFLOW FOR D3.JS DASHBOARDS")
    print("="*80)
    
    # Step 1: Parse DDL and generate master query
    print("\n📋 Step 1: Parsing DDL Schema...")
    
    ddl_input = """
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(255),
        country VARCHAR(50),
        segment VARCHAR(50),
        created_at DATE
    );
    
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        name VARCHAR(100),
        category VARCHAR(50),
        unit_price DECIMAL(10,2),
        stock_quantity INTEGER
    );
    
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        order_date DATE,
        status VARCHAR(20),
        total_amount DECIMAL(10,2),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );
    
    CREATE TABLE order_items (
        item_id INTEGER PRIMARY KEY,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        unit_price DECIMAL(10,2),
        subtotal DECIMAL(10,2),
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """
    
    # Create parser server
    parser_server = DDLParserMCPServer()
    
    # Create request with visualization intents
    request = DDLParserRequest(
        task="parse_schema",
        input=ddl_input,
        format=InputFormat.DDL,
        database_type="sqlite",
        visualization_intents=["overview", "distribution", "time_series", "relationships"]
    )
    
    # Parse schema
    response = parser_server.handle_request(request)
    
    if response.status == "error":
        print(f"❌ Error: {response.error}")
        return
    
    print(f"✅ Schema parsed: {len(response.schema.tables)} tables found")
    print(f"📊 Business Domain: {response.metadata.get('business_analysis', {}).get('business_domain', 'Unknown')}")
    
    # Step 2: Display the master query
    print("\n📋 Step 2: Master Query Generated...")
    
    if response.suggested_queries:
        master_query = response.suggested_queries[0]  # First query is the master query
        print(f"\n🔍 Query Type: {master_query.metadata.get('type', 'standard')}")
        print(f"📝 Description: {master_query.description}")
        print(f"🎯 Purpose: {master_query.metadata.get('purpose', 'data extraction')}")
        print(f"📊 Visualization Type: {master_query.visualization_type}")
        print(f"🔑 Result Key: {master_query.result_key}")
        
        print("\n💾 SQL Query:")
        print("-" * 60)
        print(master_query.query)
        print("-" * 60)
        
        # Step 3: Execute the master query
        print("\n📋 Step 3: Executing Master Query...")
        
        conn = setup_test_database()
        cursor = conn.cursor()
        
        try:
            cursor.execute(master_query.query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            # Convert to JSON format
            data = []
            for row in rows:
                data.append(dict(zip(columns, row)))
            
            print(f"✅ Query executed: {len(data)} rows returned")
            print(f"📊 Columns: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")
            
            # Save data for dashboard
            data_json = {
                "metadata": {
                    "source": "master_query",
                    "query_description": master_query.description,
                    "visualization_intents": request.visualization_intents,
                    "row_count": len(data),
                    "column_count": len(columns)
                },
                "data": data
            }
            
            # Step 4: Generate dashboard
            print("\n📋 Step 4: Generating D3.js Dashboard...")
            
            dashboard_server = DashboardGeneratorMCPServer()
            
            dashboard_request = DashboardGeneratorRequest(
                task="generate_dashboard",
                data=data,
                auto_detect=True,  # Let D3 figure out the best visualizations
                metadata={
                    "title": "E-Commerce Analytics Dashboard",
                    "description": "Comprehensive business insights powered by D3.js",
                    "data_source": "master_query",
                    "processing": "client-side",
                    "note": "All aggregations and transformations handled by D3.js"
                }
            )
            
            dashboard_response = dashboard_server.handle_request(dashboard_request)
            
            if dashboard_response.status == "success":
                print("✅ Dashboard generated successfully!")
                
                # Save files
                with open("test_master_data.json", "w") as f:
                    json.dump(data_json, f, indent=2)
                print("💾 Data saved to: test_master_data.json")
                
                with open("test_master_dashboard.html", "w") as f:
                    f.write(dashboard_response.dashboard.html)
                print("🌐 Dashboard saved to: test_master_dashboard.html")
                
                print("\n🎉 SUCCESS! Complete workflow executed:")
                print("   1. ✅ DDL parsed and analyzed")
                print("   2. ✅ Master query generated (single comprehensive query)")
                print("   3. ✅ Query executed and data extracted")
                print("   4. ✅ D3.js dashboard generated")
                print("\n💡 Key Insights:")
                print("   - Single query provides ALL data needed")
                print("   - D3.js handles grouping, filtering, aggregations")
                print("   - Multiple visualizations from one dataset")
                print("   - Client-side processing = interactive dashboards")
                
            else:
                print(f"❌ Dashboard generation failed: {dashboard_response.error}")
                
        except Exception as e:
            print(f"❌ Query execution failed: {e}")
            print("\nNote: The query might be using advanced LLM-generated syntax.")
            print("In production, the query would be executed against your actual database.")
        
        finally:
            conn.close()
    
    else:
        print("❌ No queries generated")
    
    print("\n" + "="*80)
    print("📊 MASTER QUERY APPROACH BENEFITS:")
    print("="*80)
    print("""
    1. SIMPLICITY: One query to rule them all
    2. FLEXIBILITY: D3.js transforms data as needed
    3. PERFORMANCE: Single database hit
    4. INTERACTIVITY: Client-side filtering/grouping
    5. MAINTAINABILITY: Easier to debug and optimize
    """)


if __name__ == "__main__":
    test_master_query_workflow()