# Development Tools Guide

This document explains the development tools used in this project and how to work with them.

---

## Table of Contents

- [UV - Python Package Manager](#uv---python-package-manager)
- [Ruff - Linter and Formatter](#ruff---linter-and-formatter)
- [Quick Reference](#quick-reference)

---

## UV - Python Package Manager

### What is UV?

[UV](https://github.com/astral-sh/uv) is a modern, extremely fast Python package installer and resolver written in Rust. It's designed as a drop-in replacement for pip and pip-tools, but significantly faster.

### Why UV?

- **Speed**: 10-100x faster than pip
- **Deterministic**: Creates reproducible environments
- **Modern**: Built for modern Python development workflows
- **Compatible**: Works with existing pip requirements and PyPI packages

### Installation

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Via pip (if you prefer)
pip install uv
```

### Basic Usage

#### Installing Dependencies

```bash
# Install all dependencies (base + all groups)
uv sync

# Install specific dependency groups
uv sync --group argumentation_mining
uv sync --group dev

# Install multiple groups
uv sync --group argumentation_mining --group dev
```

#### Managing Dependencies

```bash
# Add a new dependency to base dependencies
uv add pandas

# Add a dependency to a specific group
uv add --group dev pytest

# Remove a dependency
uv remove pandas

# Update all dependencies
uv sync --upgrade
```

#### Working with Virtual Environments

```bash
# UV automatically creates and manages virtual environments
# The environment is created in .venv/ by default

# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Run a command in the UV environment without activating
uv run python script.py
uv run pytest
```

### Understanding Dependency Groups

This project uses **dependency groups** (a modern Python feature) to organize dependencies:

```toml
[project]
dependencies = [
    "pandas>=2.3.3",      # Core dependencies used across all modules
    "pydantic>=2.11.10",
]

[dependency-groups]
dev = ["ruff>=0.13.3"]  # Development tools
argumentation_mining = ["openai>=2.1.0", ...]  # Module-specific
article_processing_pipeline = ["scikit-learn>=1.6.0", ...]  # Module-specific
# ... other groups
```

**Benefits:**
- Install only what you need for specific modules
- Avoid bloated environments with unnecessary dependencies
- Clear separation between production and development dependencies
- Faster installation when working on single modules

---

## Ruff - Linter and Formatter

### What is Ruff?

[Ruff](https://github.com/astral-sh/ruff) is an extremely fast Python linter and code formatter written in Rust. It replaces multiple tools like Flake8, isort, Black, and more.

### Why Ruff?

- **Fast**: 10-100x faster than existing linters
- **Comprehensive**: Implements hundreds of lint rules
- **All-in-One**: Combines linting, formatting, and import sorting
- **Configurable**: Fully compatible with existing Python tooling

### Configuration

This project's Ruff configuration is in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 80                          # Maximum line length
src = ["src"]                              # Source code directories
include = ["pyproject.toml", "src/**/*.py"] # Files to check

[tool.ruff.lint]
select = ["ALL"]                           # Enable all rules
ignore = ["D203", "D212", "COM812", "TD003"]  # Disable specific rules

[tool.ruff.lint.isort]
known-first-party = ["src"]                # First-party imports
force-sort-within-sections = true          # Sort imports alphabetically
```

### Basic Usage

#### Linting

```bash
# Check all files for issues
uv run ruff check .

# Check specific files or directories
uv run ruff check src/argumentation_mining/

# Auto-fix issues where possible
uv run ruff check --fix .

# Show all issues (including fixed ones)
uv run ruff check --fix --show-fixes .
```

#### Formatting

```bash
# Format all files
uv run ruff format .

# Format specific files or directories
uv run ruff format src/argumentation_mining/

# Check formatting without making changes
uv run ruff format --check .
```

#### Combined Workflow

```bash
# Fix and format in one go (recommended)
uv run ruff check --fix . && uv run ruff format .
```

### Common Lint Rules

Some important rules enabled in this project:

- **E/W**: pycodestyle errors and warnings (PEP 8)
- **F**: Pyflakes (undefined names, unused imports)
- **I**: isort (import sorting)
- **N**: pep8-naming (naming conventions)
- **D**: pydocstyle (docstring conventions)
- **UP**: pyupgrade (modern Python idioms)
- **B**: flake8-bugbear (likely bugs and design problems)
- **C90**: mccabe (complexity checking)

### VS Code Integration

Add to `.vscode/settings.json`:

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  }
}
```

---

## Quick Reference

### Common Commands

```bash
# Setup project
uv sync                                    # Install all dependencies
uv sync --group argumentation_mining       # Install specific module

# Development workflow
uv run ruff check --fix .                  # Lint and auto-fix
uv run ruff format .                       # Format code
uv run python -m argumentation_mining.main # Run module

# Dependency management
uv add package_name                        # Add dependency
uv add --group dev package_name            # Add dev dependency
uv remove package_name                     # Remove dependency
uv sync --upgrade                          # Update all dependencies

# Virtual environment
source .venv/bin/activate                  # Activate environment (Linux/macOS)
.venv\Scripts\activate                     # Activate environment (Windows)
uv run python script.py                    # Run without activating
```

### Troubleshooting

**Issue**: `uv: command not found`  
**Solution**: Install UV or add it to your PATH

**Issue**: Dependencies not found after `uv sync`  
**Solution**: Activate the virtual environment or use `uv run`

**Issue**: Ruff errors overwhelming  
**Solution**: Fix auto-fixable issues first: `uv run ruff check --fix .`

**Issue**: Conflicts between dependency groups  
**Solution**: Use `uv sync --upgrade` to resolve version conflicts

---

## Additional Resources

- **UV Documentation**: https://github.com/astral-sh/uv
- **Ruff Documentation**: https://docs.astral.sh/ruff/
- **Python Dependency Groups**: https://peps.python.org/pep-0735/
- **pyproject.toml Guide**: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/

---

## Best Practices

1. **Always use UV for dependency management** - Don't mix pip and UV
2. **Run Ruff before committing** - Ensure code quality
3. **Install only needed groups** - Keep environments lean
4. **Keep pyproject.toml updated** - Document all dependencies
5. **Use `uv run` for scripts** - Avoid environment activation issues
6. **Configure your IDE** - Integrate Ruff for real-time feedback

---

This document is maintained as part of the Economist Communication Analysis project.
