---
title: Advanced Usage
description: CI, JSON output, large ranges, validation, and troubleshooting.
---

# Advanced Usage

## CI-friendly output

```bash
gptchangelog generate \
  --since "$PREVIOUS_TAG" \
  --to "$GITHUB_SHA" \
  --output release.md \
  --ui plain \
  --quiet
```

Supply `OPENAI_API_KEY` through the CI environment. Creating a `.env` file does not export the variable and is not required by GPTChangelog.

## JSON artifact

```bash
gptchangelog generate --dry-run --format json > release.json
jq -r '.changelog' release.json > release.md
jq -r '.version' release.json
```

The JSON object includes repository and range metadata, version, changelog,
contributors, statistics, validation results, provider, model, and a
`provenance` object. Provenance contains normalized entries with source commit
IDs, source and covered commit counts, and whether deterministic large-input
fallback was used.

```bash
jq '.provenance | {source_commit_count, covered_commit_count, entries}' release.json
```

## Validate without writing

```bash
gptchangelog generate --check --ui plain
```

Validation checks:

- Git references and range resolution
- semantic-version release tags and baseline ancestry
- monotonic semantic version
- structured model response schema
- source commit coverage
- allowed localized sections
- duplicate headings and release versions
- unresolved placeholders and Markdown fences
- safe insertion into the target changelog

## Large ranges

GPTChangelog bounds source data before model use. If the structured input exceeds
the current 100,000-character safety limit, it emits a validated deterministic
entry for each analyzed commit instead of sending a partial history to the
model. Prefer explicit release ranges for more useful AI summaries.

```bash
gptchangelog generate --since v3.0.0 --to v3.1.0
```

## Custom rendering

Use JSON when you need HTML, Slack, or another presentation:

```bash
gptchangelog generate --dry-run --format json \
  | jq -r '.changelog' \
  | pandoc -f markdown -t html > release.html
```

## Troubleshooting

Enable diagnostic logging:

```bash
GPTCHANGELOG_DEBUG=1 gptchangelog generate --check
```

Check configuration and authentication without a model request:

```bash
gptchangelog config validate
codex login status
```

Errors are reported on stderr and return nonzero. GPTChangelog does not silently convert Git, provider, validation, or file-write failures into successful runs.
