# Damascus CLI Documentation

Damascus provides a command-line interface (CLI) for generating Python SDK code from OpenAPI specifications.

## Installation

When you install Damascus, the CLI is automatically installed:

Using pip:
```bash
pip install damascus
```

Using uv (recommended):
```bash
uv pip install damascus
```

## Compatibility

The CLI supports Python 3.8 and above, while development of Damascus itself requires Python 3.13+.

## SDK Generator

Generate Python SDK code from OpenAPI specifications (either local file or remote URL).

```bash
# Basic usage with local file
damascus /tmp/myspecs.json -o my_proj_sdk_pkgname

# Basic usage with remote URL
damascus https://example.com/api/specs.json -o my_proj_sdk_packagename

# With custom HTTP headers (for remote specs)
damascus https://example.com/api/specs.json -o my_proj_sdk_packagename -h 'Authorization: Bearer token123' -h 'Custom-Header: value'

# Specify Python version compatibility
damascus /tmp/myspecs.json -o my_proj_sdk_pkgname --py-version 3.10
```

Options:

| Option | Description |
|--------|-------------|
| `-o, --output` | Output directory name for the generated SDK package |
| `-h, --header` | HTTP header for remote spec retrieval (can be specified multiple times) |
| `--py-version` | Target Python version compatibility (default: 3.13) |

## Error Handling

When an error occurs, the CLI will print an error message and exit with a non-zero status code:

```
Error: Failed to fetch OpenAPI spec from URL (Status: 404)
```

## Examples

### Generating SDK from Local OpenAPI Spec

```bash
damascus /tmp/myspecs.json -o my_company_sdk
```

### Generating SDK from Remote OpenAPI Spec with Authentication

```bash
damascus https://api.example.com/specs.json -o my_company_sdk -h 'Authorization: Bearer mytoken' -h 'API-Key: myapikey'
``` 