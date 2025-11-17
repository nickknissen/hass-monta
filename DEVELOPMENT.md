# Development Guide

This project uses `uv` for fast, reliable Python package management.

## Prerequisites

Install `uv` (see https://docs.astral.sh/uv/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or with pip:

```bash
pip install uv
```

## Setup Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nickknissen/hass-monta.git
   cd hass-monta
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   # Create venv and install all dependencies including dev and test
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Install project with dev dependencies
   uv pip install -e ".[dev,test]"
   ```

## Quick Commands

### Install dependencies

```bash
# Install all dependencies (including dev and test)
uv pip install -e ".[dev,test]"

# Install only production dependencies
uv pip install -e .

# Install only test dependencies
uv pip install -e ".[test]"
```

### Run tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=custom_components.monta --cov-report=term-missing

# Run specific test file
pytest tests/test_config_flow.py

# Run tests matching a pattern
pytest -k "test_user_flow"
```

### Code Quality

```bash
# Run ruff linter
ruff check .

# Run ruff linter and fix auto-fixable issues
ruff check --fix .

# Format code with ruff
ruff format .

# Check types (if mypy is added)
mypy custom_components/monta
```

### Sync dependencies

If `pyproject.toml` is updated:

```bash
# Sync installed packages with pyproject.toml
uv pip sync

# Or reinstall everything
uv pip install -e ".[dev,test]"
```

## Project Structure

```
hass-monta/
├── custom_components/
│   └── monta/           # Main integration code
│       ├── __init__.py
│       ├── config_flow.py
│       ├── coordinator.py
│       ├── diagnostics.py
│       ├── entity.py
│       ├── sensor.py
│       ├── binary_sensor.py
│       ├── switch.py
│       └── ...
├── tests/               # Test suite
│   ├── conftest.py
│   ├── test_config_flow.py
│   ├── test_init.py
│   └── ...
├── pyproject.toml       # Project configuration and dependencies
├── .python-version      # Python version for uv
└── README.md           # User documentation
```

## Testing

The project aims for 100% test coverage (Platinum tier requirement). Tests are written using pytest and pytest-asyncio.

### Running Tests Locally

1. **Install test dependencies:**
   ```bash
   uv pip install -e ".[test]"
   ```

2. **Run the test suite:**
   ```bash
   pytest
   ```

3. **Generate coverage report:**
   ```bash
   pytest --cov=custom_components.monta --cov-report=html
   # Open htmlcov/index.html in your browser
   ```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linters
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Code Standards

This project follows Home Assistant's Platinum tier quality standards:

- ✅ Full type hints on all functions
- ✅ Comprehensive docstrings
- ✅ 100% test coverage target
- ✅ Ruff for linting and formatting
- ✅ Async-first architecture
- ✅ Efficient data handling

## Dependency Management

### Adding New Dependencies

**Runtime dependency:**
```bash
# Add to project.dependencies in pyproject.toml
uv pip install package-name
```

**Development dependency:**
```bash
# Add to project.optional-dependencies.dev in pyproject.toml
uv pip install package-name
```

**Test dependency:**
```bash
# Add to project.optional-dependencies.test in pyproject.toml
uv pip install package-name
```

### Updating Dependencies

```bash
# Update all dependencies to latest compatible versions
uv pip install --upgrade -e ".[dev,test]"

# Update specific package
uv pip install --upgrade package-name
```

## Debugging

The project includes debugpy for debugging:

```bash
# Install dev dependencies if not already installed
uv pip install -e ".[dev]"

# Debug configuration is in .vscode/launch.json (if using VS Code)
```

## Migration from requirements.txt

If you're migrating from the old requirements.txt system:

```bash
# Old way (deprecated)
pip install -r requirements.txt
pip install -r requirements_test.txt

# New way with uv
uv pip install -e ".[dev,test]"
```

The pyproject.toml includes all dependencies that were in requirements.txt and requirements_test.txt.

## uv Benefits

- **Fast:** 10-100x faster than pip
- **Reliable:** Consistent dependency resolution
- **Modern:** Native support for pyproject.toml
- **Compatible:** Drop-in replacement for pip
- **Cached:** Efficient caching for faster reinstalls

## Troubleshooting

### "Module not found" errors

```bash
# Reinstall the project in editable mode
uv pip install -e ".[dev,test]"
```

### Dependency conflicts

```bash
# Clear uv cache and reinstall
uv cache clean
uv pip install -e ".[dev,test]"
```

### Tests not running

```bash
# Ensure test dependencies are installed
uv pip install -e ".[test]"

# Verify pytest is installed
pytest --version
```

## Resources

- [uv Documentation](https://docs.astral.sh/uv/)
- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Monta API Documentation](https://docs.public-api.monta.com)
- [Project Issues](https://github.com/nickknissen/hass-monta/issues)
