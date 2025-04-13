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
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def get_type_from_schema(schema: Dict[str, Any], schemas: Dict[str, Any]) -> str:
    """
    Extract Python type from OpenAPI schema.

    Args:
        schema: OpenAPI schema object
        schemas: Dictionary of all schemas for reference resolution

    Returns:
        Python type as string
    """
    if not schema:
        return "Any"

    schema_type = schema.get("type", "")

    # Handle references
    if "$ref" in schema:
        ref = str(schema["$ref"])
        ref_parts = ref.split("/")
        schema_name = ref_parts[-1]
        return schema_name

    # Handle arrays
    if schema_type == "array":
        items = schema.get("items", {})
        item_type = get_type_from_schema(items, schemas)
        return f"List[{item_type}]"

    # Handle objects
    if schema_type == "object":
        if "additionalProperties" in schema:
            if isinstance(schema["additionalProperties"], bool):
                return "Dict[str, Any]"
            value_type = get_type_from_schema(schema["additionalProperties"], schemas)
            return f"Dict[str, {value_type}]"
        return "Dict[str, Any]"

    # Handle primitives
    type_mapping = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "null": "None",
    }

    # Handle format specifics
    if schema_type == "string" and "format" in schema:
        format_mapping = {
            "date": "date",
            "date-time": "datetime",
            "binary": "bytes",
            "byte": "str",  # base64 encoded
            "password": "str",
            "email": "str",
            "uuid": "str",
        }
        if schema["format"] in format_mapping:
            return format_mapping[schema["format"]]

    return type_mapping.get(schema_type, "Any")


# Alias for compatibility
get_python_type = get_type_from_schema


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
