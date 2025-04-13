"""
Unit tests for the SDK generator functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import json
import tempfile
import shutil

from damascus.core import generate_sdk


class TestSDKGenerator(unittest.TestCase):
    """Test cases for the SDK generator."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test outputs
        self.test_dir = tempfile.mkdtemp()

        # Sample minimal OpenAPI spec
        self.sample_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "description": "API for testing SDK generation",
                "version": "1.0.0",
            },
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "get_test",
                        "summary": "Test endpoint",
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"message": {"type": "string"}},
                                        }
                                    }
                                },
                            }
                        },
                    }
                }
            },
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-KEY",
                    }
                },
            },
            "servers": [{"url": "https://api.example.com"}],
        }

        # Save the sample spec to a temporary file
        self.spec_file = os.path.join(self.test_dir, "test_openapi.json")
        with open(self.spec_file, "w") as f:
            json.dump(self.sample_spec, f)

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    @patch("damascus.core.generator.load_openapi_spec")
    def test_generate_sdk_from_file(self, mock_load_spec):
        """Test generating SDK from a local file."""
        # Mock the spec loading
        mock_load_spec.return_value = self.sample_spec

        # Generate the SDK
        output_dir = os.path.join(self.test_dir, "output_sdk")
        result = generate_sdk(self.spec_file, output_dir)

        # Verify the result
        self.assertTrue(result)

        # Verify spec was loaded
        mock_load_spec.assert_called_once_with(self.spec_file)

        # Check output directory was created
        self.assertTrue(os.path.exists(output_dir))

        # Check SDK file was created
        self.assertTrue(os.path.exists(os.path.join(output_dir, "__init__.py")))

    @patch("urllib.request.urlopen")
    @patch("damascus.core.generator.load_openapi_spec")
    def test_generate_sdk_from_url(self, mock_load_spec, mock_urlopen):
        """Test generating SDK from a remote URL."""
        # Mock spec loading
        mock_load_spec.return_value = self.sample_spec

        # Mock URL response (for reference, not used in the actual test)
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.sample_spec).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        # Generate the SDK
        output_dir = os.path.join(self.test_dir, "output_sdk_url")
        result = generate_sdk("https://example.com/api/openapi.json", output_dir)

        # Verify the result
        self.assertTrue(result)

        # Verify spec was loaded
        mock_load_spec.assert_called_once_with("https://example.com/api/openapi.json")

        # Check output directory was created
        self.assertTrue(os.path.exists(output_dir))

    @patch("damascus.core.generator.load_openapi_spec")
    def test_py_version_flag_in_data(self, mock_load_spec):
        """Test Python version flag affects client data preparation."""
        # Mock spec loading
        mock_load_spec.return_value = self.sample_spec

        # First test with Python 3.9
        output_dir_39 = os.path.join(self.test_dir, "output_sdk_py39")
        generate_sdk(self.spec_file, output_dir_39, py_version=3.9)

        # Then test with Python 3.10
        output_dir_310 = os.path.join(self.test_dir, "output_sdk_py310")
        generate_sdk(self.spec_file, output_dir_310, py_version=3.10)

        # Verify the directories were created
        self.assertTrue(os.path.exists(output_dir_39))
        self.assertTrue(os.path.exists(output_dir_310))

        # Verify the files were created
        self.assertTrue(os.path.exists(os.path.join(output_dir_39, "__init__.py")))
        self.assertTrue(os.path.exists(os.path.join(output_dir_310, "__init__.py")))

    @patch("damascus.core.generator.load_openapi_spec")
    def test_file_not_found(self, mock_load_spec):
        """Test error handling when spec file is not found."""
        # Mock load_openapi_spec to return None (indicating failure)
        mock_load_spec.return_value = None

        # Try to generate SDK with non-existent file
        output_dir = os.path.join(self.test_dir, "output_not_exist")

        # Call generate_sdk
        result = generate_sdk("non_existent_file.json", output_dir)

        # Verify function returned False
        self.assertFalse(result)

        # Verify load_openapi_spec was called
        mock_load_spec.assert_called_once_with("non_existent_file.json")

        # Check output directory was not created or is empty
        self.assertFalse(os.path.isfile(os.path.join(output_dir, "__init__.py")))

    @patch("urllib.request.urlopen")
    @patch("damascus.core.generator.load_openapi_spec")
    def test_url_error(self, mock_load_spec, mock_urlopen):
        """Test error handling when URL fetch fails."""
        # Mock load_openapi_spec to return None (indicating failure)
        mock_load_spec.return_value = None

        # Mock URLError (for reference, not used in the actual test)
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("Failed to fetch")

        # Try to generate SDK with invalid URL
        output_dir = os.path.join(self.test_dir, "output_url_error")

        # Call generate_sdk
        result = generate_sdk("https://invalid-url.example.com/openapi.json", output_dir)

        # Verify function returned False
        self.assertFalse(result)

        # Check output directory was not created or is empty
        self.assertFalse(os.path.isfile(os.path.join(output_dir, "__init__.py")))

    @patch("damascus.core.generator.render_template")
    @patch("damascus.core.generator.load_openapi_spec")
    def test_template_error(self, mock_load_spec, mock_render):
        """Test error handling when template rendering fails."""
        # Mock spec loading
        mock_load_spec.return_value = self.sample_spec

        # Mock template rendering to raise an exception
        mock_render.side_effect = Exception("Template rendering error")

        # Try to generate SDK
        output_dir = os.path.join(self.test_dir, "output_template_error")

        # Call generate_sdk
        result = generate_sdk(self.spec_file, output_dir)

        # Verify function returned False
        self.assertFalse(result)

        # Check output directory exists but is empty
        self.assertTrue(os.path.exists(output_dir))
        self.assertFalse(os.path.isfile(os.path.join(output_dir, "__init__.py")))


if __name__ == "__main__":
    unittest.main()
