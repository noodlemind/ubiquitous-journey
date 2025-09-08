"""Input validation and security utilities."""

import re
import html
from typing import Optional, List, Dict, Any


def validate_input_size(input_str: str, max_size: int = 100000) -> None:
    """
    Validate input size to prevent DoS attacks.
    
    Args:
        input_str: Input string to validate
        max_size: Maximum allowed size in characters
        
    Raises:
        ValidationError: If input exceeds max size
    """
    from .errors import ValidationError
    
    if len(input_str) > max_size:
        raise ValidationError(
            f"Input too large: {len(input_str)} characters (max: {max_size})",
            {'size': len(input_str), 'max_size': max_size}
        )


def validate_ddl_safety(ddl: str) -> None:
    """
    Validate DDL contains only safe schema definition statements.
    
    Args:
        ddl: DDL string to validate
        
    Raises:
        SecurityError: If DDL contains unsafe operations
    """
    from .errors import SecurityError
    
    # List of dangerous keywords that shouldn't appear in schema definitions
    dangerous_patterns = [
        r'\bDROP\s+DATABASE\b',
        r'\bTRUNCATE\b',
        r'\bDELETE\s+FROM\b',
        r'\bUPDATE\s+.*\s+SET\b',
        r'\bINSERT\s+INTO\b',
        r'\bEXEC\b',
        r'\bEXECUTE\b',
        r'\bGRANT\b',
        r'\bREVOKE\b',
    ]
    
    ddl_upper = ddl.upper()
    for pattern in dangerous_patterns:
        if re.search(pattern, ddl_upper, re.IGNORECASE):
            raise SecurityError(
                "DDL contains potentially dangerous operations",
                {'pattern': pattern}
            )


def sanitize_html(text: str) -> str:
    """
    Sanitize text for safe HTML embedding.
    
    Args:
        text: Text to sanitize
        
    Returns:
        HTML-escaped text
    """
    return html.escape(text)


def validate_json_data(data: Any, max_rows: int = 1000000) -> None:
    """
    Validate JSON data structure for dashboard generation.
    
    Args:
        data: Data to validate (should be list of dicts or similar)
        max_rows: Maximum number of rows allowed
        
    Raises:
        ValidationError: If data structure is invalid
    """
    from .errors import ValidationError
    
    if not isinstance(data, (list, dict)):
        raise ValidationError(
            f"Data must be a list or dictionary, got {type(data).__name__}"
        )
    
    if isinstance(data, list):
        if len(data) > max_rows:
            raise ValidationError(
                f"Data exceeds maximum rows: {len(data)} (max: {max_rows})",
                {'rows': len(data), 'max_rows': max_rows}
            )
        
        # Validate structure consistency
        if data and isinstance(data[0], dict):
            first_keys = set(data[0].keys())
            for i, row in enumerate(data[1:11], 1):  # Check first 10 rows
                if not isinstance(row, dict):
                    raise ValidationError(
                        f"Inconsistent data structure at row {i}: expected dict, got {type(row).__name__}"
                    )
                if set(row.keys()) != first_keys:
                    raise ValidationError(
                        f"Inconsistent keys at row {i}",
                        {'expected': list(first_keys), 'actual': list(row.keys())}
                    )


def validate_mermaid_syntax(mermaid: str) -> None:
    """
    Basic validation of Mermaid ER diagram syntax.
    
    Args:
        mermaid: Mermaid diagram string
        
    Raises:
        ValidationError: If Mermaid syntax is invalid
    """
    from .errors import ValidationError
    
    if not mermaid.strip():
        raise ValidationError("Mermaid diagram cannot be empty")
    
    # Check for ER diagram declaration
    if not re.search(r'^\s*erDiagram\b', mermaid, re.MULTILINE):
        raise ValidationError("Mermaid input must start with 'erDiagram'")
    
    # Basic syntax checks for relationships
    relationship_pattern = r'\w+\s+[|o\-\{\}]+\s*[|o\-\{\}]+\s+\w+'
    if not re.search(relationship_pattern, mermaid):
        raise ValidationError("No valid entity relationships found in Mermaid diagram")


def validate_visualization_spec(spec: Dict[str, Any]) -> None:
    """
    Validate visualization specification.
    
    Args:
        spec: Visualization specification dictionary
        
    Raises:
        ValidationError: If spec is invalid
    """
    from .errors import ValidationError
    
    required_fields = ['type', 'data']
    for field in required_fields:
        if field not in spec:
            raise ValidationError(
                f"Visualization spec missing required field: {field}",
                {'missing_field': field, 'spec': spec}
            )
    
    valid_types = ['bar', 'line', 'pie', 'scatter', 'heatmap', 'table']
    if spec['type'] not in valid_types:
        raise ValidationError(
            f"Invalid visualization type: {spec['type']}",
            {'type': spec['type'], 'valid_types': valid_types}
        )
