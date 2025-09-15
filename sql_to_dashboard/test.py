#!/usr/bin/env python3
"""Simple test suite for SQL to Dashboard v2.0"""

import os
import json
from pathlib import Path

from schemas import GenerateRequest, GenerateResponse
from server import SqlToDashboardServer


def test_basic_generation():
    """Test basic DDL to dashboard generation."""
    print("🧪 Test 1: Basic Generation")
    
    ddl = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(255)
    );
    
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        total DECIMAL(10,2),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """
    
    server = SqlToDashboardServer()
    request = GenerateRequest(
        ddl=ddl,
        intents=["User orders", "Revenue analysis"],
        database="sqlite"
    )
    
    response = server.generate_all(request)
    
    # Verify response
    assert isinstance(response, GenerateResponse), f"Response type: {type(response)}"
    assert len(response.query) > 0, f"Query is empty: {response.query}"
    assert "SELECT" in response.query.upper(), f"No SELECT in query: {response.query[:100]}"
    assert len(response.dashboard_html) > 1000, f"Dashboard too short: {len(response.dashboard_html)} chars"
    assert "d3.js" in response.dashboard_html.lower() or "d3js" in response.dashboard_html.lower(), f"No D3.js reference found"
    assert len(response.execution_script) > 0, f"Execution script is empty"
    
    print("  ✅ Generated query, dashboard, and script")
    return True


def test_file_generation():
    """Test generating files to disk."""
    print("🧪 Test 2: File Generation")
    
    from server import generate_from_file
    
    # Create test DDL file
    test_dir = Path("./test_output")
    test_dir.mkdir(exist_ok=True)
    
    ddl_file = test_dir / "test_schema.sql"
    with open(ddl_file, 'w') as f:
        f.write("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100),
            price DECIMAL(10,2),
            category VARCHAR(50)
        );
        """)
    
    # Generate files
    response = generate_from_file(
        str(ddl_file),
        ["Product analysis", "Price trends"],
        str(test_dir)
    )
    
    # Verify files created
    assert (test_dir / "query.sql").exists()
    assert (test_dir / "dashboard.html").exists()
    assert (test_dir / "execute.sh").exists()
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    
    print("  ✅ Files generated successfully")
    return True


def test_error_handling():
    """Test error handling with invalid input."""
    print("🧪 Test 3: Error Handling")
    
    server = SqlToDashboardServer()
    
    # Test with invalid DDL
    request = GenerateRequest(
        ddl="NOT VALID SQL AT ALL",
        intents=["test"],
        database="sqlite"
    )
    
    response = server.generate_all(request)
    
    # Should still return a valid response (with error handling)
    assert isinstance(response, GenerateResponse)
    assert len(response.query) > 0  # Should have fallback query
    assert len(response.dashboard_html) > 0
    
    print("  ✅ Error handling works correctly")
    return True


def run_all_tests():
    """Run all tests."""
    print("=" * 50)
    print("🚀 SQL to Dashboard v2.0 - Test Suite")
    print("=" * 50)
    
    tests = [
        test_basic_generation,
        test_file_generation,
        test_error_handling
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)