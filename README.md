# GPT Changelog

GPT Changelog is a powerful tool designed to automatically generate high-quality changelogs with remarkable speed, using OpenAI's latest models. By analyzing commit messages since the most recent tag, GPT Changelog creates a well-structured, markdown-formatted changelog and seamlessly integrates it into your `CHANGELOG.md` file.

## Features
- **Fast and Efficient**: Quickly generates changelogs by leveraging the latest GPT models.
- **High Quality**: Produces clear, concise, and informative changelogs, ensuring your project documentation is always up-to-date.
- **Seamless Integration**: Automatically prepends the generated changelog to your existing `CHANGELOG.md` file, or creates one if it doesn't exist.

## Installation

### Using pip

To install GPT Changelog, simply run:
```sh
pip install gptchangelog
```

## Configuration

Before using GPT Changelog, you need to configure your OpenAI API key and set the desired model. Create a configuration file named `config.ini` in the `$HOME/.config/gptchangelog` directory with the following content:

```ini
[openai]
api_key = your_openai_api_key_here
model = gpt-4o
```
Replace `your_openai_api_key_here` with your actual OpenAI API key. You can set the `model` parameter to the desired version of GPT (e.g., `gpt-4o`).

## Usage

Generating a changelog and updating your `CHANGELOG.md` file is straightforward. Navigate to your Git repository directory and run:

```sh
gptchangelog
```

This command will:
1. Fetch commit messages since the most recent tag.
2. Determine the next version based on semantic versioning.
3. Generate a changelog using the specified GPT model.
4. Prepend the generated changelog to the `CHANGELOG.md` file. If the file doesn't exist, it will create one.

## Example

Here's an example of how easy it is to use GPT Changelog:

```sh
cd /path/to/your/repo
gptchangelog
```

Within seconds, your `CHANGELOG.md` will be updated with the latest changes, keeping your project documentation both current and professional.

## License

This project is licensed under the MIT License.
