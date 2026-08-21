---
title: Configuration
description: Configure providers, GPT-5.6 profiles, models, and authentication.
---

# Configuration

Initialize configuration interactively:

```bash
gptchangelog config init
```

Project configuration is stored in `.gptchangelog/config.ini`; global configuration is stored in `~/.config/gptchangelog/config.ini`. Project values take precedence over global values.

## Example

```ini
[openai]
provider = openai
profile = balanced
model = gpt-5.6-terra
```

Supported providers are `openai` and `codex`. Unsupported or misspelled values are rejected.

Supported profiles are:

| Profile | Model | Purpose |
| --- | --- | --- |
| `balanced` | `gpt-5.6-terra` | Default balance of quality and cost |
| `quality` | `gpt-5.6-sol` | Highest-quality release-note synthesis |

An explicit `--model` or `GPTCHANGELOG_MODEL` overrides the profile model.

## Authentication

For the OpenAI provider, use an environment variable:

```bash
export OPENAI_API_KEY='...'
```

The initializer uses hidden input if you explicitly choose to persist a key, and any credential-bearing configuration is written with owner-only permissions. Environment-based credentials are preferred.
On POSIX systems, GPTChangelog rejects a stored-key configuration if group or
world permission bits are present and reports the exact `chmod 600` command to
repair it.

For Codex subscription access:

```bash
codex login
```

GPTChangelog uses Codex's supported non-interactive client. Codex owns login caching and token refresh.

## Precedence

1. `--provider`, `--profile`, and `--model`
2. `GPTCHANGELOG_PROVIDER`, `GPTCHANGELOG_PROFILE`, and `GPTCHANGELOG_MODEL`
3. project configuration
4. global configuration
5. default provider discovery and the balanced profile

Provider overrides do not accidentally reuse a model configured for a different provider.

## Inspect and validate

```bash
gptchangelog config show
gptchangelog config validate
```

`show` redacts secrets. `validate` checks syntax, model resolution, and authentication availability.

## Debug logging

Set `GPTCHANGELOG_DEBUG=1` to enable debug diagnostics on stderr. Raw model responses are never written automatically because they can contain repository data.
