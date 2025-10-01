---
title: Advanced Usage | GPTChangelog
description: Advanced techniques for GPTChangelog including interactive mode, custom commit ranges, CI/CD integration, performance optimization, and troubleshooting.
keywords:
  - gptchangelog
  - advanced usage
  - interactive mode
  - custom commit range
  - ci/cd
  - performance
  - token limits
  - troubleshooting
  - semantic versioning
  - release notes
---

# Advanced Usage

This guide covers advanced usage scenarios and techniques for GPTChangelog.

## Interactive Mode

Interactive mode allows you to review and edit the generated changelog before saving it:

```bash
gptchangelog generate --interactive
```

In interactive mode, you'll be prompted to:

1. Review the generated changelog
2. Choose whether to edit it (opens in your default editor)
3. Decide whether to save it to the changelog file

This is useful for reviewing the AI-generated content and making adjustments before finalizing it.

## Working with Custom Commit Ranges

### Specific Tags or Commits

You can generate a changelog between any two git references:

```bash
# Between two tags
gptchangelog generate --since v1.0.0 --to v2.0.0

# From a specific commit to HEAD
gptchangelog generate --since 8a7d3b9

# From a tag to a branch
gptchangelog generate --since v1.0.0 --to feature/new-feature
```

### Running Against Another Repository

You can generate a changelog for a different git repository without leaving your current directory:

```bash
gptchangelog generate --repo /path/to/other/project --since v3.2.0 --to HEAD
```

For CI/CD jobs or other non-interactive environments, add `--ui plain` to skip the Textual interface.

### Generating Changelog for a Single Release

To generate a changelog for a specific release:

```bash
# Get the previous tag
PREV_TAG=$(git describe --tags --abbrev=0 --match "v*" HEAD^)

# Generate changelog from previous tag to current tag
gptchangelog generate --since $PREV_TAG --to $(git describe --tags --abbrev=0)
```

## Custom Version Handling

### Manual Version Override

You can override the automatically determined version:

```bash
gptchangelog generate --current-version 1.5.0
```

This is useful when:
- You want to maintain a specific versioning scheme
- You need to create a pre-release version (e.g., beta, alpha)
- The AI-determined version doesn't match your preferences

### Version Prefixes

GPTChangelog preserves version prefixes (like "v" in "v1.2.3") in the output. It automatically detects if your tags use a prefix and maintains consistency.

## CI/CD Integration

### GitHub Actions Example

Here's a complete example of integrating GPTChangelog in a GitHub Actions workflow:

```yaml
name: Generate Changelog

on:
  push:
    tags:
      - 'v*'

jobs:
  changelog:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install gptchangelog
      
      - name: Get previous tag
        id: previoustag
        run: |
          echo "PREVIOUS_TAG=$(git describe --tags --abbrev=0 --match "v*" HEAD^ || git rev-list --max-parents=0 HEAD)" >> $GITHUB_ENV
      
      - name: Generate changelog
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          gptchangelog generate --since ${{ env.PREVIOUS_TAG }} --to ${{ github.ref_name }} --output RELEASE_NOTES.md --ui plain
      
      - name: Create release
        uses: softprops/action-gh-release@v1
        with:
          body_path: RELEASE_NOTES.md
          files: |
            *.tar.gz
            *.zip
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### GitLab CI Example

```yaml
generate_changelog:
  stage: build
  image: python:3.10
  script:
    - pip install gptchangelog
    - PREVIOUS_TAG=$(git describe --tags --abbrev=0 --match "v*" HEAD^ || git rev-list --max-parents=0 HEAD)
    - gptchangelog generate --since $PREVIOUS_TAG --output RELEASE_NOTES.md --ui plain
  artifacts:
    paths:
      - RELEASE_NOTES.md
  only:
    - tags
```

## Performance Optimization

### Managing Token Usage

For large repositories with many commits, you may need to optimize token usage:

```bash
# Set a lower token limit for cheaper processing
gptchangelog generate --max-tokens 40000

# Use a smaller model for faster processing
gptchangelog generate --model gpt-3.5-turbo
```

You can also set these in your configuration:

```ini
[openai]
model = gpt-3.5-turbo
max_context_tokens = 40000
```

### Batch Processing

For very large projects, you can generate changelogs in smaller batches:

```bash
# Generate changelog for the last 50 commits
gptchangelog generate --since HEAD~50

# Generate changelog between specific dates (using git revisions)
gptchangelog generate --since $(git rev-list -n 1 --before="2023-01-01" HEAD) --to $(git rev-list -n 1 --before="2023-02-01" HEAD)
```

## Advanced Output Control

### Multiple Output Formats

You can redirect the output to process it further:

```bash
# Generate changelog and save to a variable
CHANGELOG=$(gptchangelog generate --dry-run)

# Generate changelog in HTML format (using a converter)
gptchangelog generate --dry-run | pandoc -f markdown -t html > changelog.html
```

### Custom Post-Processing

You can post-process the changelog with additional tools:

```bash
# Generate changelog and add additional formatting
gptchangelog generate --dry-run | sed 's/^## /## 🚀 /' > CHANGELOG.md

# Generate changelog and extract specific sections
gptchangelog generate --dry-run | grep -A 10 "### Features" > FEATURES.md
```

## Troubleshooting Advanced Usage

### Handling Large Repositories

For very large repositories, you might encounter token limits. Solutions include:

1. Generating changelogs for smaller time periods
2. Using a more powerful model with higher token limits
3. Filtering out non-essential commits before generation

### Debugging

For debugging issues:

```bash
# Enable debug logging
export GPTCHANGELOG_DEBUG=1
gptchangelog generate

# Save raw API responses for inspection
export GPTCHANGELOG_SAVE_RESPONSES=1
gptchangelog generate
```

This information can be useful when reporting issues or understanding how the tool processes your commits.
