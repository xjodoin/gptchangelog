---
title: Output contract
description: Understand which release-note decisions are model-assisted and which are deterministic.
---

# Output contract

GPTChangelog deliberately keeps the final Markdown layout out of prompt
templates. The model returns only a strict JSON summary and release entries
that cite their source commit IDs.

The application owns these decisions locally:

- semantic-version calculation;
- release date and heading format;
- category assignment from analyzed commits;
- English, French, and Spanish section titles;
- compare links and contributor placement; and
- Markdown validation and file insertion.

This boundary prevents a prompt or commit message from changing release
mechanics, adding unsupported sections, returning a lower version, or emitting
an entire fenced changelog.

The package still includes legacy prompt-rendering helpers for API
compatibility, but the current `generate` command does not load project prompt
overrides. Treat those helpers as deprecated integration surface rather than a
CLI customization mechanism.

To inspect the complete structured result without writing a file:

```bash
gptchangelog generate --dry-run --format json | jq .validation
```
