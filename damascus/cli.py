"""
Command-line interface for Damascus.

Provides functionality to generate SDK code from OpenAPI specifications.
"""

import os
import sys
import urllib.request
import tempfile
from typing import Optional, List

from damascus.cli_parser import parse_args
from damascus.core import generate_sdk


def handle_generate_sdk(spec_path: str, output_dir: str, headers: Optional[List[str]] = None, py_version: float = 3.13) -> bool:
    """
    Handle SDK generation from OpenAPI specification.
    
    Args:
        spec_path: Path to OpenAPI spec file or URL
        output_dir: Output directory for the generated SDK
        headers: Optional HTTP headers for remote spec retrieval
        py_version: Target Python version
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Process headers if provided
        header_dict = {}
        if headers:
            for header in headers:
                if ":" not in header:
                    print(f"Warning: Ignoring invalid header format: {header}")
                    continue
                name, value = header.split(":", 1)
                header_dict[name.strip()] = value.strip()
                
        # Handle URL vs local file
        is_url = spec_path.startswith(('http://', 'https://'))
        
        if is_url and headers:
            # For URLs with headers, we need to fetch the spec first
            request = urllib.request.Request(spec_path)
            for name, value in header_dict.items():
                request.add_header(name, value)
                
            with urllib.request.urlopen(request) as response:
                spec_json = response.read().decode('utf-8')
                
            # Save to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(spec_json.encode('utf-8'))
                
            try:
                # Generate SDK from the temporary file
                success = generate_sdk(temp_path, output_dir, py_version)
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
                
            return success
        else:
            # Generate directly from the path or URL
            return generate_sdk(spec_path, output_dir, py_version)
        
    except Exception as e:
        print(f"Error generating SDK: {e}")
        return False


def main() -> int:
    """Main CLI entry point."""
    args = parse_args()
    
    # Check if spec_path is provided
    if not args.spec_path:
        print("Error: OpenAPI specification path is required")
        print("Usage: damascus [spec_path] -o [output_dir]")
        return 1
    
    # Handle SDK generation
    success = handle_generate_sdk(
        args.spec_path, 
        args.output, 
        args.header, 
        args.py_version
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 