<p align="center">
  <img src="logo.png" alt="Damascus Logo" width="250" />
</p>

# Damascus - OpenAPI SDK Generator

![License](https://img.shields.io/badge/license-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-green.svg)

Damascus is a powerful Python-based SDK generator that transforms OpenAPI specifications into elegant, type-safe client libraries. Generate professional client SDKs for your API with minimal effort.

## Key Features

- **Full Response Models**: Converts API schemas into proper Python dataclasses
- **Type Safety**: Comprehensive type annotations for modern Python development
- **Authentication Support**: Handles API key, Bearer token and other auth methods
- **Multiple Input Sources**: Generate from local JSON files or remote URLs
- **Template-Based**: Easily customizable code generation via Jinja2 templates
- **Python Version Targeting**: Generate code optimized for specific Python versions

## Installation

Using pip:
```bash
pip install damascus
```

Using uv (recommended):
```bash
uv pip install damascus
```

## Requirements

- **Runtime**: Python 3.8+
- **Development**: Python 3.10+ recommended for modern type hints
- **Dependencies**: Jinja2 for templating

## Quick Start

### CLI Usage

Generate an SDK from an OpenAPI specification:

```bash
# From a local file
damascus generate ./path/to/openapi.json --output my_sdk

# From a URL
damascus generate https://api.example.com/openapi.json --output my_sdk

# With custom headers (for protected specs)
damascus generate https://api.example.com/openapi.json --header "Authorization: Bearer token123" --output my_sdk
```

### SDK Usage

Once generated, using the SDK is straightforward:

```python
from my_sdk import Client

# Initialize client
client = Client(
    base_url="https://api.example.com",
    api_key="your-api-key"
)

# Call API methods - responses are typed objects
response = client.get_user(user_id=123)
print(f"User name: {response.name}")
```

## Documentation

Comprehensive documentation is available in the [docs/](docs/) directory:

- [CLI Usage Guide](docs/cli.md)
- [SDK Generation Options](docs/sdkgen.md)
- [Template Customization](docs/templates.md)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Damascus is licensed under the GNU General Public License v3.0 (GPLv3) - see the [LICENSE](LICENSE) file for details.

## About

Damascus is created and maintained by [Beshu Limited](https://beshu.tech), a UK company based in London, established in 2017.

Beshu Limited is best known for:
- [ReadonlyREST](https://readonlyrest.com/): Security for Elasticsearch and Kibana
- [Anaphora](https://anaphora.it/): Automated reporting and alerting for Kibana
