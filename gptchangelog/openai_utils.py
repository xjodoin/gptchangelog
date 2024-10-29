# openai_utils.py

import logging
from datetime import datetime

import openai
from openai import OpenAIError
from rich.console import Console
from rich.prompt import Prompt, Confirm

from .utils import render_prompt, split_commit_messages

logger = logging.getLogger(__name__)
console = Console()


def generate_changelog_and_next_version(
    raw_commit_messages, latest_version, model, max_context_tokens
):
    commit_messages_list = raw_commit_messages.strip().split("\n")
    prompt_batches = split_commit_messages(
        commit_messages_list, max_context_tokens, model
    )

    refined_commit_messages = []
    for i, batch in enumerate(prompt_batches):
        console.print(
            f"[bold cyan]Processing commit messages batch {i + 1}/{len(prompt_batches)}...[/bold cyan]"
        )
        logger.debug(f"Processing batch {i + 1}/{len(prompt_batches)}...")

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

    console.print("\n[bold cyan]Determining the next version...[/bold cyan]")
    logger.debug("Generating next version...")
    prompt = render_prompt(
        "templates/version_prompt.txt",
        {
            "commit_messages": combined_commit_messages,
            "latest_version": latest_version,
        },
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
        # Parse the response to get the next version and the reasoning
        next_version_info = response.choices[0].message.content.strip()
        # Assuming the assistant returns the version followed by an explanation
        if "\n" in next_version_info:
            next_version_line, explanation = next_version_info.split("\n", 1)
        else:
            next_version_line = next_version_info
            explanation = "No explanation provided."

        suggested_version = next_version_line.strip()
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        suggested_version = latest_version  # Fallback to the latest version
        explanation = "Could not determine the next version due to an API error."

    # Present the suggested version and explanation to the user
    console.print(f"\n[bold green]Suggested next version:[/bold green] {suggested_version}")
    console.print(f"[bold green]Reasoning:[/bold green]\n{explanation}")

    # Ask the user to confirm or input a different version
    use_suggested = Confirm.ask(
        f"Do you want to use the suggested version '{suggested_version}'?", default=True
    )

    if not use_suggested:
        user_version = Prompt.ask("Please enter the desired version")
        next_version = user_version.strip()
    else:
        next_version = suggested_version

    logger.info(f"Next version selected: {next_version}")

    console.print("\n[bold cyan]Generating changelog...[/bold cyan]")
    logger.debug("Generating changelog...")
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

    return changelog, next_version
