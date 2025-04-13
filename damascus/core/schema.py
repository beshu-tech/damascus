"""
Schema handling utilities for SDK generation.
"""

import re
from typing import Dict, List, Any, Optional, Tuple, Set, cast

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
    if not method_spec.get("operationId"):
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
            def get_prop_type(s: Dict[str, Any]) -> str:
                if not s:
                    return "Any"
                if "$ref" in s:
                    s["$ref"].split("/")[-1]
                    return "dict"  # Simplified for response models
                if "anyOf" in s:
                    return "Any"
                s_type = s.get("type")
                if s_type == "array":
                    items = s.get("items", {})
                    return f"List[{get_prop_type(items)}]"
                if s_type == "integer":
                    return "int"
                if s_type == "number":
                    return "float"
                if s_type == "boolean":
                    return "bool"
                if s_type == "string":
                    return "str"
                if s_type == "object":
                    return "dict"
                return "Any"

            field_type = get_prop_type(prop_schema)

            # Add descriptions as docstrings
            description = prop_schema.get("description", "")
            field_entry = []
            if description:
                field_entry.append(f"    # {description}")

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
        op_id = method_spec["operationId"]
        base_name = op_id.split("_api_")[0] if "_api_" in op_id else op_id
        sanitized_name = re.sub(r"\W+", "_", base_name)
        class_name = f"{to_snake_case(sanitized_name).title().replace('_', '')}Response"

        return f"@dataclass(frozen=True, slots=True)\nclass {class_name}:\n" + "\n".join(fields)

    except KeyError as e:
        print(f"Warning: Missing key in method spec - {e}")
        return None
    except Exception as e:
        print(f"Warning: Error generating response model - {e}")
        return None


def has_only_native_types(schema: Dict, schemas: Dict) -> bool:
    """
    Check if a schema has only native types (no references to other schemas)
    """
    if not schema or not isinstance(schema, dict):
        return True

    if "$ref" in schema:
        # Resolve the ref to check the underlying schema
        ref_path = schema["$ref"]
        if ref_path.startswith("#/components/schemas/"):
            schema_name = ref_path.split("/")[-1]
            if schema_name in schemas:
                # Check the resolved schema, avoid infinite recursion for self-references
                # Passing an empty dict for schemas here might be incorrect if deep checking is needed
                # Revisit this logic if needed for complex dependencies within native check
                return has_only_native_types(schemas[schema_name], schemas)  # Pass schemas recursively
            else:
                return False  # Unresolved ref
        else:
            return False  # Non-component ref

    # Check properties for object type
    if schema.get("type") == "object" and "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            if not has_only_native_types(prop_schema, schemas):  # Pass schemas recursively
                return False

    # Check for array item references
    if schema.get("type") == "array" and "items" in schema:
        if not has_only_native_types(schema["items"], schemas):  # Pass schemas recursively
            return False

    # Check for oneOf, anyOf, allOf
    for key in ["oneOf", "anyOf", "allOf"]:
        if key in schema and isinstance(schema[key], list):
            for sub_schema in schema[key]:
                if not has_only_native_types(sub_schema, schemas):  # Pass schemas recursively
                    return False

    return True


def resolve_schema_references(schema: Dict[str, Any], components_schemas: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve all references in a schema to their actual definition
    """
    if not schema or not isinstance(schema, dict):
        return schema if isinstance(schema, dict) else {}

    if "$ref" in schema:
        ref_path = str(schema["$ref"])
        if ref_path.startswith("#/components/schemas/"):
            schema_name = ref_path.split("/")[-1]
            if schema_name in components_schemas:
                # Cast the return value to Dict[str, Any]
                return cast(Dict[str, Any], components_schemas[schema_name])
            else:
                return {}  # Indicate unresolved reference

    # Process nested properties
    resolved_schema = schema.copy()
    for key, value in schema.items():
        if isinstance(value, dict):
            resolved_schema[key] = resolve_schema_references(value, components_schemas)
        elif isinstance(value, list):
            resolved_schema[key] = [
                (resolve_schema_references(item, components_schemas) if isinstance(item, dict) else item)
                for item in value
            ]

    return resolved_schema


def get_request_body_parameters(request_body: Dict, schemas: Dict) -> List[Dict]:
    """
    Extract parameters from the request body schema
    """
    if not request_body:
        return []

    content = request_body.get("content", {})
    if not content:
        return []

    # Try to get JSON schema first, then fallback to any other content type
    schema = None
    if "application/json" in content:
        schema = content["application/json"].get("schema", {})
    else:
        # Fallback to first available content type
        for content_type, content_schema in content.items():
            schema = content_schema.get("schema", {})
            break

    if not schema:
        return []

    # Resolve any references in the schema
    schema = resolve_schema_references(schema, schemas)

    # Extract parameters
    properties = {}
    if schema.get("type") == "object":
        properties = schema.get("properties", {})
    elif "allOf" in schema:
        for sub_schema in schema.get("allOf", []):
            sub_schema = resolve_schema_references(sub_schema, schemas)
            if sub_schema.get("type") == "object":
                properties.update(sub_schema.get("properties", {}))

    required = schema.get("required", [])

    params = []
    for prop_name, prop_schema in properties.items():
        params.append(
            {
                "name": prop_name,
                "schema": prop_schema,
                "required": prop_name in required,
            }
        )

    return params


def get_response_type(responses: Dict, schemas: Dict) -> Tuple[Optional[Dict], bool]:
    """
    Get the response schema from the responses object
    Returns (schema, is_array) tuple
    """
    # Find successful response (2XX)
    response = None
    for status_code, resp in responses.items():
        if status_code.startswith("2"):
            response = resp
            break

    if not response:
        return None, False

    content = response.get("content", {})
    if not content:
        return None, False

    # Try to get JSON schema first, then fallback to any other content type
    schema = None
    if "application/json" in content:
        schema = content["application/json"].get("schema", {})
    else:
        # Fallback to first available content type
        for content_type, content_schema in content.items():
            schema = content_schema.get("schema", {})
            break

    if not schema:
        return None, False

    # Resolve any references in the schema
    schema = resolve_schema_references(schema, schemas)

    # Check if this is an array schema
    is_array = schema.get("type") == "array"
    if is_array and "items" in schema:
        return schema["items"], True

    return schema, False


def identify_response_schemas(openapi_spec: Dict) -> Set[str]:
    """
    Identify all schema references used in successful responses
    """
    schemas_set = set()
    paths = openapi_spec.get("paths", {})
    components_schemas = openapi_spec.get("components", {}).get("schemas", {})

    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method not in ["get", "post", "put", "delete", "patch"]:
                continue

            responses = operation.get("responses", {})
            for status_code, response in responses.items():
                if not status_code.startswith("2"):  # Only look at successful responses
                    continue

                content = response.get("content", {})
                for content_type, content_schema in content.items():
                    schema = content_schema.get("schema", {})
                    if "$ref" in schema:
                        ref_path = schema["$ref"]
                        if ref_path.startswith("#/components/schemas/"):
                            schema_name = ref_path.split("/")[-1]
                            schemas_set.add(schema_name)
                    elif schema.get("type") == "array" and "items" in schema:
                        items = schema["items"]
                        if "$ref" in items:
                            ref_path = items["$ref"]
                            if ref_path.startswith("#/components/schemas/"):
                                schema_name = ref_path.split("/")[-1]
                                schemas_set.add(schema_name)

    # Find dependencies of identified schemas
    dependencies = find_schema_dependencies(schemas_set, components_schemas)
    schemas_set.update(dependencies)

    return schemas_set


def find_schema_dependencies(schema_names: Set[str], components_schemas: Dict) -> Set[str]:
    """
    Find all dependencies of given schema names
    """
    all_dependencies: Set[str] = set()
    to_process = list(schema_names)

    while to_process:
        schema_name = to_process.pop()
        schema = components_schemas.get(schema_name, {})

        dependencies = get_schema_dependencies(schema, components_schemas)

        for dep in dependencies:
            if dep not in all_dependencies and dep not in schema_names:
                all_dependencies.add(dep)
                to_process.append(dep)

    return all_dependencies


def get_schema_dependencies(schema: Dict, components_schemas: Dict) -> Set[str]:
    """
    Extract all schema references from a schema
    """
    dependencies: Set[str] = set()

    if not schema or not isinstance(schema, dict):
        return dependencies

    # Check for direct reference
    if "$ref" in schema:
        ref_path = schema["$ref"]
        if ref_path.startswith("#/components/schemas/"):
            schema_name = ref_path.split("/")[-1]
            dependencies.add(schema_name)

    # Check properties for object type
    if schema.get("type") == "object" and "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            if isinstance(prop_schema, dict):
                nested_deps = get_schema_dependencies(prop_schema, components_schemas)
                dependencies.update(nested_deps)

    # Check for array item references
    if schema.get("type") == "array" and "items" in schema:
        items_schema = schema["items"]
        if isinstance(items_schema, dict):
            items_deps = get_schema_dependencies(items_schema, components_schemas)
            dependencies.update(items_deps)

    # Check for oneOf, anyOf, allOf
    for key in ["oneOf", "anyOf", "allOf"]:
        if key in schema and isinstance(schema[key], list):
            for sub_schema in schema[key]:
                sub_deps = get_schema_dependencies(sub_schema, components_schemas)
                dependencies.update(sub_deps)

    return dependencies


def build_dependency_graph(schemas: Dict) -> Dict[str, Set[str]]:
    """
    Build a graph of schema dependencies
    """
    graph: Dict[str, Set[str]] = {}

    for schema_name, schema in schemas.items():
        graph[schema_name] = set()
        dependencies = get_schema_dependencies(schema, schemas)
        for dep in dependencies:
            if dep != schema_name:  # Avoid self-dependency
                graph[schema_name].add(dep)

    return graph


def topological_sort(graph: Dict[str, Set[str]], schemas: Dict) -> List[str]:
    """
    Sort schemas based on their dependencies (topological sort)
    """
    # States for DFS
    UNVISITED = 0
    VISITING = 1
    VISITED = 2

    result = []
    status = {node: UNVISITED for node in graph}

    def dfs(node: str) -> None:
        if status[node] == VISITING:
            # Circular dependency detected
            msg = f"Circular dependency detected involving {node}"
            raise Exception(msg)

        if status[node] == VISITED:
            return

        status[node] = VISITING

        # Visit all dependencies first
        for neighbor in graph.get(node, set()):
            if neighbor in status:  # Only process nodes that exist in the graph
                dfs(neighbor)

        status[node] = VISITED
        result.append(node)

    # First process models with dependencies
    for node in list(graph.keys()):  # Use list() to avoid modification during iteration issues
        # Check if node exists in schemas before accessing it
        if node in schemas and node in status and status[node] == UNVISITED:
            # Pass schemas to has_only_native_types
            if not has_only_native_types(schemas[node], schemas):
                dfs(node)

    # Then add remaining models (native types only or nodes not in schemas)
    for node in list(graph.keys()):  # Use list()
        if node in status and status[node] == UNVISITED:
            dfs(node)

    # Return the list in dependency order (dependencies first)
    # In a DFS topological sort, the last nodes added are those with no dependencies
    # (i.e., independent nodes that other nodes depend on), so we don't need to reverse
    return result
