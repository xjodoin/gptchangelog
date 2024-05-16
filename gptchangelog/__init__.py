import argparse
import configparser
import os
from datetime import datetime
from string import Template

import git
import openai
import pkg_resources


def get_package_version():
    try:
        return pkg_resources.get_distribution("gptchangelog").version
    except pkg_resources.DistributionNotFound:
        return "Unknown"


def render_prompt(template_path, context):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_template_path = os.path.join(script_dir, template_path)
    with open(full_template_path, "r") as template_file:
        template_content = template_file.read()

    template = Template(template_content)
    return template.safe_substitute(context)


def split_commit_messages(commit_messages, max_length):
    message_batches = []
    current_batch = []

    current_length = 0
    for message in commit_messages:
        message_length = len(message)
        if current_length + message_length > max_length:
            message_batches.append("\n".join(current_batch))
            current_batch = [message]
            current_length = message_length
        else:
            current_batch.append(message)
            current_length += message_length

    if current_batch:
        message_batches.append("\n".join(current_batch))

    return message_batches


def generate_changelog_and_next_version(raw_commit_messages, latest_version, model, max_context_length):
    prompt_batches = split_commit_messages(raw_commit_messages.split("\n"), max_context_length)

    refined_commit_messages = []
    for i, batch in enumerate(prompt_batches):
        print(f"Processing batch {i + 1}/{len(prompt_batches)}...")

        prompt = render_prompt(
            "templates/commits_prompt.txt",
            {"commit_messages": batch},
        )

        response = openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in refining commit messages. Your task is to analyze, identify redundancies, and improve the clarity and conciseness of the provided commit messages. "
                        "Combine similar or redundant elements to create a single cohesive message that clearly communicates all relevant changes and updates. "
                        "Ensure the final message is concise, clear, and follows standard commit message guidelines."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        refined_commit_messages.append(response.choices[0].message.content)

    combined_commit_messages = "\n".join(refined_commit_messages)

    print("Generating next version...")
    prompt = render_prompt(
        "templates/version_prompt.txt",
        {"commit_messages": combined_commit_messages, "latest_version": latest_version},
    )

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert in software versioning. Your task is to determine the next software version number based on semantic versioning principles. "
                    "Analyze the provided commit messages and increment the version number according to the following rules: "
                    "MAJOR update for incompatible API changes, MINOR update for new, backwards-compatible functionality, and PATCH update for backwards-compatible bug fixes."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    next_version = response.choices[0].message.content.strip()

    print(f"Next version: {next_version}")

    print("Generating changelog...")
    # Generate the changelog
    prompt = render_prompt(
        "templates/changelog_prompt.txt",
        {
            "commit_messages": combined_commit_messages,
            "next_version": next_version,
            "current_date": datetime.today().strftime("%Y-%m-%d"),
        },
    )

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert in creating structured and clear changelogs. Your task is to generate a concise and accurate changelog in markdown format based on the provided commit messages. "
                    "Categorize the changes under appropriate headers such as 'Added', 'Fixed', and 'Changed'. "
                    "Exclude any empty sections and ensure the changelog adheres to markdown syntax."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    changelog = response.choices[0].message.content

    return changelog


# Function to fetch commit messages since the specified commit or the most recent tag
def get_commit_messages_since(latest_commit, repo_path=".", min_length=10):
    repo = git.Repo(repo_path)
    # Using --no-merges to exclude merge commits and iterating over the log
    commit_messages = set()
    for commit in repo.iter_commits(f"{latest_commit}..HEAD", no_merges=True):
        message = commit.message.strip().split("\n")[0]  # Taking the first line of the commit message
        # Check if message length is within the specified range
        if len(message) >= min_length:
            commit_messages.add(message)

    return latest_commit, "\n".join(commit_messages)


# Function to prepend changelog to CHANGELOG.md
def prepend_changelog_to_file(changelog, filepath="CHANGELOG.md"):
    if not os.path.exists(filepath):
        with open(filepath, "w") as file:
            file.write(changelog)
    else:
        with open(filepath, "r+") as file:
            original_content = file.read()
            file.seek(0)
            file.write(changelog + "\n\n" + original_content)


def load_openai_config(config_file_name="config.ini"):
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".config", "gptchangelog")
    config_file = os.path.join(config_dir, config_file_name)

    if not os.path.exists(config_file):
        raise FileNotFoundError(
            f"Configuration file '{config_file}' not found in the .config/gptchangelog directory."
        )

    config = configparser.ConfigParser()
    config.read(config_file)
    return config["openai"]["api_key"], config["openai"].get("model", "gpt-4o")


def main():
    # Set up the argument parser with version information from the package
    parser = argparse.ArgumentParser(description="gptchangelog")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"gptchangelog {get_package_version()}",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Specify the commit hash or tag to start fetching commit messages from. If not provided, uses the most recent tag."
    )

    # Parse the arguments
    args = parser.parse_args()

    api_key, model = load_openai_config()

    openai.api_key = api_key

    latest_commit = args.since
    if latest_commit is None:
        repo = git.Repo(".")
        latest_commit = repo.git.describe("--tags", "--abbrev=0")

    latest_commit, commit_messages = get_commit_messages_since(latest_commit)
    max_context_length = 128 * 1024  # 128K context length limit for GPT-4
    changelog = generate_changelog_and_next_version(commit_messages, latest_commit, model, max_context_length)

    prepend_changelog_to_file(changelog)

    print("Changelog generated and prepended to CHANGELOG.md:")
    print(changelog)


if __name__ == "__main__":
    main()
