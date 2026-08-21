---
title: GPTChangelog
description: Generate validated, source-grounded changelogs from Git history.
---

# GPTChangelog

GPTChangelog generates source-grounded release notes from Git history while keeping release mechanics deterministic and safe.

## What it does

- Validates the requested Git range before contacting a model
- Includes the root commit correctly for first releases
- Classifies conventional and inferred commit types
- Calculates the next semantic version locally
- Makes one structured model request for release-note synthesis
- Requires source commit IDs for generated entries
- Renders consistent English, French, or Spanish Markdown
- Rejects malformed or duplicate releases
- Updates changelog files atomically
- Produces clean Markdown or JSON for CI pipelines

## Models

The default `balanced` profile uses GPT-5.6 Terra. The `quality` profile uses GPT-5.6 Sol.

```bash
gptchangelog generate --profile balanced
gptchangelog generate --profile quality
```

## Quick start

```bash
pip install gptchangelog
export OPENAI_API_KEY='...'
gptchangelog generate
```

Or reuse a Codex login:

```bash
codex login
gptchangelog generate --provider codex
```

Preview without writing:

```bash
gptchangelog generate --dry-run > release.md
```

Continue with [Getting Started](getting-started.md) or browse the [User Guide](user-guide/index.md).
