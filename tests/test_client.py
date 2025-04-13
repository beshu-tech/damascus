"""
Tests for the Damascus Client class.
"""

import pytest
import responses
from urllib.parse import urljoin
from unittest.mock import MagicMock, patch

from damascus import Client
from damascus.exceptions import AuthenticationError, ConfigurationError, DamascusError


class TestClient:
    """Test suite for the Client class."""

    def test_init_requires_base_url(self):
        """Test that a base URL is required."""
        with pytest.raises(ConfigurationError):
            Client(base_url=None, api_key="test-key")

    def test_init_requires_auth(self):
        """Test that either api_key or jwt_token is required."""
        with pytest.raises(AuthenticationError):
            Client(base_url="https://example.com")

    def test_init_with_api_key(self):
        """Test initialization with an API key."""
        client = Client(base_url="https://example.com", api_key="test-key")
        assert client.base_url == "https://example.com"
        assert client.api_key == "test-key"
        assert client.jwt_token is None
        client.close()

    def test_init_with_jwt_token(self):
        """Test initialization with a JWT token."""
        client = Client(base_url="https://example.com", jwt_token="test-token")
        assert client.base_url == "https://example.com"
        assert client.api_key is None
        assert client.jwt_token == "test-token"
        client.close()

    def test_headers_with_api_key(self):
        """Test that headers are set correctly with API key auth."""
        client = Client(base_url="https://example.com", api_key="test-key")
        assert client.session.headers["Authorization"] == "ApiKey test-key"
        client.close()

    def test_headers_with_jwt_token(self):
        """Test that headers are set correctly with JWT token auth."""
        client = Client(base_url="https://example.com", jwt_token="test-token")
        assert client.session.headers["Authorization"] == "Bearer test-token"
        client.close()

    @responses.activate
    def test_get_version(self):
        """Test the get_version method."""
        base_url = "https://example.com"
        client = Client(base_url=base_url, api_key="test-key")

        # Mock the API response
        responses.add(
            responses.GET,
            urljoin(base_url, "/api/version"),
            json={"version": "1.0.0", "build_date": "2023-08-15T12:00:00Z"},
            status=200,
        )

        # Call the method and check the response
        response = client.get_version()
        assert response["version"] == "1.0.0"
        assert response["build_date"] == "2023-08-15T12:00:00Z"
        client.close()

    @responses.activate
    def test_get_resources(self):
        """Test the get_resources method."""
        base_url = "https://api.example.com"
        api_key = "test_api_key"

        # Mock response data
        requests_mock = MagicMock()
        requests_mock.request.return_value.status_code = 200
        requests_mock.request.return_value.json.return_value = [
            {"resource_id": "res_v1", "description": "Core resource"},
            {"resource_id": "res_v2", "description": "Extended resource"},
        ]

        # Set up mock for the session
        with patch("damascus.client.requests.Session", return_value=requests_mock):
            client = Client(base_url=base_url, api_key=api_key)
            response = client.get_resources()

        # Verify request was made correctly
        requests_mock.request.assert_called_once()
        assert response[0]["resource_id"] == "res_v1"
        assert response[1]["resource_id"] == "res_v2"

    @responses.activate
    def test_error_handling(self):
        """Test error handling in the client."""
        base_url = "https://example.com"
        client = Client(base_url=base_url, api_key="test-key")

        # Mock the API response with an error
        responses.add(
            responses.GET,
            urljoin(base_url, "/api/version"),
            json={"message": "Unauthorized access"},
            status=401,
        )

        # Call the method and check the error handling
        with pytest.raises(DamascusError) as excinfo:
            client.get_version()

        assert "API request failed: Unauthorized access" in str(excinfo.value)
        assert excinfo.value.status_code == 401
        client.close()

    def test_context_manager(self):
        """Test using the client as a context manager."""
        with Client(base_url="https://example.com", api_key="test-key") as client:
            assert client.base_url == "https://example.com"
            assert client.api_key == "test-key"
