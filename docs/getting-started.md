---
title: Getting Started
description: Install, authenticate, and generate a validated changelog.
---

# Getting Started

GPTChangelog requires Python 3.12 or newer, Git history, and either an OpenAI API key or a Codex login.

## Install

```bash
pip install gptchangelog

# Optional terminal UI
pip install 'gptchangelog[tui]'
```

For a one-off run:

```bash
uvx gptchangelog --help
```

## Authenticate

OpenAI API:

```bash
export OPENAI_API_KEY='...'
gptchangelog config init
```

Codex subscription:

```bash
codex login
gptchangelog config init
```

GPTChangelog does not need to copy Codex tokens or read them directly. Check the resolved configuration with `gptchangelog config validate`.

## Generate

From a tagged repository:

```bash
gptchangelog generate
```

GPTChangelog validates the Git range, calculates the next version locally, requests one structured release-note draft, validates it, and atomically inserts the rendered Markdown into `CHANGELOG.md`.

Preview raw Markdown without modifying files:

```bash
gptchangelog generate --dry-run > release.md
```

Generate JSON for automation:

```bash
gptchangelog generate --dry-run --format json > release.json
```

Use the higher-quality GPT-5.6 Sol profile:

```bash
gptchangelog generate --profile quality
```

The default balanced profile uses GPT-5.6 Terra.

## Next steps

- [Basic usage](user-guide/basic-usage.md)
- [Configuration](user-guide/configuration.md)
- [Output contract](user-guide/templates.md)
- [CI and advanced usage](user-guide/advanced-usage.md)
