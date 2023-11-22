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


def generate_changelog_and_next_version(raw_commit_messages, latest_version):
    
    prompt = render_prompt(
        "templates/commits_prompt.txt",
        {"commit_messages": raw_commit_messages},
    )
    
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "Your task is to process the following series of commit messages. Start by analyzing each message to identify key themes and changes. Detect and mark any redundant information across these messages. Focus on refining the clarity and conciseness of each message. Merge similar or redundant points to create a single cohesive message that clearly communicates all relevant changes and updates. Ensure the final message is concise, clear, and aligns with standard commit message guidelines.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    
    commit_messages = response.choices[0].message.content
    
    print(f"Refactor commits: {commit_messages}")
    
    # Assuming render_prompt is a function you've defined elsewhere
    prompt = render_prompt(
        "templates/version_prompt.txt",
        {"commit_messages": commit_messages, "latest_version": latest_version},
    )

    # Refactored to use the updated OpenAI API
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant, optimized to provide accurate and concise information.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    next_version = response.choices[0].message.content.strip()

    print(f"Next version: {next_version}")

    # Generate the changelog
    prompt = render_prompt(
        "templates/changelog_prompt.txt",
        {
            "commit_messages": commit_messages,
            "next_version": next_version,
            "current_date": datetime.today().strftime("%Y-%m-%d"),
        },
    )

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant, optimized to provide accurate and concise information.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    changelog = response.choices[0].message.content

    return changelog


# Function to fetch commit messages since the most recent tag
def get_commit_messages_since_latest_tag(repo_path=".", min_length=10, max_length=200):
    repo = git.Repo(repo_path)
    latest_tag = repo.git.describe("--tags", "--abbrev=0")
    # Using --no-merges to exclude merge commits and iterating over the log
    commit_messages = set()
    for commit in repo.iter_commits(f"{latest_tag}..HEAD", no_merges=True):
        message = commit.message.strip().split("\n")[0]  # Taking the first line of the commit message
        # Check if message length is within the specified range
        if min_length <= len(message) <= max_length:
            commit_messages.add(message)
        elif len(message) > max_length:
            commit_messages.add(message[:max_length] + "...")  # Truncate and add ellipsis


    return latest_tag, "\n".join(commit_messages)



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


def load_openai_api_key(config_file_name="config.ini"):
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".config", "gptchangelog")
    config_file = os.path.join(config_dir, config_file_name)

    if not os.path.exists(config_file):
        raise FileNotFoundError(
            f"Configuration file '{config_file}' not found in the .config/gptchangelog directory."
        )

    config = configparser.ConfigParser()
    config.read(config_file)
    return config["openai"]["api_key"]


def main():
    # Set up the argument parser with version information from the package
    parser = argparse.ArgumentParser(description="gptchangelog")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"gptchangelog {get_package_version()}",
    )

    # Parse the arguments
    args = parser.parse_args()

    openai.api_key = load_openai_api_key()

    latest_tag, commit_messages = get_commit_messages_since_latest_tag()
    changelog = generate_changelog_and_next_version(commit_messages, latest_tag)

    prepend_changelog_to_file(changelog)

    print("Changelog generated and prepended to CHANGELOG.md:")
    print(changelog)
