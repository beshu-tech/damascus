"""
Template handling for SDK generation.
"""

import os
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader


def get_template_dir() -> str:
    """
    Gets the path to the templates directory.

    Returns:
        The path to the templates directory
    """
    # Templates are in the 'templates' directory at the same level as 'core'
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


def load_environment(template_dir: Optional[str] = None) -> Environment:
    """
    Loads and configures the Jinja2 environment.

    Args:
        template_dir: Optional path to a directory containing custom templates.

    Returns:
        A configured Jinja2 Environment
    """
    if template_dir is None:
        template_dir = get_template_dir()
    return Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)


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
