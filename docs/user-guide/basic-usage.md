---
title: Basic Usage | GPTChangelog
description: Learn the basic usage of GPTChangelog to generate high-quality changelogs from your git commits using OpenAI. Includes common commands, options, and examples.
keywords:
  - gptchangelog
  - basic usage
  - generate changelog
  - git commits
  - semantic versioning
  - openai
  - python cli
---

# Basic Usage

This page covers the basic usage of GPTChangelog for generating changelogs from your git commits.

## Command Line Interface

GPTChangelog provides a command-line interface with several commands and options.

### Main Commands

- `gptchangelog generate`: Generate a changelog
- `gptchangelog config`: Manage configuration
  - `gptchangelog config init`: Initialize configuration
  - `gptchangelog config show`: Show current configuration
- `gptchangelog --version`: Show version information
- `gptchangelog --help`: Show help information

## Generating a Changelog

The most common operation is generating a changelog from your git commit history.

### Simple Usage

To generate a changelog from your latest tag to the current HEAD:

```bash
gptchangelog generate
```

This will:

1. Find your latest git tag
2. Fetch all commit messages since that tag
3. Process them using OpenAI
4. Determine the next version based on semantic versioning
5. Generate a well-structured changelog
6. Prepend it to your CHANGELOG.md file

### Example Output

The generated changelog will look something like this:

```markdown
## [1.2.0] - 2024-10-20

### ✨ Features
- Add support for interactive editing mode
- Implement automatic conventional commit detection

### 🐛 Bug Fixes
- Resolve issue with version detection on Windows
- Fix token counting logic for large repositories

### 🔄 Changes
- Update default model to gpt-5-mini
- Improve commit message grouping algorithm
```

## Common Options

Here are some common options for the `generate` command:

### Custom Commit Range

You can specify a custom range of commits:

```bash
gptchangelog generate --since v1.0.0
```

Or between two specific references:

```bash
gptchangelog generate --since v1.0.0 --to v2.0.0-beta
```

### Custom Output File

By default, the changelog is prepended to `CHANGELOG.md`, but you can specify a different file:

```bash
gptchangelog generate --output docs/CHANGES.md
```

### Analyze Another Repository

Pass the `--repo` flag to run GPTChangelog against a different project without leaving your current directory:

```bash
gptchangelog generate --repo ../another-project
```

### Switching UI Modes

Launch the Textual interface for a richer review experience:

```bash
gptchangelog generate --ui textual
```

Use `--ui plain` if you prefer the traditional console output or are running in an environment without full terminal capabilities.

### Current Version Override

You can override the automatically detected version:

```bash
gptchangelog generate --current-version 1.5.0
```

### Dry Run

To preview the changelog without saving it:

```bash
gptchangelog generate --dry-run
```

## Exit Codes

GPTChangelog returns the following exit codes:

- `0`: Success
- `1`: Error (configuration error, git error, API error, etc.)

You can use these exit codes in scripts to check if the command succeeded:

```bash
gptchangelog generate
if [ $? -eq 0 ]; then
  echo "Changelog generated successfully"
else
  echo "Error generating changelog"
fi
```

## Error Handling

If GPTChangelog encounters an error, it will display an error message and exit with code 1. Common errors include:

- Configuration errors (missing API key)
- Git errors (not a git repository, no commits found)
- OpenAI API errors (authentication, rate limits)
- File I/O errors (permission denied, file not found)

Check the error message for details on how to resolve the issue.
