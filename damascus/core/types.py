"""
Type conversion utilities for SDK generation.
"""

import re
from typing import Dict, Any, Optional


def to_snake_case(name: str) -> str:
    """
    Converts a string to snake_case.
    
    Args:
        name: The string to convert
        
    Returns:
        The string in snake_case format
    """
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def get_type_from_schema(schema: Dict[str, Any], components_schemas: Dict[str, Any]) -> str:
    """
    Extracts Python type from an OpenAPI schema, handling refs and primitives.
    
    Args:
        schema: The OpenAPI schema object
        components_schemas: The components/schemas section of the spec
        
    Returns:
        A Python type as a string
    """
    # Handle empty schema
    if not schema:
        return "Any"
        
    if "$ref" in schema:
        # Resolve references to components/schemas
        ref_name = schema["$ref"].split("/")[-1]
        ref_schema = components_schemas.get(ref_name)
        if ref_schema:
            # Treat referenced schemas as dict
            return "dict"
        else:
            return "Any"  # Unknown ref
            
    if "anyOf" in schema: 
        return "Any"
        
    schema_type = schema.get("type")
    if schema_type == "array": 
        # Handle array items safely
        items = schema.get('items', {})
        item_type = get_type_from_schema(items, components_schemas)
        return f"List[{item_type}]"
    if schema_type == "integer": return "int"
    if schema_type == "number": return "float"
    if schema_type == "boolean": return "bool"
    if schema_type == "string": return "str"
    if schema_type == "object": return "dict"
    
    return "Any"


def get_default_value(schema: Dict[str, Any]) -> Optional[str]:
    """
    Returns the default value for a schema, handling different types.
    Returns a string representation suitable for code generation.
    
    Args:
        schema: The OpenAPI schema object
        
    Returns:
        A string representation of the default value, or None if no default
    """
    # Handle empty schema
    if not schema:
        return None
        
    if "default" not in schema:
        return None  # No default

    default_value = schema["default"]
    schema_type = schema.get("type")

    if schema_type == "string":
        return f'"{default_value}"'  # Quote strings
    elif schema_type == "boolean":
        return str(default_value).capitalize()  # True or False
    elif schema_type in ("integer", "number"):
        return str(default_value)  # Numbers as strings
    elif default_value is None:
        return "None"
    else:
        return "None"  # Fallback. Shouldn't normally happen. 