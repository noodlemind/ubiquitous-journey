"""DDL Parser MCP Server - Parses schemas and generates SQL queries."""

import json
from typing import Optional
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ddl_parser_mcp.schema import (
    DDLParserRequest, 
    DDLParserResponse, 
    InputFormat,
    QuerySuggestion
)
from ddl_parser_mcp.parser.ddl_parser import DDLParser
from ddl_parser_mcp.generator.sql_generator import SQLGenerator
from shared.validators import validate_input_size, validate_ddl_safety
from shared.errors import MCPError, ParsingError, ValidationError


class DDLParserMCPServer:
    """MCP Server for DDL parsing and SQL generation."""
    
    def __init__(self):
        """Initialize the DDL Parser MCP Server."""
        self.max_input_size = 100000  # 100KB limit
        
    def handle_request(self, request: DDLParserRequest) -> DDLParserResponse:
        """
        Handle DDL parser request.
        
        Args:
            request: DDLParserRequest object
            
        Returns:
            DDLParserResponse object
        """
        try:
            # Validate input size
            validate_input_size(request.input, self.max_input_size)
            
            # Parse based on format
            if request.format == InputFormat.DDL:
                return self._handle_ddl_input(request)
            elif request.format == InputFormat.MERMAID:
                return self._handle_mermaid_input(request)
            else:
                return DDLParserResponse(
                    status="error",
                    error=f"Unsupported format: {request.format}"
                )
                
        except ValidationError as e:
            return DDLParserResponse(
                status="error",
                error=f"Validation error: {e.message}",
                metadata={"details": e.details}
            )
        except ParsingError as e:
            return DDLParserResponse(
                status="error",
                error=f"Parsing error: {e.message}",
                metadata={"details": e.details}
            )
        except Exception as e:
            return DDLParserResponse(
                status="error",
                error=f"Server error: {str(e)}"
            )
    
    def _handle_ddl_input(self, request: DDLParserRequest) -> DDLParserResponse:
        """Handle DDL input parsing and SQL generation."""
        # Validate DDL safety
        validate_ddl_safety(request.input)
        
        # Parse DDL
        parser = DDLParser(dialect=request.database_type or "sqlite")
        schema = parser.parse(request.input)
        
        if not schema.tables:
            return DDLParserResponse(
                status="error",
                error="No tables found in DDL"
            )
        
        # Generate SQL suggestions
        generator = SQLGenerator(schema)
        suggestions = generator.generate_suggestions(request.visualization_intents)
        
        # Extract just the SQL statements for easy copying
        sql_statements = [suggestion.query for suggestion in suggestions]
        
        # Create instructions for the user
        instructions = self._create_user_instructions(schema, suggestions)
        
        return DDLParserResponse(
            status="success",
            schema=schema,
            suggested_queries=suggestions,
            sql_statements=sql_statements,
            instructions=instructions,
            metadata={
                "table_count": len(schema.tables),
                "relationship_count": len(schema.relationships),
                "query_count": len(suggestions)
            }
        )
    
    def _handle_mermaid_input(self, request: DDLParserRequest) -> DDLParserResponse:
        """Handle Mermaid ER diagram input."""
        # For now, return a placeholder - full Mermaid parsing to be implemented
        return DDLParserResponse(
            status="success",
            instructions="""
Mermaid ER diagram parsing is coming soon!

For now, please convert your Mermaid diagram to DDL statements manually.
Example Mermaid:
```
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ ORDER_ITEM : contains
```

Equivalent DDL:
```sql
CREATE TABLE customer (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE order (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customer(id)
);

CREATE TABLE order_item (
    id INTEGER PRIMARY KEY,
    order_id INTEGER,
    FOREIGN KEY (order_id) REFERENCES order(id)
);
```
""",
            metadata={"note": "Mermaid parser implementation pending"}
        )
    
    def _create_user_instructions(self, schema, suggestions: list[QuerySuggestion]) -> str:
        """Create clear instructions for the user."""
        instructions = f"""
📊 Schema Analysis Complete!

Found {len(schema.tables)} table(s) with {len(schema.relationships)} relationship(s).

📝 Next Steps:
1. Copy one of the SQL queries below
2. Execute it in your database
3. Save the results as JSON or CSV
4. Use the Dashboard Generator with your data

🔍 Suggested Queries by Visualization Type:
"""
        
        # Group queries by visualization type
        by_viz_type = {}
        for suggestion in suggestions:
            viz_type = suggestion.visualization_type
            if viz_type not in by_viz_type:
                by_viz_type[viz_type] = []
            by_viz_type[viz_type].append(suggestion)
        
        for viz_type, queries in by_viz_type.items():
            instructions += f"\n{viz_type.upper()} Charts ({len(queries)} queries):\n"
            for i, query in enumerate(queries[:3], 1):  # Show first 3 of each type
                instructions += f"  {i}. {query.description}\n"
        
        instructions += """
💡 Tips:
- Start with 'table' visualizations to explore your data
- Use 'bar' charts for categorical distributions
- Use 'line' charts for time series data
- Save query results as JSON for best compatibility

Run queries with your preferred database tool and save the results!
"""
        
        return instructions
    
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
            request = DDLParserRequest(**request_data)
            
            # Handle request
            response = self.handle_request(request)
            
            # Return JSON response
            return response.model_dump_json(indent=2)
            
        except json.JSONDecodeError as e:
            error_response = DDLParserResponse(
                status="error",
                error=f"Invalid JSON: {str(e)}"
            )
            return error_response.model_dump_json(indent=2)
        except Exception as e:
            error_response = DDLParserResponse(
                status="error",
                error=f"Request processing failed: {str(e)}"
            )
            return error_response.model_dump_json(indent=2)


# Example usage
if __name__ == "__main__":
    server = DDLParserMCPServer()
    
    # Example DDL input
    example_ddl = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        title VARCHAR(200),
        content TEXT,
        published_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """
    
    request = DDLParserRequest(
        task="parse_schema",
        input=example_ddl,
        format=InputFormat.DDL,
        database_type="sqlite",
        visualization_intents=["overview", "distributions", "relationships"]
    )
    
    response = server.handle_request(request)
    print(json.dumps(response.model_dump(), indent=2))
