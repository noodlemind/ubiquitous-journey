"""Ollama LLM connector for SQL and Dashboard intelligence."""

import json
import re
import requests
from typing import Dict, Any, Optional, List
from enum import Enum


class QueryIntent(Enum):
    """Types of SQL query intents."""
    OVERVIEW = "overview"
    AGGREGATION = "aggregation"
    DISTRIBUTION = "distribution"
    RELATIONSHIP = "relationship"
    TIME_SERIES = "time_series"
    COMPARISON = "comparison"
    RANKING = "ranking"
    DETAIL = "detail"


class OllamaConnector:
    """Connector for Ollama local LLM with SQL/Dashboard focus."""
    
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama connector.
        
        Args:
            model: Ollama model to use (llama3, codellama, mistral, etc.)
            base_url: Ollama API base URL
        """
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
    
    def generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.3) -> str:
        """
        Generate text using Ollama.
        
        Args:
            prompt: User prompt
            system: System message for context
            temperature: Generation temperature (0.0-1.0)
            
        Returns:
            Generated text response
        """
        if not prompt or not prompt.strip():
            return "Error: Empty prompt provided"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": max(0.0, min(1.0, temperature)),
            "options": {
                "num_predict": 2048,  # Increase for longer SQL queries
                "top_p": 0.9,
                "top_k": 40
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                return f"LLM Error: {result['error']}"
            
            response_text = result.get("response", "").strip()
            if not response_text:
                return "Error: Empty response from LLM"
            
            return response_text
            
        except requests.exceptions.Timeout:
            return "Error: Request to LLM timed out"
        except requests.exceptions.ConnectionError:
            return "Error: Cannot connect to Ollama. Make sure it's running with 'ollama run llama3'"
        except requests.exceptions.RequestException as e:
            return f"Error: Ollama request failed - {str(e)}"
        except json.JSONDecodeError:
            return "Error: Invalid JSON response from Ollama"
        except Exception as e:
            return f"Error: Unexpected error - {str(e)}"
    
    def analyze_schema(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze database schema to understand business context.
        
        Args:
            schema_info: Dictionary containing table and relationship information
            
        Returns:
            Analysis with business insights and query suggestions
        """
        # Format schema for LLM
        schema_text = self._format_schema_for_llm(schema_info)
        
        prompt = f"""You are a database analyst. Analyze this database schema and provide business insights.

SCHEMA:
{schema_text}

Provide analysis in JSON format with these keys:
1. "business_domain": What type of business/domain this database represents
2. "key_entities": Main business entities (e.g., customers, products, orders)
3. "metrics": Potential business metrics that can be calculated
4. "insights": Key insights about the data model
5. "suggested_queries": List of 5 valuable business queries

Example format:
{{
    "business_domain": "e-commerce",
    "key_entities": ["customers", "products", "orders"],
    "metrics": ["revenue", "customer_lifetime_value", "product_performance"],
    "insights": ["The schema supports order tracking", "Customer segmentation is possible"],
    "suggested_queries": ["Top selling products", "Customer purchase patterns"]
}}

Analyze the schema and return ONLY valid JSON:"""
        
        response = self.generate(prompt, temperature=0.3)
        
        # Parse JSON response
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "business_domain": "unknown",
                    "key_entities": [],
                    "metrics": [],
                    "insights": [],
                    "suggested_queries": []
                }
        except json.JSONDecodeError:
            return {
                "business_domain": "unknown",
                "key_entities": [],
                "metrics": [],
                "insights": [],
                "suggested_queries": []
            }
    
    def generate_sql_query(self, user_intent: str, schema_info: Dict[str, Any], 
                          database_type: str = "sqlite") -> Dict[str, Any]:
        """
        Generate SQL query based on user intent and schema.
        
        Args:
            user_intent: Natural language description of what user wants
            schema_info: Database schema information
            database_type: Type of database (sqlite, postgres, mysql)
            
        Returns:
            Dictionary with SQL query and metadata
        """
        schema_text = self._format_schema_for_llm(schema_info)
        
        system_message = f"""You are an expert SQL developer for {database_type} databases.
Generate precise, optimized SQL queries based on user requests.
Follow {database_type} syntax strictly.
Include appropriate JOINs, aggregations, and filters.
Consider performance implications."""
        
        prompt = f"""Given this database schema:
{schema_text}

User Request: "{user_intent}"

Generate a SQL query to fulfill this request.

Return your response in this JSON format:
{{
    "query": "SELECT ...",
    "description": "Brief description of what the query does",
    "intent_type": "overview|aggregation|distribution|relationship|time_series|comparison|ranking|detail",
    "tables_used": ["table1", "table2"],
    "visualization_hint": "bar|line|pie|scatter|table|heatmap",
    "expected_columns": ["column1", "column2"],
    "has_aggregation": true/false,
    "has_time_component": true/false
}}

Generate the SQL query:"""
        
        response = self.generate(prompt, system=system_message, temperature=0.2)
        
        # Parse response
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # Validate and clean SQL
                if "query" in result:
                    result["query"] = self._clean_sql(result["query"])
                return result
            else:
                # Fallback: try to extract SQL directly
                sql_match = re.search(r'(SELECT.*?;)', response, re.IGNORECASE | re.DOTALL)
                if sql_match:
                    return {
                        "query": self._clean_sql(sql_match.group(1)),
                        "description": "Generated query",
                        "intent_type": "overview",
                        "visualization_hint": "table"
                    }
                return {"error": "Could not generate valid SQL"}
        except Exception as e:
            return {"error": f"Failed to parse SQL response: {str(e)}"}
    
    def recommend_visualization(self, data_sample: List[Dict], query_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommend best visualization for given data.
        
        Args:
            data_sample: Sample of query results
            query_metadata: Metadata about the query
            
        Returns:
            Visualization recommendations
        """
        # Prepare data summary
        if not data_sample:
            return {
                "primary": "table",
                "alternatives": [],
                "reason": "No data available"
            }
        
        columns = list(data_sample[0].keys()) if data_sample else []
        row_count = len(data_sample)
        
        # Analyze data types
        data_types = {}
        for col in columns:
            sample_values = [row.get(col) for row in data_sample[:5] if row.get(col) is not None]
            if sample_values:
                if all(isinstance(v, (int, float)) for v in sample_values):
                    data_types[col] = "numeric"
                elif any(d in str(sample_values[0]).lower() for d in ["date", "time", "-", "/"]):
                    data_types[col] = "temporal"
                else:
                    data_types[col] = "categorical"
        
        prompt = f"""You are a data visualization expert. Recommend the best chart type for this data.

DATA CHARACTERISTICS:
- Columns: {columns}
- Data types: {json.dumps(data_types)}
- Row count: {row_count}
- Query type: {query_metadata.get('intent_type', 'unknown')}
- Has aggregation: {query_metadata.get('has_aggregation', False)}
- Has time component: {query_metadata.get('has_time_component', False)}

SAMPLE DATA (first 3 rows):
{json.dumps(data_sample[:3], indent=2)}

Available chart types: bar, line, pie, scatter, table, heatmap

Return JSON with:
{{
    "primary": "best chart type",
    "alternatives": ["other suitable types"],
    "reason": "why this visualization is best",
    "x_axis": "recommended x-axis column",
    "y_axis": "recommended y-axis column",
    "grouping": "optional grouping column",
    "title_suggestion": "suggested chart title"
}}

Recommend visualization:"""
        
        response = self.generate(prompt, temperature=0.3)
        
        # Parse response
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback recommendation
                return self._fallback_visualization_recommendation(data_types, query_metadata)
        except Exception:
            return self._fallback_visualization_recommendation(data_types, query_metadata)
    
    def explain_query(self, sql_query: str) -> str:
        """
        Explain what a SQL query does in plain language.
        
        Args:
            sql_query: SQL query to explain
            
        Returns:
            Plain language explanation
        """
        prompt = f"""Explain this SQL query in simple, non-technical language:

{sql_query}

Provide a brief, clear explanation that a business user would understand:"""
        
        response = self.generate(prompt, temperature=0.3)
        
        if response.startswith("Error:"):
            return "This query retrieves data from the database."
        
        return response
    
    def _format_schema_for_llm(self, schema_info: Dict[str, Any]) -> str:
        """Format schema information for LLM consumption."""
        lines = []
        
        tables = schema_info.get("tables", [])
        for table in tables:
            lines.append(f"Table: {table.get('name', 'unknown')}")
            columns = table.get("columns", [])
            for col in columns:
                col_def = f"  - {col.get('name', 'unknown')}: {col.get('type', 'unknown')}"
                if col.get("primary_key"):
                    col_def += " [PRIMARY KEY]"
                if col.get("foreign_key"):
                    col_def += f" [FK -> {col['foreign_key']}]"
                if col.get("nullable") == False:
                    col_def += " [NOT NULL]"
                lines.append(col_def)
            lines.append("")
        
        relationships = schema_info.get("relationships", [])
        if relationships:
            lines.append("Relationships:")
            for rel in relationships:
                lines.append(f"  - {rel.get('from_table', '?')}.{rel.get('from_column', '?')} -> "
                           f"{rel.get('to_table', '?')}.{rel.get('to_column', '?')}")
        
        return "\n".join(lines)
    
    def _clean_sql(self, sql: str) -> str:
        """Clean and format SQL query."""
        # Remove markdown code blocks if present
        sql = re.sub(r'```sql?\s*', '', sql)
        sql = re.sub(r'```', '', sql)
        
        # Remove extra whitespace
        sql = ' '.join(sql.split())
        
        # Ensure semicolon at end
        sql = sql.rstrip(';') + ';'
        
        return sql
    
    def _fallback_visualization_recommendation(self, data_types: Dict, metadata: Dict) -> Dict[str, Any]:
        """Provide fallback visualization recommendation."""
        # Simple heuristics
        numeric_cols = [col for col, dtype in data_types.items() if dtype == "numeric"]
        temporal_cols = [col for col, dtype in data_types.items() if dtype == "temporal"]
        categorical_cols = [col for col, dtype in data_types.items() if dtype == "categorical"]
        
        if temporal_cols and numeric_cols:
            return {
                "primary": "line",
                "alternatives": ["bar", "area"],
                "reason": "Time series data is best shown with line charts",
                "x_axis": temporal_cols[0] if temporal_cols else None,
                "y_axis": numeric_cols[0] if numeric_cols else None
            }
        elif categorical_cols and numeric_cols:
            return {
                "primary": "bar",
                "alternatives": ["pie", "table"],
                "reason": "Categorical comparisons work well with bar charts",
                "x_axis": categorical_cols[0] if categorical_cols else None,
                "y_axis": numeric_cols[0] if numeric_cols else None
            }
        elif len(numeric_cols) >= 2:
            return {
                "primary": "scatter",
                "alternatives": ["line", "table"],
                "reason": "Multiple numeric values can show correlations",
                "x_axis": numeric_cols[0] if numeric_cols else None,
                "y_axis": numeric_cols[1] if len(numeric_cols) > 1 else None
            }
        else:
            return {
                "primary": "table",
                "alternatives": [],
                "reason": "Table view provides detailed data inspection",
                "x_axis": None,
                "y_axis": None
            }
