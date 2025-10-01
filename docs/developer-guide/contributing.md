# Contributing to GPTChangelog

Thank you for your interest in contributing to GPTChangelog! This guide will help you get started with development and show you how to contribute to the project.

## Development Setup

### Fork and Clone the Repository

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/gptchangelog.git
   cd gptchangelog
   ```

### Sync Dependencies with uv

GPTChangelog now uses [uv](https://docs.astral.sh/uv/) for dependency management. After installing uv, run:

```bash
uv sync --dev --extra docs --extra release
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

The `uv sync` command creates a managed `.venv` and installs the core package together with the development, documentation, and release tooling declared in `pyproject.toml`.

## Development Workflow

### Running Tests

Run tests using pytest:

```bash
uv run pytest
```

For coverage information:

```bash
uv run pytest --cov=gptchangelog
```

### Code Style

GPTChangelog follows the PEP 8 style guide. We use Black for code formatting and isort for import sorting:

```bash
uv run black gptchangelog tests
uv run isort gptchangelog tests
```

### Type Checking

We use mypy for type checking:

```bash
uv run mypy gptchangelog
```

### Running the CLI in Development

When developing, you can run the CLI directly:

```bash
uv run python -m gptchangelog generate
```

## Making Contributions

### Creating a Branch

Create a branch for your changes:

```bash
git checkout -b feature/your-feature-name
```

### Making Changes

1. Make your changes to the code
2. Add or update tests as needed
3. Run the tests to make sure they pass
4. Update documentation if needed

### Committing Changes

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages:

```
feat: add new feature
fix: fix bug in token counting
docs: update installation instructions
refactor: improve commit analysis logic
test: add tests for version determination
chore: update dependencies
```

### Submitting a Pull Request

1. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create a pull request on GitHub
3. Describe your changes in the pull request
4. Link any relevant issues

### Code Review

All contributions go through code review before they are merged. You may be asked to make changes to your pull request based on feedback.

## Project Structure

Here's an overview of the project structure:

```
gptchangelog/
├── __init__.py           # Package metadata
├── __main__.py           # Entry point
├── cli.py                # Command-line interface
├── config.py             # Configuration management
├── git_utils.py          # Git utilities
├── openai_utils.py       # OpenAI API integration
├── utils.py              # Utility functions
└── templates/            # Prompt templates
    ├── changelog_prompt.txt
    ├── commits_prompt.txt
    └── version_prompt.txt
```

## Documentation

### Building Documentation

We use MkDocs for documentation:

```bash
uv run mkdocs serve
```

### Documentation Structure

The documentation is in the `docs/` directory:

```
docs/
├── index.md              # Home page
├── getting-started.md    # Getting started guide
├── user-guide/           # User guide
├── developer-guide/      # Developer guide
└── examples.md           # Examples
```

## Release Process

1. Update version in `gptchangelog/__init__.py`
2. Update CHANGELOG.md using GPTChangelog itself
3. Create a new tag and push it:
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```
4. The CI pipeline will build and publish the package to PyPI

## Questions and Discussions

If you have questions or want to discuss development, please:

1. Open an issue on GitHub
2. Join our community discussions on GitHub Discussions

Thank you for contributing to GPTChangelog!
