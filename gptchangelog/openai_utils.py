import logging
from datetime import datetime
import re
from typing import Tuple, Dict, List, Any, Optional

import openai
from openai import OpenAIError

from .utils import render_prompt, split_commit_messages

logger = logging.getLogger(__name__)


def process_commit_messages(
        raw_commit_messages: str,
        model: str,
        max_context_tokens: int,
        context: Dict[str, Any] = None
) -> str:
    """
    Process and refine commit messages using the OpenAI API.

    Args:
        raw_commit_messages: The raw commit messages to process
        model: The OpenAI model to use
        max_context_tokens: Maximum number of tokens to use in each API call
        context: Additional context information for the prompts

    Returns:
        Processed commit messages as a single string
    """
    if not context:
        context = {}

    commit_messages_list = raw_commit_messages.strip().split("\n")
    prompt_batches = split_commit_messages(commit_messages_list, max_context_tokens, model)

    refined_commit_messages = []
    for i, batch in enumerate(prompt_batches):
        logger.info(f"Processing commit batch {i + 1}/{len(prompt_batches)}...")

        # Add batch to context
        batch_context = {**context, "commit_messages": batch}

        prompt = render_prompt(
            "templates/commits_prompt.txt",
            batch_context,
        )

        try:
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an assistant that analyzes and refines git commit messages to prepare them for "
                            "changelog generation. You categorize commits by type, identify breaking changes, and "
                            "improve clarity and consistency."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.3,  # Lower temperature for more consistent output
            )
            refined_message = response.choices[0].message.content
            refined_commit_messages.append(refined_message)
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            refined_commit_messages.append(batch)  # Fall back to using the original batch

    return "\n".join(refined_commit_messages)


def determine_next_version(
        current_version: str,
        commit_messages: str,
        model: str,
        context: Dict[str, Any] = None
) -> str:
    """
    Determine the next version number based on the commit messages.

    Args:
        current_version: The current version string
        commit_messages: The processed commit messages
        model: The OpenAI model to use
        context: Additional context information for the prompts

    Returns:
        The next version string
    """
    if not context:
        context = {}

    logger.info("Determining next version...")

    # Extract version numbers if the current version has a prefix
    has_prefix = False
    version_prefix = ""
    if current_version.startswith('v'):
        version_prefix = 'v'
        version_number = current_version[1:]
        has_prefix = True
    else:
        version_number = current_version

    # Add relevant data to context
    version_context = {
        **context,
        "commit_messages": commit_messages,
        "latest_version": version_number,
    }

    prompt = render_prompt(
        "templates/version_prompt.txt",
        version_context,
    )

    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that determines the next software version based on semantic versioning "
                        "principles. You analyze commit messages to identify breaking changes, new features, and bug fixes "
                        "to determine whether to increment the major, minor, or patch version."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,  # Lower temperature for more consistent output
        )

        # Extract the version number from the response
        raw_response = response.choices[0].message.content
        # Look for a version pattern (with or without 'v' prefix)
        version_match = re.search(r'(?:Version:\s*)(v?\d+\.\d+\.\d+)', raw_response)

        if version_match:
            next_version = version_match.group(1)

            # Handle version prefix consistency
            if has_prefix and not next_version.startswith('v'):
                next_version = f"v{next_version}"
            elif not has_prefix and next_version.startswith('v'):
                next_version = next_version[1:]
        else:
            # Fallback: just return the response text (should be a version number)
            next_version = raw_response.strip()

            # Add prefix if needed for consistency
            if has_prefix and not next_version.startswith('v'):
                next_version = f"{version_prefix}{next_version}"

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        logger.warning("Falling back to incrementing patch version")

        # Extract version components
        try:
            version_parts = list(map(int, re.findall(r'\d+', version_number)))
            while len(version_parts) < 3:
                version_parts.append(0)

            # Increment patch version
            version_parts[2] += 1
            next_version = ".".join(map(str, version_parts))

            # Add prefix if needed
            if has_prefix:
                next_version = f"{version_prefix}{next_version}"
        except Exception:
            # If all else fails, just return the current version
            next_version = current_version

    return next_version


def generate_changelog(
        commit_messages: str,
        next_version: str,
        model: str,
        context: Dict[str, Any] = None,
        language: Optional[str] = "en"
) -> str:
    """
    Generate a changelog from the processed commit messages.

    Args:
        commit_messages: The processed commit messages
        next_version: The next version string
        model: The OpenAI model to use
        context: Additional context information for the prompts

    Returns:
        The generated changelog as markdown text
    """
    if not context:
        context = {}

    logger.info("Generating changelog...")

    # Prepare context
    changelog_context = {
        **context,
        "commit_messages": commit_messages,
        "next_version": next_version,
        "current_date": context.get("current_date", datetime.today().strftime("%Y-%m-%d")),
    }

    template_path = "templates/changelog_prompt.txt"
    if language and language.lower() != "en":
        lang = language.lower()
        if lang == "fr":
            template_path = "templates/fr_changelog_prompt.txt"
        elif lang == "es":
            template_path = "templates/es_changelog_prompt.txt"
    prompt = render_prompt(
        template_path,
        changelog_context,
    )

    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that generates detailed, well-structured changelogs in markdown format. "
                        "You organize changes by type (features, fixes, etc.) and ensure the changelog is clear and useful "
                        "for users to understand what has changed in the new version."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.4,  # Slightly higher temperature for more natural text
        )
        changelog = response.choices[0].message.content
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")

        # Create a basic fallback changelog
        changelog = f"""## [{next_version}] - {changelog_context['current_date']}

### Changes
- Various updates and improvements

_Note: This is a fallback changelog due to an error in generation._
"""

    return changelog


def generate_changelog_and_next_version(
        raw_commit_messages: str,
        current_version: str,
        model: str,
        max_context_tokens: int,
        context: Dict[str, Any] = None,
        language: Optional[str] = "en"
) -> Tuple[str, str]:
    """
    Generate a changelog and determine the next version based on commit messages.

    Args:
        raw_commit_messages: The raw commit messages
        current_version: The current version string
        model: The OpenAI model to use
        max_context_tokens: Maximum number of tokens to use in each API call
        context: Additional context information for the prompts

    Returns:
        A tuple of (changelog, next_version)
    """
    if not context:
        context = {}

    # Process commit messages
    processed_commits = process_commit_messages(
        raw_commit_messages,
        model,
        max_context_tokens,
        context
    )

    # Determine next version
    next_version = determine_next_version(
        current_version,
        processed_commits,
        model,
        context
    )

    # Generate changelog
    changelog = generate_changelog(
        processed_commits,
        next_version,
        model,
        context,
        language=language
    )

    return changelog, next_version
