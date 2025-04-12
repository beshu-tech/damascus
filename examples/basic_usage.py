#!/usr/bin/env python3
"""
Basic usage example for Damascus SDK.

This example demonstrates the fundamental operations using Damascus:
- Connecting to the API
- Getting version information
- Listing available ontologies
- Error handling

Compatible with Python 3.8+ (Runtime requirements)
"""

import os
from pprint import pprint

from damascus import Client, DamascusError


def main():
    # Get credentials from environment variables or set them directly
    base_url = os.environ.get("DAMASCUS_BASE_URL", "https://your-elasticsearch-instance.com")
    api_key = os.environ.get("DAMASCUS_API_KEY", "your-api-key")
    
    # Initialize the client
    try:
        client = Client(
            base_url=base_url,
            api_key=api_key,
            timeout=20.0,
            verify_ssl=True,
            retry_enabled=True,
            max_retries=3
        )
        
        # Using the client as a context manager automatically closes the session
        with client:
            # Get version information
            print("\nGetting version information...")
            version_info = client.get_version()
            pprint(version_info)
            
            # List available ontologies
            print("\nListing available ontologies...")
            ontologies = client.get_ontologies()
            pprint(ontologies)
            
    except DamascusError as e:
        print(f"Error occurred: {e}")
        if hasattr(e, "status_code"):
            print(f"Status code: {e.status_code}")


if __name__ == "__main__":
    main() 