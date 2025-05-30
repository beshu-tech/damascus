"""
Base client module for Damascus-generated SDKs.
"""

import os
import requests
from typing import Dict, List, Optional, Any, cast, Type, Self
from types import TracebackType

from damascus.exceptions import AuthenticationError, ConfigurationError, DamascusError


class Client:
    """
    Base client for interacting with APIs through Damascus-generated SDKs.

    This client handles authentication, requests, and data parsing
    for operations with APIs that have an SDK generated by Damascus.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        jwt_token: Optional[str] = None,
        request_timeout: float = 10.0,
        verify_ssl: bool = True,
        retry_enabled: bool = True,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize a new API client.

        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            jwt_token: JWT token for authentication (alternative to api_key)
            request_timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            retry_enabled: Whether to enable automatic retries
            max_retries: Maximum number of retries for failed requests
            headers: Additional headers to include in all requests
        """
        self.base_url = base_url or os.environ.get("DAMASCUS_BASE_URL")
        if not self.base_url:
            raise ConfigurationError("Base URL is required. Provide it as an argument or set DAMASCUS_BASE_URL environment variable.")

        # Authentication setup
        self.api_key = api_key or os.environ.get("DAMASCUS_API_KEY")
        self.jwt_token = jwt_token or os.environ.get("DAMASCUS_JWT_TOKEN")

        if not (self.api_key or self.jwt_token):
            raise AuthenticationError(
                "Authentication credentials required. Provide either api_key or jwt_token, "
                "or set DAMASCUS_API_KEY or DAMASCUS_JWT_TOKEN environment variables."
            )

        # Session configuration
        self.session = requests.Session()
        self.request_timeout = request_timeout
        self.verify_ssl = verify_ssl

        # Retry configuration
        self.retry_enabled = retry_enabled
        self.max_retries = max_retries

        # Custom headers
        self.custom_headers = headers or {}

        # Set up default headers
        self._setup_headers()

    def _setup_headers(self) -> None:
        """Set up default headers for requests."""
        self.session.headers.update(
            {
                "User-Agent": "Damascus-SDK/Python",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        if self.api_key:
            self.session.headers.update({"Authorization": f"ApiKey {self.api_key}"})
        elif self.jwt_token:
            self.session.headers.update({"Authorization": f"Bearer {self.jwt_token}"})

        # Add custom headers
        if self.custom_headers:
            self.session.headers.update(self.custom_headers)

    def get_version(self) -> Dict[str, str]:
        """
        Get API version information.

        Returns:
            Dict containing version information
        """
        response = self._request("GET", "/api/version")
        return cast(Dict[str, str], response)

    def get_resources(self) -> List[Dict[str, Any]]:
        """
        Get available API resources.

        Returns:
            List of resource information
        """
        response = self._request("GET", "/api/resources")
        return cast(List[Dict[str, Any]], response)

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """
        Make a request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional request parameters (type Any)

        Returns:
            Parsed response data (type Any)

        Raises:
            DamascusError: If the request fails
        """
        if self.base_url is None:
            raise ConfigurationError("Base URL is not configured.")
        # Assign to local variable for better type narrowing
        base_url: str = self.base_url
        url = f"{base_url.rstrip('/')}{endpoint}"

        # Set default request parameters
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.request_timeout
        if "verify" not in kwargs:
            kwargs["verify"] = self.verify_ssl

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()

            if response.content:
                return response.json()
            return {}

        except requests.RequestException as e:
            # Handle errors
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("message", str(e))
                except ValueError:
                    error_message = e.response.text or str(e)

                raise DamascusError(f"API request failed: {error_message}", status_code=status_code) from e
            else:
                raise DamascusError(f"API request failed: {str(e)}") from e

    def close(self) -> None:
        """Close the client session."""
        self.session.close()

    def __enter__(self) -> Self:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        """Exit context manager and close session."""
        self.close()
