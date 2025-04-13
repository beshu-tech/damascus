"""
Command-line interface for Damascus.

Provides functionality to generate SDK code from OpenAPI specifications.
"""

import argparse
import os
import sys

from damascus.core.generator import generate_sdk, load_openapi_spec


def main() -> None:
    """
    Main entry point for the Damascus CLI.
    """
    parser = argparse.ArgumentParser(description="Damascus SDK Generator")

    # Main command arguments
    parser.add_argument("spec", help="Path to an OpenAPI specification file or URL")
    parser.add_argument("-o", "--output", required=True, help="Output directory for the generated SDK")
    parser.add_argument(
        "-p",
        "--package",
        help="Package name for the generated SDK (defaults to API title from spec)",
    )
    parser.add_argument(
        "--modern-python",
        action="store_true",
        help="Generate code using modern Python features (3.7+)",
    )
    parser.add_argument(
        "-H",
        "--header",
        action="append",
        help="HTTP headers for remote spec retrieval (format: 'Key: Value')",
    )

    args = parser.parse_args()

    # Process headers if provided
    headers = None
    if args.header:
        headers = {}
        for header in args.header:
            try:
                key, value = [x.strip() for x in header.split(":", 1)]
                headers[key] = value
            except ValueError:
                print(f"Error: Invalid header format '{header}'. Use 'Key: Value' format.")
                sys.exit(1)

    # Load OpenAPI spec
    try:
        openapi_spec = load_openapi_spec(args.spec, headers)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Generate SDK
    try:
        success = generate_sdk(
            openapi_spec=openapi_spec,
            output_dir=args.output,
            package_name=args.package,
            use_modern_py=args.modern_python,
        )

        if success:
            print(f"SDK generated successfully at {os.path.abspath(args.output)}")
        else:
            print("SDK generation failed")
            sys.exit(1)
    except Exception as e:
        print(f"Error generating SDK: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
