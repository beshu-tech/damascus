"""
Tests for verifying the generated SDK client API methods, parameters, and model types.
"""

import unittest
import json
import os
import tempfile
import shutil
import sys

from damascus.core.types import to_snake_case  # Import to_snake_case


class TestSDKTypes(unittest.TestCase):
    """Test cases for verifying SDK code generation with focus on types."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        # Define the output directory for generate_sdk
        self.sdk_dir = os.path.join(self.temp_dir, "generated_sdk_output")

        # Define the OpenAPI spec
        self.openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "version": "1.0.0",
                "description": "API for testing SDK generation",
            },
            "servers": [{"url": "https://api.example.com/v1"}],
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "summary": "List all users",
                        "parameters": [
                            {
                                "name": "page",
                                "in": "query",
                                "schema": {"type": "integer", "default": 1},
                                "required": False,
                            },
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer", "default": 10},
                                "required": False,
                            },
                            {
                                "name": "sort",
                                "in": "query",
                                "schema": {"type": "string", "enum": ["asc", "desc"]},
                                "required": False,
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "List of users",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UserList"}}},
                            }
                        },
                    },
                    "post": {
                        "operationId": "createUser",
                        "summary": "Create a new user",
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UserCreate"}}},
                        },
                        "responses": {
                            "201": {
                                "description": "User created",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}},
                            },
                            "400": {"description": "Bad request"},
                        },
                    },
                },
                "/users/{user_id}": {
                    "get": {
                        "operationId": "getUser",
                        "summary": "Get a user by ID",
                        "parameters": [
                            {
                                "name": "user_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "User found",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}},
                            },
                            "404": {"description": "User not found"},
                        },
                    },
                    "put": {
                        "operationId": "updateUser",
                        "summary": "Update a user",
                        "parameters": [
                            {
                                "name": "user_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UserUpdate"}}},
                        },
                        "responses": {
                            "200": {
                                "description": "User updated",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}},
                            }
                        },
                    },
                    "delete": {
                        "operationId": "deleteUser",
                        "summary": "Delete a user",
                        "parameters": [
                            {
                                "name": "user_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {"204": {"description": "User deleted"}},
                    },
                },
                "/items": {
                    "get": {
                        "operationId": "listItems",
                        "summary": "List all items",
                        "parameters": [
                            {
                                "name": "tags",
                                "in": "query",
                                "schema": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "required": False,
                            },
                            {
                                "name": "status",
                                "in": "query",
                                "schema": {
                                    "type": "string",
                                    "enum": ["active", "inactive", "pending"],
                                },
                                "required": False,
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "List of items",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ItemList"}}},
                            }
                        },
                    }
                },
            },
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "email": {"type": "string", "format": "email"},
                            "name": {"type": "string"},
                            "is_active": {"type": "boolean", "default": True},
                            "created_at": {"type": "string", "format": "date-time"},
                            "role": {
                                "type": "string",
                                "enum": ["admin", "user", "guest"],
                                "default": "user",
                            },
                            "settings": {
                                "type": "object",
                                "additionalProperties": {"type": "string"},
                            },
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["id", "email", "name", "created_at"],
                    },
                    "UserList": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/User"},
                            },
                            "total": {"type": "integer"},
                            "page": {"type": "integer"},
                            "limit": {"type": "integer"},
                        },
                        "required": ["items", "total", "page", "limit"],
                    },
                    "UserCreate": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "format": "email"},
                            "name": {"type": "string"},
                            "password": {"type": "string", "format": "password"},
                            "role": {
                                "type": "string",
                                "enum": ["admin", "user", "guest"],
                                "default": "user",
                            },
                        },
                        "required": ["email", "name", "password"],
                    },
                    "UserUpdate": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                            "is_active": {"type": "boolean"},
                            "settings": {
                                "type": "object",
                                "additionalProperties": {"type": "string"},
                            },
                        },
                    },
                    "Item": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "price": {"type": "number", "format": "float"},
                            "status": {
                                "type": "string",
                                "enum": ["active", "inactive", "pending"],
                            },
                            "description": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "created_at": {"type": "string", "format": "date-time"},
                            "owner": {"$ref": "#/components/schemas/User"},
                        },
                        "required": ["id", "name", "price", "status"],
                    },
                    "ItemList": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Item"},
                            },
                            "total": {"type": "integer"},
                        },
                        "required": ["items", "total"],
                    },
                },
                "securitySchemes": {
                    "BearerAuth": {"type": "http", "scheme": "bearer"},
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-KEY",
                    },
                },
            },
        }

        # Write the OpenAPI spec to a temporary file
        self.spec_file = os.path.join(self.temp_dir, "openapi.json")
        with open(self.spec_file, "w") as f:
            json.dump(self.openapi_spec, f)

        # Determine package name and directory based on spec title
        self.package_name = to_snake_case(self.openapi_spec["info"]["title"].lower())
        self.package_dir = os.path.join(self.sdk_dir, self.package_name)

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove the temporary directory and generated SDK
        shutil.rmtree(self.temp_dir)

        # Clean up sys.modules to remove any imported test SDK
        # Adjust the check to use the actual package name
        if self.package_name in sys.modules:
            del sys.modules[self.package_name]
        models_module_name = f"{self.package_name}.models"
        if models_module_name in sys.modules:
            del sys.modules[models_module_name]
        client_module_name = f"{self.package_name}.client"
        if client_module_name in sys.modules:
            del sys.modules[client_module_name]

        # Ensure the test directory is removed from path if it was added
        if self.sdk_dir in sys.path:
            sys.path.remove(self.sdk_dir)


if __name__ == "__main__":
    unittest.main()
