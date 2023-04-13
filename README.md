# GPT Changelog

GPT Changelog is a tool to automatically generate a changelog using OpenAI's GPT-3 based on commit messages since the most recent tag. It will generate a changelog in Markdown format and prepend it to the `CHANGELOG.md` file.

## Installation

### Using pip

    pip install gptchangelog

## Configuration

Before using GPT Changelog, you need to create a configuration file named config.ini in the $HOME/.config/gptchangelog directory.

    [openai]
    api_key = your_openai_api_key_here

Replace your_openai_api_key_here with your actual OpenAI API key.
Usage

To generate a changelog and prepend it to the CHANGELOG.md file, navigate to your Git repository directory and run the following command:

    gptchangelog


The script will fetch commit messages since the most recent tag, determine the next version based on semantic versioning, generate a changelog using OpenAI's GPT-3, and prepend the changelog to the CHANGELOG.md file. If the CHANGELOG.md file does not exist, the script will create it.

## License

This project is licensed under the MIT License.
