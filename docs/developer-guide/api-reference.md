---
title: API Reference
description: Public Git, generation, provider, validation, and persistence APIs.
---

# API Reference

## Git ranges

```python
from git import Repo
from gptchangelog.git_utils import resolve_release_range

repo = Repo("/path/to/project")
release_range = resolve_release_range(repo, since="v1.2.0", to_ref="HEAD")
```

`resolve_release_range()` validates both refs and returns `ReleaseRange` with
the display refs, immutable SHAs, and detected current version. If no tag is
reachable, `from_ref` and `from_sha` are `None`, `current_version` is `0.0.0`,
and downstream iteration includes the root commit.

Use `get_enhanced_commit_data(from_ref, to_ref, repo_path=...)` to return
analyzed `CommitInfo` values and aggregate statistics. Invalid refs propagate as
Git errors.

## Generation

```python
from gptchangelog.enhanced_openai_utils import (
    generate_enhanced_changelog_and_version,
    generate_enhanced_changelog_result,
)

markdown, version = generate_enhanced_changelog_and_version(
    commits,
    current_version="v1.2.0",
    project_name="example",
    stats=stats,
    model="gpt-5.6-terra",
    language="en",
)

result = generate_enhanced_changelog_result(
    commits,
    current_version="v1.2.0",
    project_name="example",
    stats=stats,
)
for entry in result.entries:
    print(entry.category, entry.description, entry.commit_ids)
```

Semantic versioning, category assignment, localization, and Markdown rendering
are local. The provider receives one structured request for the release summary
and bounded topics. Its schema requires an assignment for every known source
commit ID and fixes each assignment to the locally determined category.

`generate_enhanced_changelog_result(...)` is the preferred auditing API. It
returns `EnhancedGenerationResult` with `changelog`, `version`, `summary`,
normalized `entries`, and `used_fallback`. The tuple-returning
`generate_enhanced_changelog_and_version(...)` remains available for existing
callers.

`validate_changelog(markdown, expected_version, language=None)` returns a list
of validation errors. `analyze_changelog_quality(markdown)` returns concrete
validation and content counts; it does not calculate a subjective score.

The functions in `gptchangelog.openai_utils` remain compatibility wrappers over
this same pipeline.

## Providers

```python
from gptchangelog.openai_client import (
    ProviderSettings,
    configure_provider,
    create_structured_response,
)

configure_provider(
    ProviderSettings(provider="openai", api_key="...", max_retries=2)
)
payload = create_structured_response(
    model="gpt-5.6-terra",
    instructions="Summarize supplied changes.",
    prompt="...",
    json_schema={"type": "object", "properties": {}, "additionalProperties": False},
)
```

The OpenAI adapter uses the Responses API with strict JSON Schema. The Codex
adapter invokes ephemeral, read-only `codex exec` and leaves authentication and
token refresh to Codex CLI.

Model helpers include `normalize_provider()`, `normalize_profile()`,
`get_profile_model()`, and `resolve_model()`. Provider failures raise
`ProviderError`; invalid configuration raises `ProviderConfigurationError`.

## Safe persistence

```python
from gptchangelog.utils import prepend_changelog_to_file

result = prepend_changelog_to_file(
    markdown,
    "CHANGELOG.md",
    version=version,
    check=False,
    force=False,
)
```

`prepend_changelog_to_file()` validates canonical SemVer, rejects duplicate or
non-monotonic new releases, rejects symlink targets, preserves `[Unreleased]`,
and writes atomically. `check=True` prepares and validates the resulting content
without modifying the file. `force=True` replaces an existing matching release;
it cannot add a missing historical version.

Failures derive from `ChangelogError`, including `ChangelogValidationError`,
`DuplicateReleaseError`, `NonMonotonicReleaseError`,
`ReleaseNotFoundError`, `ChangelogWriteError`, and
`UnsafeChangelogTargetError`.

Legacy `render_prompt()` and `resolve_template_path()` helpers remain available
for integrations, but the CLI generation path does not load prompt overrides.
