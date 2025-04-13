"""
Command-line argument parser for Damascus CLI.
"""

import argparse
from typing import Dict, Any

from damascus import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Damascus - Python SDK Generator for OpenAPI specifications",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--version", action="version", version=f"Damascus {__version__}")

    # Main SDK Generator command structure
    parser.add_argument("spec_path", nargs="?", help="Path to OpenAPI spec file or URL")
    parser.add_argument("-o", "--output", help="Output directory for the generated SDK package")
    parser.add_argument(
        "-h",
        "--header",
        action="append",
        help="HTTP header for remote spec retrieval (format: 'Name: Value')",
    )
    parser.add_argument(
        "--py-version",
        type=float,
        default=3.13,
        help="Target Python version compatibility",
    )

    return parser


def parse_args() -> Dict[str, Any]:
    """
    Parses command line arguments.

    Returns:
        A dictionary containing the parsed arguments.
    """
    parser = create_parser()
    args = parser.parse_args()

    # Validate required arguments
    if args.spec_path and not args.output:
        parser.error("the -o/--output argument is required for SDK generation")

    return vars(args)  # Convert Namespace to dict
