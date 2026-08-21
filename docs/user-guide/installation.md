---
title: Installation
description: Install GPTChangelog and its optional terminal interface.
---

# Installation

GPTChangelog requires Python 3.12 or newer.

## pip

```bash
pip install gptchangelog
```

The Textual interface is optional:

```bash
pip install 'gptchangelog[tui]'
```

## uv and uvx

```bash
uv tool install gptchangelog
gptchangelog --version

# Ephemeral execution
uvx gptchangelog --help
```

## Source checkout

```bash
git clone https://github.com/xjodoin/gptchangelog.git
cd gptchangelog
uv sync --dev --extra docs --extra release --extra tui
uv run pytest
```

## Verify

```bash
gptchangelog --version
gptchangelog config validate
```

Configuration validation reports the selected provider, profile, model, and whether the required authentication is available. It does not generate a changelog.
