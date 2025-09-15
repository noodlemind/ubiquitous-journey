"""SQL Intelligence Agent using LLM for smart query generation and analysis."""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from .ollama_connector import OllamaConnector, QueryIntent


@dataclass
class QueryPlan:
    """Represents a planned SQL query with metadata."""
    query: str
    description: str
    intent: QueryIntent
    visualization_type: str
    confidence: float
    explanation: str
    tables_used: List[str]
    expected_columns: List[str]
    result_key: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SQLIntelligenceAgent:
    """
    Agent that uses LLM to provide intelligent SQL capabilities:
    - Natural language to SQL conversion
    - Schema understanding and analysis
    - Query optimization suggestions
    - Visualization recommendations
    """
    
    def __init__(self, llm_model: str = "llama3", ollama_url: str = "http://localhost:11434"):
        """
        Initialize SQL Intelligence Agent.
        
        Args:
            llm_model: Ollama model to use
            ollama_url: Ollama API URL
        """
        self.llm = OllamaConnector(model=llm_model, base_url=ollama_url)
        self.schema_cache = {}
        self.query_history = []
    
    def analyze_business_context(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze schema to understand business context and opportunities.
        
        Args:
            schema: Database schema information
            
        Returns:
            Business analysis with insights and recommendations
        """
        print("🧠 [Agent] Analyzing business context...")
        
        # Use LLM to analyze schema
        analysis = self.llm.analyze_schema(schema)
        
        # Cache schema for future use
        schema_hash = self._hash_schema(schema)
        self.schema_cache[schema_hash] = {
            "schema": schema,
            "analysis": analysis
        }
        
        # Enhance with specific recommendations
        if analysis.get("business_domain"):
            analysis["recommended_dashboards"] = self._get_dashboard_recommendations(
                analysis["business_domain"],
                analysis.get("key_entities", [])
            )
        
        return analysis
    
    def generate_query_from_intent(self, 
                                  user_intent: str, 
                                  schema: Dict[str, Any],
                                  database_type: str = "sqlite") -> QueryPlan:
        """
        Generate SQL query from natural language intent.
        
        Args:
            user_intent: Natural language description
            schema: Database schema
            database_type: Target database type
            
        Returns:
            QueryPlan with generated query and metadata
        """
        print(f"🤖 [Agent] Generating query for: {user_intent}")
        
        # Generate SQL using LLM
        result = self.llm.generate_sql_query(user_intent, schema, database_type)
        
        if "error" in result:
            print(f"❌ [Agent] Error generating query: {result['error']}")
            return self._create_fallback_query(user_intent, schema)
        
        # Get explanation
        explanation = self.llm.explain_query(result.get("query", ""))
        
        # Create query plan
        query_plan = QueryPlan(
            query=result.get("query", ""),
            description=result.get("description", user_intent),
            intent=self._map_intent_type(result.get("intent_type", "overview")),
            visualization_type=result.get("visualization_hint", "table"),
            confidence=0.8 if "query" in result else 0.3,
            explanation=explanation,
            tables_used=result.get("tables_used", []),
            expected_columns=result.get("expected_columns", [])
        )
        
        # Store in history
        self.query_history.append({
            "intent": user_intent,
            "query": query_plan.query,
            "timestamp": self._get_timestamp()
        })
        
        return query_plan
    
    def suggest_queries_for_schema(self, 
                                  schema: Dict[str, Any],
                                  visualization_intents: Optional[List[str]] = None) -> List[QueryPlan]:
        """
        Generate a single comprehensive query for D3.js dashboard.
        
        Args:
            schema: Database schema
            visualization_intents: Types of visualizations desired
            
        Returns:
            List with master query plan (and optionally focused queries)
        """
        print("💡 [Agent] Generating comprehensive master query for D3.js visualizations...")
        
        # First analyze the schema
        analysis = self.analyze_business_context(schema)
        
        # Generate the master query that joins all relevant tables
        master_query = self._generate_master_query(schema, analysis, visualization_intents)
        
        # Return the master query (D3 will handle all transformations)
        return [master_query]
    
    def optimize_query(self, query: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze and optimize an existing SQL query.
        
        Args:
            query: SQL query to optimize
            schema: Database schema
            
        Returns:
            Optimization suggestions and improved query
        """
        prompt = f"""You are a SQL optimization expert. Analyze this query and suggest improvements.

SCHEMA:
{self.llm._format_schema_for_llm(schema)}

QUERY:
{query}

Provide optimization suggestions in JSON format:
{{
    "optimized_query": "improved SQL query",
    "improvements": ["list of improvements made"],
    "performance_tips": ["performance considerations"],
    "indexes_suggested": ["suggested indexes if applicable"]
}}

Optimize the query:"""
        
        response = self.llm.generate(prompt, temperature=0.3)
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        
        return {
            "optimized_query": query,
            "improvements": [],
            "performance_tips": ["Consider adding appropriate indexes"],
            "indexes_suggested": []
        }
    
    def recommend_visualization_for_data(self, 
                                        data_sample: List[Dict],
                                        query_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Recommend best visualization for query results.
        
        Args:
            data_sample: Sample of query results
            query_metadata: Optional metadata about the query
            
        Returns:
            Visualization recommendations
        """
        print("📊 [Agent] Analyzing data for visualization recommendations...")
        
        if not query_metadata:
            query_metadata = {}
        
        # Use LLM to recommend visualization
        recommendation = self.llm.recommend_visualization(data_sample, query_metadata)
        
        # Enhance with specific configuration
        if recommendation.get("primary"):
            recommendation["config"] = self._get_chart_config(
                recommendation["primary"],
                data_sample,
                recommendation
            )
        
        return recommendation
    
    def explain_data_insights(self, data: List[Dict], query: str) -> str:
        """
        Generate natural language insights from query results.
        
        Args:
            data: Query results
            query: Original SQL query
            
        Returns:
            Natural language insights
        """
        if not data:
            return "No data available for analysis."
        
        # Prepare data summary
        summary = {
            "row_count": len(data),
            "columns": list(data[0].keys()) if data else [],
            "sample": data[:3]
        }
        
        prompt = f"""Analyze this data and provide key business insights.

QUERY:
{query}

DATA SUMMARY:
{json.dumps(summary, indent=2)}

Provide 2-3 key insights in plain language that a business user would find valuable:"""
        
        response = self.llm.generate(prompt, temperature=0.5)
        
        if response.startswith("Error:"):
            return f"The query returned {len(data)} results."
        
        return response
    
    def _generate_overview_queries(self, schema: Dict, analysis: Dict) -> List[QueryPlan]:
        """Generate overview queries for the schema."""
        queries = []
        
        # Find main fact table (usually has most foreign keys)
        main_table = self._find_main_fact_table(schema)
        if main_table:
            intent = f"Show overview statistics for {main_table['name']}"
            queries.append(self.generate_query_from_intent(intent, schema))
        
        return queries
    
    def _generate_distribution_queries(self, schema: Dict, analysis: Dict) -> List[QueryPlan]:
        """Generate distribution analysis queries."""
        queries = []
        
        # Look for categorical columns
        for table in schema.get("tables", []):
            categorical_cols = [
                col for col in table.get("columns", [])
                if "varchar" in col.get("type", "").lower() or "text" in col.get("type", "").lower()
            ]
            
            if categorical_cols and len(categorical_cols) > 0:
                col = categorical_cols[0]
                intent = f"Show distribution of {col['name']} in {table['name']}"
                queries.append(self.generate_query_from_intent(intent, schema))
                break
        
        return queries
    
    def _generate_time_series_queries(self, schema: Dict, analysis: Dict) -> List[QueryPlan]:
        """Generate time series queries."""
        queries = []
        
        # Look for date/time columns
        for table in schema.get("tables", []):
            time_cols = [
                col for col in table.get("columns", [])
                if any(t in col.get("type", "").lower() for t in ["date", "time", "timestamp"])
            ]
            
            if time_cols:
                col = time_cols[0]
                intent = f"Show trends over time using {col['name']} from {table['name']}"
                queries.append(self.generate_query_from_intent(intent, schema))
                break
        
        return queries
    
    def _generate_relationship_queries(self, schema: Dict, analysis: Dict) -> List[QueryPlan]:
        """Generate relationship analysis queries."""
        queries = []
        
        relationships = schema.get("relationships", [])
        if relationships:
            rel = relationships[0]
            intent = f"Analyze relationship between {rel['from_table']} and {rel['to_table']}"
            queries.append(self.generate_query_from_intent(intent, schema))
        
        return queries
    
    def _find_main_fact_table(self, schema: Dict) -> Optional[Dict]:
        """Find the main fact table (usually has most foreign keys)."""
        tables = schema.get("tables", [])
        if not tables:
            return None
        
        # Count foreign keys per table
        fk_counts = {}
        for table in tables:
            fk_count = sum(1 for col in table.get("columns", []) if col.get("foreign_key"))
            fk_counts[table["name"]] = fk_count
        
        # Return table with most foreign keys
        if fk_counts:
            main_table_name = max(fk_counts, key=fk_counts.get)
            return next((t for t in tables if t["name"] == main_table_name), None)
        
        return tables[0] if tables else None
    
    def _generate_master_query(self, schema: Dict, analysis: Dict, 
                              visualization_intents: Optional[List[str]] = None) -> QueryPlan:
        """
        Generate a single comprehensive query that returns all data needed for D3 visualizations.
        D3 will handle grouping, filtering, and aggregations on the client side.
        """
        print("🎯 [Agent] Creating comprehensive master query for D3.js...")
        
        # Build the master query intent
        tables = schema.get("tables", [])
        relationships = schema.get("relationships", [])
        
        if not tables:
            return self._create_fallback_query("No tables found", schema)
        
        # Construct the intent for a comprehensive data query
        intent = f"""
        Generate a single comprehensive SQL query that:
        1. JOINs all related tables based on foreign key relationships
        2. Returns ALL columns from ALL tables (using table aliases to avoid conflicts)
        3. Includes all date/time columns for time-series analysis
        4. Includes all categorical columns for grouping/filtering
        5. Includes all numeric columns for aggregations
        6. Does NOT perform any aggregations (D3.js will handle that)
        7. Returns raw, denormalized data that D3 can transform as needed
        8. Limits results to a reasonable amount (e.g., 10000 rows) for performance
        
        The dashboard will use D3.js to:
        - Group data dynamically
        - Calculate aggregations on the fly
        - Filter based on user interactions
        - Create multiple visualizations from this single dataset
        
        Schema has {len(tables)} tables with {len(relationships)} relationships.
        Business domain: {analysis.get('business_domain', 'general')}
        Key entities: {', '.join(analysis.get('key_entities', []))}
        """
        
        # Add specific requirements based on visualization intents
        if visualization_intents:
            intent += f"\nVisualization requirements: {', '.join(visualization_intents)}"
        
        # Generate the master query using LLM
        query_plan = self.generate_query_from_intent(intent, schema)
        
        # Update metadata for master query
        query_plan.description = "Comprehensive dataset for D3.js dashboard (all tables joined)"
        query_plan.visualization_type = "d3-multi"  # Special type for D3 multi-visualization
        query_plan.metadata = {
            "type": "master_query",
            "purpose": "D3.js dashboard data source",
            "processing": "client-side",
            "tables_included": len(tables),
            "relationships_used": len(relationships),
            "visualization_intents": visualization_intents or ["overview", "distribution", "time_series"],
            "note": "D3.js will handle all aggregations and transformations"
        }
        
        # Ensure we have a result key for the data
        query_plan.result_key = "master_dataset"
        
        return query_plan
    
    def _get_dashboard_recommendations(self, domain: str, entities: List[str]) -> List[str]:
        """Get dashboard recommendations based on business domain."""
        recommendations = {
            "e-commerce": [
                "Sales Performance Dashboard",
                "Customer Analytics Dashboard",
                "Product Performance Dashboard",
                "Order Fulfillment Dashboard"
            ],
            "finance": [
                "Financial Overview Dashboard",
                "Transaction Analysis Dashboard",
                "Risk Analytics Dashboard",
                "Portfolio Performance Dashboard"
            ],
            "healthcare": [
                "Patient Analytics Dashboard",
                "Clinical Operations Dashboard",
                "Resource Utilization Dashboard",
                "Quality Metrics Dashboard"
            ],
            "manufacturing": [
                "Production Overview Dashboard",
                "Quality Control Dashboard",
                "Supply Chain Dashboard",
                "Equipment Performance Dashboard"
            ]
        }
        
        return recommendations.get(domain.lower(), [
            "Overview Dashboard",
            "Analytics Dashboard",
            "Performance Dashboard",
            "Insights Dashboard"
        ])
    
    def _get_chart_config(self, chart_type: str, data: List[Dict], recommendation: Dict) -> Dict:
        """Get specific chart configuration."""
        config = {
            "type": chart_type,
            "responsive": True
        }
        
        if recommendation.get("x_axis"):
            config["x_column"] = recommendation["x_axis"]
        if recommendation.get("y_axis"):
            config["y_column"] = recommendation["y_axis"]
        if recommendation.get("grouping"):
            config["group_by"] = recommendation["grouping"]
        if recommendation.get("title_suggestion"):
            config["title"] = recommendation["title_suggestion"]
        
        # Set appropriate dimensions
        if chart_type == "pie":
            config["width"] = 450
            config["height"] = 400
        elif chart_type in ["line", "bar", "scatter"]:
            config["width"] = 700
            config["height"] = 400
        else:
            config["width"] = 800
            config["height"] = 500
        
        return config
    
    def _map_intent_type(self, intent_str: str) -> QueryIntent:
        """Map string intent to QueryIntent enum."""
        mapping = {
            "overview": QueryIntent.OVERVIEW,
            "aggregation": QueryIntent.AGGREGATION,
            "distribution": QueryIntent.DISTRIBUTION,
            "relationship": QueryIntent.RELATIONSHIP,
            "time_series": QueryIntent.TIME_SERIES,
            "comparison": QueryIntent.COMPARISON,
            "ranking": QueryIntent.RANKING,
            "detail": QueryIntent.DETAIL
        }
        return mapping.get(intent_str.lower(), QueryIntent.OVERVIEW)
    
    def _create_fallback_query(self, intent: str, schema: Dict) -> QueryPlan:
        """Create a simple fallback query."""
        tables = schema.get("tables", [])
        if not tables:
            return QueryPlan(
                query="SELECT 1;",
                description="Fallback query",
                intent=QueryIntent.OVERVIEW,
                visualization_type="table",
                confidence=0.1,
                explanation="Could not generate query",
                tables_used=[],
                expected_columns=[]
            )
        
        table = tables[0]
        query = f"SELECT * FROM {table['name']} LIMIT 10;"
        
        return QueryPlan(
            query=query,
            description=f"Sample data from {table['name']}",
            intent=QueryIntent.OVERVIEW,
            visualization_type="table",
            confidence=0.3,
            explanation=f"Shows first 10 rows from {table['name']}",
            tables_used=[table['name']],
            expected_columns=[col['name'] for col in table.get('columns', [])]
        )
    
    def _hash_schema(self, schema: Dict) -> str:
        """Create a hash of the schema for caching."""
        import hashlib
        schema_str = json.dumps(schema, sort_keys=True)
        return hashlib.md5(schema_str.encode()).hexdigest()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
