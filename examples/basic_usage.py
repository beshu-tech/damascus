#!/usr/bin/env python3
"""
Basic usage example for Damascus SDK.

This example demonstrates the fundamental operations using Damascus:
- Connecting to the API
- Setting custom headers
- Getting version information
- Listing available resources
- Error handling

Compatible with Python 3.8+ (Runtime requirements)
"""

import os
from pprint import pprint

from damascus import Client, DamascusError


def main():
    # Get credentials from environment variables or set them directly
    base_url = os.environ.get("DAMASCUS_BASE_URL", "https://your-api-instance.com")
    api_key = os.environ.get("DAMASCUS_API_KEY", "your-api-key")

    # Define custom headers
    custom_headers = {"X-API-Version": "1.0", "X-Request-ID": "example-request-123"}

    # Initialize the client
    try:
        client = Client(
            base_url=base_url,
            api_key=api_key,
            request_timeout=20.0,
            verify_ssl=True,
            retry_enabled=True,
            max_retries=3,
            headers=custom_headers,
        )

        # Using the client as a context manager automatically closes the session
        with client:
            # Get version information
            print("\nGetting version information...")
            version_info = client.get_version()
            pprint(version_info)

            # List available resources
            print("\nListing available resources...")
            resources = client.get_resources()
            pprint(resources)

    except DamascusError as e:
        print(f"Error occurred: {e}")
        if hasattr(e, "status_code"):
            print(f"Status code: {e.status_code}")


if __name__ == "__main__":
    main()
