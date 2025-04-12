"""
Core functionality for Damascus SDK generation.
"""

# Import the main generator function
from damascus.core.generator import generate_sdk

# Import the necessary types and utility functions
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

# Define what gets imported with "from damascus.core import *"
__all__ = ["generate_sdk"] 