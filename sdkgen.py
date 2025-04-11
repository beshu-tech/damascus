import json
import re
import os
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader

def generate_sdk(openapi_spec_path: str, output_dir: str = "octostar_sdk", py_version: float = 3.13):
    """
    Generates a Python SDK from an OpenAPI specification using Jinja2 templates.

    Args:
        openapi_spec_path: Path to the OpenAPI specification (JSON file) or URL.
        output_dir: Directory to create the SDK in.
        py_version: Target Python version for the SDK.
    """

    # Check if the input is a URL or a file path
    is_url = openapi_spec_path.startswith(('http://', 'https://'))
    
    if is_url:
        try:
            with urllib.request.urlopen(openapi_spec_path) as response:
                spec = json.loads(response.read().decode('utf-8'))
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
    use_modern_py = py_version >= 3.10

    # --- Helper Functions ---
    def to_snake_case(name: str) -> str:
        """Converts a string to snake_case."""
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    def get_response_type(responses: dict) -> str:
        """
        Determines the response type from the responses section, handling refs.
        """
        if "200" in responses:
            content = responses["200"].get("content")
            if content:
                if "application/json" in content:
                    schema = content["application/json"].get("schema")
                    if schema:
                        return get_type_from_schema(schema)  # Use helper
                elif "application/x-ndjson" in content:
                    return "requests.Response"  # Streaming
                return "requests.Response"  # Other content types
            return "None"  # No content in 200 response
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
            # Resolve references to components/schemas
            ref_name = schema["$ref"].split("/")[-1]
            ref_schema = spec["components"]["schemas"].get(ref_name)
            if ref_schema:
                # Treat referenced schemas as dict
                return "dict"
            else:
                return "Any" # Unknown ref
        if "anyOf" in schema: return "Any"
        schema_type = schema.get("type")
        if schema_type == "array": 
            # Handle array items safely
            items = schema.get('items', {})
            return f"List[{get_type_from_schema(items)}]"
        if schema_type == "integer": return "int"
        if schema_type == "number": return "float"
        if schema_type == "boolean": return "bool"
        if schema_type == "string": return "str"
        if schema_type == "object": return "dict"
        return "Any"

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
            return "None" # Fallback.  Shouldn't normally happen.

    def get_request_body_params(request_body: Optional[Dict]) -> List[Dict]:
        """Extracts and flattens request body parameters."""
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
            schema = spec["components"]["schemas"].get(ref_name)
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
            if not has_only_native_types(schemas[node]):
                visit(node)

        # Then add remaining models (native types only)
        for node in graph:
            if node not in visited:
                visit(node)

        return sorted_list[::-1]  # Reverse to get correct dependency order

    def get_response_model(method_spec: dict) -> Optional[str]:
        """Generates dataclass code for response model if needed"""
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
                schema = spec["components"]["schemas"].get(ref_name, {})
            
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

    # --- Template Loading ---
    template_dir = os.path.join(os.path.dirname(__file__), "templates")  # templates alongside script
    env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)
    try:
        client_template = env.get_template("client.py.j2")
    except TemplateNotFound:
        print("Error: Could not find templates. Make sure 'client.py.j2' is in a 'templates' folder next to the script.")
        return

    # --- Create output directory structure ---
    os.makedirs(output_dir, exist_ok=True)

    # --- Model Generation ---
    if "components" in spec and "schemas" in spec["components"]:
        # Skip model generation entirely
        pass

    # --- Client Generation ---
    # Prepare data for the client template
    client_data = {
        "title": spec["info"]["title"].replace(" ", ""),
        "description": spec["info"]["description"],
        "base_url": spec.get("servers", [{"url": "http://localhost"}])[0]["url"],
        "paths": spec["paths"],
        "to_snake_case": to_snake_case,
        "get_response_type": get_response_type,
        "get_type_from_schema": get_type_from_schema,
        "get_request_body_params": get_request_body_params,
        "get_default_value": get_default_value, # Make available to template
        "get_response_model": get_response_model,
        "security_schemes": spec.get("components", {}).get("securitySchemes", {}),
        "async_support": True,  # Enable async support by default
        "use_modern_py": use_modern_py,  # Pass Python version flag
    }

    # Render the client template
    client_code = client_template.render(**client_data)
    client_file_path = os.path.join(output_dir, "__init__.py")  # client in __init__.py
    with open(client_file_path, "w") as f:
        f.write(client_code)

    print(f"SDK generated and saved to {output_dir}")


# --- Main Execution ---
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
        print("Usage: python sdkgen.py [path_to_openapi_json or URL]")
        generate_sdk("openapi.json")
