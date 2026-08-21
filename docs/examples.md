---
title: Examples
description: Safe local, CI, JSON, localization, and validation examples.
---

# Examples

## Latest release

```bash
gptchangelog generate
```

## Explicit release tags

```bash
gptchangelog generate --since v1.8.0 --to v1.9.0
```

## First release without tags

```bash
gptchangelog generate --current-version 0.0.0
```

The root commit is included automatically.

## Preview Markdown

```bash
gptchangelog generate --dry-run > release.md
```

## JSON for another tool

```bash
gptchangelog generate --dry-run --format json > release.json
gh release create "$(jq -r .version release.json)" \
  --notes-file <(jq -r .changelog release.json)
```

## Another repository

```bash
gptchangelog generate \
  --repo ../service-api \
  --output docs/CHANGELOG.md
```

Relative output paths are resolved against the target repository, not the caller's process directory.

## Quality profile

```bash
gptchangelog generate --profile quality --check
```

Balanced generation uses `gpt-5.6-terra`; quality generation uses `gpt-5.6-sol`.

## French and Spanish

```bash
gptchangelog generate --language fr --output CHANGELOG.fr.md
gptchangelog generate --language es --output CHANGELOG.es.md
```

## Inspect the output contract

```bash
gptchangelog generate --dry-run --format json | jq .validation
```

## GitHub Actions

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
- run: pip install gptchangelog
- name: Generate changelog
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    PREVIOUS_TAG="$(git describe --tags --abbrev=0 HEAD^)"
    gptchangelog generate \
      --since "$PREVIOUS_TAG" \
      --to "$GITHUB_SHA" \
      --output RELEASE_NOTES.md \
      --ui plain
```

## Diagnose a failure

```bash
gptchangelog config validate
GPTCHANGELOG_DEBUG=1 gptchangelog generate --check --ui plain
```

Invalid Git ranges, authentication failures, schema violations, and file-write errors all return nonzero exit codes.
