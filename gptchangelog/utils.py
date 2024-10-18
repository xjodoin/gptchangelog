import os
from string import Template
import tiktoken
import logging
import pkg_resources

logger = logging.getLogger(__name__)


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


def estimate_tokens(text, model="gpt-4o-mini"):
    """Estimate the number of tokens in a text for a given model."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def split_commit_messages(commit_messages, max_tokens, model="gpt-4o-mini"):
    """Split commit messages into batches that fit within the max token limit."""
    message_batches = []
    current_batch = []
    current_tokens = 0

    for message in commit_messages:
        message_tokens = estimate_tokens(message, model)
        # Add a buffer for prompt tokens
        if current_tokens + message_tokens + 50 > max_tokens:
            message_batches.append("\n".join(current_batch))
            current_batch = [message]
            current_tokens = message_tokens
        else:
            current_batch.append(message)
            current_tokens += message_tokens

    if current_batch:
        message_batches.append("\n".join(current_batch))

    return message_batches


def prepend_changelog_to_file(changelog, filepath="CHANGELOG.md"):
    if not changelog:
        logger.warning("No changelog to write.")
        return

    if not os.path.exists(filepath):
        with open(filepath, "w") as file:
            file.write(changelog)
    else:
        with open(filepath, "r+") as file:
            original_content = file.read()
            file.seek(0)
            file.write(changelog + "\n\n" + original_content)
