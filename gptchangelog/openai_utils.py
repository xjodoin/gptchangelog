# openai_utils.py

import logging
from datetime import datetime

import openai
from openai import OpenAIError

from .utils import render_prompt, split_commit_messages

logger = logging.getLogger(__name__)


def generate_changelog_and_next_version(raw_commit_messages, latest_version, model, max_context_tokens):
    commit_messages_list = raw_commit_messages.strip().split("\n")
    prompt_batches = split_commit_messages(commit_messages_list, max_context_tokens, model)

    refined_commit_messages = []
    for i, batch in enumerate(prompt_batches):
        logger.info(f"Processing batch {i + 1}/{len(prompt_batches)}...")

        prompt = render_prompt(
            "templates/commits_prompt.txt",
            {"commit_messages": batch},
        )

        try:
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an assistant that refines commit messages for clarity and conciseness."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
            refined_message = response.choices[0].message.content
            refined_commit_messages.append(refined_message)
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            continue

    combined_commit_messages = "\n".join(refined_commit_messages)

    logger.info("Generating next version...")
    prompt = render_prompt(
        "templates/version_prompt.txt",
        {"commit_messages": combined_commit_messages, "latest_version": latest_version},
    )

    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that determines the next software version based on semantic versioning."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
        next_version = response.choices[0].message.content
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        next_version = latest_version  # Fallback to the latest version

    logger.info(f"Next version: {next_version}")

    logger.info("Generating changelog...")
    prompt = render_prompt(
        "templates/changelog_prompt.txt",
        {
            "commit_messages": combined_commit_messages,
            "next_version": next_version,
            "current_date": datetime.today().strftime("%Y-%m-%d"),
        },
    )

    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that generates changelogs in markdown format based on commit messages."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
        changelog = response.choices[0].message.content
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        changelog = ""  # Fallback to empty changelog

    return changelog
