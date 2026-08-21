---
title: Basic Usage
description: Generate, preview, validate, and write changelogs safely.
---

# Basic Usage

## Generate a release

```bash
gptchangelog generate
```

Without `--since`, GPTChangelog finds the newest tag reachable from `--to`. In a repository without tags it includes the root commit and uses `0.0.0` as the version baseline.

## Select a range

```bash
gptchangelog generate --since v1.0.0 --to v1.1.0
gptchangelog generate --since HEAD~20 --to HEAD
gptchangelog generate --repo ../project --since v2.0.0
```

Both references are resolved before any model request. Invalid or unreachable ranges fail with a nonzero exit code.

## Preview and pipe output

```bash
gptchangelog generate --dry-run > release.md
gptchangelog generate --output - > release.md
gptchangelog generate --dry-run --format json | jq .version
```

Only the requested artifact is written to stdout. Diagnostics use stderr.

## Safe file updates

```bash
gptchangelog generate --output CHANGELOG.md
gptchangelog generate --check
```

Writing is atomic. GPTChangelog rejects duplicate or non-monotonic versions,
symlink targets, unresolved template placeholders, code fences, malformed
headings, and unsupported source references. Existing `[Unreleased]` content is
preserved. `--force` only replaces a matching existing release.

Use `--force` only when intentionally replacing an existing version:

```bash
gptchangelog generate --force --current-version 1.4.0
```

## Models

```bash
# Default GPT-5.6 Terra profile
gptchangelog generate --profile balanced

# GPT-5.6 Sol
gptchangelog generate --profile quality

# Explicit override
gptchangelog generate --model gpt-5.6-sol
```

## Interface

```bash
gptchangelog generate --interactive
gptchangelog generate --ui textual
gptchangelog generate --ui plain
```

Textual requires the `tui` package extra. Auto mode uses it only in an interactive terminal; CI and redirected output remain plain.
