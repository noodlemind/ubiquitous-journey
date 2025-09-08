"""SQL query generator from database schema."""

from typing import List, Optional, Dict, Any
import sys
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from ddl_parser_mcp.schema import DatabaseSchema, TableInfo, QuerySuggestion, Relationship


class SQLGenerator:
    """Generate SQL queries from database schema for visualizations."""
    
    def __init__(self, schema: DatabaseSchema):
        """
        Initialize SQL generator.
        
        Args:
            schema: Parsed database schema
        """
        self.schema = schema
        self.dialect = schema.database_type or "sqlite"
        
    def generate_suggestions(self, visualization_intents: Optional[List[str]] = None) -> List[QuerySuggestion]:
        """
        Generate SQL query suggestions based on schema and visualization intents.
        
        Args:
            visualization_intents: List of desired visualization types
            
        Returns:
            List of QuerySuggestion objects
        """
        suggestions = []
        
        # Default intents if none provided
        if not visualization_intents:
            visualization_intents = ["overview", "distributions", "relationships", "time_series"]
        
        for intent in visualization_intents:
            if intent == "overview":
                suggestions.extend(self._generate_overview_queries())
            elif intent == "distributions":
                suggestions.extend(self._generate_distribution_queries())
            elif intent == "relationships":
                suggestions.extend(self._generate_relationship_queries())
            elif intent == "time_series":
                suggestions.extend(self._generate_time_series_queries())
            elif intent == "aggregations":
                suggestions.extend(self._generate_aggregation_queries())
        
        return suggestions
    
    def _generate_overview_queries(self) -> List[QuerySuggestion]:
        """Generate overview queries for basic table exploration."""
        suggestions = []
        
        for table in self.schema.tables:
            # Basic SELECT * with limit
            suggestions.append(QuerySuggestion(
                query=f"SELECT * FROM {self._quote_identifier(table.name)} LIMIT 100",
                description=f"Sample data from {table.name} table",
                visualization_type="table",
                expected_columns=[col.name for col in table.columns]
            ))
            
            # Count query
            suggestions.append(QuerySuggestion(
                query=f"SELECT COUNT(*) as row_count FROM {self._quote_identifier(table.name)}",
                description=f"Total number of records in {table.name}",
                visualization_type="table",
                expected_columns=["row_count"]
            ))
        
        return suggestions
    
    def _generate_distribution_queries(self) -> List[QuerySuggestion]:
        """Generate queries for data distribution analysis."""
        suggestions = []
        
        for table in self.schema.tables:
            # Find categorical columns (VARCHAR, TEXT, ENUM)
            categorical_cols = [
                col for col in table.columns
                if self._is_categorical_type(col.data_type) and not col.is_primary_key
            ]
            
            for col in categorical_cols[:3]:  # Limit to first 3 categorical columns
                suggestions.append(QuerySuggestion(
                    query=f"""
SELECT {self._quote_identifier(col.name)} as category, 
       COUNT(*) as count
FROM {self._quote_identifier(table.name)}
GROUP BY {self._quote_identifier(col.name)}
ORDER BY count DESC
LIMIT 20""".strip(),
                    description=f"Distribution of {col.name} in {table.name}",
                    visualization_type="bar",
                    expected_columns=["category", "count"]
                ))
            
            # Find numeric columns for histogram
            numeric_cols = [
                col for col in table.columns
                if self._is_numeric_type(col.data_type) and not col.is_primary_key
            ]
            
            for col in numeric_cols[:2]:  # Limit to first 2 numeric columns
                suggestions.append(QuerySuggestion(
                    query=f"""
SELECT 
    CASE 
        WHEN {self._quote_identifier(col.name)} IS NULL THEN 'NULL'
        ELSE CAST(({self._quote_identifier(col.name)} / 10) * 10 AS VARCHAR(50))
    END as range,
    COUNT(*) as count
FROM {self._quote_identifier(table.name)}
GROUP BY range
ORDER BY range""".strip(),
                    description=f"Distribution of {col.name} values in {table.name}",
                    visualization_type="bar",
                    expected_columns=["range", "count"]
                ))
        
        return suggestions
    
    def _generate_relationship_queries(self) -> List[QuerySuggestion]:
        """Generate queries that explore relationships between tables."""
        suggestions = []
        
        for relationship in self.schema.relationships:
            from_table = self._find_table(relationship.from_table)
            to_table = self._find_table(relationship.to_table)
            
            if not from_table or not to_table:
                continue
            
            # Basic join query
            join_query = f"""
SELECT t1.*, t2.*
FROM {self._quote_identifier(relationship.from_table)} t1
JOIN {self._quote_identifier(relationship.to_table)} t2
    ON t1.{self._quote_identifier(relationship.from_column)} = t2.{self._quote_identifier(relationship.to_column)}
LIMIT 100""".strip()
            
            suggestions.append(QuerySuggestion(
                query=join_query,
                description=f"Join data between {relationship.from_table} and {relationship.to_table}",
                visualization_type="table",
                expected_columns=["*"]  # All columns from both tables
            ))
            
            # Aggregated join for visualization
            # Find a categorical column in the parent table
            parent_categorical = next(
                (col.name for col in to_table.columns 
                 if self._is_categorical_type(col.data_type) and not col.is_primary_key),
                None
            )
            
            if parent_categorical:
                agg_query = f"""
SELECT t2.{self._quote_identifier(parent_categorical)} as category,
       COUNT(t1.{self._quote_identifier(relationship.from_column)}) as count
FROM {self._quote_identifier(relationship.from_table)} t1
JOIN {self._quote_identifier(relationship.to_table)} t2
    ON t1.{self._quote_identifier(relationship.from_column)} = t2.{self._quote_identifier(relationship.to_column)}
GROUP BY t2.{self._quote_identifier(parent_categorical)}
ORDER BY count DESC""".strip()
                
                suggestions.append(QuerySuggestion(
                    query=agg_query,
                    description=f"Count of {relationship.from_table} by {parent_categorical}",
                    visualization_type="bar",
                    expected_columns=["category", "count"]
                ))
        
        return suggestions
    
    def _generate_time_series_queries(self) -> List[QuerySuggestion]:
        """Generate time series queries if date/time columns exist."""
        suggestions = []
        
        for table in self.schema.tables:
            # Find date/time columns
            date_cols = [
                col for col in table.columns
                if self._is_date_type(col.data_type)
            ]
            
            if not date_cols:
                continue
            
            date_col = date_cols[0]  # Use first date column
            
            # Daily counts
            if self.dialect == "sqlite":
                date_format = f"DATE({self._quote_identifier(date_col.name)})"
            elif self.dialect in ["postgres", "postgresql"]:
                date_format = f"DATE({self._quote_identifier(date_col.name)})"
            else:  # MySQL
                date_format = f"DATE({self._quote_identifier(date_col.name)})"
            
            suggestions.append(QuerySuggestion(
                query=f"""
SELECT {date_format} as date,
       COUNT(*) as count
FROM {self._quote_identifier(table.name)}
WHERE {self._quote_identifier(date_col.name)} IS NOT NULL
GROUP BY date
ORDER BY date""".strip(),
                description=f"Daily counts in {table.name} over time",
                visualization_type="line",
                expected_columns=["date", "count"]
            ))
            
            # Find numeric columns for time series aggregation
            numeric_cols = [
                col for col in table.columns
                if self._is_numeric_type(col.data_type) and not col.is_primary_key
            ]
            
            for num_col in numeric_cols[:2]:
                suggestions.append(QuerySuggestion(
                    query=f"""
SELECT {date_format} as date,
       AVG({self._quote_identifier(num_col.name)}) as avg_value,
       MIN({self._quote_identifier(num_col.name)}) as min_value,
       MAX({self._quote_identifier(num_col.name)}) as max_value
FROM {self._quote_identifier(table.name)}
WHERE {self._quote_identifier(date_col.name)} IS NOT NULL
    AND {self._quote_identifier(num_col.name)} IS NOT NULL
GROUP BY date
ORDER BY date""".strip(),
                    description=f"Trend of {num_col.name} over time in {table.name}",
                    visualization_type="line",
                    expected_columns=["date", "avg_value", "min_value", "max_value"]
                ))
        
        return suggestions
    
    def _generate_aggregation_queries(self) -> List[QuerySuggestion]:
        """Generate aggregation queries for summary statistics."""
        suggestions = []
        
        for table in self.schema.tables:
            numeric_cols = [
                col for col in table.columns
                if self._is_numeric_type(col.data_type) and not col.is_primary_key
            ]
            
            if numeric_cols:
                # Summary statistics
                select_parts = []
                for col in numeric_cols[:5]:  # Limit to 5 columns
                    col_name = self._quote_identifier(col.name)
                    select_parts.extend([
                        f"AVG({col_name}) as avg_{col.name}",
                        f"MIN({col_name}) as min_{col.name}",
                        f"MAX({col_name}) as max_{col.name}"
                    ])
                
                if select_parts:
                    suggestions.append(QuerySuggestion(
                        query=f"""
SELECT {',\\n       '.join(select_parts)}
FROM {self._quote_identifier(table.name)}""".strip(),
                        description=f"Summary statistics for {table.name}",
                        visualization_type="table",
                        expected_columns=[part.split(' as ')[1] for part in select_parts]
                    ))
        
        return suggestions
    
    def _find_table(self, table_name: str) -> Optional[TableInfo]:
        """Find table by name in schema."""
        for table in self.schema.tables:
            if table.name.lower() == table_name.lower():
                return table
        return None
    
    def _quote_identifier(self, identifier: str) -> str:
        """Quote identifier based on dialect."""
        if self.dialect in ["postgres", "postgresql"]:
            return f'"{identifier}"'
        elif self.dialect == "mysql":
            return f"`{identifier}`"
        else:  # SQLite uses double quotes or backticks
            return f'"{identifier}"'
    
    def _is_categorical_type(self, data_type: str) -> bool:
        """Check if data type is categorical."""
        categorical_types = ['VARCHAR', 'CHAR', 'TEXT', 'STRING', 'ENUM', 'NVARCHAR']
        return any(cat in data_type.upper() for cat in categorical_types)
    
    def _is_numeric_type(self, data_type: str) -> bool:
        """Check if data type is numeric."""
        numeric_types = ['INT', 'DECIMAL', 'FLOAT', 'DOUBLE', 'NUMERIC', 'REAL', 'NUMBER']
        return any(num in data_type.upper() for num in numeric_types)
    
    def _is_date_type(self, data_type: str) -> bool:
        """Check if data type is date/time."""
        date_types = ['DATE', 'TIME', 'DATETIME', 'TIMESTAMP']
        return any(dt in data_type.upper() for dt in date_types)
