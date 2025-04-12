"""
Main SDK generation orchestration.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional, Set

from damascus.core.types import to_snake_case, get_type_from_schema, get_default_value
from damascus.core.schema import (
    get_request_body_params,
    get_response_type,
    get_response_model,
    build_dependency_graph,
    has_only_native_types,
    topological_sort
)
from damascus.core.template import render_template


def generate_sdk(openapi_spec_path: str, output_dir: str = "generated_sdk", py_version: float = 3.13) -> bool:
    """
    Generates a Python SDK from an OpenAPI specification using Jinja2 templates.

    Args:
        openapi_spec_path: Path to the OpenAPI specification (JSON file) or URL.
        output_dir: Directory to create the SDK in.
        py_version: Target Python version for the SDK.
        
    Returns:
        True if generation was successful, False otherwise
    """
    # Load the OpenAPI spec
    spec = load_openapi_spec(openapi_spec_path)
    if not spec:
        return False
        
    # Flag for Python version-specific features
    # For testing consistency, set a hard cutoff at 3.10
    use_modern_py = py_version >= 3.10

    # Create output directory structure first
    # This ensures the directory exists even if template loading fails
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # --- Model Generation ---
        # Generate model classes for responses
        components_schemas = spec.get("components", {}).get("schemas", {})
        if components_schemas:
            # Create models directory
            models_dir = os.path.join(output_dir, "models")
            os.makedirs(models_dir, exist_ok=True)
            
            # Identify schemas used in responses
            response_schemas = identify_response_schemas(spec)
            
            # Create model files
            response_models = generate_response_models(
                response_schemas, 
                components_schemas, 
                models_dir, 
                use_modern_py
            )
            
            # Create models/__init__.py to export all models
            create_models_init(response_models, models_dir)
        else:
            response_models = {}
        
        # Prepare data for the client template
        client_data = prepare_client_data(spec, use_modern_py, response_models)
        
        # Render the client template
        client_code = render_template("client.py.j2", client_data)
        
        # Write the generated code to file
        client_file_path = os.path.join(output_dir, "__init__.py")  # client in __init__.py
        with open(client_file_path, "w") as f:
            f.write(client_code)
            
        print(f"SDK generated and saved to {output_dir}")
        return True
    except Exception as e:
        print(f"Error generating SDK: {e}")
        return False


def load_openapi_spec(openapi_spec_path: str) -> Optional[Dict[str, Any]]:
    """
    Loads an OpenAPI specification from a file or URL.
    
    Args:
        openapi_spec_path: Path to the OpenAPI specification file or URL
        
    Returns:
        The loaded OpenAPI spec as a dictionary, or None if loading failed
    """
    # Check if the input is a URL or a file path
    is_url = openapi_spec_path.startswith(('http://', 'https://'))
    
    if is_url:
        try:
            with urllib.request.urlopen(openapi_spec_path) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.URLError as e:
            print(f"Error: Failed to fetch OpenAPI spec from URL: {e}")
            return None
    else:
        try:
            with open(openapi_spec_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: OpenAPI spec file not found: {openapi_spec_path}")
            return None
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in OpenAPI spec file: {openapi_spec_path}")
            return None


def identify_response_schemas(spec: Dict[str, Any]) -> Set[str]:
    """
    Identifies schemas used in responses.
    
    Args:
        spec: The OpenAPI specification
        
    Returns:
        A set of schema names used in responses
    """
    response_schemas = set()
    paths = spec.get("paths", {})
    
    # Function to extract schema reference from response content
    def extract_schema_ref(content: Dict) -> Optional[str]:
        if content and "application/json" in content:
            schema = content["application/json"].get("schema", {})
            if "$ref" in schema:
                ref = schema["$ref"]
                if ref.startswith("#/components/schemas/"):
                    return ref.split("/")[-1]
        return None
    
    # Process all paths and methods
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method in ("get", "post", "put", "delete", "patch"):
                responses = operation.get("responses", {})
                for status_code, response in responses.items():
                    if status_code == "200" or status_code == "201":
                        content = response.get("content", {})
                        schema_name = extract_schema_ref(content)
                        if schema_name:
                            response_schemas.add(schema_name)
    
    return response_schemas


def generate_response_models(
    response_schemas: Set[str], 
    components_schemas: Dict[str, Dict], 
    models_dir: str,
    use_modern_py: bool
) -> Dict[str, str]:
    """
    Generates model classes for responses.
    
    Args:
        response_schemas: Set of schema names used in responses
        components_schemas: The components/schemas section of the spec
        models_dir: Directory to save the model files
        use_modern_py: Whether to use modern Python features
        
    Returns:
        A mapping of schema names to their model class names
    """
    # Collect all schemas, including dependencies
    all_required_schemas = set(response_schemas)
    schemas_to_process = list(response_schemas)
    
    # Helper to extract schema references
    def extract_refs(schema: Dict) -> List[str]:
        refs = []
        
        if not schema:
            return refs
            
        # Direct reference
        if "$ref" in schema:
            ref = schema["$ref"].split("/")[-1]
            refs.append(ref)
            return refs
            
        # Array items
        if schema.get("type") == "array" and "items" in schema:
            refs.extend(extract_refs(schema["items"]))
            
        # Object properties
        if schema.get("type") == "object" and "properties" in schema:
            for prop in schema["properties"].values():
                refs.extend(extract_refs(prop))
                
        # Combined schemas
        for key in ["allOf", "anyOf", "oneOf"]:
            if key in schema:
                for sub_schema in schema[key]:
                    refs.extend(extract_refs(sub_schema))
                    
        return refs
    
    # Find all dependencies
    while schemas_to_process:
        schema_name = schemas_to_process.pop()
        schema = components_schemas.get(schema_name)
        
        if not schema:
            continue
            
        # Extract references
        refs = extract_refs(schema)
        
        # Add new references to process
        for ref in refs:
            if ref not in all_required_schemas:
                all_required_schemas.add(ref)
                schemas_to_process.append(ref)
    
    # Filter to only schemas that exist
    filtered_schemas = {name: components_schemas[name] for name in all_required_schemas if name in components_schemas}
    
    # Build dependency graph
    dependency_graph = build_dependency_graph(filtered_schemas)
    
    # Sort schemas in dependency order
    sorted_schemas = topological_sort(dependency_graph, filtered_schemas)
    
    # Generate model files
    model_mapping = {}  # Schema name -> Model class name
    
    for schema_name in sorted_schemas:
        schema = filtered_schemas[schema_name]
        
        # Convert schema name to class name
        class_name = schema_name
        if class_name.endswith("DTO"):
            class_name = class_name[:-3]
        
        # Save model mapping
        model_mapping[schema_name] = class_name
        
        # Generate model code
        model_code = generate_model_code(schema_name, schema, model_mapping, use_modern_py)
        
        # Write to file
        file_name = f"{to_snake_case(class_name)}.py"
        file_path = os.path.join(models_dir, file_name)
        
        with open(file_path, "w") as f:
            f.write(model_code)
            
    return model_mapping


def generate_model_code(
    schema_name: str, 
    schema: Dict[str, Any], 
    model_mapping: Dict[str, str],
    use_modern_py: bool
) -> str:
    """
    Generates Python code for a model class.
    
    Args:
        schema_name: The name of the schema
        schema: The schema definition
        model_mapping: Mapping of schema names to class names
        use_modern_py: Whether to use modern Python features
        
    Returns:
        Python code for the model class
    """
    # Create class name from schema name
    class_name = model_mapping[schema_name]
    
    # Process properties
    properties = schema.get("properties", {})
    required_props = schema.get("required", [])
    
    # Imports
    imports = ["from dataclasses import dataclass, field"]
    import_types = {"typing": set(), "models": set()}
    
    # Helper to add required imports
    def add_imports_for_type(prop_type: str, field_type_hint: str):
        if "List[" in field_type_hint:
            import_types["typing"].add("List")
        if "Dict[" in field_type_hint:
            import_types["typing"].add("Dict")
        if "Optional[" in field_type_hint:
            import_types["typing"].add("Optional")
        
        # Check for model references
        for model_schema, model_class in model_mapping.items():
            if model_class in field_type_hint and model_schema != schema_name:
                if not model_class.endswith("DTO"):
                    import_types["models"].add(model_class)
    
    # Separate required and optional properties
    required_fields = []
    optional_fields = []
    
    # First process required properties
    for prop_name in properties:
        if prop_name in required_props:
            prop_schema = properties[prop_name]
            snake_case_name = to_snake_case(prop_name)
            
            # Get type and handle possible models
            field_type = get_field_type(prop_schema, model_mapping)
            add_imports_for_type(field_type, field_type)
            
            # Add description as comment
            description = prop_schema.get("description", "")
            if description:
                required_fields.append(f"    # {description}")
            
            required_fields.append(f"    {snake_case_name}: {field_type}")
    
    # Then process optional properties
    for prop_name in properties:
        if prop_name not in required_props:
            prop_schema = properties[prop_name]
            snake_case_name = to_snake_case(prop_name)
            
            # Get type and handle possible models
            field_type = get_field_type(prop_schema, model_mapping)
            add_imports_for_type(field_type, field_type)
            
            # Add description as comment
            description = prop_schema.get("description", "")
            if description:
                optional_fields.append(f"    # {description}")
            
            # Default value handling
            default_value = get_default_value(prop_schema)
            
            # Optional fields
            if use_modern_py:
                # Python 3.10+ union syntax
                optional_fields.append(f"    {snake_case_name}: {field_type} | None = {default_value or 'None'}")
            else:
                # Python 3.8+ Optional syntax
                optional_fields.append(f"    {snake_case_name}: Optional[{field_type}] = {default_value or 'None'}")
    
    # Add imports
    final_imports = []
    final_imports.append("from dataclasses import dataclass")
    
    if import_types["typing"]:
        typing_imports = ", ".join(sorted(import_types["typing"]))
        final_imports.append(f"from typing import {typing_imports}")
    
    for model_class in sorted(import_types["models"]):
        snake_case = to_snake_case(model_class)
        final_imports.append(f"from .{snake_case} import {model_class}")
    
    # Combine everything
    code = []
    code.append('"""\n' + f"Model class for {schema_name}\n" + '"""\n')
    code.extend(final_imports)
    code.append("")
    code.append("")
    code.append("@dataclass")
    code.append(f"class {class_name}:")
    
    if description := schema.get("description", ""):
        code.append(f'    """{description}"""')
    
    # Add all required fields first, followed by optional fields
    if required_fields:
        code.extend(required_fields)
    if optional_fields:
        code.extend(optional_fields)
    if not required_fields and not optional_fields:
        code.append("    pass")
    
    return "\n".join(code)


def get_field_type(prop_schema: Dict[str, Any], model_mapping: Dict[str, str]) -> str:
    """
    Get the Python type for a property schema, handling models.
    
    Args:
        prop_schema: The property schema
        model_mapping: Mapping from schema names to class names
        
    Returns:
        The Python type string
    """
    # Direct reference to a model
    if "$ref" in prop_schema:
        ref = prop_schema["$ref"].split("/")[-1]
        if ref in model_mapping:
            return model_mapping[ref]
        return "dict"  # Fallback if model not in mapping
    
    # Array type
    if prop_schema.get("type") == "array":
        items = prop_schema.get("items", {})
        item_type = get_field_type(items, model_mapping)
        return f"List[{item_type}]"
    
    # Map basic types
    type_map = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "object": "dict",
    }
    
    schema_type = prop_schema.get("type")
    return type_map.get(schema_type, "Any")


def create_models_init(model_mapping: Dict[str, str], models_dir: str) -> None:
    """
    Create __init__.py file for the models package.
    
    Args:
        model_mapping: Mapping of schema names to class names
        models_dir: Directory path for models
    """
    imports = []
    exports = []
    
    for schema_name, class_name in model_mapping.items():
        snake_name = to_snake_case(class_name)
        imports.append(f"from .{snake_name} import {class_name}")
        exports.append(class_name)
    
    code = []
    code.append('"""')
    code.append("Response model classes.")
    code.append('"""\n')
    code.extend(imports)
    code.append("\n")
    code.append(f"__all__ = {repr(exports)}")
    
    # Write the file
    init_path = os.path.join(models_dir, "__init__.py")
    with open(init_path, "w") as f:
        f.write("\n".join(code))


def prepare_client_data(spec: Dict[str, Any], use_modern_py: bool, model_mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Prepares data for the client template.
    
    Args:
        spec: The OpenAPI specification
        use_modern_py: Whether to use modern Python features
        model_mapping: Mapping of schema names to model class names
        
    Returns:
        A dictionary of data to pass to the template
    """
    components_schemas = spec.get("components", {}).get("schemas", {})
    
    # Function to convert response type based on models
    def get_model_response_type(responses: Dict) -> str:
        if "200" in responses:
            content = responses["200"].get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                if "$ref" in schema:
                    ref_name = schema["$ref"].split("/")[-1]
                    if ref_name in model_mapping:
                        return f"models.{model_mapping[ref_name]}"
        
        # Fall back to standard response type if no model found
        return get_response_type(responses, components_schemas)
    
    return {
        "title": spec["info"]["title"].replace(" ", ""),
        "description": spec["info"]["description"],
        "base_url": spec.get("servers", [{"url": "http://localhost"}])[0]["url"],
        "paths": spec["paths"],
        "to_snake_case": to_snake_case,
        "get_response_type": get_model_response_type,
        "get_type_from_schema": lambda schema: get_type_from_schema(schema, components_schemas),
        "get_request_body_params": lambda request_body: get_request_body_params(request_body, components_schemas),
        "get_default_value": get_default_value,
        "get_response_model": lambda method_spec: get_response_model(method_spec, components_schemas),
        "security_schemes": spec.get("components", {}).get("securitySchemes", {}),
        "async_support": True,  # Enable async support by default
        "use_modern_py": use_modern_py,  # Pass Python version flag
        "has_models": bool(model_mapping),  # Indicate if models are used
    }


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
        print("Usage: python -m damascus.core [path_to_openapi_json or URL]")
        generate_sdk("openapi.json") 