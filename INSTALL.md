## Installation Instructions for gptchangelog

### Prerequisites

Install Python 3.12 or newer. Install the [uv](https://docs.astral.sh/uv/) CLI if you plan to work with the project from source.

For a normal installation:

```sh
pip install gptchangelog

# Optional Textual interface
pip install 'gptchangelog[tui]'
```

### Steps to Install

1. **Clone the Repository:**

   ```sh
   git clone https://github.com/xjodoin/gptchangelog.git
   cd gptchangelog
   ```

2. **Sync Dependencies with uv:**

   ```sh
   uv sync --dev --extra docs --extra release --extra tui
   ```

   This command creates a managed `.venv` and installs the package in editable mode together with tooling required for development, documentation, and release workflows.

3. **Activate the Virtual Environment:**

   ```sh
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```

### Verify the Installation

You can verify the installation by running the `gptchangelog` command:

```sh
uv run gptchangelog --help
```

### One-Off Runs with uvx (No Install)

If you just want to run GPTChangelog without installing it, you can use `uvx`:

```sh
uvx gptchangelog --help
```

To run directly from a local checkout without creating a virtual environment:

```sh
uvx --from . gptchangelog --help
```

### Additional Information

- **Running Tests:** (if applicable)
  
  If your project includes tests, you can run them with:

```sh
uv run pytest
```

- **Uninstalling:**
  
  To uninstall the project, simply run:

```sh
uv pip uninstall gptchangelog
```

### Authentication

Export `OPENAI_API_KEY` for OpenAI API usage, or run `codex login` for Codex subscription usage. Validate the resolved configuration with:

```sh
uv run gptchangelog config validate
```
