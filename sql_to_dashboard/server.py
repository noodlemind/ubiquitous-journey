"""Unified SQL to Dashboard Server - Version 2.0
Combines DDL parsing, LLM query generation, and dashboard creation in one module.
"""

import sqlglot
from pathlib import Path
from typing import List, Optional

from schemas import GenerateRequest, GenerateResponse, DashboardConfig
from llm import LLMAgent
from dashboard import generate_dashboard_html


class SqlToDashboardServer:
    """Single unified server for the entire SQL to Dashboard workflow."""
    
    def __init__(self, llm_model: str = "llama3"):
        """Initialize server with LLM agent."""
        self.llm = LLMAgent(model=llm_model)
        print("🚀 SQL to Dashboard Server v2.0 initialized")
    
    def generate_all(self, request: GenerateRequest) -> GenerateResponse:
        """
        Main entry point: Generate everything from DDL and intents.
        
        One method to rule them all:
        1. Validate DDL
        2. Generate master query (single LLM call)
        3. Create dashboard HTML
        4. Generate execution script
        5. Return everything
        """
        try:
            # Simple input validation
            if len(request.ddl) > 100000:
                raise ValueError(f"DDL too large: {len(request.ddl)} chars (max 100000)")
            
            if not request.intents:
                request.intents = ["General overview", "Key metrics", "Trends"]
            
            print(f"📋 Processing DDL with {len(request.intents)} intents...")
            
            # 1. Parse DDL to validate syntax
            tables = self._parse_ddl(request.ddl)
            print(f"✅ Found {len(tables)} tables")
            
            # 2. Generate master query (ONE LLM call)
            print("🤖 Generating master query...")
            master_query = self.llm.generate_master_query(
                ddl=request.ddl,
                intents=request.intents,
                database=request.database
            )
            
            # 3. Generate dashboard HTML
            print("📊 Creating dashboard template...")
            dashboard_html = generate_dashboard_html(
                title=f"Dashboard: {', '.join(request.intents[:2])}",
                theme="light"
            )
            
            # 4. Create execution script
            execution_script = self._create_execution_script(
                query=master_query,
                database=request.database
            )
            
            # 5. Simple instructions
            instructions = f"""
✅ Generation Complete!

1. Save these files:
   - query.sql (the master query)
   - dashboard.html (the dashboard)
   - execute.sh (execution helper)

2. Execute the query:
   {self._get_execution_command(request.database)}

3. Save results as 'data.json' in the same directory as dashboard.html

4. Open dashboard.html in your browser

The dashboard will automatically load data.json and create visualizations!
"""
            
            return GenerateResponse(
                query=master_query,
                dashboard_html=dashboard_html,
                execution_script=execution_script,
                instructions=instructions
            )
            
        except Exception as e:
            print(f"❌ Error: {e}")
            # Return a minimal valid response even on error
            return GenerateResponse(
                query="SELECT 'Error occurred' as message;",
                dashboard_html=generate_dashboard_html(title="Error"),
                execution_script="echo 'Error occurred'",
                instructions=f"Error: {str(e)}"
            )
    
    def _parse_ddl(self, ddl: str) -> List[str]:
        """Parse DDL and extract table names for validation."""
        tables = []
        try:
            # Use sqlglot for parsing
            statements = sqlglot.parse(ddl)
            for statement in statements:
                # Check if it's a CREATE TABLE statement
                if statement and hasattr(statement, 'kind') and statement.kind == 'TABLE':
                    # Extract table name
                    if hasattr(statement, 'this') and hasattr(statement.this, 'name'):
                        tables.append(statement.this.name)
                elif statement and str(statement).upper().startswith('CREATE TABLE'):
                    # Alternative extraction for different sqlglot versions
                    try:
                        # Try to find table name in the SQL text
                        sql_text = str(statement)
                        import re
                        match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"\']?)(\w+)\1', sql_text, re.IGNORECASE)
                        if match:
                            tables.append(match.group(2))
                    except:
                        pass
        except Exception as e:
            print(f"⚠️ DDL parsing warning: {e}")
            # Fallback to regex - this is actually quite reliable
            pass
        
        # Always use regex as backup/primary method since it's reliable
        if not tables:
            import re
            pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"\']?)(\w+)\1'
            matches = re.finditer(pattern, ddl, re.IGNORECASE)
            for match in matches:
                table_name = match.group(2)
                if table_name not in tables:
                    tables.append(table_name)
        
        return tables
    
    def _create_execution_script(self, query: str, database: str) -> str:
        """Create a shell script to execute the query."""
        if database == "sqlite":
            return f"""#!/bin/bash
# SQLite execution
sqlite3 your_database.db <<EOF
.mode json
.output data.json
{query}
EOF
echo "✅ Query executed, results saved to data.json"
"""
        elif database == "postgres":
            return f"""#!/bin/bash
# PostgreSQL execution
psql -h localhost -U your_user -d your_database -c "
COPY (
{query}
) TO STDOUT WITH (FORMAT CSV, HEADER)
" | python3 -c "
import sys, csv, json
reader = csv.DictReader(sys.stdin)
data = list(reader)
print(json.dumps({{'data': data}}, indent=2))
" > data.json
echo "✅ Query executed, results saved to data.json"
"""
        elif database == "mysql":
            return f"""#!/bin/bash
# MySQL execution
mysql -h localhost -u your_user -p your_database -e "{query}" --batch --raw | python3 -c "
import sys, json
lines = sys.stdin.readlines()
if len(lines) > 1:
    headers = lines[0].strip().split('\\t')
    data = []
    for line in lines[1:]:
        values = line.strip().split('\\t')
        data.append(dict(zip(headers, values)))
    print(json.dumps({{'data': data}}, indent=2))
" > data.json
echo "✅ Query executed, results saved to data.json"
"""
        else:
            return f"""#!/bin/bash
# Generic execution - adapt for your database
# Execute: {query}
# Save results as data.json
echo "Please execute the query and save results as data.json"
"""
    
    def _get_execution_command(self, database: str) -> str:
        """Get the appropriate execution command for the database."""
        commands = {
            "sqlite": "sqlite3 your_db.db < query.sql > data.json",
            "postgres": "psql -d your_db -f query.sql -o data.json",
            "mysql": "mysql your_db < query.sql > data.json"
        }
        return commands.get(database, "Execute query.sql and save as data.json")


# Standalone function for easy testing
def generate_from_file(ddl_file: str, intents: List[str], output_dir: str = "./output"):
    """
    Convenience function to generate everything from a DDL file.
    
    Usage:
        generate_from_file("schema.sql", ["sales analytics", "customer insights"])
    """
    # Read DDL
    with open(ddl_file, 'r') as f:
        ddl = f.read()
    
    # Create server and generate
    server = SqlToDashboardServer()
    request = GenerateRequest(ddl=ddl, intents=intents)
    response = server.generate_all(request)
    
    # Save files
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    with open(output_path / "query.sql", 'w') as f:
        f.write(response.query)
    
    with open(output_path / "dashboard.html", 'w') as f:
        f.write(response.dashboard_html)
    
    with open(output_path / "execute.sh", 'w') as f:
        f.write(response.execution_script)
    
    print(f"\n📁 Files saved to: {output_path}")
    print(response.instructions)
    
    return response


# Quick test
if __name__ == "__main__":
    test_ddl = """
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100),
        country VARCHAR(50)
    );
    
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        amount DECIMAL(10,2),
        order_date DATE,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );
    """
    
    server = SqlToDashboardServer()
    request = GenerateRequest(
        ddl=test_ddl,
        intents=["Customer order analysis", "Revenue trends"],
        database="sqlite"
    )
    
    response = server.generate_all(request)
    
    print("\n📋 Generated Query:")
    print(response.query[:200] + "..." if len(response.query) > 200 else response.query)
    print("\n✅ Dashboard HTML generated")
    print("\n📝 Instructions:")
    print(response.instructions)