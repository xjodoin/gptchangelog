# GPTChangelog

Generate validated changelogs from Git history with OpenAI or an existing Codex login.

GPTChangelog keeps release mechanics deterministic: Git ranges are validated locally, semantic versions are calculated from classified commits, model output is schema-validated, and Markdown is rendered and written atomically.

## Features

- Conventional-commit analysis with noise filtering and source commit tracking
- Deterministic semantic-version increments
- At most one structured model request per release
- GPT-5.6 Terra balanced/default and GPT-5.6 Sol quality profiles
- Markdown and JSON output with auditable entry-to-commit provenance
- English, French, and Spanish rendering
- Atomic, monotonic, duplicate-safe updates that preserve an `[Unreleased]` section
- OpenAI API-key and Codex login providers
- Optional Textual review UI

## Requirements and installation

GPTChangelog requires Python 3.12 or newer and a Git repository.

```bash
pip install gptchangelog

# Include the optional terminal UI
pip install 'gptchangelog[tui]'
```

You can also run it without a persistent installation:

```bash
uvx gptchangelog --help

# Run this checkout
uvx --from . gptchangelog --help
```

## Authentication

For the OpenAI API, export a key. GPTChangelog does not write API keys to project configuration by default.

```bash
export OPENAI_API_KEY='...'
gptchangelog config init
```

To use Codex subscription access, let Codex manage its own login and token refresh:

```bash
codex login
gptchangelog config init
```

Use `gptchangelog config show` to inspect configuration and `gptchangelog config validate` to check the resolved provider and model.

## Basic usage

Generate and safely insert a release into `CHANGELOG.md`:

```bash
gptchangelog generate
```

Generate raw Markdown without writing a file:

```bash
gptchangelog generate --dry-run > release.md
```

Generate machine-readable output:

```bash
gptchangelog generate --dry-run --format json > release.json
```

Generate for another repository and explicit range:

```bash
gptchangelog generate \
  --repo ../another-project \
  --since v1.4.0 \
  --to HEAD
```

Use the quality model profile:

```bash
gptchangelog generate --profile quality
```

The profiles resolve to:

- `balanced`: `gpt-5.6-terra` (default)
- `quality`: `gpt-5.6-sol`

`--model` remains available as an explicit override.

## Output and safety controls

```text
--output FILE, -o FILE       Write to a file; use - for stdout
--format markdown|json       Select artifact format
--dry-run                    Print the artifact without writing
--check                      Validate generation without modifying files
--force                      Replace an existing version intentionally
--quiet                      Suppress diagnostic output
--ui auto|textual|plain      Select the review interface
```

Diagnostics and progress go to stderr. Raw Markdown or JSON goes to stdout only when requested with `--dry-run` or `--output -`, so shell pipelines remain clean.
JSON also defaults to stdout when `--output` is omitted, preventing accidental
replacement of `CHANGELOG.md` with a machine-readable artifact.

Textual is selected by `--ui auto` only in a capable interactive terminal. Use `--ui textual` to request it explicitly or `--ui plain` for CI.

## Configuration

Project configuration lives at `.gptchangelog/config.ini`; global configuration lives at `~/.config/gptchangelog/config.ini`. Project configuration takes precedence.
On POSIX systems, a configuration containing a stored API key must have mode
`0600`; insecure legacy files are rejected with a remediation command.

```ini
[openai]
provider = openai
profile = balanced
model = gpt-5.6-terra
```

Environment and CLI precedence is:

1. CLI flags
2. `GPTCHANGELOG_PROVIDER`, `GPTCHANGELOG_PROFILE`, and `GPTCHANGELOG_MODEL`
3. project configuration
4. global configuration
5. defaults

`OPENAI_API_KEY` supplies API authentication. For Codex, GPTChangelog invokes the supported non-interactive Codex client and does not parse cached tokens itself.

## Output contract

Commit messages are treated as untrusted source data. The structured model
response must cite supplied commit identifiers, which lets GPTChangelog reject
invented or omitted source changes. Version selection, categories,
localization, headings, and Markdown rendering remain deterministic.

Breaking changes require a Conventional Commit `!` marker or a
blank-line-separated `BREAKING CHANGE:`/`BREAKING-CHANGE:` footer. Words such as
"remove" or "breaking" in an ordinary subject never trigger a major version.
JSON artifacts include every normalized release entry, its source commit IDs,
and source-versus-covered commit counts.

Legacy prompt-rendering helpers remain import-compatible, but the `generate`
command no longer loads project prompt overrides. This prevents templates from
silently changing the validated release contract.

## CI example

```yaml
name: Generate changelog

on:
  workflow_dispatch:

jobs:
  changelog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install gptchangelog
      - name: Generate release notes
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          gptchangelog generate \
            --since "$(git describe --tags --abbrev=0 HEAD^)" \
            --to "$GITHUB_SHA" \
            --output release.md \
            --ui plain
```

## Development

```bash
uv sync --dev --extra docs --extra release --extra tui
uv run pytest --cov=gptchangelog
uv run mypy --check-untyped-defs gptchangelog
uv run black --check gptchangelog tests
uv run isort --check-only gptchangelog tests
uv run mkdocs build --strict
```

## License

MIT
