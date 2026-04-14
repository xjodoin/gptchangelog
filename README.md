# GPTChangelog

Automatically generate detailed, well-structured changelogs from your git commit history using OpenAI models or an OpenAI Codex ChatGPT subscription.

## Features

- 🤖 AI-powered changelog generation from git commit messages
- 🔄 Automatic semantic versioning determination
- 🏷️ Support for conventional commits
- ✨ Beautiful formatting with Markdown
- 🧠 Smart categorization of changes
- 🧹 Filters noisy commits so release notes stay focused
- 🖋️ Interactive editing mode
- 📋 Customizable templates
- 🛠️ Project-specific or global configuration
- 🔐 Supports both OpenAI API keys and local Codex ChatGPT sign-in reuse
- 🗂️ Run against any repo path with a single command (`--repo`)
- 🖥️ Optional Textual TUI for exploring results (`--ui textual`)

## Installation

Install from PyPI with your preferred toolchain:

```bash
pip install gptchangelog
```

Or run it directly with [uv](https://docs.astral.sh/uv/):

```bash
uv tool run gptchangelog --help
```

Or use `uvx` for an ephemeral execution without pre-installing the tool:

```bash
uvx gptchangelog --help
```

If you want to run the local checkout without creating a virtual environment:

```bash
uvx --from . gptchangelog --help
```

## Quick Start

### Using pip or a virtual environment

1. Initialize the configuration (only needed once):

```bash
gptchangelog config init
```

If you want to use your OpenAI Codex subscription instead of an API key, sign in once first:

```bash
codex login
gptchangelog config init
```

2. Generate a changelog from your latest tag:

```bash
gptchangelog generate
```

The tool will:
- Fetch commit messages since your latest tag
- Process and categorize them using OpenAI
- Determine the next version number based on semantic versioning
- Generate a well-structured changelog
- Prepend it to your CHANGELOG.md file

### Using uv (no manual virtualenv required)

```bash
uv tool run gptchangelog config init
uv tool run gptchangelog generate

# or, for one-off runs, use uvx
uvx gptchangelog config init
uvx gptchangelog generate

# or run the local checkout with uvx
uvx --from . gptchangelog config init
uvx --from . gptchangelog generate
```

## Command Line Usage

```
gptchangelog generate [OPTIONS]
```

### Options

- `--since <ref>`: Starting point (commit hash, tag, or reference)
- `--to <ref>`: Ending point (commit hash, tag, or reference, defaults to HEAD)
- `--repo <path>`: Run against a different git repository without changing directories
- `--output <file>`, `-o <file>`: Output file (defaults to CHANGELOG.md)
- `--current-version <version>`: Override the current version
- `--dry-run`: Generate changelog but don't save it
- `--interactive`, `-i`: Review and edit before saving
- `--provider {openai,codex}`: Use the OpenAI API or reuse a local Codex ChatGPT login
- `--ui {auto,textual,plain}`: Choose between the Textual TUI and plain console output (default: auto)

### Examples

Generate changelog since the latest tag:
```bash
gptchangelog generate
```

Generate changelog between two specific tags:
```bash
gptchangelog generate --since v1.0.0 --to v2.0.0
```

Generate changelog with interactive editing:
```bash
gptchangelog generate -i
```

Run against another repository without leaving your current directory:
```bash
gptchangelog generate --repo ../another-project
```

Add commit statistics and quality checks to the output:
```bash
gptchangelog generate --stats --quality-analysis
```

Launch the Textual TUI review experience:
```bash
gptchangelog generate --ui textual
```

Force the Codex subscription backend for a one-off run:
```bash
gptchangelog generate --provider codex --model gpt-5.4-mini
```

With uv you can mirror the same commands by replacing `gptchangelog` with `uv tool run gptchangelog`, for example:

```bash
uv tool run gptchangelog generate --repo ../another-project --stats --quality-analysis

# or run ad-hoc with uvx
uvx gptchangelog generate --repo ../another-project --stats --quality-analysis
```

## Configuration

GPTChangelog supports both global and project-specific configuration:

- Global: Stored in `~/.config/gptchangelog/config.ini`
- Project: Stored in `./.gptchangelog/config.ini`

### Managing Configuration

Show current configuration:
```bash
gptchangelog config show
```

Initialize configuration:
```bash
gptchangelog config init
```

### Configuration Options

- `provider`: `openai` for API keys or `codex` to reuse `~/.codex/auth.json`
- `api_key`: Your OpenAI API key when `provider = openai`
- `model`: The model to use. Defaults to `gpt-5.2` for `openai` and `gpt-5.4-mini` for `codex`

## Integrating with CI/CD

You can integrate GPTChangelog into your CI/CD pipeline to automatically generate changelogs for new releases:

```yaml
# Example GitHub Actions workflow
name: Generate Changelog

on:
  push:
    tags:
      - 'v*'

jobs:
  changelog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Important to fetch all history

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install gptchangelog

      - name: Generate changelog
        run: |
          echo "OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}" > .env
          gptchangelog generate --since $(git describe --tags --abbrev=0 --match "v*" HEAD^) --to ${{ github.ref_name }} --ui plain
```

## Working from Source

To develop GPTChangelog locally, use [uv](https://docs.astral.sh/uv/) to manage dependencies:

```bash
git clone https://github.com/xjodoin/gptchangelog.git
cd gptchangelog
uv sync --dev --extra docs --extra release
uv run gptchangelog config init  # optional: seeds local config
uv run gptchangelog generate --dry-run
```

`uv sync` creates a managed virtual environment with the editable package and all tooling needed for docs, testing, and releases. `uv run ...` executes commands inside that environment, so there is no need to activate the virtualenv manually.

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
