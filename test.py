import asyncio
import os
from pprint import pprint

from octostar_sdk import ApiError, ClientConfig, OctostarAPIClient

# Example function to demonstrate synchronous usage of the SDK
def test_sync_client():
    """
    Test synchronous client operations
    """
    # Get credentials from environment variables or use placeholders
    jwt_token = os.environ.get("OCTOSTAR_JWT_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.eyJ0aW1icl9iYXNlX3VybCI6Imh0dHBzOi8vZnVzaW9uLmRldi5vY3Rvc3Rhci5jb20iLCJpZCI6MywidXNlcm5hbWUiOiJhZG1pbiIsImVtYWlsIjoiYWRtaW5AZmFiLm9yZyIsInJvbGVzIjpbIkFkbWluIl0sInRpbWJyX3Rva2VuX2VuYyI6IjA0OWJmZjIyMjcwOTUxNzUyMmYzYjI0MjE2NTAzZGJhNzFhMDliMzY1OTNkMjZiZmI4MWIyM2ZmOWM4ODNhNzQzMWVlM2I4MWFiNDY5YzE0ZjFlMDQ2ZTk2NjRjMmRmMzVmNThhMjg5OGYyYzFiYTFlZjVmZjUyYmFjNjQ3N2FlYTQzYjdkZmE4NTk1MGI4ZWFmNzRiYWUwNGIxZTI2Yzg2NTJiMTQ0NDBiNjJjMjU5MWQ0NGE5MGRlNTk1OWFkMGRlOTliZTI1ZTY3YWMxM2UzZGZjYTExMzNkODFkNmZiZWVjNmU0ZTZmMTA0Y2VkNzBiNGQ1MTBlOWM0YTQ5OWIyY2E4ZmIwZTMzNzk1OGRhMGM2MjlmNjc3ZDIwZjVlYTE3YjQwMzNmZWZjZTg4NTdjNmExNGJjNjE3ZDZlM2MyMmQ2NjQ2NjQiLCJhc3luY19jaGFubmVsIjoiMDUxYTMwNTAtYmVkMS00MDU5LTk4ZGItNTMzNTQ3Nzg3YWM2Iiwic3ViIjozLCJpYXQiOjE3NDQzMTUzMzcsImV4cCI6MTc0NTYxMTMzNywiaXNzIjoib2N0b3N0YXJfcGxhdGZvcm0ifQ.u_ilbjAlQRK8tirf3WwA3zrOZBISIzwMJq_xm7o3gojALf7BkOymzdy1nON3g4euhDSPAUDlRa7ItcU5YNCgRA")
    ontology = os.environ.get("OCTOSTAR_ONTOLOGY", "os_ontology_v1")
    base_url = os.environ.get("OCTOSTAR_BASE_URL", "https://1973.pr.dev.octostar.com")
    
    # Create a custom client configuration
    config = ClientConfig(
        timeout=20.0,
        retry_enabled=True,
        max_retries=5,
        enable_type_checking=True
    )
    
    # Initialize the client
    client = OctostarAPIClient(
        jwt_token=jwt_token,
        ontology=ontology,
        base_url=base_url,
        config=config
    )
    
    try:
        # Get current user information
        #print("Getting user information...")
        #user_info = client.get_whoami()
        #print(f"Logged in as: {user_info.username} ({user_info.email})")
        
        # Get version information
        print("\nGetting version information...")
        version_info = client.get_version()
        print(f"Octostar version: {version_info.version}")
        
        # List available ontologies
        print("\nListing available ontologies...")
        ontologies = client.get_ontologies()
        print("Available ontologies:")
        for ont in ontologies:
            print(f"- {ont.ontology_name}")
        
        # Try to list running apps
        print("\nListing running apps...")
        apps = client.list_apps()
        print(f"Found {len(apps)} apps:")
        for app_id, app_info in apps.items():
            print(f"- {app_id}: {app_info.get('app_name', 'Unknown')}")
        
        # Example: Create a workspace (commented out to prevent actual creation)
        # print("\nCreating a workspace...")
        # workspace = client.create_workspace(os_item_name="Test Workspace")
        # print(f"Created workspace: {workspace.entity_id} ({workspace.entity_label})")
        
    except ApiError as e:
        print(f"API Error occurred: {str(e)}")
        if hasattr(e, "status_code"):
            print(f"Status code: {e.status_code}")
        if hasattr(e, "error_code"):
            print(f"Error code: {e.error_code}")
    finally:
        # Close the client session
        client.session.close()

# Example function to demonstrate asynchronous usage of the SDK
async def test_async_client():
    """
    Test asynchronous client operations
    """
    # Get credentials from environment variables or use placeholders
    jwt_token = os.environ.get("OCTOSTAR_JWT_TOKEN", "your_jwt_token_here")
    ontology = os.environ.get("OCTOSTAR_ONTOLOGY", "os_ontology_v1")
    base_url = os.environ.get("OCTOSTAR_BASE_URL", "https://octostar-api.example.com")
    
    # Initialize the client
    client = OctostarAPIClient(
        jwt_token=jwt_token,
        ontology=ontology,
        base_url=base_url
    )
    
    try:
        # Use the client as an async context manager
        async with client:
            # Example async operations could be added here when implemented in the SDK
            # For now, we'll use the synchronous methods
            
            print("\nAsync: Getting version information...")
            version_info = client.get_version()
            print(f"Octostar version: {version_info.version}")
            
    except ApiError as e:
        print(f"Async API Error occurred: {str(e)}")
    finally:
        # Ensure the client is closed
        await client.close()

# Example of working with secrets management
def test_secrets_management():
    """
    Demonstrate secrets management operations
    """
    # Initialize the client
    jwt_token = os.environ.get("OCTOSTAR_JWT_TOKEN", "your_jwt_token_here")
    ontology = os.environ.get("OCTOSTAR_ONTOLOGY", "os_ontology_v1")
    client = OctostarAPIClient(jwt_token=jwt_token, ontology=ontology)
    
    try:
        # Example app and workspace IDs
        app_id = "example-app-id"
        workspace = "example-workspace-id"
        entity_id = "example-entity-id"
        
        # Write a secret
        print("\nWriting secrets...")
        secrets_data = [
            {"key": "API_KEY", "value": "your-api-key-123"},
            {"key": "DATABASE_URL", "value": "postgresql://user:pass@localhost:5432/db"}
        ]
        
        response = client.write_secret(
            app_id=app_id,
            os_workspace=workspace,
            os_entity_id=entity_id,
            data=secrets_data
        )
        print(f"Write secret response: {response}")
        
        # Get secrets
        print("\nGetting secrets...")
        secrets = client.get_secret(
            app_id=app_id,
            os_workspace=workspace,
            os_entity_id=entity_id
        )
        print(f"Retrieved secrets: {secrets}")
        
        # Delete secrets (commented out to prevent actual deletion)
        # print("\nDeleting secrets...")
        # delete_response = client.delete_secret(
        #     app_id=app_id,
        #     os_workspace=workspace,
        #     os_entity_id=entity_id
        # )
        # print(f"Delete secret response: {delete_response}")
        
    except ApiError as e:
        print(f"Secrets API Error: {str(e)}")
    finally:
        client.session.close()

# Example of working with file operations
def test_file_operations():
    """
    Demonstrate file operations with the SDK
    """
    # Initialize the client
    jwt_token = os.environ.get("OCTOSTAR_JWT_TOKEN", "your_jwt_token_here")
    ontology = os.environ.get("OCTOSTAR_ONTOLOGY", "os_ontology_v1")
    client = OctostarAPIClient(jwt_token=jwt_token, ontology=ontology)
    
    try:
        # Example workspace and entity IDs
        workspace_id = "example-workspace-id"
        entity_id = "example-entity-id"
        
        # Request attachment upload URL
        print("\nRequesting attachment upload URL...")
        upload_response = client.request_attachment_upload(
            workspace_id=workspace_id,
            entity_id=entity_id
        )
        print(f"Upload URL: {upload_response.url}")
        print(f"S3 fields: {upload_response.fields}")
        
        # Get file tree for a workspace
        print("\nGetting files tree...")
        files_tree = client.get_files_tree(
            os_workspace=workspace_id,
            recurse=True,
            minimal=False
        )
        print(f"Files tree status: {files_tree.status}")
        print(f"Number of items: {len(files_tree.data) if files_tree.data else 0}")
        
    except ApiError as e:
        print(f"File operations API Error: {str(e)}")
    finally:
        client.session.close()

# Main execution
if __name__ == "__main__":
    print("=== Testing Octostar SDK ===")
    
    # Run synchronous tests
    test_sync_client()
    
    # Run secrets management tests
    # test_secrets_management()
    
    # Run file operations tests
    # test_file_operations()
    
    # Run asynchronous tests
    # asyncio.run(test_async_client())
    
    print("\n=== Tests completed ===")
