---
title: Getting Started with GPTChangelog
description: Step-by-step guide to install, configure, and generate changelogs with GPTChangelog, an AI-powered changelog generator for Git.
keywords:
  - gptchangelog
  - getting started
  - installation
  - configuration
  - generate changelog
  - openai
  - python
  - release notes
---

# Getting Started

This guide will help you get up and running with GPTChangelog quickly.

## Prerequisites

- Python 3.8 or higher
- Git repository
- OpenAI API key

## Installation

Install GPTChangelog using pip:

```bash
pip install gptchangelog
```

## Configuration

Before using GPTChangelog, you need to configure it with your OpenAI API key:

```bash
gptchangelog config init
```

This will prompt you for:

1. Configuration type (global or project-specific)
2. Your OpenAI API key
3. The model to use (default: gpt-4o)
4. Maximum context tokens (default: 80000)

### Global vs. Project Configuration

- **Global configuration** is stored in `~/.config/gptchangelog/config.ini` and applies to all projects
- **Project configuration** is stored in `./.gptchangelog/config.ini` and only applies to the current project

Project configuration takes precedence over global configuration when both exist.

## Basic Usage

### Generate a Changelog

To generate a changelog from your latest tag to the current HEAD:

```bash
gptchangelog generate
```

This will:

1. Find your latest git tag
2. Fetch all commit messages since that tag
3. Process and analyze the commit messages using OpenAI
4. Determine the next version based on semantic versioning
5. Generate a well-structured changelog
6. Prepend it to your CHANGELOG.md file

### Interactive Mode

For more control, use interactive mode:

```bash
gptchangelog generate --interactive
```

This allows you to review and edit the changelog before saving it.

### Custom Commit Range

You can specify a custom range of commits:

```bash
gptchangelog generate --since v1.0.0 --to v2.0.0
```

### Output to a Different File

By default, the changelog is prepended to `CHANGELOG.md`, but you can specify a different file:

```bash
gptchangelog generate --output docs/CHANGES.md
```

### Dry Run

To preview the changelog without saving it:

```bash
gptchangelog generate --dry-run
```

## Next Steps

- Learn about [configuration options](user-guide/configuration.md)
- Explore [advanced usage](user-guide/advanced-usage.md)
- Check out [templates](user-guide/templates.md)
