#!/usr/bin/env python3
"""
SDK Generator Example for Damascus.

This example demonstrates how to use Damascus to generate a Python SDK from:
1. A local OpenAPI specification file
2. A remote OpenAPI specification URL with custom headers

Compatible with Python 3.8+ (Runtime requirements)
"""

import os
import tempfile
import urllib.request
from pathlib import Path

# Import the SDK generator directly from its new location
from damascus.core.sdkgen import generate_sdk


def generate_from_local_file():
    """Generate an SDK from a local OpenAPI specification file."""
    # Path to the OpenAPI specification file
    spec_path = "./openapi.json"  # Replace with your actual file path
    
    # Output directory for the generated SDK
    output_dir = "./my_company_sdk"
    
    print(f"Generating SDK from local file: {spec_path}")
    generate_sdk(spec_path, output_dir)
    print(f"SDK successfully generated in {output_dir}")


def generate_from_remote_url():
    """Generate an SDK from a remote OpenAPI specification URL with custom headers."""
    # Remote URL of the OpenAPI specification
    spec_url = "https://example.com/api/specs.json"  # Replace with actual URL
    
    # Custom headers for accessing the remote specification
    headers = {
        "Authorization": "Bearer token123",
        "Custom-Header": "value"
    }
    
    # Output directory for the generated SDK
    output_dir = "./my_remote_sdk"
    
    print(f"Generating SDK from remote URL: {spec_url}")
    
    # Create a request with headers
    request = urllib.request.Request(spec_url)
    for name, value in headers.items():
        request.add_header(name, value)
    
    # Fetch the specification
    with urllib.request.urlopen(request) as response:
        spec_json = response.read().decode('utf-8')
    
    # Save to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
        temp_path = temp_file.name
        temp_file.write(spec_json.encode('utf-8'))
    
    try:
        # Generate the SDK from the temporary file
        generate_sdk(temp_path, output_dir, py_version=3.10)
        print(f"SDK successfully generated in {output_dir}")
    finally:
        # Clean up the temporary file
        os.unlink(temp_path)


def main():
    """Run the example."""
    # Uncomment the example you want to run
    
    # Example 1: Generate from a local file
    # generate_from_local_file()
    
    # Example 2: Generate from a remote URL with custom headers
    # generate_from_remote_url()
    
    print("\nAlternatively, you can use the Damascus CLI:")
    print("\n# Generate from local file:")
    print("damascus /tmp/myspecs.json -o my_proj_sdk_pkgname")
    print("\n# Generate from remote URL with headers:")
    print("damascus https://example.com/api/specs.json -o my_proj_sdk_packagename -h 'Authorization: Bearer token123' -h 'Custom-Header: value'")


if __name__ == "__main__":
    main() 