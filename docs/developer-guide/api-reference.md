# API Reference

This page documents the primary functions and classes in GPTChangelog that you may want to use programmatically or extend.

## Module: `gptchangelog.cli`

The CLI module provides the command-line interface for GPTChangelog.

### Functions

#### `app()`

The main entry point for the command-line interface.

**Returns:**
- `int`: Exit code (0 for success, 1 for error)

#### `run_gptchangelog(args)`

Runs the main changelog generation process.

**Parameters:**
- `args`: Parsed command-line arguments

**Returns:**
- `int`: Exit code (0 for success, 1 for error)

## Module: `gptchangelog.config`

The configuration module handles loading and saving configuration settings.

### Functions

#### `load_openai_config(config_file_name="config.ini")`

Loads the OpenAI configuration from the config file.

**Parameters:**
- `config_file_name` (str): Name of the configuration file

**Returns:**
- `tuple`: (api_key, model, max_context_tokens)

**Raises:**
- `FileNotFoundError`: If the configuration file is not found

#### `init_config()`

Initializes a new configuration file with user input.

**Returns:**
- None

#### `show_config()`

Displays the current configuration settings.

**Returns:**
- None

## Module: `gptchangelog.git_utils`

The git utilities module interacts with git repositories.

### Functions

#### `get_commit_messages_since(latest_commit, to_commit="HEAD", repo_path=".", min_length=10)`

Gets commit messages between two git references.

**Parameters:**
- `latest_commit` (str): The starting reference (commit hash, tag, etc.)
- `to_commit` (str): The ending reference (defaults to "HEAD")
- `repo_path` (str): Path to the git repository
- `min_length` (int): Minimum length of commit messages to include

**Returns:**
- `tuple`: (from_ref, commit_messages_text)

#### `get_repository_name(repo)`

Extracts the repository name from a git repository.

**Parameters:**
- `repo` (git.Repo): Git repository object

**Returns:**
- `str`: Repository name

#### `get_latest_tag(repo)`

Gets the latest tag from the repository.

**Parameters:**
- `repo` (git.Repo): Git repository object

**Returns:**
- `str`: Latest tag name

#### `analyze_commit_message(message)`

Analyzes a commit message to determine its type.

**Parameters:**
- `message` (str): Commit message

**Returns:**
- `tuple`: (inferred_type, cleaned_message, is_breaking_change)

## Module: `gptchangelog.openai_utils`

The OpenAI utilities module interacts with the OpenAI API.

### Functions

#### `process_commit_messages(raw_commit_messages, model, max_context_tokens, context=None)`

Processes and refines commit messages using the OpenAI API.

**Parameters:**
- `raw_commit_messages` (str): Raw commit messages
- `model` (str): OpenAI model to use
- `max_context_tokens` (int): Maximum tokens for context
- `context` (dict, optional): Additional context for prompts

**Returns:**
- `str`: Processed commit messages

#### `determine_next_version(current_version, commit_messages, model, context=None)`

Determines the next version based on semantic versioning.

**Parameters:**
- `current_version` (str): Current version string
- `commit_messages` (str): Processed commit messages
- `model` (str): OpenAI model to use
- `context` (dict, optional): Additional context for prompts

**Returns:**
- `str`: Next version string

#### `generate_changelog(commit_messages, next_version, model, context=None)`

Generates a changelog from processed commit messages.

**Parameters:**
- `commit_messages` (str): Processed commit messages
- `next_version` (str): Next version string
- `model` (str): OpenAI model to use
- `context` (dict, optional): Additional context for prompts

**Returns:**
- `str`: Generated changelog in markdown format

#### `generate_changelog_and_next_version(raw_commit_messages, current_version, model, max_context_tokens, context=None)`

Complete process to generate a changelog and determine the next version.

**Parameters:**
- `raw_commit_messages` (str): Raw commit messages
- `current_version` (str): Current version string
- `model` (str): OpenAI model to use
- `max_context_tokens` (int): Maximum tokens for context
- `context` (dict, optional): Additional context for prompts

**Returns:**
- `tuple`: (changelog, next_version)

## Module: `gptchangelog.utils`

The utilities module provides common functions used across the package.

### Functions

#### `get_package_version()`

Gets the package version from pkg_resources or fallback.

**Returns:**
- `str`: Package version

#### `render_prompt(template_path, context)`

Renders a prompt template with provided context.

**Parameters:**
- `template_path` (str): Path to template file
- `context` (dict): Context variables for template

**Returns:**
- `str`: Rendered prompt

#### `estimate_tokens(text, model="gpt-4o")`

Estimates the number of tokens in a text for a given model.

**Parameters:**
- `text` (str): Text to estimate tokens for
- `model` (str): Model to use for estimation

**Returns:**
- `int`: Estimated number of tokens

#### `split_commit_messages(commit_messages, max_tokens, model="gpt-4o")`

Splits commit messages into batches that fit within token limits.

**Parameters:**
- `commit_messages` (list): List of commit message strings
- `max_tokens` (int): Maximum tokens per batch
- `model` (str): Model to use for estimation

**Returns:**
- `list`: List of batches, each a string of commit messages

#### `prepend_changelog_to_file(changelog, filepath="CHANGELOG.md")`

Prepends the changelog to the specified file.

**Parameters:**
- `changelog` (str): Changelog content
- `filepath` (str): Path to changelog file

**Returns:**
- None

#### `get_project_metadata()`

Gets metadata about the current project.

**Returns:**
- `dict`: Project metadata (name, version, description)

#### `format_commit_for_changelog(commit_message)`

Formats a commit message for inclusion in the changelog.

**Parameters:**
- `commit_message` (str): Commit message

**Returns:**
- `str`: Formatted commit message

## Programmatic Usage

You can use GPTChangelog programmatically in your own Python code:

```python
from gptchangelog.openai_utils import generate_changelog_and_next_version
from gptchangelog.git_utils import get_commit_messages_since
from gptchangelog.config import load_openai_config
import openai

# Load configuration
api_key, model, max_tokens = load_openai_config()
openai.api_key = api_key

# Get commit messages
from_ref, commit_messages = get_commit_messages_since("v1.0.0")

# Generate changelog
changelog, next_version = generate_changelog_and_next_version(
    commit_messages, 
    from_ref, 
    model, 
    max_tokens,
    {"project_name": "My Project"}
)

# Use the generated changelog
print(f"Next version: {next_version}")
print(changelog)
```

## Extending GPTChangelog

### Custom Commit Processing

You can extend the commit processing by creating a custom function:

```python
def custom_commit_processor(commit_messages):
    # Your custom processing logic
    processed_messages = []
    for message in commit_messages.split("\n"):
        # Process each message
        processed_messages.append(f"Processed: {message}")
    
    return "\n".join(processed_messages)

# Then use it instead of the built-in processor
from gptchangelog.openai_utils import generate_changelog
changelog = generate_changelog(
    custom_commit_processor(commit_messages),
    next_version,
    model
)
```

### Custom Template Rendering

You can provide a custom template renderer:

```python
def custom_template_renderer(template_path, context):
    # Your custom template rendering logic
    with open(template_path, "r") as f:
        template = f.read()
    
    # Simple string substitution
    for key, value in context.items():
        template = template.replace(f"${key}", str(value))
    
    return template

# Then use it in your workflow
```

### Adding New Output Formats

To add a new output format, create a converter function:

```python
def convert_to_html(changelog_markdown):
    # Convert markdown to HTML
    # (using a library like markdown2 or similar)
    html = f"""
    <html>
    <head><title>Changelog</title></head>
    <body>
    {markdown_to_html(changelog_markdown)}
    </body>
    </html>
    """
    return html

# Then use it after generating the changelog
html_changelog = convert_to_html(changelog)
with open("changelog.html", "w") as f:
    f.write(html_changelog)
```