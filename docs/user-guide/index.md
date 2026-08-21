---
title: User Guide | GPTChangelog
description: Learn how to install, configure, and use GPTChangelog to generate high-quality changelogs from your Git commit history using OpenAI.
keywords:
  - gptchangelog
  - user guide
  - installation
  - configuration
  - basic usage
  - advanced usage
  - output contract
  - changelog generator
---

# User Guide

Start here to install, configure, and use GPTChangelog effectively. The guides below cover everything from first-time setup to advanced workflows.

## Contents

- Installation
  - Learn how to install GPTChangelog and verify your setup.
  - Go to the Installation guide: [Installation](installation.md)

- Configuration
  - Configure providers, GPT-5.6 profiles, explicit models, and authentication.
  - Go to the Configuration guide: [Configuration](configuration.md)

- Basic Usage
  - Generate your first changelog from Git commits and understand common options.
  - Go to Basic Usage: [Basic Usage](basic-usage.md)

- Advanced Usage
  - JSON output, CI/CD integration, validation, large ranges, and troubleshooting.
  - Go to Advanced Usage: [Advanced Usage](advanced-usage.md)

- Output contract
  - Understand the strict model schema and deterministic release mechanics.
  - Go to Output contract: [Output contract](templates.md)

## Tips for Best Results

- Follow Conventional Commits (feat:, fix:, docs:, refactor:, etc.) for clearer categorization.
- Tag your releases (e.g., v1.2.3) so version detection works consistently.
- Use `--check` in release automation before allowing a file update.
- Use `--profile balanced` for GPT-5.6 Terra or `--profile quality` for GPT-5.6 Sol.
