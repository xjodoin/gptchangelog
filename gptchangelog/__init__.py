import configparser
import os

import git
import openai


def generate_changelog_and_next_version(commit_messages, latest_version):
    prompt = (
        f"Based on the following commit messages and the latest version {latest_version}, "
        f"determine the next version using semantic versioning:\n\n{commit_messages}\n\n"
        f"Just the next version: "
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt, }
        ],
    )
    next_version = response.choices[0].message['content'].strip()

    print(f"Next version: {next_version}")

    prompt = (
        f"Generate a well-formatted changelog in markdown format for a software project "
        f"with the following commit messages:\n\n{commit_messages}\n\n"
        f"Please exclude empty sections in the changelog. The next version is {next_version}.\n\n"
        f"Changelog:\n"
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt, }
        ],
    )
    changelog = response.choices[0].message['content'].strip()

    return changelog


# Function to fetch commit messages since the most recent tag
def get_commit_messages_since_latest_tag(repo_path="."):
    repo = git.Repo(repo_path)
    latest_tag = repo.git.describe("--tags", "--abbrev=0")
    commit_messages = repo.git.log(f"{latest_tag}..HEAD", pretty="%s").split("\n")
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
        raise FileNotFoundError(f"Configuration file '{config_file}' not found in the .config/gptchangelog directory.")

    config = configparser.ConfigParser()
    config.read(config_file)
    return config["openai"]["api_key"]


def main():
    openai.api_key = load_openai_api_key()

    latest_tag, commit_messages = get_commit_messages_since_latest_tag()
    changelog = generate_changelog_and_next_version(commit_messages, latest_tag)

    prepend_changelog_to_file(changelog)

    print("Changelog generated and prepended to CHANGELOG.md:")
    print(changelog)
