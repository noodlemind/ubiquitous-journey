"""Query executor utility for running SQL queries and combining results."""

import json
import sqlite3
import psycopg2
import mysql.connector
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, date
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class QueryExecutionConfig:
    """Configuration for query execution."""
    database_type: str  # sqlite, postgres, mysql
    connection_params: Dict[str, Any]
    output_format: str = "json"
    combine_results: bool = True
    
    
@dataclass
class QueryWithMetadata:
    """Query with execution metadata."""
    query: str
    description: str
    result_key: str  # Key name in the combined JSON
    visualization_type: Optional[str] = None
    expected_columns: Optional[List[str]] = None
    aggregation_type: Optional[str] = None  # sum, avg, count, etc.


class QueryExecutor:
    """Executes multiple SQL queries and combines results."""
    
    def __init__(self, config: QueryExecutionConfig):
        self.config = config
        self.connection = None
        
    def __enter__(self):
        """Context manager entry - establish database connection."""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close database connection."""
        self.disconnect()
        
    def connect(self):
        """Establish database connection based on type."""
        try:
            if self.config.database_type == "sqlite":
                self.connection = sqlite3.connect(
                    self.config.connection_params.get("database", ":memory:")
                )
                self.connection.row_factory = sqlite3.Row
                
            elif self.config.database_type == "postgres":
                self.connection = psycopg2.connect(
                    host=self.config.connection_params.get("host", "localhost"),
                    port=self.config.connection_params.get("port", 5432),
                    database=self.config.connection_params.get("database"),
                    user=self.config.connection_params.get("user"),
                    password=self.config.connection_params.get("password")
                )
                
            elif self.config.database_type == "mysql":
                self.connection = mysql.connector.connect(
                    host=self.config.connection_params.get("host", "localhost"),
                    port=self.config.connection_params.get("port", 3306),
                    database=self.config.connection_params.get("database"),
                    user=self.config.connection_params.get("user"),
                    password=self.config.connection_params.get("password")
                )
                
            else:
                raise ValueError(f"Unsupported database type: {self.config.database_type}")
                
            logger.info(f"Connected to {self.config.database_type} database")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
            
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
            
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a single query and return results as list of dicts."""
        if not self.connection:
            raise RuntimeError("Not connected to database")
            
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            # Fetch column names
            if self.config.database_type == "sqlite":
                columns = [description[0] for description in cursor.description] if cursor.description else []
            elif self.config.database_type == "postgres":
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
            elif self.config.database_type == "mysql":
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
            # Fetch all rows
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            results = []
            for row in rows:
                if self.config.database_type == "sqlite":
                    row_dict = dict(row)
                else:
                    row_dict = dict(zip(columns, row))
                    
                # Convert special types to JSON-serializable format
                row_dict = self._serialize_row(row_dict)
                results.append(row_dict)
                
            cursor.close()
            return results
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            raise
            
    def _serialize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database types to JSON-serializable format."""
        serialized = {}
        for key, value in row.items():
            if isinstance(value, (datetime, date)):
                serialized[key] = value.isoformat()
            elif isinstance(value, Decimal):
                serialized[key] = float(value)
            elif value is None:
                serialized[key] = None
            else:
                serialized[key] = value
        return serialized
        
    def execute_queries(self, queries: List[QueryWithMetadata]) -> Dict[str, Any]:
        """Execute multiple queries and combine results."""
        combined_results = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "database_type": self.config.database_type,
                "query_count": len(queries)
            },
            "data": {},
            "queries": []
        }
        
        for idx, query_meta in enumerate(queries):
            try:
                logger.info(f"Executing query {idx + 1}/{len(queries)}: {query_meta.description}")
                
                # Execute query
                results = self.execute_query(query_meta.query)
                
                # Store results with metadata
                if self.config.combine_results:
                    combined_results["data"][query_meta.result_key] = {
                        "description": query_meta.description,
                        "visualization_type": query_meta.visualization_type,
                        "row_count": len(results),
                        "results": results
                    }
                else:
                    combined_results["data"][query_meta.result_key] = results
                    
                # Store query info
                combined_results["queries"].append({
                    "description": query_meta.description,
                    "query": query_meta.query,
                    "result_key": query_meta.result_key,
                    "row_count": len(results)
                })
                
                logger.info(f"Query {idx + 1} returned {len(results)} rows")
                
            except Exception as e:
                logger.error(f"Failed to execute query: {query_meta.description}")
                logger.error(f"Error: {e}")
                
                # Add error info to results
                combined_results["data"][query_meta.result_key] = {
                    "error": str(e),
                    "description": query_meta.description,
                    "query": query_meta.query
                }
                
        return combined_results
        
    def save_results(self, results: Dict[str, Any], output_path: Path):
        """Save combined results to JSON file."""
        try:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            raise
            

def execute_queries_from_parsed_output(
    parsed_output_path: Path,
    database_config: Dict[str, Any],
    output_path: Path
) -> Dict[str, Any]:
    """
    Execute queries from DDL parser output and save combined results.
    
    Args:
        parsed_output_path: Path to JSON file from DDL parser
        database_config: Database connection configuration
        output_path: Path to save combined results
        
    Returns:
        Combined results dictionary
    """
    # Load parsed output
    with open(parsed_output_path, 'r') as f:
        parsed_data = json.load(f)
        
    # Extract queries
    queries = []
    for query_data in parsed_data.get("queries", []):
        queries.append(QueryWithMetadata(
            query=query_data["query"],
            description=query_data["description"],
            result_key=query_data.get("result_key", f"query_{len(queries) + 1}"),
            visualization_type=query_data.get("visualization_type")
        ))
        
    # Create executor config
    config = QueryExecutionConfig(
        database_type=database_config.get("type", "sqlite"),
        connection_params=database_config
    )
    
    # Execute queries
    with QueryExecutor(config) as executor:
        results = executor.execute_queries(queries)
        executor.save_results(results, output_path)
        
    return results


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python query_executor.py <parsed_queries.json> <output.json>")
        sys.exit(1)
        
    # Example database config (for SQLite)
    db_config = {
        "type": "sqlite",
        "database": "example.db"  # or ":memory:" for in-memory
    }
    
    # Execute queries from parsed output
    results = execute_queries_from_parsed_output(
        Path(sys.argv[1]),
        db_config,
        Path(sys.argv[2])
    )
    
    print(f"Executed {results['metadata']['query_count']} queries")
    print(f"Results saved to {sys.argv[2]}")