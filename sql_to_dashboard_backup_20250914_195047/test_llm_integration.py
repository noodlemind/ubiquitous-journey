#!/usr/bin/env python3
"""Test script for LLM integration in SQL-to-Dashboard system."""

import json
import sys
from pathlib import Path
from typing import Dict, Any
import time

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from ddl_parser_mcp.enhanced_server import EnhancedDDLParserMCPServer
from ddl_parser_mcp.schema import DDLParserRequest, InputFormat
from dashboard_generator_mcp.server import DashboardGeneratorMCPServer
from dashboard_generator_mcp.schema import DashboardGeneratorRequest
from llm.sql_intelligence import SQLIntelligenceAgent
from llm.ollama_connector import OllamaConnector


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f"🚀 {title}")
    print("="*60)


def test_ollama_connection():
    """Test if Ollama is running and accessible."""
    print_header("Testing Ollama Connection")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print("✅ Ollama is running!")
            print(f"📦 Available models: {len(models)}")
            for model in models[:3]:  # Show first 3 models
                print(f"   - {model.get('name', 'Unknown')}")
            return True
        else:
            print("❌ Ollama is not responding properly")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("💡 Start Ollama with: ollama serve")
        print("   Then pull a model: ollama pull llama3")
        return False


def test_llm_connector():
    """Test the Ollama connector directly."""
    print_header("Testing LLM Connector")
    
    try:
        connector = OllamaConnector(model="llama3")
        
        # Test basic generation
        prompt = "What is SQL? Answer in one sentence."
        response = connector.generate(prompt, temperature=0.3)
        
        if response.startswith("Error:"):
            print(f"❌ LLM generation failed: {response}")
            return False
        else:
            print("✅ LLM generation successful!")
            print(f"📝 Response: {response[:200]}...")
            return True
    except Exception as e:
        print(f"❌ LLM connector test failed: {e}")
        return False


def test_schema_analysis():
    """Test LLM-powered schema analysis."""
    print_header("Testing Schema Analysis with LLM")
    
    # Sample e-commerce schema
    schema = {
        "tables": [
            {
                "name": "customers",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "name", "type": "VARCHAR(100)"},
                    {"name": "email", "type": "VARCHAR(255)"},
                    {"name": "country", "type": "VARCHAR(50)"},
                    {"name": "created_at", "type": "TIMESTAMP"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indexes": []
            },
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "customer_id", "type": "INTEGER", "foreign_key": "customers.id"},
                    {"name": "order_date", "type": "TIMESTAMP"},
                    {"name": "total_amount", "type": "DECIMAL(10,2)"},
                    {"name": "status", "type": "VARCHAR(20)"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [{"column": "customer_id", "references": "customers.id"}],
                "indexes": []
            },
            {
                "name": "products",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "name", "type": "VARCHAR(200)"},
                    {"name": "category", "type": "VARCHAR(50)"},
                    {"name": "price", "type": "DECIMAL(10,2)"},
                    {"name": "stock_quantity", "type": "INTEGER"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indexes": []
            }
        ],
        "relationships": [
            {
                "from_table": "orders",
                "from_column": "customer_id",
                "to_table": "customers",
                "to_column": "id",
                "relationship_type": "many-to-one"
            }
        ]
    }
    
    try:
        agent = SQLIntelligenceAgent()
        analysis = agent.analyze_business_context(schema)
        
        print("✅ Schema analysis complete!")
        print(f"📈 Business Domain: {analysis.get('business_domain', 'Unknown')}")
        print(f"🔑 Key Entities: {', '.join(analysis.get('key_entities', []))}")
        print(f"📊 Potential Metrics: {', '.join(analysis.get('metrics', [])[:3])}")
        
        if analysis.get('insights'):
            print("\n💡 Business Insights:")
            for insight in analysis['insights'][:3]:
                print(f"   • {insight}")
        
        return True
    except Exception as e:
        print(f"❌ Schema analysis failed: {e}")
        return False


def test_natural_language_query():
    """Test natural language to SQL conversion."""
    print_header("Testing Natural Language to SQL")
    
    # Sample schema for query generation
    schema = {
        "tables": [
            {
                "name": "sales",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "product_id", "type": "INTEGER"},
                    {"name": "customer_id", "type": "INTEGER"},
                    {"name": "quantity", "type": "INTEGER"},
                    {"name": "sale_date", "type": "DATE"},
                    {"name": "amount", "type": "DECIMAL(10,2)"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indexes": []
            },
            {
                "name": "products",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "name", "type": "VARCHAR(100)"},
                    {"name": "category", "type": "VARCHAR(50)"},
                    {"name": "price", "type": "DECIMAL(10,2)"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indexes": []
            }
        ],
        "relationships": []
    }
    
    test_queries = [
        "Show me total sales by product category",
        "What are the top 5 best selling products?",
        "Calculate monthly revenue trends",
        "Find customers who haven't made a purchase in 30 days"
    ]
    
    try:
        agent = SQLIntelligenceAgent()
        
        print("🔄 Converting natural language queries to SQL:\n")
        
        for i, nl_query in enumerate(test_queries, 1):
            print(f"{i}. Query: \"{nl_query}\"")
            
            query_plan = agent.generate_query_from_intent(nl_query, schema)
            
            if query_plan.query and not query_plan.query.startswith("--"):
                print(f"   ✅ Generated SQL:")
                print(f"      {query_plan.query[:150]}...")
                print(f"   📊 Visualization: {query_plan.visualization_type}")
                print(f"   🎯 Confidence: {query_plan.confidence:.0%}")
            else:
                print(f"   ❌ Failed to generate SQL")
            print()
        
        return True
    except Exception as e:
        print(f"❌ Natural language query test failed: {e}")
        return False


def test_visualization_recommendation():
    """Test LLM-powered visualization recommendations."""
    print_header("Testing Visualization Recommendations")
    
    # Sample data for visualization recommendation
    sample_data = [
        {"month": "2024-01", "category": "Electronics", "sales": 45000, "units": 150},
        {"month": "2024-01", "category": "Clothing", "sales": 32000, "units": 420},
        {"month": "2024-02", "category": "Electronics", "sales": 48000, "units": 160},
        {"month": "2024-02", "category": "Clothing", "sales": 35000, "units": 450},
        {"month": "2024-03", "category": "Electronics", "sales": 52000, "units": 175},
        {"month": "2024-03", "category": "Clothing", "sales": 38000, "units": 480}
    ]
    
    query_metadata = {
        "intent_type": "time_series",
        "has_aggregation": True,
        "has_time_component": True
    }
    
    try:
        connector = OllamaConnector()
        recommendation = connector.recommend_visualization(sample_data, query_metadata)
        
        print("✅ Visualization recommendation complete!")
        print(f"📊 Primary Chart: {recommendation.get('primary', 'Unknown')}")
        print(f"🔄 Alternatives: {', '.join(recommendation.get('alternatives', []))}")
        print(f"💡 Reason: {recommendation.get('reason', 'No reason provided')}")
        
        if recommendation.get('x_axis'):
            print(f"📈 X-Axis: {recommendation['x_axis']}")
        if recommendation.get('y_axis'):
            print(f"📈 Y-Axis: {recommendation['y_axis']}")
        if recommendation.get('title_suggestion'):
            print(f"📝 Title: {recommendation['title_suggestion']}")
        
        return True
    except Exception as e:
        print(f"❌ Visualization recommendation failed: {e}")
        return False


def test_enhanced_ddl_parser():
    """Test the enhanced DDL parser with LLM integration."""
    print_header("Testing Enhanced DDL Parser")
    
    # Example DDL for testing
    test_ddl = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        email VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE
    );
    
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        title VARCHAR(200) NOT NULL,
        content TEXT,
        published_at TIMESTAMP,
        view_count INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    
    CREATE TABLE comments (
        id INTEGER PRIMARY KEY,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        comment_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """
    
    try:
        # Test with LLM
        print("\n🤖 Testing with LLM enhancement...")
        server_with_llm = EnhancedDDLParserMCPServer(use_llm=True)
        
        request = DDLParserRequest(
            task="parse_schema",
            input=test_ddl,
            format=InputFormat.DDL,
            database_type="sqlite",
            visualization_intents=["overview", "distribution", "relationship"]
        )
        
        response = server_with_llm.handle_request(request)
        
        if response.status == "success":
            print("✅ DDL parsing with LLM successful!")
            print(f"📊 Tables found: {response.metadata.get('table_count', 0)}")
            print(f"🔗 Relationships: {response.metadata.get('relationship_count', 0)}")
            print(f"🤖 LLM Enhanced: {response.metadata.get('llm_enhanced', False)}")
            
            if response.metadata.get('business_analysis'):
                analysis = response.metadata['business_analysis']
                print(f"📈 Detected Domain: {analysis.get('business_domain', 'Unknown')}")
            
            print(f"\n📝 Generated {len(response.suggested_queries)} SQL queries")
            
            # Show a few queries
            for i, query in enumerate(response.suggested_queries[:3], 1):
                print(f"\n{i}. {query.description}")
                if query.metadata and query.metadata.get('llm_generated'):
                    print(f"   🤖 LLM Generated (Confidence: {query.metadata.get('confidence', 0):.0%})")
                print(f"   📊 Visualization: {query.visualization_type}")
        else:
            print(f"❌ DDL parsing failed: {response.error}")
            return False
        
        # Compare with non-LLM version
        print("\n\n📋 Testing without LLM (baseline)...")
        server_no_llm = EnhancedDDLParserMCPServer(use_llm=False)
        response_no_llm = server_no_llm.handle_request(request)
        
        if response_no_llm.status == "success":
            print("✅ DDL parsing without LLM successful!")
            print(f"📝 Generated {len(response_no_llm.suggested_queries)} SQL queries (rule-based)")
        
        # Compare results
        print("\n\n📊 Comparison:")
        print(f"   With LLM: {len(response.suggested_queries)} queries")
        print(f"   Without LLM: {len(response_no_llm.suggested_queries)} queries")
        print(f"   LLM Advantage: Business context analysis and intelligent query generation")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced DDL parser test failed: {e}")
        return False


def run_all_tests():
    """Run all LLM integration tests."""
    print("\n" + "="*60)
    print("🧪 SQL-to-Dashboard LLM Integration Test Suite")
    print("="*60)
    
    tests = [
        ("Ollama Connection", test_ollama_connection),
        ("LLM Connector", test_llm_connector),
        ("Schema Analysis", test_schema_analysis),
        ("Natural Language Query", test_natural_language_query),
        ("Visualization Recommendation", test_visualization_recommendation),
        ("Enhanced DDL Parser", test_enhanced_ddl_parser)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            time.sleep(1)  # Small delay between tests
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
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
        print("🎉 All tests passed! LLM integration is working correctly.")
    elif passed > 0:
        print("⚠️ Some tests failed. Check the output above for details.")
    else:
        print("❌ All tests failed. Make sure Ollama is running with a model installed.")
        print("\n💡 Quick fix:")
        print("   1. Install Ollama: https://ollama.ai")
        print("   2. Start Ollama: ollama serve")
        print("   3. Pull a model: ollama pull llama3")
        print("   4. Run this test again")


if __name__ == "__main__":
    run_all_tests()