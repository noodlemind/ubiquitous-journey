"""Simplified LLM-powered DDL Parser MCP Server."""

import json
from typing import Dict, Any, List, Optional
import sys
from pathlib import Path
import requests

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ddl_parser_mcp.schema import (
    DDLParserRequest, 
    DDLParserResponse, 
    InputFormat,
    QuerySuggestion,
    DatabaseSchema
)
from ddl_parser_mcp.parser.ddl_parser import DDLParser
from shared.validators import validate_input_size, validate_ddl_safety
from shared.errors import ParsingError, ValidationError
from llm.sql_intelligence import SQLIntelligenceAgent


class DDLParserMCPServer:
    """Simplified MCP Server for DDL parsing with mandatory LLM intelligence."""
    
    def __init__(self, llm_model: str = "llama3"):
        """
        Initialize the DDL Parser MCP Server with LLM.
        
        Args:
            llm_model: Which Ollama model to use (default: llama3)
        """
        self.max_input_size = 100000  # 100KB limit
        self.llm_model = llm_model
        
        # Check if Ollama is running and initialize LLM agent
        if not self._check_ollama():
            raise RuntimeError(
                "Ollama is not running. Please start it with:\n"
                "  ollama serve\n"
                "  ollama pull llama3"
            )
        
        # Initialize LLM agent (required)
        self.llm_agent = SQLIntelligenceAgent(llm_model=llm_model)
        print(f"✨ LLM agent initialized with model: {llm_model}")
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def handle_request(self, request: DDLParserRequest) -> DDLParserResponse:
        """
        Handle DDL parser request with LLM intelligence.
        
        Args:
            request: DDLParserRequest object
            
        Returns:
            DDLParserResponse object with LLM-generated queries
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
        """Handle DDL input parsing with LLM intelligence."""
        # Validate DDL safety
        validate_ddl_safety(request.input)
        
        # Parse DDL using sqlglot
        parser = DDLParser(dialect=request.database_type or "sqlite")
        schema = parser.parse(request.input)
        
        if not schema.tables:
            return DDLParserResponse(
                status="error",
                error="No tables found in DDL"
            )
        
        print("🤖 Analyzing schema with LLM...")
        
        # Convert schema to dict format for LLM
        schema_dict = self._schema_to_dict(schema)
        
        # Get business analysis from LLM
        analysis = self.llm_agent.analyze_business_context(schema_dict)
        
        # Get LLM-powered query suggestions
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
                    "confidence": plan.confidence,
                    "explanation": plan.explanation,
                    "intent": plan.intent.value
                }
            ))
        
        # Extract SQL statements for convenience
        sql_statements = [suggestion.query for suggestion in suggestions]
        
        # Create metadata with business analysis
        metadata = {
            "table_count": len(schema.tables),
            "relationship_count": len(schema.relationships),
            "query_count": len(suggestions),
            "business_analysis": analysis,
            "llm_model": self.llm_model
        }
        
        # Create user instructions
        instructions = self._create_user_instructions(schema, suggestions, analysis)
        
        return DDLParserResponse(
            status="success",
            schema=schema,
            suggested_queries=suggestions,
            sql_statements=sql_statements,
            instructions=instructions,
            metadata=metadata
        )
    
    def _handle_mermaid_input(self, request: DDLParserRequest) -> DDLParserResponse:
        """Handle Mermaid ER diagram input (future implementation)."""
        # For now, convert Mermaid to DDL using LLM
        prompt = f"""Convert this Mermaid ER diagram to SQL DDL statements:

{request.input}

Return only the CREATE TABLE statements in standard SQL format."""
        
        try:
            # Use LLM to convert Mermaid to DDL
            from llm.ollama_connector import OllamaConnector
            connector = OllamaConnector(model=self.llm_model)
            ddl_result = connector.generate(prompt, temperature=0.2)
            
            if ddl_result.startswith("Error:"):
                return DDLParserResponse(
                    status="error",
                    error="Could not convert Mermaid diagram to DDL",
                    metadata={"llm_response": ddl_result}
                )
            
            # Now process the generated DDL
            request.input = ddl_result
            request.format = InputFormat.DDL
            return self._handle_ddl_input(request)
            
        except Exception as e:
            return DDLParserResponse(
                status="error",
                error=f"Mermaid conversion failed: {str(e)}"
            )
    
    def generate_natural_language_query(self, user_request: str, schema: DatabaseSchema) -> QuerySuggestion:
        """
        Generate SQL from natural language request.
        
        Args:
            user_request: Natural language query request
            schema: Database schema
            
        Returns:
            QuerySuggestion with generated SQL
        """
        schema_dict = self._schema_to_dict(schema)
        query_plan = self.llm_agent.generate_query_from_intent(user_request, schema_dict)
        
        return QuerySuggestion(
            query=query_plan.query,
            description=query_plan.description,
            visualization_type=query_plan.visualization_type,
            expected_columns=query_plan.expected_columns,
            tables_used=query_plan.tables_used,
            metadata={
                "confidence": query_plan.confidence,
                "explanation": query_plan.explanation,
                "user_request": user_request
            }
        )
    
    def _create_user_instructions(self, schema: DatabaseSchema, 
                                 suggestions: List[QuerySuggestion], 
                                 analysis: Dict[str, Any]) -> str:
        """Create intelligent user instructions based on LLM analysis."""
        
        # Build header with business context
        header = f"""
📊 Schema Analysis Complete!
🤖 Powered by LLM: {self.llm_model}
"""
        
        if analysis.get("business_domain"):
            header += f"📈 Business Domain: {analysis['business_domain']}\n"
        if analysis.get("key_entities"):
            header += f"🔑 Key Entities: {', '.join(analysis['key_entities'])}\n"
        
        header += f"""
Found {len(schema.tables)} table(s) with {len(schema.relationships)} relationship(s).

📝 Next Steps:
1. Review the AI-generated SQL queries below
2. Execute them in your database
3. Save results as JSON
4. Generate dashboard with the Dashboard Generator

🔍 AI-Generated Queries ({len(suggestions)} total):
"""
        
        # Group queries by visualization type
        by_viz_type = {}
        for suggestion in suggestions:
            viz_type = suggestion.visualization_type
            if viz_type not in by_viz_type:
                by_viz_type[viz_type] = []
            by_viz_type[viz_type].append(suggestion)
        
        query_section = ""
        for viz_type, queries in by_viz_type.items():
            query_section += f"\n📊 {viz_type.upper()} Visualizations ({len(queries)} queries):\n"
            for i, query in enumerate(queries[:3], 1):
                confidence = ""
                if query.metadata and query.metadata.get("confidence"):
                    conf_val = query.metadata["confidence"]
                    confidence = f" (Confidence: {conf_val:.0%})"
                query_section += f"  {i}. {query.description}{confidence}\n"
                if query.metadata and query.metadata.get("explanation"):
                    query_section += f"     💡 {query.metadata['explanation'][:80]}...\n"
        
        # Add business insights
        insights_section = ""
        if analysis.get("insights"):
            insights_section = "\n🎯 Business Insights:\n"
            for insight in analysis["insights"][:3]:
                insights_section += f"  • {insight}\n"
        
        # Add recommended dashboards
        dashboard_section = ""
        if analysis.get("recommended_dashboards"):
            dashboard_section = "\n📈 Recommended Dashboards:\n"
            for dashboard in analysis["recommended_dashboards"][:4]:
                dashboard_section += f"  • {dashboard}\n"
        
        footer = """
💡 Pro Tips:
- Use natural language to request specific queries
- The AI understands your business context
- All queries are optimized for your database type
- Save query results as JSON for best compatibility

Ready to create amazing dashboards! 🚀
"""
        
        return header + query_section + insights_section + dashboard_section + footer
    
    def _schema_to_dict(self, schema: DatabaseSchema) -> Dict[str, Any]:
        """Convert Schema object to dictionary for LLM processing."""
        return {
            "tables": [
                {
                    "name": table.name,
                    "columns": [
                        {
                            "name": col.name,
                            "type": col.data_type,
                            "nullable": col.is_nullable,
                            "primary_key": col.is_primary_key,
                            "foreign_key": col.is_foreign_key,
                            "unique": getattr(col, 'is_unique', False),
                            "default": col.default_value
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
                    "relationship_type": rel.type.value
                }
                for rel in schema.relationships
            ]
        }
    
    def process_json_request(self, json_str: str) -> str:
        """
        Process a JSON string request and return JSON response.
        
        Args:
            json_str: JSON string containing request
            
        Returns:
            JSON string containing response
        """
        try:
            request_data = json.loads(json_str)
            request = DDLParserRequest(**request_data)
            response = self.handle_request(request)
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


# Quick test
if __name__ == "__main__":
    try:
        server = DDLParserMCPServer()
        print("✅ Server initialized successfully!")
        
        # Test with sample DDL
        test_ddl = """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title VARCHAR(200),
            content TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """
        
        request = DDLParserRequest(
            task="parse_schema",
            input=test_ddl,
            format=InputFormat.DDL,
            database_type="sqlite",
            visualization_intents=["overview", "distribution"]
        )
        
        response = server.handle_request(request)
        
        if response.status == "success":
            print(f"📊 Tables: {response.metadata.get('table_count', 0)}")
            print(f"🤖 Business Domain: {response.metadata.get('business_analysis', {}).get('business_domain', 'Unknown')}")
            print(f"📝 Generated {len(response.suggested_queries)} queries")
        else:
            print(f"❌ Error: {response.error}")
            
    except RuntimeError as e:
        print(f"❌ {e}")