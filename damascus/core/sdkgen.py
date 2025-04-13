import json
import re
import os
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Set, cast
from jinja2 import Environment, FileSystemLoader


def generate_sdk(openapi_spec_path: str, output_dir: str = "generated_sdk", py_version: float = 3.13) -> None:
    """
    Generates a Python SDK from an OpenAPI specification using Jinja2 templates.

    Args:
        openapi_spec_path: Path to the OpenAPI specification (JSON file) or URL.
        output_dir: Directory to create the SDK in.
        py_version: Target Python version for the SDK.
    """

    # Check if the input is a URL or a file path
    is_url = openapi_spec_path.startswith(("http://", "https://"))

    if is_url:
        try:
            with urllib.request.urlopen(openapi_spec_path) as response:
                spec = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            print(f"Error: Failed to fetch OpenAPI spec from URL: {e}")
            return
    else:
        try:
            with open(openapi_spec_path, "r") as f:
                spec = json.load(f)
        except FileNotFoundError:
            print(f"Error: OpenAPI spec file not found: {openapi_spec_path}")
            return

    # Flag for Python version-specific features
    # For testing consistency, set a hard cutoff at 3.10
    use_modern_py = py_version >= 3.10

    # --- Create output directory structure first ---
    # This ensures the directory exists even if template loading fails
    os.makedirs(output_dir, exist_ok=True)

    # Determine if OpenAPI 3.0+ (components) or Swagger/OpenAPI 2.0 (definitions)
    is_openapi3 = "components" in spec
    schemas_dict = {}

    if is_openapi3:
        schemas_dict = spec.get("components", {}).get("schemas", {})
    else:
        # Handle Swagger 2.0 format
        schemas_dict = spec.get("definitions", {})

    # --- Helper Functions ---
    def to_snake_case(name: str) -> str:
        """Converts a string to snake_case."""
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    def get_response_type(responses: dict) -> str:
        """
        Determines the response type from the responses section, handling refs.
        """
        if "200" in responses:
            content = responses["200"].get("content") if is_openapi3 else None
            schema = None

            if is_openapi3 and content:
                if "application/json" in content:
                    schema = content["application/json"].get("schema")
                elif "application/x-ndjson" in content:
                    return "requests.Response"  # Streaming
            else:
                # OpenAPI 2.0 / Swagger format
                schema = responses["200"].get("schema")

            if schema:
                return get_type_from_schema(schema)

            return "None" if not schema else "dict"

        if "204" in responses:
            return "None"  # No Content
        return "dict"  # Default fallback

    def get_type_from_schema(schema: dict) -> str:
        """
        Extracts Python type from schema, handling refs and primitives.
        """
        # Instead of trying to hash the dict directly, we'll use a more direct approach
        if not schema:
            return "Any"

        if "$ref" in schema:
            # Resolve references - handle both OpenAPI 3 and Swagger 2 formats
            ref_path = schema["$ref"]
            ref_name = ref_path.split("/")[-1]

            ref_schema = None
            if is_openapi3:
                ref_schema = spec.get("components", {}).get("schemas", {}).get(ref_name)
            else:
                ref_schema = spec.get("definitions", {}).get(ref_name)

            if ref_schema:
                # Treat referenced schemas as dict or use the model name if it's a response model
                return cast(str, ref_name if ref_name in response_models else "dict")
            else:
                # Return "str" for unresolved refs as a fallback
                return cast(str, "str")

        if "anyOf" in schema:
            # Return "str" for anyOf as a fallback
            return cast(str, "str")
        if "oneOf" in schema:
            # Return "str" for oneOf as a fallback
            return cast(str, "str")

        schema_type = schema.get("type")
        if schema_type == "array":
            # Handle array items safely
            items = schema.get("items", {})
            return cast(str, f"List[{get_type_from_schema(items)}]")
        if schema_type == "integer":
            return cast(str, "int")
        if schema_type == "number":
            return cast(str, "float")
        if schema_type == "boolean":
            return cast(str, "bool")
        if schema_type == "string":
            return cast(str, "str")
        if schema_type == "object":
            return cast(str, "dict")
        # Final fallback: return "str"
        return cast(str, "str")

    def get_default_value(schema: dict) -> Any:
        """
        Returns the default value for a schema, handling different types.
        Returns a string representation suitable for code generation.
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
            return "None"  # Fallback.  Shouldn't normally happen.

    def get_request_body_params(request_body: Optional[Dict]) -> List[Dict]:
        """Extracts and flattens request body parameters."""
        if not request_body:
            return []

        # Handle OpenAPI 3.0 format
        if is_openapi3:
            content = request_body.get("content", {})
            if "application/json" not in content:
                return []

            schema = content["application/json"].get("schema")
            if not schema:
                return []

            if "$ref" in schema:
                ref_name = schema["$ref"].split("/")[-1]
                schema = schemas_dict.get(ref_name)
                if not schema:
                    return []
        else:
            # Handle Swagger/OpenAPI 2.0 format - request body is in parameters
            schema = request_body
            if not schema:
                return []

        if schema.get("type") == "object":
            properties = schema.get("properties", {})
            params = []
            for name, prop_schema in properties.items():
                param_info = {
                    "name": to_snake_case(name),
                    "type": get_type_from_schema(prop_schema),
                    "required": name in schema.get("required", []),
                    "description": prop_schema.get("description", ""),
                    "in": "body",  # Mark as coming from the body
                    "default": get_default_value(prop_schema),  # Get default
                }
                params.append(param_info)
            return params

        # Handle other schema types if needed (e.g., array, string)
        return []  # Return empty list for unsupported types

    def extract_request_body_from_parameters(parameters: List[Dict]) -> Optional[Dict]:
        """
        Extracts the body parameter from Swagger 2.0 style parameters.
        Returns the body parameter schema or None if not found.
        """
        if not parameters:
            return None

        for param in parameters:
            if param.get("in") == "body" and "schema" in param:
                return param.get("schema")

        return None

    def build_dependency_graph(schemas: Dict[str, Dict]) -> Dict[str, List[str]]:
        """Builds a dependency graph of model classes."""

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

        graph: Dict[str, List[str]] = {}
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

    def has_only_native_types(schema: Dict) -> bool:
        """Check if a schema only uses native types (no refs)."""

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

    def topological_sort(graph: Dict[str, List[str]], schemas: Dict) -> List[str]:
        """Performs a topological sort, prioritizing models with only native types."""
        visited = set()
        recursion_stack = set()
        sorted_list = []

        def visit(node: str) -> None:
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
            if not has_only_native_types(schemas[node]):
                visit(node)

        # Then add remaining models (native types only)
        for node in graph:
            if node not in visited:
                visit(node)

        return sorted_list[::-1]  # Reverse to get correct dependency order

    def identify_response_schemas(openapi_spec: Dict[str, Any]) -> Set[str]:
        """
        Identifies schemas used in responses throughout the API spec.
        Returns a set of schema names used in any successful response.
        """
        response_schemas = set()
        paths = openapi_spec.get("paths", {})

        for path_item in paths.values():
            for method_spec in path_item.values():
                if not isinstance(method_spec, dict):
                    continue

                responses = method_spec.get("responses", {})
                success_responses = [r for r in responses.keys() if r.startswith("2")]

                for status_code in success_responses:
                    response = responses[status_code]

                    # Handle OpenAPI 3.0 format
                    if is_openapi3:
                        content = response.get("content", {})

                        for content_type, content_schema in content.items():
                            if content_type == "application/json":
                                schema = content_schema.get("schema", {})

                                # Extract schema names from direct refs
                                if "$ref" in schema:
                                    ref_name = schema["$ref"].split("/")[-1]
                                    response_schemas.add(ref_name)

                                # For array responses, check items
                                if schema.get("type") == "array" and "items" in schema:
                                    if "$ref" in schema["items"]:
                                        ref_name = schema["items"]["$ref"].split("/")[-1]
                                        response_schemas.add(ref_name)
                    # Handle Swagger 2.0 format
                    else:
                        schema = response.get("schema", {})
                        if schema:
                            # Extract schema names from direct refs
                            if "$ref" in schema:
                                ref_name = schema["$ref"].split("/")[-1]
                                response_schemas.add(ref_name)

                            # For array responses, check items
                            if schema.get("type") == "array" and "items" in schema:
                                if "$ref" in schema["items"]:
                                    ref_name = schema["items"]["$ref"].split("/")[-1]
                                    response_schemas.add(ref_name)

        return response_schemas

    def resolve_schema_dependencies(schema_names: Set[str], all_schemas: Dict[str, Dict]) -> Set[str]:
        """
        Recursively resolves all dependencies for a set of schema names.
        Returns a set containing the original schemas plus all their dependencies.
        """

        def get_refs(schema: Dict) -> List[str]:
            refs = []
            if "$ref" in schema:
                refs.append(schema["$ref"].split("/")[-1])
            elif schema.get("type") == "array" and "items" in schema:
                if "$ref" in schema["items"]:
                    refs.append(schema["items"]["$ref"].split("/")[-1])
            elif schema.get("type") == "object" and "properties" in schema:
                for prop in schema["properties"].values():
                    refs.extend(get_refs(prop))
            elif "anyOf" in schema:
                for item in schema["anyOf"]:
                    refs.extend(get_refs(item))
            elif "allOf" in schema:
                for item in schema["allOf"]:
                    refs.extend(get_refs(item))
            elif "oneOf" in schema:
                for item in schema["oneOf"]:
                    refs.extend(get_refs(item))
            return refs

        result = set(schema_names)
        pending = list(schema_names)

        while pending:
            current = pending.pop()
            if current in all_schemas:
                schema = all_schemas[current]
                # Get all direct refs from this schema
                for ref in get_refs(schema):
                    if ref not in result and ref in all_schemas:
                        result.add(ref)
                        pending.append(ref)

        return result

    def generate_model_code(schema_name: str, schema: Dict, schemas: Dict[str, Dict], use_modern_py: bool) -> str:
        """
        Generates Python code for a model class based on a schema.
        """
        # Generate class documentation
        description = schema.get("description", f"Model for {schema_name}")
        class_doc = f'    """{description}"""' if description else ""

        # Generate fields with type annotations
        fields = []
        required_fields = []
        optional_fields = []

        required_props = schema.get("required", [])

        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                snake_name = to_snake_case(prop_name)
                field_type = get_schema_field_type(prop_schema, schemas, use_modern_py)

                # Add property documentation if available
                prop_doc = prop_schema.get("description", "")
                if prop_doc:
                    field_doc = f"    # {prop_doc}"
                    if prop_name in required_props:
                        required_fields.append(field_doc)
                    else:
                        optional_fields.append(field_doc)

                # Add the field with type annotation
                if prop_name in required_props:
                    # Required field - no default value
                    required_fields.append(f"    {snake_name}: {field_type}")
                else:
                    # Optional field - add default=None
                    optional_type = f"{field_type} | None" if use_modern_py else f"Optional[{field_type}]"
                    optional_fields.append(f"    {snake_name}: {optional_type} = None")

        # Combine fields with required fields first, then optional
        fields = required_fields + optional_fields

        class_code = ["@dataclass(frozen=True)", f"class {schema_name}:", class_doc]

        if fields:
            class_code.extend(fields)
        else:
            class_code.append("    pass  # No properties defined")

        return "\n".join(class_code)

    def get_schema_field_type(schema: Dict, schemas: Dict[str, Dict], use_modern_py: bool) -> str:
        """
        Gets the Python type for a schema field, resolving references to other models.
        """
        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            # Reference to another model - use the class name directly
            return cast(str, ref_name)

        schema_type = schema.get("type")

        if schema_type == "array":
            item_type = get_schema_field_type(schema.get("items", {}), schemas, use_modern_py)
            return cast(str, f"List[{item_type}]")

        if schema_type == "object":
            return cast(str, "Dict[str, Any]")  # Keep specific type for object

        if schema_type == "string":
            format_type = schema.get("format")
            if format_type == "date-time":
                return cast(str, "datetime")  # Use datetime for date-time format
            if format_type == "date":
                return cast(str, "date")  # Use date for date format
            return cast(str, "str")

        if schema_type == "integer":
            return cast(str, "int")

        if schema_type == "number":
            return cast(str, "float")

        if schema_type == "boolean":
            return cast(str, "bool")

        if "anyOf" in schema or "oneOf" in schema:
            # Return "str" for anyOf/oneOf as a fallback
            return cast(str, "str")

        # Default fallback: return "str"
        return cast(str, "str")

    def generate_response_models(
        response_schemas: Set[str],
        all_schemas: Dict[str, Dict],
        output_dir: str,
        use_modern_py: bool,
    ) -> Dict[str, str]:
        """
        Generates response model classes and saves them to the models directory.
        Returns a dict mapping schema names to their model class names.
        """
        if not response_schemas:
            return {}

        # Create models directory
        models_dir = os.path.join(output_dir, "models")
        os.makedirs(models_dir, exist_ok=True)

        # Get dependencies and build the graph
        response_schema_dict = {name: all_schemas[name] for name in response_schemas if name in all_schemas}
        if not response_schema_dict:
            print("No valid response schemas found")
            return {}

        # Build dependency graph for topological sorting
        graph = build_dependency_graph(response_schema_dict)

        try:
            # Sort schemas in dependency order
            sorted_schemas = topological_sort(graph, response_schema_dict)
        except ValueError as e:
            print(f"Warning: {e}. Using original schema order.")
            sorted_schemas = list(response_schema_dict.keys())

        # Create imports for model.py
        imports = [
            "from dataclasses import dataclass",
            "from typing import List, Dict, Any, Optional, Union",
            "from datetime import datetime, date",
        ]

        model_classes = []
        response_models = {}

        # Generate model classes in sorted order
        for schema_name in sorted_schemas:
            schema = response_schema_dict[schema_name]
            model_code = generate_model_code(schema_name, schema, all_schemas, use_modern_py)
            model_classes.append(model_code)
            response_models[schema_name] = schema_name

        # Write models.py file
        models_file = os.path.join(models_dir, "models.py")
        with open(models_file, "w") as f:
            f.write("\n".join(imports))
            f.write("\n\n\n")  # Add spacing
            f.write("\n\n".join(model_classes))

        return response_models

    def create_models_init(response_models: Dict[str, str], models_dir: str) -> None:
        """
        Creates the __init__.py file in the models directory to export all models.
        """
        if not response_models:
            return

        # Create exports
        exports = [f"from .models import {model_name}" for model_name in response_models.values()]
        exports.append(f"\n__all__ = {list(response_models.values())}")

        # Write __init__.py file
        init_file = os.path.join(models_dir, "__init__.py")
        with open(init_file, "w") as f:
            f.write("\n".join(exports))

    # Define response_models at a higher scope so get_type_from_schema can use it
    response_models = {}

    def prepare_client_data(spec: Dict[str, Any], use_modern_py: bool, response_models: Dict[str, str]) -> Dict[str, Any]:
        """
        Prepares data for the client template, including models.
        """

        # Handle request body extraction based on API spec version
        def get_request_body(method_spec: Dict[str, Any]) -> Optional[Dict]:
            if is_openapi3:
                return method_spec.get("requestBody")
            else:
                # Swagger 2.0 - parameters with "in: body"
                return extract_request_body_from_parameters(method_spec.get("parameters", []))

        client_data = {
            "title": spec["info"]["title"].replace(" ", ""),
            "description": spec["info"].get("description", ""),
            "base_url": spec.get("servers", [{"url": spec.get("host", "http://localhost")}])[0]["url"],
            "paths": spec["paths"],
            "to_snake_case": to_snake_case,
            "get_response_type": get_response_type,
            "get_type_from_schema": get_type_from_schema,
            "get_request_body_params": get_request_body_params,
            "get_request_body": get_request_body,
            "get_default_value": get_default_value,
            "security_schemes": (spec.get("components", {}).get("securitySchemes", {}) if is_openapi3 else spec.get("securityDefinitions", {})),
            "async_support": True,  # Enable async support by default
            "use_modern_py": use_modern_py,  # Pass Python version flag
            "response_models": response_models,  # Add response models
            "is_openapi3": is_openapi3,  # Pass API version info
        }
        return client_data

    # --- Template Loading ---
    # Update the template directory path to be within the damascus package
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)
    try:
        client_template = env.get_template("client.py.j2")
    except Exception as e:
        print(f"Error: Could not find templates. {e}")
        return

    # --- Model Generation for Responses ---
    if schemas_dict:
        # Identify response schemas
        response_schema_names = identify_response_schemas(spec)

        if response_schema_names:
            print(f"Found {len(response_schema_names)} response schemas")

            # Resolve dependencies (add schemas that response schemas depend on)
            response_schema_names = resolve_schema_dependencies(response_schema_names, schemas_dict)

            # Generate model classes for response schemas
            response_models = generate_response_models(response_schema_names, schemas_dict, output_dir, use_modern_py)

            if response_models:
                # Create models/__init__.py to export all models
                create_models_init(response_models, os.path.join(output_dir, "models"))

    # --- Client Generation ---
    # Prepare data for the client template
    client_data = prepare_client_data(spec, use_modern_py, response_models)

    # Render the client template
    client_code = client_template.render(**client_data)
    client_file_path = os.path.join(output_dir, "__init__.py")  # client in __init__.py
    with open(client_file_path, "w") as f:
        f.write(client_code)

    print(f"SDK generated and saved to {output_dir}")


# --- Main Execution (When run directly) ---
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # If a file path is provided as an argument
        openapi_file = sys.argv[1]
        print(f"Generating SDK from: {openapi_file}")
        generate_sdk(openapi_file)
    else:
        # Default behavior
        print("No OpenAPI file specified, using default: openapi.json")
        print("Usage: python -m damascus.core.sdkgen [path_to_openapi_json or URL]")
        generate_sdk("openapi.json")
