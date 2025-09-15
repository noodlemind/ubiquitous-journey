#!/usr/bin/env python3
"""Simplified test suite for LLM-powered SQL-to-Dashboard system."""

import json
import sys
from pathlib import Path
import time
import requests

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from ddl_parser_mcp.server import DDLParserMCPServer
from ddl_parser_mcp.schema import DDLParserRequest, InputFormat
from dashboard_generator_mcp.server import DashboardGeneratorMCPServer
from dashboard_generator_mcp.schema import DashboardGeneratorRequest


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f"🚀 {title}")
    print("="*60)


def test_ollama_status():
    """Test if Ollama is running (required for system to work)."""
    print_header("Testing Ollama Status (Required)")
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print("✅ Ollama is running!")
            print(f"📦 Available models: {len(models)}")
            
            # Check if llama3 is available
            model_names = [m.get('name', '') for m in models]
            if any('llama3' in name for name in model_names):
                print("✅ llama3 model is available")
            else:
                print("⚠️ llama3 model not found. Pull it with: ollama pull llama3")
            
            return True
        else:
            print("❌ Ollama is not responding properly")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("\n🔧 To fix this:")
        print("  1. Install Ollama: https://ollama.ai")
        print("  2. Start Ollama: ollama serve")
        print("  3. Pull model: ollama pull llama3")
        return False


def test_ddl_parser():
    """Test the simplified DDL parser with LLM."""
    print_header("Testing LLM-Powered DDL Parser")
    
    test_ddl = """
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE,
        country VARCHAR(50)
    );
    
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        order_date DATE,
        total_amount DECIMAL(10,2),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );
    
    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name VARCHAR(200),
        category VARCHAR(50),
        price DECIMAL(10,2)
    );
    """
    
    try:
        # Initialize server (will fail if Ollama not running)
        server = DDLParserMCPServer(llm_model="llama3")
        print("✅ Server initialized with LLM")
        
        # Create request
        request = DDLParserRequest(
            task="parse_schema",
            input=test_ddl,
            format=InputFormat.DDL,
            database_type="sqlite",
            visualization_intents=["overview", "distribution", "relationship"]
        )
        
        # Process request
        print("🤖 Processing schema with LLM...")
        response = server.handle_request(request)
        
        if response.status == "success":
            print(f"✅ Schema parsed successfully!")
            print(f"📊 Tables found: {response.metadata.get('table_count', 0)}")
            
            # Check business analysis
            business_analysis = response.metadata.get('business_analysis', {})
            if business_analysis:
                print(f"📈 Business Domain: {business_analysis.get('business_domain', 'Unknown')}")
                print(f"🔑 Key Entities: {', '.join(business_analysis.get('key_entities', []))}")
            
            # Check queries
            print(f"📝 Generated {len(response.suggested_queries)} AI-powered queries")
            
            # Show a sample query
            if response.suggested_queries:
                sample = response.suggested_queries[0]
                print(f"\n🔍 Sample Query:")
                print(f"   Description: {sample.description}")
                print(f"   Visualization: {sample.visualization_type}")
                if sample.metadata:
                    print(f"   Confidence: {sample.metadata.get('confidence', 0):.0%}")
                print(f"   SQL: {sample.query[:100]}...")
            
            return True
        else:
            print(f"❌ Parsing failed: {response.error}")
            return False
            
    except RuntimeError as e:
        print(f"❌ Server initialization failed: {e}")
        print("   Make sure Ollama is running!")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_natural_language_query():
    """Test natural language to SQL conversion."""
    print_header("Testing Natural Language to SQL")
    
    test_ddl = """
    CREATE TABLE sales (
        id INTEGER PRIMARY KEY,
        product_id INTEGER,
        customer_id INTEGER,
        sale_date DATE,
        amount DECIMAL(10,2)
    );
    
    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100),
        category VARCHAR(50)
    );
    """
    
    try:
        server = DDLParserMCPServer()
        
        # First parse the schema
        request = DDLParserRequest(
            task="parse_schema",
            input=test_ddl,
            format=InputFormat.DDL,
            database_type="sqlite"
        )
        
        response = server.handle_request(request)
        
        if response.status != "success":
            print("❌ Failed to parse schema")
            return False
        
        # Test natural language query
        nl_query = "Show me total sales by product category"
        print(f"📝 Natural Language: \"{nl_query}\"")
        
        suggestion = server.generate_natural_language_query(nl_query, response.schema)
        
        print(f"✅ Generated SQL:")
        print(f"   {suggestion.query}")
        print(f"📊 Visualization: {suggestion.visualization_type}")
        
        if suggestion.metadata:
            print(f"🎯 Confidence: {suggestion.metadata.get('confidence', 0):.0%}")
            explanation = suggestion.metadata.get('explanation', '')
            if explanation:
                print(f"💡 Explanation: {explanation[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_dashboard_generation():
    """Test dashboard generation (unchanged)."""
    print_header("Testing Dashboard Generation")
    
    sample_data = [
        {"month": "2024-01", "category": "Electronics", "sales": 45000},
        {"month": "2024-01", "category": "Clothing", "sales": 32000},
        {"month": "2024-02", "category": "Electronics", "sales": 48000},
        {"month": "2024-02", "category": "Clothing", "sales": 35000}
    ]
    
    try:
        server = DashboardGeneratorMCPServer()
        
        request = DashboardGeneratorRequest(
            task="generate_dashboard",
            data=sample_data,
            auto_detect=True
        )
        
        response = server.handle_request(request)
        
        if response.status == "success":
            print("✅ Dashboard generated successfully!")
            print(f"📈 Charts created: {response.metadata.get('chart_count', 0)}")
            return True
        else:
            print(f"❌ Dashboard generation failed: {response.error}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_end_to_end_workflow():
    """Test complete workflow from DDL to Dashboard."""
    print_header("Testing End-to-End Workflow")
    
    # Step 1: Parse DDL with LLM
    print("\n📋 Step 1: Parse DDL with LLM")
    
    test_ddl = """
    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100),
        category VARCHAR(50),
        price DECIMAL(10,2)
    );
    
    CREATE TABLE sales (
        id INTEGER PRIMARY KEY,
        product_id INTEGER,
        quantity INTEGER,
        sale_date DATE,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """
    
    try:
        parser = DDLParserMCPServer()
        
        parse_request = DDLParserRequest(
            task="parse_schema",
            input=test_ddl,
            format=InputFormat.DDL,
            database_type="sqlite",
            visualization_intents=["overview", "distribution"]
        )
        
        parse_response = parser.handle_request(parse_request)
        
        if parse_response.status != "success":
            print(f"❌ DDL parsing failed: {parse_response.error}")
            return False
        
        print(f"✅ Parsed {parse_response.metadata.get('table_count', 0)} tables")
        print(f"🤖 AI generated {len(parse_response.suggested_queries)} queries")
        
        # Step 2: Generate Dashboard
        print("\n📋 Step 2: Generate Dashboard")
        
        # Sample data (would normally come from executing queries)
        sample_data = [
            {"category": "Electronics", "total_sales": 120000},
            {"category": "Clothing", "total_sales": 85000},
            {"category": "Books", "total_sales": 45000}
        ]
        
        dashboard_server = DashboardGeneratorMCPServer()
        
        dashboard_request = DashboardGeneratorRequest(
            task="generate_dashboard",
            data=sample_data,
            auto_detect=True
        )
        
        dashboard_response = dashboard_server.handle_request(dashboard_request)
        
        if dashboard_response.status != "success":
            print(f"❌ Dashboard generation failed: {dashboard_response.error}")
            return False
        
        print("✅ Dashboard generated successfully!")
        print("\n🎉 Complete workflow executed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("🧪 Simplified SQL-to-Dashboard Test Suite")
    print("   (LLM-Only Architecture)")
    print("="*60)
    
    tests = [
        ("Ollama Status Check", test_ollama_status),
        ("DDL Parser with LLM", test_ddl_parser),
        ("Natural Language Query", test_natural_language_query),
        ("Dashboard Generation", test_dashboard_generation),
        ("End-to-End Workflow", test_end_to_end_workflow)
    ]
    
    results = []
    
    # First check if Ollama is running
    if not test_ollama_status():
        print("\n" + "="*60)
        print("❌ CRITICAL: Ollama is not running!")
        print("   The system requires Ollama to be running.")
        print("   Please start Ollama and try again.")
        print("="*60)
        return
    
    # Run remaining tests
    for test_name, test_func in tests[1:]:  # Skip Ollama test as we already ran it
        try:
            time.sleep(1)  # Small delay between tests
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Add Ollama test result
    results.insert(0, ("Ollama Status Check", True))
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed ({(passed/total)*100:.0f}%)")
    
    if passed == total:
        print("🎉 All tests passed! The simplified system is working perfectly.")
        print("\n✨ Benefits of the simplified architecture:")
        print("   • No fallback logic needed")
        print("   • Consistent AI-powered query generation")
        print("   • Natural language support throughout")
        print("   • Cleaner, more maintainable code")
    elif passed > 0:
        print("⚠️ Some tests failed. Check the output above for details.")
    else:
        print("❌ All tests failed. Make sure Ollama is properly configured.")


if __name__ == "__main__":
    run_all_tests()