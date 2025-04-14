"""
Template handling for SDK generation.
"""

import os
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader
import importlib.resources as pkg_resources

# Import helper functions needed in templates
from damascus.core.types import to_snake_case, get_type_from_schema
from damascus.core.schema import get_response_type, get_request_body_parameters


def get_template_dir() -> str:
    """
    Gets the path to the templates directory using importlib.resources.

    Returns:
        The path to the templates directory
    """
    # Use importlib.resources to reliably find the package data
    # Assumes 'templates' is adjacent to the 'damascus' package directory
    # This returns a Traversable, Jinja's loader needs a string path.
    try:
        # Use the modern API if available (Python 3.9+)
        return str(pkg_resources.files('damascus') / 'templates')
    except AttributeError:
        # Fallback for Python 3.8 using deprecated API
        # This context manager provides a temporary concrete path
        with pkg_resources.path('damascus', 'templates') as p:
            return str(p)


def load_environment(template_dir: Optional[str] = None) -> Environment:
    """
    Loads and configures the Jinja2 environment.

    Args:
        template_dir: Optional path to a directory containing custom templates.
                       If None, uses the default templates directory.

    Returns:
        A configured Jinja2 Environment
    """
    if template_dir is None:
        # Get the template directory using the updated function
        template_dir = get_template_dir()

    # Ensure template_dir is a valid directory path string
    if not isinstance(template_dir, str) or not os.path.isdir(template_dir):
         # It's possible the lookup failed or returned an unexpected type.
         # Add error handling or logging here if needed.
         # For now, raise an error if the directory isn't found.
         raise FileNotFoundError(f"Template directory not found or invalid: {template_dir}")

    # Create the environment
    env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)

    # Add helper functions to Jinja globals
    env.globals['to_snake_case'] = to_snake_case
    env.globals['get_type_from_schema'] = get_type_from_schema
    env.globals['get_response_type'] = get_response_type
    env.globals['get_request_body_parameters'] = get_request_body_parameters

    return env


def render_template(template_name: str, context: Dict[str, Any], template_dir: Optional[str] = None) -> str:
    """
    Renders a template with the given context.

    Args:
        template_name: The name of the template to render
        context: The context data to pass to the template
        template_dir: Optional path to a directory containing custom templates.

    Returns:
        The rendered template as a string

    Raises:
        Exception: If the template cannot be loaded or rendered
    """
    env = load_environment(template_dir)
    template = env.get_template(template_name)
    return template.render(**context)
