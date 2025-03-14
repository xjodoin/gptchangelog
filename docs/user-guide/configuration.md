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

You'll be prompted to choose between global or project-specific configuration and enter your OpenAI API key and other settings.

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
model = gpt-4o
max_context_tokens = 80000
```

## Configuration Options

### OpenAI Settings

| Option | Description | Default | 
|--------|-------------|---------|
| `api_key` | Your OpenAI API key | (Required) |
| `model` | The OpenAI model to use | `gpt-4o` |
| `max_context_tokens` | Maximum tokens to use in each API call | `80000` |

### Environment Variables

You can also use environment variables to override configuration settings:

| Variable | Corresponding Config Option |
|----------|----------------------------|
| `OPENAI_API_KEY` | `[openai] api_key` |
| `GPTCHANGELOG_MODEL` | `[openai] model` |
| `GPTCHANGELOG_MAX_TOKENS` | `[openai] max_context_tokens` |

Environment variables take precedence over configuration file settings.

## Advanced Configuration

### Using Different Models

GPTChangelog works best with GPT-4 variants, but you can use other models:

```ini
[openai]
model = gpt-3.5-turbo
```

Smaller models may produce less comprehensive results but use fewer tokens.

### Token Management

The `max_context_tokens` setting controls how many tokens are used in each API call. If you have a large repository with many commits, you might need to adjust this:

```ini
[openai]
max_context_tokens = 120000
```

Keep in mind that larger values use more API tokens and may be more expensive.

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
model = gpt-4o
max_context_tokens = 80000
```

### Configuration for Large Repositories

```ini
[openai]
api_key = your-api-key-here
model = gpt-4o
max_context_tokens = 120000
```

### Configuration for Lower Cost

```ini
[openai]
api_key = your-api-key-here
model = gpt-3.5-turbo
max_context_tokens = 60000
```