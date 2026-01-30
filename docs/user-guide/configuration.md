---
title: GPTChangelog Configuration Guide
description: Configure GPTChangelog globally or per project. Learn about config locations, environment variable overrides, and OpenAI settings like API keys and models.
keywords:
  - gptchangelog
  - configuration
  - config file
  - environment variables
  - openai model
  - semantic versioning
---

# Configuration

GPTChangelog can be configured at both the global and project levels. This page explains all available configuration options and how to manage them.

## Configuration Locations

GPTChangelog looks for configuration in the following locations, in order of precedence:

1. Project-specific configuration: `./.gptchangelog/config.ini`
2. Global configuration: `~/.config/gptchangelog/config.ini`

If a setting is defined in both places, the project-specific setting takes precedence.

## Managing Configuration

### Initializing Configuration

To create a new configuration file:

```bash
gptchangelog config init
```

You'll be prompted to choose between global or project-specific configuration and enter your OpenAI API key and preferred model.

### Viewing Current Configuration

To see your current configuration:

```bash
gptchangelog config show
```

This will display both global and project-specific configurations if they exist.

## Configuration File Format

The configuration file uses the INI format:

```ini
[openai]
api_key = your-api-key-here
model = gpt-5.2
```

## Configuration Options

### OpenAI Settings

| Option | Description | Default | 
|--------|-------------|---------|
| `api_key` | Your OpenAI API key | (Required) |
| `model` | The OpenAI model to use | `gpt-5.2` |

### Environment Variables

You can also use environment variables to override configuration settings:

| Variable | Corresponding Config Option |
|----------|----------------------------|
| `OPENAI_API_KEY` | `[openai] api_key` |
| `GPTCHANGELOG_MODEL` | `[openai] model` |

Environment variables take precedence over configuration file settings.

## Advanced Configuration

### Using Different Models

GPTChangelog works best with GPT-5 family models, but you can use other options:

```ini
[openai]
model = gpt-3.5-turbo
```

Smaller models may produce less comprehensive results but can be more cost-efficient.

### Multiple Configurations

You can maintain different configurations for different projects:

1. Set up a global configuration with default settings
2. Create project-specific configurations for projects with special requirements

## Example Configurations

### Minimal Configuration

```ini
[openai]
api_key = your-api-key-here
```

### Full Configuration

```ini
[openai]
api_key = your-api-key-here
model = gpt-5.2
```

### Configuration for Large Repositories

```ini
[openai]
api_key = your-api-key-here
model = gpt-5.2
```

### Configuration for Lower Cost

```ini
[openai]
api_key = your-api-key-here
model = gpt-3.5-turbo
```
