# Contributing to Damascus

Thank you for your interest in contributing to Damascus! This document provides guidelines and instructions for contributing to this project.

## Contributor License Agreement

Before your contribution can be accepted, you must sign the [Contributor License Agreement](CLA.md). This agreement provides Beshu Limited with a license to redistribute your contributions as part of the project.

## Getting Started

### Requirements

- Python 3.13+ for development
- uv package manager (recommended) or pip

Note: While development is done using Python 3.13+, the produced SDK supports Python 3.8+.

### Fork and Clone the Repository

1. Fork the [Damascus repository](https://github.com/beshu-tech/damascus) on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/damascus.git
   cd damascus
   ```
3. Add the original repository as upstream:
   ```bash
   git remote add upstream https://github.com/beshu-tech/damascus.git
   ```

### Set Up Development Environment

#### Using uv (Recommended)

1. Install uv if you don't have it already:
   ```bash
   pip install uv
   ```

2. Create a virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies separately to avoid circular imports:
   ```bash
   # First install dependencies
   uv pip install -r requirements-dev.txt
   
   # Then install the package in development mode
   uv pip install -e .
   ```

#### Using Traditional venv

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies separately:
   ```bash
   # Install uv
   pip install uv
   
   # First install dependencies
   uv pip install -r requirements-dev.txt
   
   # Then install the package in development mode
   uv pip install -e .
   ```

## Development Workflow

### Branching Strategy

- `main`: The main branch contains the latest stable release.
- `develop`: The development branch contains the latest code.
- Feature branches: Create a new branch for each feature or bugfix.

### Creating a Feature Branch

```bash
git checkout develop
git pull upstream develop
git checkout -b feature/your-feature-name
```

### Code Style

This project uses:
- [Black](https://black.readthedocs.io/) for code formatting
- [isort](https://pycqa.github.io/isort/) for import sorting
- [mypy](https://mypy.readthedocs.io/) for type checking
- [flake8](https://flake8.pycqa.org/) for linting

You can run these tools with:

```bash
# Format code
black damascus tests examples

# Sort imports
isort damascus tests examples

# Type checking
mypy damascus

# Linting
flake8 damascus tests examples
```

### Running Tests

First, make sure all test dependencies are installed:

```bash
# Install or update test dependencies
uv pip install pytest pytest-cov responses
```

Run tests with pytest:

```bash
# Run all tests
pytest

# Run with coverage report
python -m pytest --cov=damascus tests/

# Generate HTML coverage report
python -m pytest --cov=damascus --cov-report=html tests/

# Run specific test file
pytest tests/test_client.py

# Run with verbose output
pytest -v
```

### Common Test Issues

1. **Missing `responses` package**:
   ```
   ModuleNotFoundError: No module named 'responses'
   ```
   Fix by installing the responses package:
   ```bash
   uv pip install responses
   ```

2. **Unrecognized `--cov` argument**:
   ```
   ERROR: unrecognized arguments: --cov=damascus
   ```
   Fix by installing pytest-cov:
   ```bash
   uv pip install pytest-cov
   ```

3. **No data collected warning**:
   If you see "No data was collected" warning, make sure tests are actually running. If tests fail to collect or run, coverage data won't be generated.

### Troubleshooting

If you encounter issues with package installation:

1. Make sure your Python version is 3.13+
2. Try installing dependencies before the package:
   ```bash
   uv pip install -r requirements-dev.txt
   uv pip install -e .
   ```
3. Check for circular dependencies in imports

### Commit Guidelines

- Write clear, concise commit messages.
- Prefix your commit messages with the type of change:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation changes
  - `style:` for formatting changes
  - `refactor:` for code refactoring
  - `test:` for adding or modifying tests
  - `chore:` for build process or tooling changes

Example: `feat: add support for OIDC authentication`

## Pull Request Process

1. Update the documentation and tests for your changes.
2. Run all tests and style checks locally.
3. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
4. Open a pull request against the `develop` branch.
5. Ensure the PR description clearly describes the problem and solution.
6. Request review from a maintainer.

## Release Process

Releases are managed by the project maintainers. The general process is:

1. Update version number in `damascus/__init__.py`
2. Update CHANGELOG.md
3. Create a new release in GitHub

## Community

- For questions and discussions, please open a discussion on GitHub.
- For bug reports and feature requests, please open an issue on GitHub.

Thank you for contributing to Damascus! 