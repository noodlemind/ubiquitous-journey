"""DDL parser using sqlglot library."""

import sqlglot
from sqlglot import parse_one, exp
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from ddl_parser_mcp.schema import TableInfo, ColumnInfo, Relationship, DatabaseSchema, RelationType
from shared.errors import ParsingError


class DDLParser:
    """Parse DDL statements into structured schema."""
    
    def __init__(self, dialect: str = "sqlite"):
        """
        Initialize DDL parser.
        
        Args:
            dialect: SQL dialect (sqlite, postgres, mysql)
        """
        self.dialect = self._map_dialect(dialect)
        
    def _map_dialect(self, dialect: str) -> str:
        """Map dialect names to sqlglot dialect names."""
        dialect_map = {
            "sqlite": "sqlite",
            "postgresql": "postgres",
            "postgres": "postgres",
            "mysql": "mysql",
            "mariadb": "mysql"
        }
        return dialect_map.get(dialect.lower(), "sqlite")
    
    def parse(self, ddl: str) -> DatabaseSchema:
        """
        Parse DDL statements into a DatabaseSchema.
        
        Args:
            ddl: DDL statements as string
            
        Returns:
            DatabaseSchema object
            
        Raises:
            ParsingError: If DDL parsing fails
        """
        tables = []
        relationships = []
        
        try:
            # Parse multiple statements
            statements = sqlglot.parse(ddl, dialect=self.dialect)
            
            for statement in statements:
                if isinstance(statement, exp.Create):
                    table_info = self._parse_create_table(statement)
                    if table_info:
                        tables.append(table_info)
                        # Extract relationships from foreign keys
                        for fk in table_info.foreign_keys:
                            rel = self._extract_relationship(table_info.name, fk)
                            if rel:
                                relationships.append(rel)
                                
        except Exception as e:
            raise ParsingError(f"Failed to parse DDL: {str(e)}")
        
        return DatabaseSchema(
            tables=tables,
            relationships=relationships,
            database_type=self.dialect
        )
    
    def _parse_create_table(self, create_stmt: exp.Create) -> Optional[TableInfo]:
        """Parse CREATE TABLE statement."""
        if not create_stmt.this:
            return None
            
        # The table name is in create_stmt.this.this for Schema objects
        if hasattr(create_stmt.this, 'this') and create_stmt.this.this:
            table_name = create_stmt.this.this.name
        else:
            table_name = create_stmt.this.name
            
        if not table_name:
            return None
            
        columns = []
        primary_keys = []
        foreign_keys = []
        
        # Parse columns
        if create_stmt.this.expressions:
            for expr in create_stmt.this.expressions:
                if isinstance(expr, exp.ColumnDef):
                    col_info = self._parse_column_def(expr)
                    if col_info:
                        columns.append(col_info)
                        if col_info.is_primary_key:
                            primary_keys.append(col_info.name)
                elif isinstance(expr, exp.PrimaryKey):
                    # Handle table-level primary key constraint
                    for col in expr.expressions:
                        if isinstance(col, exp.Column):
                            primary_keys.append(col.name)
                elif isinstance(expr, exp.ForeignKey):
                    # Handle foreign key constraint
                    fk_info = self._parse_foreign_key(expr)
                    if fk_info:
                        foreign_keys.append(fk_info)
                        # Mark columns as foreign keys
                        for col in columns:
                            if col.name in fk_info.get('columns', []):
                                col.is_foreign_key = True
                                col.references = {
                                    'table': fk_info['referenced_table'],
                                    'column': fk_info['referenced_columns'][0] if fk_info.get('referenced_columns') else None
                                }
        
        return TableInfo(
            name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys
        )
    
    def _parse_column_def(self, col_def: exp.ColumnDef) -> Optional[ColumnInfo]:
        """Parse column definition."""
        if not col_def.this:
            return None
            
        col_name = col_def.this.name
        data_type = "TEXT"  # Default type
        is_nullable = True
        is_primary_key = False
        default_value = None
        
        # Get data type
        if col_def.kind:
            data_type = str(col_def.kind).upper()
        
        # Check constraints
        if col_def.constraints:
            for constraint in col_def.constraints:
                if isinstance(constraint, exp.NotNullColumnConstraint):
                    is_nullable = False
                elif isinstance(constraint, exp.PrimaryKeyColumnConstraint):
                    is_primary_key = True
                    is_nullable = False
                elif isinstance(constraint, exp.DefaultColumnConstraint):
                    if constraint.this:
                        default_value = str(constraint.this)
        
        return ColumnInfo(
            name=col_name,
            data_type=data_type,
            is_primary_key=is_primary_key,
            is_nullable=is_nullable,
            default_value=default_value
        )
    
    def _parse_foreign_key(self, fk: exp.ForeignKey) -> Optional[Dict[str, Any]]:
        """Parse foreign key constraint."""
        fk_info = {
            'columns': [],
            'referenced_table': None,
            'referenced_columns': []
        }
        
        # Get local columns
        for expr in fk.expressions:
            if isinstance(expr, exp.Column):
                fk_info['columns'].append(expr.name)
        
        # Get referenced table and columns
        # In sqlglot, the reference is stored in the 'reference' property
        if hasattr(fk, 'args') and 'reference' in fk.args:
            ref = fk.args['reference']
            if ref:
                if isinstance(ref, exp.Table):
                    fk_info['referenced_table'] = ref.name
                elif hasattr(ref, 'this'):
                    fk_info['referenced_table'] = ref.this.name
                if hasattr(ref, 'expressions'):
                    for expr in ref.expressions:
                        if isinstance(expr, exp.Column):
                            fk_info['referenced_columns'].append(expr.name)
        
        return fk_info if fk_info['referenced_table'] else None
    
    def _extract_relationship(self, table_name: str, fk_info: Dict[str, Any]) -> Optional[Relationship]:
        """Extract relationship from foreign key information."""
        if not fk_info.get('referenced_table'):
            return None
            
        return Relationship(
            from_table=table_name,
            to_table=fk_info['referenced_table'],
            from_column=fk_info['columns'][0] if fk_info.get('columns') else 'id',
            to_column=fk_info['referenced_columns'][0] if fk_info.get('referenced_columns') else 'id',
            type=RelationType.ONE_TO_MANY  # Default assumption
        )
