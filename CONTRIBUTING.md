# Contributing to OWL-AGENT

Thank you for your interest in contributing to OWL-AGENT! This document provides guidelines and information for contributors.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How to Contribute](#how-to-contribute)
3. [Development Setup](#development-setup)
4. [Pull Request Process](#pull-request-process)
5. [Coding Standards](#coding-standards)
6. [Testing](#testing)
7. [Documentation](#documentation)
8. [License](#license)

## Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [GitHub Issues](https://github.com/owl-agent/owl-agent/issues)
2. If not, create a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the issue
   - Expected behavior
   - Actual behavior
   - Your environment (OS, Python version, etc.)

### Suggesting Features

1. Check if the feature has already been suggested in [GitHub Issues](https://github.com/owl-agent/owl-agent/issues)
2. If not, create a new issue with:
   - A clear, descriptive title
   - The problem your feature would solve
   - How you envision it working
   - Any alternatives you considered

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature/fix
3. Make your changes
4. Add or update tests
5. Update documentation
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.9+
- pip
- Git

### Setup

```bash
# Clone your fork
git clone https://github.com/your-username/owl-agent.git
cd owl-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov flake8 black isort mypy
```

### Environment Variables

```bash
export OWL_LOG_LEVEL=DEBUG
export OWL_TEST_MODE=true
```

## Pull Request Process

### 1. Create a Branch

```bash
# Create a branch for your feature/fix
git checkout -b feature/my-feature

# Or for a bug fix
git checkout -b fix/my-bug-fix
```

### 2. Make Changes

- Follow our [Coding Standards](#coding-standards)
- Add or update tests
- Update documentation as needed

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=proxy_defense

# Run specific test
pytest tests/test_proxy_defense.py
```

### 4. Lint and Format

```bash
# Check style
flake8 proxy_defense.py

# Format code
black proxy_defense.py

# Sort imports
isort proxy_defense.py

# Type checking
mypy proxy_defense.py
```

### 5. Commit Changes

```bash
# Stage changes
git add .

# Commit with a descriptive message
git commit -m "feat: add new feature description"

# Or for bug fixes
git commit -m "fix: describe the bug fix"

# Or for documentation
git commit -m "docs: update documentation"
```

### 6. Push and Create PR

```bash
# Push to your fork
git push origin feature/my-feature

# Create a pull request on GitHub
```

## Coding Standards

### Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use [Black](https://black.readthedocs.io/) for formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use [mypy](https://mypy-lang.org/) for type checking

### Code Organization

- Keep functions focused and small
- Use meaningful variable and function names
- Add docstrings to public functions and classes
- Use type hints for all public functions

### Example

```python
from typing import Optional, Dict, Any

def fetch_url(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Fetch a URL with proxy rotation and quality scoring.

    Args:
        url: The URL to fetch
        method: HTTP method (GET, POST, etc.)
        headers: Optional request headers
        **kwargs: Additional request parameters

    Returns:
        Dictionary containing response data

    Raises:
        ConnectionError: If the request fails after all retries
    """
    # Implementation here
    pass
```

## Testing

### Writing Tests

```python
import pytest
from proxy_defense import ResilientClient

@pytest.mark.asyncio
async def test_fetch_url():
    async with ResilientClient() as client:
        resp = await client.request("GET", "https://httpbin.org/get")
        assert resp.status == 200

@pytest.mark.asyncio
async def test_proxy_statistics():
    async with ResilientClient() as client:
        stats = await client.get_stats()
        assert "proxies_total" in stats
        assert "proxies_healthy" in stats
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_proxy_defense.py

# Run with coverage
pytest --cov=proxy_defense --cov-report=html

# Run in parallel
pytest -n auto
```

## Documentation

### Adding Documentation

1. Update the relevant markdown files
2. Add docstrings to new functions/classes
3. Include examples in documentation
4. Test documentation examples

### Documentation Style

- Use clear, concise language
- Include code examples
- Keep documentation up-to-date
- Use proper markdown formatting

## License

By contributing to OWL-AGENT, you agree that your contributions will be licensed under the MIT License.

## Questions?

If you have questions about contributing, please open an issue or reach out to the maintainers.
