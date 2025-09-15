"""Enhanced DDL Parser MCP Server with LLM integration."""

import json
from typing import Optional, Dict, Any, List
import sys
from pathlib import Path
import os

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

# Import LLM components if available
try:
    from llm.sql_intelligence import SQLIntelligenceAgent
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("⚠️ LLM module not available. Running without AI enhancements.")


class EnhancedDDLParserMCPServer:
    """Enhanced MCP Server for DDL parsing with LLM intelligence."""
    
    def __init__(self, use_llm: bool = True, llm_model: str = "llama3"):
        """
        Initialize the Enhanced DDL Parser MCP Server.
        
        Args:
            use_llm: Whether to use LLM for enhanced capabilities
            llm_model: Which Ollama model to use
        """
        self.max_input_size = 100000  # 100KB limit
        
        # Initialize LLM agent if available and requested
        self.llm_agent = None
        self.use_llm = use_llm and LLM_AVAILABLE
        
        if self.use_llm:
            try:
                # Check if Ollama is running
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    self.llm_agent = SQLIntelligenceAgent(llm_model=llm_model)
                    print(f"✨ LLM agent initialized with model: {llm_model}")
                else:
                    print("⚠️ Ollama is not responding. Running without LLM.")
                    self.use_llm = False
            except Exception as e:
                print(f"⚠️ Could not initialize LLM agent: {e}")
                self.use_llm = False
        
    def handle_request(self, request: DDLParserRequest) -> DDLParserResponse:
        """
        Handle DDL parser request with optional LLM enhancement.
        
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
        """Handle DDL input parsing with LLM enhancement."""
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
        if self.use_llm and self.llm_agent:
            # Use LLM for intelligent query generation
            print("🤖 Using LLM for intelligent query generation...")
            
            # Convert schema to dict format for LLM
            schema_dict = self._schema_to_dict(schema)
            
            # Get business analysis
            analysis = self.llm_agent.analyze_business_context(schema_dict)
            
            # Get LLM-powered suggestions
            query_plans = self.llm_agent.suggest_queries_for_schema(
                schema_dict,
                visualization_intents=request.visualization_intents
            )
            
            # Convert QueryPlans to QuerySuggestions
            suggestions = []
            for plan in query_plans:
                suggestions.append(QuerySuggestion(
                    query=plan.query,
                    description=plan.description,
                    visualization_type=plan.visualization_type,
                    expected_columns=plan.expected_columns,
                    tables_used=plan.tables_used,
                    metadata={
                        "llm_generated": True,
                        "confidence": plan.confidence,
                        "explanation": plan.explanation,
                        "intent": plan.intent.value
                    }
                ))
            
            # Create enhanced metadata
            metadata = {
                "table_count": len(schema.tables),
                "relationship_count": len(schema.relationships),
                "query_count": len(suggestions),
                "llm_enhanced": True,
                "business_analysis": analysis
            }
        else:
            # Fallback to rule-based query generation
            generator = SQLGenerator(schema)
            suggestions = generator.generate_suggestions(request.visualization_intents)
            
            metadata = {
                "table_count": len(schema.tables),
                "relationship_count": len(schema.relationships),
                "query_count": len(suggestions),
                "llm_enhanced": False
            }
        
        # Extract SQL statements
        sql_statements = [suggestion.query for suggestion in suggestions]
        
        # Create instructions
        instructions = self._create_user_instructions(schema, suggestions, metadata)
        
        return DDLParserResponse(
            status="success",
            schema=schema,
            suggested_queries=suggestions,
            sql_statements=sql_statements,
            instructions=instructions,
            metadata=metadata
        )
    
    def _handle_mermaid_input(self, request: DDLParserRequest) -> DDLParserResponse:
        """Handle Mermaid ER diagram input."""
        # For now, return a placeholder
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
    
    def _create_user_instructions(self, schema, suggestions: List[QuerySuggestion], 
                                 metadata: Dict[str, Any]) -> str:
        """Create clear instructions for the user."""
        llm_note = ""
        if metadata.get("llm_enhanced"):
            llm_note = "\n🤖 AI-Powered: Queries generated using LLM for better business insights!\n"
            
            # Add business analysis if available
            if metadata.get("business_analysis"):
                analysis = metadata["business_analysis"]
                if analysis.get("business_domain"):
                    llm_note += f"📈 Detected Business Domain: {analysis['business_domain']}\n"
                if analysis.get("key_entities"):
                    llm_note += f"🔑 Key Entities: {', '.join(analysis['key_entities'])}\n"
        
        instructions = f"""
📊 Schema Analysis Complete!
{llm_note}
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
                confidence = ""
                if suggestion.metadata and suggestion.metadata.get("confidence"):
                    conf_val = suggestion.metadata["confidence"]
                    if conf_val >= 0.8:
                        confidence = " ⭐"
                    elif conf_val >= 0.6:
                        confidence = " ✓"
                instructions += f"  {i}. {query.description}{confidence}\n"
                
                # Add explanation if available
                if suggestion.metadata and suggestion.metadata.get("explanation"):
                    instructions += f"     💡 {suggestion.metadata['explanation'][:100]}...\n"
        
        # Add insights if LLM was used
        if metadata.get("business_analysis") and metadata["business_analysis"].get("insights"):
            instructions += "\n🎯 Business Insights:\n"
            for insight in metadata["business_analysis"]["insights"][:3]:
                instructions += f"  • {insight}\n"
        
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
    
    def generate_natural_language_query(self, user_request: str, 
                                       schema: Any) -> QuerySuggestion:
        """
        Generate SQL from natural language request.
        
        Args:
            user_request: Natural language query request
            schema: Database schema
            
        Returns:
            QuerySuggestion with generated SQL
        """
        if not self.use_llm or not self.llm_agent:
            return QuerySuggestion(
                query="-- LLM not available for natural language processing",
                description="Please enable LLM for natural language queries",
                visualization_type="table"
            )
        
        schema_dict = self._schema_to_dict(schema)
        query_plan = self.llm_agent.generate_query_from_intent(
            user_request, 
            schema_dict
        )
        
        return QuerySuggestion(
            query=query_plan.query,
            description=query_plan.description,
            visualization_type=query_plan.visualization_type,
            expected_columns=query_plan.expected_columns,
            tables_used=query_plan.tables_used,
            metadata={
                "llm_generated": True,
                "confidence": query_plan.confidence,
                "explanation": query_plan.explanation,
                "user_request": user_request
            }
        )
    
    def _schema_to_dict(self, schema) -> Dict[str, Any]:
        """Convert Schema object to dictionary for LLM processing."""
        return {
            "tables": [
                {
                    "name": table.name,
                    "columns": [
                        {
                            "name": col.name,
                            "type": col.data_type,  # Fixed: use data_type instead of type
                            "nullable": col.is_nullable,  # Fixed: use is_nullable
                            "primary_key": col.is_primary_key,  # Fixed: use is_primary_key
                            "foreign_key": col.is_foreign_key,  # Fixed: use is_foreign_key
                            "unique": getattr(col, 'is_unique', False),  # Safe access
                            "default": col.default_value  # Fixed: use default_value
                        }
                        for col in table.columns
                    ],
                    "primary_keys": table.primary_keys,
                    "foreign_keys": table.foreign_keys,
                    "indexes": table.indexes
                }
                for table in schema.tables
            ],
            "relationships": [
                {
                    "from_table": rel.from_table,
                    "from_column": rel.from_column,
                    "to_table": rel.to_table,
                    "to_column": rel.to_column,
                    "relationship_type": rel.type.value  # Fixed: use type.value
                }
                for rel in schema.relationships
            ]
        }


# Example usage
if __name__ == "__main__":
    # Try with LLM if available
    server = EnhancedDDLParserMCPServer(use_llm=True)
    
    # Example DDL input
    example_ddl = """
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE,
        country VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        category VARCHAR(50),
        price DECIMAL(10,2),
        stock_quantity INTEGER DEFAULT 0
    );
    
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount DECIMAL(10,2),
        status VARCHAR(20) DEFAULT 'pending',
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );
    
    CREATE TABLE order_items (
        id INTEGER PRIMARY KEY,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price DECIMAL(10,2),
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """
    
    request = DDLParserRequest(
        task="parse_schema",
        input=example_ddl,
        format=InputFormat.DDL,
        database_type="sqlite",
        visualization_intents=["overview", "distribution", "time_series", "relationship"]
    )
    
    response = server.handle_request(request)
    
    if response.status == "success":
        print("✅ Schema parsed successfully!")
        print(f"📊 Tables: {response.metadata.get('table_count', 0)}")
        print(f"🔗 Relationships: {response.metadata.get('relationship_count', 0)}")
        print(f"🤖 LLM Enhanced: {response.metadata.get('llm_enhanced', False)}")
        
        if response.metadata.get('business_analysis'):
            analysis = response.metadata['business_analysis']
            print(f"\n📈 Business Domain: {analysis.get('business_domain', 'Unknown')}")
            print(f"🔑 Key Entities: {', '.join(analysis.get('key_entities', []))}")
        
        print("\n📝 Generated Queries:")
        for i, query in enumerate(response.suggested_queries[:3], 1):
            print(f"\n{i}. {query.description}")
            if query.metadata and query.metadata.get('confidence'):
                print(f"   Confidence: {query.metadata['confidence']:.0%}")
            print(f"   SQL: {query.query[:100]}...")
    else:
        print(f"❌ Error: {response.error}")