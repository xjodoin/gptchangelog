# GPT Changelog

GPT Changelog is a powerful tool that automatically generates high-quality changelogs using OpenAI's advanced language models. By analyzing commit messages since the most recent tag, GPT Changelog creates a well-structured, markdown-formatted changelog and seamlessly integrates it into your `CHANGELOG.md` file.

## Features

- **Fast and Efficient**: Quickly generates changelogs by leveraging OpenAI's GPT models.
- **High Quality**: Produces clear, concise, and informative changelogs to keep your project documentation up-to-date.
- **Seamless Integration**: Automatically prepends the generated changelog to your existing `CHANGELOG.md` file or creates one if it doesn't exist.
- **Customizable**: Supports configuration of the OpenAI model and context token limits.
- **Semantic Versioning**: Determines the next version number based on semantic versioning principles.

## Installation

### Prerequisites

- **Python 3.6 or higher**: Ensure that Python is installed on your system.
- **OpenAI API Key**: You need an OpenAI API key to use this tool. Sign up at [OpenAI](https://platform.openai.com/) to obtain one.

### Using pip

Install GPT Changelog via pip:

```sh
pip install gptchangelog
```

## Configuration

Before using GPT Changelog, you need to configure your OpenAI API key and settings. You can initialize the configuration using the built-in command:

```sh
gptchangelog config init
```

This command will guide you through setting up your configuration file, where you can specify your OpenAI API key, the model to use, and other settings.

By default, the configuration file is created in one of the following locations:

- **Global Configuration**: `$HOME/.config/gptchangelog/config.ini`
- **Project Configuration**: `./.gptchangelog/config.ini`

### Manual Configuration

Alternatively, you can manually create a configuration file named `config.ini` with the following content:

```ini
[openai]
api_key = your_openai_api_key_here
model = gpt-4
max_context_tokens = 8000
```

- Replace `your_openai_api_key_here` with your actual OpenAI API key.
- Set the `model` parameter to the desired OpenAI model (e.g., `gpt-4` or `gpt-3.5-turbo`).
- Optionally adjust `max_context_tokens` based on your model's token limit.

## Usage

Navigate to your Git repository directory and run:

```sh
gptchangelog
```

This command will:

1. Fetch commit messages since the most recent tag or specified commit.
2. Refine commit messages for clarity and conciseness.
3. Determine the next version number based on semantic versioning.
4. Generate a changelog using the specified OpenAI model.
5. Prepend the generated changelog to the `CHANGELOG.md` file. If the file doesn't exist, it will create one.

### Command-Line Options

- `--since <commit>`: Specify the commit hash or tag to start fetching commit messages from. If not provided, it uses the most recent tag.

Example:

```sh
gptchangelog --since v1.2.3
```

### Configuration Commands

- `gptchangelog config init`: Initialize the configuration file.
- `gptchangelog config show`: Display the current configuration.

## Example

Here's how to use GPT Changelog:

```sh
cd /path/to/your/repo
gptchangelog
```

Within seconds, your `CHANGELOG.md` will be updated with the latest changes, keeping your project documentation current and professional.

### Sample Generated Changelog

```markdown
## [1.3.0] - 2023-10-18

### Added

- Implemented user authentication feature.

### Fixed

- Resolved bug in the payment processing module.

### Changed

- Updated the API documentation for clarity.

### Removed

- Deprecated endpoints removed from the API.
```

## Templates

GPT Changelog uses customizable templates for prompts. You can modify the templates located in the `templates` directory within the `gptchangelog` package to tailor the prompts to your needs.

- **commits_prompt.txt**: Template for refining commit messages.
- **version_prompt.txt**: Template for determining the next version number.
- **changelog_prompt.txt**: Template for generating the changelog.

## Development

### Project Structure

```
gptchangelog/
├── __init__.py
├── main.py
├── config.py
├── git_utils.py
├── openai_utils.py
├── utils.py
└── templates/
    ├── commits_prompt.txt
    ├── version_prompt.txt
    └── changelog_prompt.txt
```

- **main.py**: Entry point of the application.
- **config.py**: Handles configuration management.
- **git_utils.py**: Contains Git-related utility functions.
- **openai_utils.py**: Manages interactions with the OpenAI API.
- **utils.py**: Contains shared utility functions.
- **templates/**: Contains prompt templates used by the application.

## Contributing

Contributions are welcome! If you'd like to contribute:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them with clear messages.
4. Submit a pull request to the `main` branch.

Please ensure that your code adheres to the project's coding standards and passes all tests.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please open an issue on the [GitHub repository](https://github.com/xjodoin/gptchangelog).
