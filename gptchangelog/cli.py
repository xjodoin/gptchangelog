# main.py

import argparse
import logging
import git
import openai
from rich.console import Console

from .utils import get_package_version
from .config import load_openai_config, init_config, show_config
from .git_utils import get_commit_messages_since
from .openai_utils import generate_changelog_and_next_version
from .utils import prepend_changelog_to_file

console = Console()


def run_gptchangelog(args):
    try:
        api_key, model, max_context_tokens = load_openai_config()
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return

    openai.api_key = api_key

    latest_commit = args.since
    repo = git.Repo(".")
    if latest_commit is None:
        try:
            latest_commit = repo.git.describe("--tags", "--abbrev=0")
        except git.GitCommandError:
            latest_commit = repo.git.rev_list("--max-parents=0", "HEAD")

    latest_commit, commit_messages = get_commit_messages_since(latest_commit)
    if not commit_messages:
        console.print("[bold yellow]No new commit messages found.[/bold yellow]")
        return

    changelog, next_version = generate_changelog_and_next_version(
        commit_messages, latest_commit, model, max_context_tokens
    )

    if not changelog:
        console.print("[bold red]Failed to generate changelog.[/bold red]")
        return

    prepend_changelog_to_file(changelog)

    console.print("\n[bold green]Changelog generated and prepended to CHANGELOG.md:[/bold green]")
    console.print(changelog)
    console.print(f"\n[bold green]Next version:[/bold green] {next_version}")
    console.print("[bold cyan]Done.[/bold cyan]")


def app():
    parser = argparse.ArgumentParser(description="Generate a changelog using GPT.")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"gpt-changelog {get_package_version()}",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # 'config' sub-command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_subparsers = config_parser.add_subparsers(
        dest="config_command", help="Config commands"
    )

    # 'config show' sub-command
    config_subparsers.add_parser("show", help="Show current configuration")

    # 'config init' sub-command
    config_subparsers.add_parser("init", help="Initialize configuration")

    # Main options
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Specify the commit hash or tag to start fetching commit messages from. If not provided, uses the most recent tag.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with detailed logging.",
    )
    args = parser.parse_args()

    # Configure logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
    else:
        logging.basicConfig(level=logging.ERROR)
        logger = logging.getLogger(__name__)

    if args.command == "config":
        if args.config_command == "show":
            show_config()
        elif args.config_command == "init":
            init_config()
        else:
            parser.print_help()
    else:
        # Proceed with the main functionality
        run_gptchangelog(args)


if __name__ == "__main__":
    app()
