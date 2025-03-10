import os
from string import Template
import tiktoken
import logging
import pkg_resources
import json
import re
import time
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def get_package_version():
    """Get the package version from pkg_resources or fallback to version file."""
    try:
        return pkg_resources.get_distribution("gptchangelog").version
    except pkg_resources.DistributionNotFound:
        # Fallback to reading from the package's __init__.py
        script_dir = os.path.dirname(os.path.abspath(__file__))
        init_file = os.path.join(script_dir, "__init__.py")

        if os.path.exists(init_file):
            with open(init_file, "r") as f:
                content = f.read()
                version_match = re.search(r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]', content)
                if version_match:
                    return version_match.group(1)

        return "0.1.0"  # Default fallback version


def render_prompt(template_path, context):
    """
    Render a prompt template with the provided context.

    Args:
        template_path: Path to the template file, relative to the package directory
        context: Dictionary of values to substitute in the template

    Returns:
        The rendered prompt string
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_template_path = os.path.join(script_dir, template_path)

    try:
        with open(full_template_path, "r") as template_file:
            template_content = template_file.read()

        template = Template(template_content)
        return template.safe_substitute(context)
    except FileNotFoundError:
        logger.error(f"Template file not found: {template_path}")
        # Create a simple fallback template based on the context
        fallback = f"Context:\n"
        for key, value in context.items():
            if key == "commit_messages":
                fallback += f"\nCommit Messages:\n{value}\n"
            else:
                fallback += f"\n{key}: {value}"

        return fallback


def estimate_tokens(text, model="gpt-4o"):
    """
    Estimate the number of tokens in a text for a given model.

    Args:
        text: The text to estimate tokens for
        model: The OpenAI model to use for token estimation

    Returns:
        Estimated number of tokens
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Error estimating tokens: {e}")
        # Fallback estimation: rough approximation
        return len(text) // 4  # Rough average for English text


def split_commit_messages(commit_messages, max_tokens, model="gpt-4o"):
    """
    Split commit messages into batches that fit within the max token limit.

    Args:
        commit_messages: List of commit message strings
        max_tokens: Maximum number of tokens per batch
        model: The OpenAI model to use for token estimation

    Returns:
        List of batches, where each batch is a string of commit messages
    """
    # Reserve tokens for the prompt template and response
    prompt_reserve = 1000  # Reserve tokens for the prompt text
    response_reserve = 1000  # Reserve tokens for the response
    effective_max = max(max_tokens - prompt_reserve - response_reserve, 1000)

    message_batches = []
    current_batch = []
    current_tokens = 0

    for message in commit_messages:
        message_tokens = estimate_tokens(message, model)

        # If this message would put us over the limit, start a new batch
        if current_batch and current_tokens + message_tokens > effective_max:
            message_batches.append("\n".join(current_batch))
            current_batch = [message]
            current_tokens = message_tokens
        else:
            current_batch.append(message)
            current_tokens += message_tokens

    # Add the final batch if it's not empty
    if current_batch:
        message_batches.append("\n".join(current_batch))

    return message_batches


def prepend_changelog_to_file(changelog, filepath="CHANGELOG.md"):
    """
    Prepend the changelog to the specified file.

    Args:
        changelog: The changelog content to prepend
        filepath: Path to the changelog file
    """
    if not changelog:
        logger.warning("No changelog to write.")
        return

    # Create directories if they don't exist
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    try:
        if not os.path.exists(filepath):
            # Create a new file with header
            with open(filepath, "w") as file:
                file.write("# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n")
                file.write(changelog)
        else:
            # Read existing content
            with open(filepath, "r") as file:
                original_content = file.read()

            # Find the first entry in the changelog to insert after the header
            header_match = re.search(r'^(#\s+Changelog.*?)(?=##\s+\[|\Z)', original_content, re.DOTALL | re.MULTILINE)

            if header_match:
                # Insert the new changelog after the header
                header = header_match.group(1)
                rest = original_content[len(header):]
                with open(filepath, "w") as file:
                    file.write(header + changelog + "\n\n" + rest)
            else:
                # No header found, just prepend
                with open(filepath, "w") as file:
                    file.write(changelog + "\n\n" + original_content)

    except Exception as e:
        logger.error(f"Error writing changelog to file: {e}")

        # Create backup with timestamp
        if os.path.exists(filepath):
            timestamp = int(time.time())
            backup_path = f"{filepath}.{timestamp}.bak"
            try:
                with open(filepath, "r") as src, open(backup_path, "w") as dst:
                    dst.write(src.read())
                logger.info(f"Created backup of changelog at {backup_path}")
            except Exception as backup_error:
                logger.error(f"Failed to create backup: {backup_error}")


def get_project_metadata():
    """
    Get metadata about the current project from package files.

    Returns:
        Dictionary with project metadata
    """
    metadata = {
        "name": "",
        "version": get_package_version(),
        "description": "",
    }

    # Try to get from setup.py, pyproject.toml, or package.json
    cwd = os.getcwd()

    # Check for package.json (Node.js projects)
    package_json = os.path.join(cwd, "package.json")
    if os.path.exists(package_json):
        try:
            with open(package_json, "r") as f:
                pkg_data = json.load(f)
                metadata["name"] = pkg_data.get("name", "")
                metadata["version"] = pkg_data.get("version", metadata["version"])
                metadata["description"] = pkg_data.get("description", "")
        except Exception:
            pass

    # Check for pyproject.toml (modern Python projects)
    pyproject_toml = os.path.join(cwd, "pyproject.toml")
    if os.path.exists(pyproject_toml) and not metadata["name"]:
        try:
            with open(pyproject_toml, "r") as f:
                content = f.read()
                name_match = re.search(r'name\s*=\s*[\'"]([^\'"]*)[\'"]', content)
                if name_match:
                    metadata["name"] = name_match.group(1)

                # Only override version if we couldn't get it from package_version()
                if metadata["version"] == "0.1.0":
                    version_match = re.search(r'version\s*=\s*[\'"]([^\'"]*)[\'"]', content)
                    if version_match:
                        metadata["version"] = version_match.group(1)

                description_match = re.search(r'description\s*=\s*[\'"]([^\'"]*)[\'"]', content)
                if description_match:
                    metadata["description"] = description_match.group(1)
        except Exception:
            pass

    # If all else fails, use the directory name as the project name
    if not metadata["name"]:
        metadata["name"] = os.path.basename(cwd)

    return metadata


def format_commit_for_changelog(commit_message):
    """
    Format a single commit message for inclusion in the changelog.

    Args:
        commit_message: The commit message to format

    Returns:
        Formatted commit message suitable for changelog
    """
    # Handle conventional commit format
    match = re.match(r'^(\w+)(\([^)]+\))?(!)?:\s+(.+)$', commit_message)

    if match:
        commit_type, scope, breaking, message = match.groups()
        scope = scope or ""

        # Process the message based on commit type
        if commit_type == "feat":
            prefix = "Added"
        elif commit_type == "fix":
            prefix = "Fixed"
        elif commit_type == "refactor":
            prefix = "Improved"
        elif commit_type == "docs":
            prefix = "Documentation"
        elif commit_type == "style":
            prefix = "Style"
        elif commit_type == "perf":
            prefix = "Performance"
        elif commit_type == "test":
            prefix = "Tests"
        elif commit_type == "chore":
            prefix = "Maintenance"
        else:
            prefix = "Changed"

        # Add scope if present
        if scope:
            return f"{prefix} {scope.strip('()')}: {message}"
        else:
            return f"{prefix}: {message}"

    # Return the original message if it's not in conventional commit format
    return commit_message


def cache_api_response(func):
    """
    Decorator to cache API responses to reduce API calls.

    Args:
        func: The function to cache

    Returns:
        Wrapped function with caching
    """
    cache = {}

    def wrapper(*args, **kwargs):
        # Create a cache key from the function arguments
        key = str(args) + str(sorted(kwargs.items()))

        if key in cache:
            logger.debug(f"Using cached result for {func.__name__}")
            return cache[key]

        result = func(*args, **kwargs)
        cache[key] = result
        return result

    return wrapper