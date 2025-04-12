"""
Pytest configuration for the Damascus test suite.
"""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_render_template():
    """Mock the template rendering function to avoid actual file operations during tests."""
    with patch('damascus.core.generator.render_template') as mock:
        mock.return_value = "# Generated SDK code"
        yield mock 