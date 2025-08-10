---
title: Install GPTChangelog
description: Installation instructions for GPTChangelog via pip or from source. Requirements, dependencies, and troubleshooting tips for the AI-powered changelog generator.
keywords:
  - gptchangelog
  - install
  - pip
  - python
  - openai
  - git
  - cli
---

# Installation

This page provides detailed installation instructions for GPTChangelog.

## Requirements

- Python 3.8 or higher
- Git (installed and in your PATH)
- OpenAI API key

## Installing with pip

The recommended way to install GPTChangelog is using pip:

```bash
pip install gptchangelog
```

This will install GPTChangelog and all its dependencies.

## Installing from Source

If you prefer to install from source, you can clone the repository and install it:

```bash
git clone https://github.com/xjodoin/gptchangelog.git
cd gptchangelog
pip install -e .
```

The `-e` flag installs the package in "editable" mode, which is useful if you plan to modify the source code.

## Dependencies

GPTChangelog depends on the following packages:

- `openai`: For interacting with OpenAI's API
- `gitpython`: For accessing git repository information
- `tiktoken`: For token counting and management
- `rich`: For beautiful terminal output
- `setuptools`: For packaging utilities

These dependencies are automatically installed when you install GPTChangelog using pip.

## Verifying Installation

To verify that GPTChangelog is installed correctly, run:

```bash
gptchangelog --version
```

This should display the version number of GPTChangelog.

## Setting Up Your Environment

### OpenAI API Key

You'll need an OpenAI API key to use GPTChangelog. If you don't have one, you can get it from the [OpenAI website](https://platform.openai.com/).

You can configure your API key in two ways:

1. Through the configuration file (recommended):
   ```bash
   gptchangelog config init
   ```

2. Using an environment variable:
   ```bash
   export OPENAI_API_KEY=your-api-key
   ```

## Troubleshooting

### Common Installation Issues

**Package not found**

If you get a "command not found" error after installation, make sure your Python scripts directory is in your PATH.

**Dependency conflicts**

If you encounter dependency conflicts, try installing in a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install gptchangelog
```

**Git not found**

If you get an error about Git not being found, make sure Git is installed and in your PATH.

### Getting Help

If you continue to experience issues, please:

1. Check the [GitHub issues](https://github.com/xjodoin/gptchangelog/issues) to see if your problem has been reported
2. Open a new issue if needed, providing details about your environment and the error messages
