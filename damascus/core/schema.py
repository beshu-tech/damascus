"""
Schema handling utilities for SDK generation.
"""

import re
from typing import Dict, List, Any, Optional

from damascus.core.types import to_snake_case, get_type_from_schema


def get_request_body_params(request_body: Optional[Dict[str, Any]], components_schemas: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts and flattens request body parameters.
    
    Args:
        request_body: The request body object from the OpenAPI spec
        components_schemas: The components/schemas section of the spec
        
    Returns:
        A list of parameter dictionaries
    """
    from damascus.core.types import get_default_value
    
    if not request_body:
        return []

    content = request_body.get("content", {})
    if "application/json" not in content:
        return []

    schema = content["application/json"].get("schema")
    if not schema:
        return []

    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        schema = components_schemas.get(ref_name)
        if not schema:
            return []

    if schema.get("type") == "object":
        properties = schema.get("properties", {})
        params = []
        for name, prop_schema in properties.items():
            param_info = {
                "name": to_snake_case(name),
                "type": get_type_from_schema(prop_schema, components_schemas),
                "required": name in schema.get("required", []),
                "description": prop_schema.get("description", ""),
                "in": "body",  # Mark as coming from the body
                "default": get_default_value(prop_schema),  # Get default
            }
            params.append(param_info)
        return params

    # Handle other schema types if needed (e.g., array, string)
    return []  # Return empty list for unsupported types


def get_response_type(responses: Dict[str, Any], components_schemas: Dict[str, Any]) -> str:
    """
    Determines the response type from the responses section, handling refs.
    
    Args:
        responses: The responses object from the OpenAPI spec
        components_schemas: The components/schemas section of the spec
        
    Returns:
        A Python type as a string
    """
    if "200" in responses:
        content = responses["200"].get("content")
        if content:
            if "application/json" in content:
                schema = content["application/json"].get("schema")
                if schema:
                    return get_type_from_schema(schema, components_schemas)
            elif "application/x-ndjson" in content:
                return "requests.Response"  # Streaming
            return "requests.Response"  # Other content types
        return "None"  # No content in 200 response
    if "204" in responses:
        return "None"  # No Content
    return "dict"  # Default fallback


def get_response_model(method_spec: Dict[str, Any], components_schemas: Dict[str, Any]) -> Optional[str]:
    """
    Generates dataclass code for response model if needed.
    
    Args:
        method_spec: The method specification from the OpenAPI spec
        components_schemas: The components/schemas section of the spec
        
    Returns:
        A string with dataclass code, or None if no model is needed
    """
    # Type and structure validation
    if not isinstance(method_spec, dict):
        return None
    if not method_spec.get('operationId'):
        return None
    
    try:
        responses = method_spec.get("responses", {})
        if "200" not in responses:
            return None
        
        content = responses["200"].get("content", {})
        if "application/json" not in content:
            return None
        
        schema = content["application/json"].get("schema")
        if not schema:
            return None

        # Resolve $ref if present
        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            schema = components_schemas.get(ref_name, {})
        
        if schema.get("type") != "object" or not schema.get("properties"):
            return None

        # Generate fields with improved typing
        required_fields = []
        optional_fields = []
        
        required_props = schema.get("required", [])
        
        for prop_name, prop_schema in schema["properties"].items():
            snake_name = to_snake_case(prop_name)
            
            # Use a non-cached version of get_type_from_schema to avoid hashing issues
            def get_prop_type(s):
                if not s:
                    return "Any"
                if "$ref" in s:
                    ref = s["$ref"].split("/")[-1]
                    return "dict"  # Simplified for response models
                if "anyOf" in s: return "Any"
                s_type = s.get("type")
                if s_type == "array": 
                    items = s.get('items', {})
                    return f"List[{get_prop_type(items)}]"
                if s_type == "integer": return "int"
                if s_type == "number": return "float"
                if s_type == "boolean": return "bool"
                if s_type == "string": return "str"
                if s_type == "object": return "dict"
                return "Any"
            
            field_type = get_prop_type(prop_schema)
            
            # Add descriptions as docstrings
            description = prop_schema.get("description", "")
            field_entry = []
            if description:
                field_entry.append(f'    # {description}')
            
            # Add field with type annotation
            is_required = prop_name in required_props
            if is_required:
                field_entry.append(f"    {snake_name}: {field_type}")
                required_fields.extend(field_entry)
            else:
                # Use | None syntax for optional fields (Python 3.10+)
                field_entry.append(f"    {snake_name}: {field_type} | None = None")
                optional_fields.extend(field_entry)
        
        # Combine fields with required fields first, then optional fields
        fields = required_fields + optional_fields
        
        # Add frozen=True for immutability and slots=True for memory efficiency
        op_id = method_spec['operationId']
        base_name = op_id.split('_api_')[0] if '_api_' in op_id else op_id
        sanitized_name = re.sub(r'\W+', '_', base_name)
        class_name = f"{to_snake_case(sanitized_name).title().replace('_', '')}Response"
        
        return f"@dataclass(frozen=True, slots=True)\nclass {class_name}:\n" + "\n".join(fields)
    
    except KeyError as e:
        print(f"Warning: Missing key in method spec - {e}")
        return None
    except Exception as e:
        print(f"Warning: Error generating response model - {e}")
        return None


def build_dependency_graph(schemas: Dict[str, Dict]) -> Dict[str, List[str]]:
    """
    Builds a dependency graph of model classes.
    
    Args:
        schemas: The components/schemas section of the spec
        
    Returns:
        A dictionary mapping schema names to their dependencies
    """
    def get_dependencies(schema: Dict) -> List[str]:
        deps = []
        if "$ref" in schema:
            deps.append(schema["$ref"].split("/")[-1])
        elif schema.get("type") == "array":
            if "$ref" in schema.get("items", {}):
                deps.append(schema["items"]["$ref"].split("/")[-1])
            elif "anyOf" in schema.get("items", {}):
                for item in schema["items"]["anyOf"]:
                    if "$ref" in item:
                        deps.append(item["$ref"].split("/")[-1])
        elif schema.get("type") == "object":
            if "properties" in schema:
                for prop in schema["properties"].values():
                    deps.extend(get_dependencies(prop))
            if "additionalProperties" in schema:
                deps.extend(get_dependencies(schema["additionalProperties"]))
        elif "anyOf" in schema:
            for item in schema["anyOf"]:
                deps.extend(get_dependencies(item))
        elif "allOf" in schema:
            for item in schema["allOf"]:
                deps.extend(get_dependencies(item))
        elif "oneOf" in schema:
            for item in schema["oneOf"]:
                deps.extend(get_dependencies(item))
        return deps

    graph = {}
    for name, schema in schemas.items():
        graph[name] = []
        if "properties" in schema:
            for prop_schema in schema["properties"].values():
                deps = get_dependencies(prop_schema)
                for dep in deps:
                    if dep != name:  # Avoid self-loops
                        graph[name].append(dep)
        # Check if the schema itself has type array (for cases like NotificationList)
        if schema.get("type") == "array":
            deps = get_dependencies(schema)
            for dep in deps:
                if dep != name:
                    graph[name].append(dep)

    return graph


def has_only_native_types(schema: Dict, schemas: Dict[str, Dict]) -> bool:
    """
    Check if a schema only uses native types (no refs).
    
    Args:
        schema: The schema to check
        schemas: All schemas from the spec
        
    Returns:
        True if the schema only uses native types, False otherwise
    """
    def check_schema(s: Dict) -> bool:
        if not s:
            return True
        if "$ref" in s:
            return False
        if s.get("type") == "array":
            return check_schema(s.get("items", {}))
        if s.get("type") == "object":
            if "properties" in s:
                return all(check_schema(p) for p in s["properties"].values())
            if "additionalProperties" in s:
                return check_schema(s["additionalProperties"])
        if "anyOf" in s:
            return all(check_schema(item) for item in s["anyOf"])
        if "allOf" in s:
            return all(check_schema(item) for item in s["allOf"])
        if "oneOf" in s:
            return all(check_schema(item) for item in s["oneOf"])
        return True

    if not schema.get("properties"):
        return True
        
    return all(check_schema(prop) for prop in schema["properties"].values())


def topological_sort(graph: Dict[str, List[str]], schemas: Dict[str, Dict]) -> List[str]:
    """
    Performs a topological sort, prioritizing models with only native types.
    
    Args:
        graph: The dependency graph
        schemas: All schemas from the spec
        
    Returns:
        A list of schema names in dependency order
    """
    visited = set()
    recursion_stack = set()
    sorted_list = []

    def visit(node):
        if node in recursion_stack:
            raise ValueError(f"Circular dependency detected involving {node}")
        if node not in visited:
            visited.add(node)
            recursion_stack.add(node)
            # Visit dependencies first
            for neighbor in graph.get(node, []):
                visit(neighbor)
            recursion_stack.remove(node)
            sorted_list.append(node)

    # First process models with dependencies
    for node in graph:
        if not has_only_native_types(schemas[node], schemas):
            visit(node)

    # Then add remaining models (native types only)
    for node in graph:
        if node not in visited:
            visit(node)

    return sorted_list[::-1]  # Reverse to get correct dependency order 