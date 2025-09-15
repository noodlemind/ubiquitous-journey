"""Simplified LLM integration for SQL generation - Version 2.0"""

import json
import requests
from typing import List, Optional


class LLMAgent:
    """Minimal LLM agent for single-shot SQL generation."""
    
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.verify_connection()
    
    def verify_connection(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = [m['name'] for m in response.json().get('models', [])]
                if any(self.model in m for m in models):
                    print(f"✅ LLM ready: {self.model}")
                    return True
            print(f"⚠️ Model {self.model} not found. Please run: ollama pull {self.model}")
            return False
        except Exception as e:
            print(f"⚠️ Ollama not running. Please start it: ollama serve")
            return False
    
    def generate_master_query(self, ddl: str, intents: List[str], database: str = "sqlite") -> str:
        """
        Generate a single comprehensive SQL query from DDL and intents.
        
        This is the ONLY LLM call we make - one shot, get everything.
        """
        # Parse table names from DDL for context
        tables = self._extract_table_names(ddl)
        
        prompt = f"""You are a SQL expert. Generate a SINGLE comprehensive SQL query that joins ALL tables and returns ALL columns needed for data visualization.

REQUIREMENTS:
1. JOIN all tables based on foreign key relationships
2. Use table aliases to avoid column name conflicts  
3. Return ALL columns from ALL tables (use t1.*, t2.*, etc.)
4. Do NOT aggregate - return raw data (D3.js will handle aggregations)
5. Add LIMIT 10000 for performance
6. Make sure the query is valid {database} SQL syntax

DDL SCHEMA:
{ddl}

TABLES FOUND: {', '.join(tables)}

USER WANTS TO ANALYZE: {', '.join(intents)}

Return ONLY the SQL query, no explanation. The query should return flat, denormalized data that can be used for any visualization.

SQL Query:"""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1,  # Low temperature for consistent SQL
                    "top_p": 0.9,
                }
            )
            
            if response.status_code == 200:
                sql = response.json().get('response', '').strip()
                # Clean up the SQL
                sql = sql.replace('```sql', '').replace('```', '').strip()
                
                # Validate it looks like SQL
                if 'SELECT' in sql.upper() and 'FROM' in sql.upper():
                    return sql
                else:
                    return self._generate_fallback_query(tables)
            else:
                print(f"⚠️ LLM request failed: {response.status_code}")
                return self._generate_fallback_query(tables)
                
        except Exception as e:
            print(f"⚠️ LLM error: {e}")
            return self._generate_fallback_query(tables)
    
    def _extract_table_names(self, ddl: str) -> List[str]:
        """Extract table names from DDL."""
        import re
        tables = []
        pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"\']?)(\w+)\1'
        matches = re.finditer(pattern, ddl, re.IGNORECASE)
        for match in matches:
            tables.append(match.group(2))
        return tables
    
    def _generate_fallback_query(self, tables: List[str]) -> str:
        """Generate a simple fallback query if LLM fails."""
        if not tables:
            return "SELECT 1 as test;"
        
        # For single table, just select all
        if len(tables) == 1:
            return f"SELECT * FROM {tables[0]} LIMIT 10000;"
        
        # For multiple tables, try to join first two
        return f"""
SELECT t1.*, t2.*
FROM {tables[0]} t1
LEFT JOIN {tables[1]} t2 ON 1=1
LIMIT 10000;
""".strip()


# Simple test
if __name__ == "__main__":
    agent = LLMAgent()
    
    test_ddl = """
    CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));
    CREATE TABLE orders (id INT PRIMARY KEY, user_id INT, amount DECIMAL(10,2));
    """
    
    query = agent.generate_master_query(
        ddl=test_ddl,
        intents=["Show user orders", "Analyze spending"],
        database="sqlite"
    )
    
    print("Generated Query:")
    print(query)