# GPTChangelog

Automatically generate detailed, well-structured changelogs from your git commit history using OpenAI's GPT models.

## Features

- 🤖 AI-powered changelog generation from git commit messages
- 🔄 Automatic semantic versioning determination
- 🏷️ Support for conventional commits
- ✨ Beautiful formatting with Markdown
- 🧠 Smart categorization of changes
- 🖋️ Interactive editing mode
- 📋 Customizable templates
- 🛠️ Project-specific or global configuration
- 🗂️ Run against any repo path with a single command (`--repo`)
- 🖥️ Optional Textual TUI for exploring results (`--ui textual`)

## Installation

```bash
pip install gptchangelog
```

## Quick Start

1. Initialize the configuration (only needed once):

```bash
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

- `api_key`: Your OpenAI API key
- `model`: The OpenAI model to use (default: gpt-5-mini)
- `max_context_tokens`: Maximum tokens to use in each API call (default: 200000)

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
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv run gptchangelog generate --dry-run
```

`uv sync` creates a managed virtual environment with the editable package and all tooling needed for docs, testing, and releases.

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
