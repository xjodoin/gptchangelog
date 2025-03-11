# GPTChangelog

**Automatically generate detailed, well-structured changelogs from your git commit history using OpenAI's GPT models.**

## Overview

GPTChangelog is a powerful command-line tool that leverages OpenAI's GPT models to automatically generate high-quality changelogs from your git commit history. It analyzes your commit messages, categorizes changes, and creates a beautifully formatted changelog in Markdown format.

## Key Features

- 🤖 **AI-powered Analysis**: Uses OpenAI's GPT models to understand commit messages and generate meaningful changelog entries
- 🔄 **Semantic Versioning**: Automatically determines the next version based on the changes detected
- 🏷️ **Smart Categorization**: Groups changes into categories like features, bug fixes, and improvements
- ✨ **Beautiful Formatting**: Creates well-structured Markdown with emojis and consistent styling
- 🧠 **Conventional Commit Support**: Works with conventional commit messages (feat:, fix:, etc.)
- 🖋️ **Interactive Mode**: Allows you to review and edit the changelog before saving
- 🛠️ **Flexible Configuration**: Supports both global and project-specific settings

## Quick Example

Here's what a generated changelog might look like:

```markdown
## [1.2.0] - 2024-10-20

### ✨ Features
- Add support for interactive editing mode
- Implement automatic conventional commit detection

### 🐛 Bug Fixes
- Resolve issue with version detection on Windows
- Fix token counting logic for large repositories

### 🔄 Changes
- Update default model to gpt-4o
- Improve commit message grouping algorithm

### 🔧 Maintenance
- Update dependencies to latest versions
```

## Getting Started

```bash
# Install GPTChangelog
pip install gptchangelog

# Initialize configuration
gptchangelog config init

# Generate changelog
gptchangelog generate
```

Check out the [Getting Started](getting-started.md) guide for more detailed instructions.

## Why GPTChangelog?

Maintaining a good changelog is essential for any project, but it can be tedious and time-consuming. GPTChangelog automates this process, saving you time while creating high-quality, consistent changelogs that your users will appreciate.

GPTChangelog excels at:

- Understanding the intent behind commit messages
- Grouping related changes together
- Eliminating redundancy and noise
- Creating human-readable descriptions
- Maintaining consistent formatting

## License

GPTChangelog is released under the MIT License.