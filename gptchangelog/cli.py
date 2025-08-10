import argparse
import logging
import os
import sys
import git
import openai
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress
from rich.prompt import Confirm, Prompt
from datetime import datetime

from .utils import get_package_version, prepend_changelog_to_file, render_prompt
from .config import load_openai_config, init_config, show_config
from .git_utils import get_commit_messages_since, get_latest_tag, get_repository_name
from .openai_utils import generate_changelog_and_next_version
from .enhanced_git_utils import get_enhanced_commit_data
from .enhanced_openai_utils import generate_enhanced_changelog_and_version, analyze_changelog_quality

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()


def run_gptchangelog(args):
    # Check for environment variables first
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("GPTCHANGELOG_MODEL")
    max_tokens = os.environ.get("GPTCHANGELOG_MAX_TOKENS")

    # If not in environment, load from config
    if not api_key or not model or not max_tokens:
        try:
            config_api_key, config_model, config_max_tokens = load_openai_config()
            api_key = api_key or config_api_key
            model = model or config_model
            max_tokens = max_tokens or config_max_tokens
        except FileNotFoundError as e:
            logger.error(e)
            return 1

    # Command line arguments override config and env vars
    if args.model:
        model = args.model

    if args.max_tokens:
        max_tokens = args.max_tokens

    # Ensure we have values or use defaults
    model = model or "gpt-4o"
    max_tokens = int(max_tokens or 80000)

    if not api_key:
        logger.error("No OpenAI API key found. Set it in config or use OPENAI_API_KEY environment variable.")
        return 1

    openai.api_key = api_key

    # Get repository information
    try:
        repo = git.Repo(".")
        repo_name = get_repository_name(repo)
    except git.InvalidGitRepositoryError:
        logger.error("Current directory is not a git repository.")
        return 1

    # Get commit range
    from_commit = args.since
    to_commit = args.to or "HEAD"

    if from_commit is None:
        try:
            from_commit = get_latest_tag(repo)
            console.print(f"[green]Using latest tag: {from_commit}[/green]")
        except Exception as e:
            logger.error(f"Failed to get latest tag: {e}")
            from_commit = repo.git.rev_list("--max-parents=0", "HEAD")
            console.print(f"[yellow]No tags found, using initial commit: {from_commit[:8]}...[/yellow]")

    # Get current version from latest tag or provided version
    current_version = args.current_version or from_commit
    
    # Choose between enhanced and legacy generation (enhanced is default)
    if args.legacy:
        console.print("[cyan]Using legacy changelog generation...[/cyan]")
        
        # Standard generation
        with Progress() as progress:
            task = progress.add_task("[cyan]Fetching commit messages...", total=100)
            progress.update(task, advance=50)

            commit_range = f"{from_commit}..{to_commit}"
            try:
                latest_commit, commit_messages = get_commit_messages_since(
                    latest_commit=from_commit,
                    to_commit=to_commit
                )

                if not commit_messages:
                    console.print("[yellow]No new commit messages found.[/yellow]")
                    return 0

                num_commits = len(commit_messages.strip().split("\n"))
                console.print(f"[green]Found {num_commits} commits in range {commit_range}[/green]")
                progress.update(task, advance=50)
            except Exception as e:
                logger.error(f"Failed to fetch commit messages: {e}")
                return 1

        # Generate standard changelog
        with Progress() as progress:
            task = progress.add_task("[cyan]Generating changelog...", total=100)

            # Set up context for prompt rendering
            context = {
                "project_name": repo_name,
                "current_date": datetime.today().strftime("%Y-%m-%d"),
            }

            progress.update(task, advance=25)

            # Generate the changelog
            try:
                # Handle language setting for multi-language support
                language = args.language
                if language != "en":
                    console.print(f"[blue]Generating changelog in {language}[/blue]")

                changelog, next_version = generate_changelog_and_next_version(
                    commit_messages,
                    current_version,
                    model,
                    max_tokens,
                    context,
                    language=language
                )
                progress.update(task, advance=75)
            except Exception as e:
                logger.error(f"Failed to generate changelog: {e}")
                return 1
                
    else:
        console.print("[cyan]Using enhanced changelog generation...[/cyan]")
        
        # Get enhanced commit data
        with Progress() as progress:
            task = progress.add_task("[cyan]Analyzing commits with enhanced parser...", total=100)
            progress.update(task, advance=25)

            try:
                commits, stats = get_enhanced_commit_data(from_commit, to_commit)
                
                if not commits:
                    console.print("[yellow]No commits found in the specified range.[/yellow]")
                    return 0

                console.print(f"[green]Analyzed {len(commits)} commits with enhanced parser[/green]")
                progress.update(task, advance=75)
                
                # Show commit statistics if requested
                if args.stats:
                    console.print("\n[bold cyan]📊 Commit Statistics:[/bold cyan]")
                    console.print(f"[green]Total commits:[/green] {stats['total_commits']}")
                    console.print(f"[yellow]Breaking changes:[/yellow] {stats['breaking_changes']}")
                    console.print(f"[blue]Files changed:[/blue] {stats['total_files_changed']}")
                    console.print(f"[magenta]Code changes:[/magenta] +{stats['total_insertions']} -{stats['total_deletions']} lines")
                    
                    if stats['most_changed_components']:
                        components = [f"{comp}({count})" for comp, count in stats['most_changed_components'][:5]]
                        console.print(f"[cyan]Main components:[/cyan] {', '.join(components)}")
                    
                    console.print()
                
                progress.update(task, advance=100)
            except Exception as e:
                logger.error(f"Failed to analyze commits: {e}")
                return 1

        # Generate enhanced changelog
        with Progress() as progress:
            task = progress.add_task("[cyan]Generating enhanced changelog...", total=100)

            try:
                # Handle language setting for multi-language support
                language = args.language
                if language != "en":
                    console.print(f"[blue]Generating changelog in {language}[/blue]")

                # Optional compare URL (GitHub)
                compare_url = None
                if not args.no_compare_link:
                    try:
                        remote_url = repo.remotes.origin.url
                        path = None
                        if remote_url.startswith("git@github.com:"):
                            path = remote_url[len("git@github.com:"):]
                        elif "github.com/" in remote_url:
                            path = remote_url.split("github.com/")[1]
                        if path:
                            if path.endswith(".git"):
                                path = path[:-4]
                            compare_url = f"https://github.com/{path}/compare/{from_commit}...{to_commit}"
                    except Exception:
                        compare_url = None

                # Contributors summary
                contributors = None
                if not args.no_contributors:
                    try:
                        contributors = sorted({c.author for c in commits})
                    except Exception:
                        contributors = None

                extra_context = {
                    "compare_url": compare_url,
                    "contributors": contributors,
                    "use_emojis": not args.no_emojis,
                }
                if args.section_order:
                    extra_context["section_order"] = args.section_order

                changelog, next_version = generate_enhanced_changelog_and_version(
                    commits,
                    current_version,
                    repo_name,
                    stats,
                    model,
                    max_tokens,
                    language=language,
                    extra_context=extra_context
                )
                progress.update(task, advance=100)
            except Exception as e:
                logger.error(f"Failed to generate enhanced changelog: {e}")
                return 1

    # Display the generated changelog
    console.print("\n[bold]Generated Changelog:[/bold]")
    console.print(Markdown(changelog))
    console.print(f"\n[bold]Next version:[/bold] {next_version}")
    
    # Show quality analysis if requested
    if args.quality_analysis:
        console.print("\n[bold cyan]📊 Changelog Quality Analysis:[/bold cyan]")
        quality_metrics = analyze_changelog_quality(changelog)
        
        console.print(f"[green]Quality Score:[/green] {quality_metrics['quality_score']}/100")
        console.print(f"[blue]Structure:[/blue] {'✓' if quality_metrics['has_proper_header'] else '✗'} Header, {'✓' if quality_metrics['has_categories'] else '✗'} Categories, {'✓' if quality_metrics['has_bullet_points'] else '✗'} Bullets")
        console.print(f"[yellow]Content:[/yellow] {quality_metrics['line_count']} lines, {quality_metrics['avg_bullet_length']:.1f} avg chars per bullet")
        
        if quality_metrics['has_breaking_changes']:
            console.print("[red]⚠️ Contains breaking changes[/red]")
        
        if quality_metrics['empty_sections'] > 0:
            console.print(f"[orange]⚠️ {quality_metrics['empty_sections']} empty sections detected[/orange]")
        
        # Quality recommendations
        if quality_metrics['quality_score'] < 70:
            console.print("\n[bold yellow]💡 Quality Improvement Suggestions:[/bold yellow]")
            if not quality_metrics['has_proper_header']:
                console.print("- Add proper version header with date")
            if not quality_metrics['has_categories']:
                console.print("- Organize changes into categories")
            if quality_metrics['avg_bullet_length'] < 20:
                console.print("- Add more descriptive bullet points")
            if quality_metrics['empty_sections'] > 0:
                console.print("- Remove empty sections")
        
        console.print()

    # Interactive mode to confirm or edit the changelog
    if args.interactive:
        should_edit = Confirm.ask("Would you like to edit the changelog?")
        if should_edit:
            temp_file = os.path.join(os.getcwd(), ".temp_changelog.md")
            with open(temp_file, "w") as f:
                f.write(changelog)

            # Open editor
            editor = os.environ.get("EDITOR", "vim")
            os.system(f"{editor} {temp_file}")

            # Read edited content
            with open(temp_file, "r") as f:
                changelog = f.read()

            # Remove temp file
            os.unlink(temp_file)

            # Show the edited changelog
            console.print("\n[bold]Edited Changelog:[/bold]")
            console.print(Markdown(changelog))

    # Save changelog
    if not args.dry_run:
        should_save = True
        if args.interactive:
            should_save = Confirm.ask("Save this changelog to CHANGELOG.md?")

        if should_save:
            output_file = args.output or "CHANGELOG.md"
            prepend_changelog_to_file(changelog, output_file)
            console.print(f"[green]Changelog saved to {output_file}[/green]")
    else:
        console.print("[yellow]Dry run mode - changelog not saved[/yellow]")

    return 0


def app():
    parser = argparse.ArgumentParser(
        description="Generate changelogs from git commit messages using AI"
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"gptchangelog {get_package_version()}",
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # 'config' sub-command
    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_subparsers = config_parser.add_subparsers(dest='config_command', help='Config commands')

    # 'config show' sub-command
    config_subparsers.add_parser('show', help='Show current configuration')

    # 'config init' sub-command
    config_subparsers.add_parser('init', help='Initialize configuration')

    # 'generate' sub-command
    generate_parser = subparsers.add_parser('generate', help='Generate changelog')

    # Commit range options
    generate_parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Starting point (commit hash, tag, or reference). Defaults to the most recent tag."
    )
    generate_parser.add_argument(
        "--to",
        type=str,
        default="HEAD",
        help="Ending point (commit hash, tag, or reference). Defaults to HEAD."
    )

    # Output options
    generate_parser.add_argument(
        "--output", "-o",
        type=str,
        default="CHANGELOG.md",
        help="Output file for the changelog. Defaults to CHANGELOG.md."
    )
    generate_parser.add_argument(
        "--current-version",
        type=str,
        default=None,
        help="Current version to use (overrides auto-detection from git tags)."
    )
    generate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate changelog but don't save it to file."
    )
    generate_parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Enable interactive mode to review and edit the changelog before saving."
    )
    generate_parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="OpenAI model to use (overrides the one in config)."
    )
    generate_parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum context tokens to use (overrides the one in config)."
    )
    generate_parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Language for the changelog (default: English)."
    )
    generate_parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use legacy changelog generation (default is enhanced mode with better commit analysis and AI processing)."
    )
    generate_parser.add_argument(
        "--quality-analysis",
        action="store_true",
        help="Show quality metrics for the generated changelog."
    )
    generate_parser.add_argument(
        "--stats",
        action="store_true",
        help="Display detailed commit statistics and analysis."
    )
    generate_parser.add_argument(
        "--no-compare-link",
        action="store_true",
        help="Do not include a compare link in the changelog header."
    )
    generate_parser.add_argument(
        "--no-contributors",
        action="store_true",
        help="Do not include a contributors summary."
    )
    generate_parser.add_argument(
        "--section-order",
        type=str,
        default=None,
        help="Custom section order as a comma-separated list (e.g., '⚠️ Breaking Changes,✨ Features,🐛 Bug Fixes')."
    )
    generate_parser.add_argument(
        "--no-emojis",
        action="store_true",
        help="Do not include emojis in section titles."
    )

    # Set generate as the default command
    if len(sys.argv) > 1 and sys.argv[1] not in ['config', 'generate', '-v', '--version', '-h', '--help']:
        # If first arg is not a known command but looks like an option, insert 'generate'
        sys.argv.insert(1, 'generate')
    elif len(sys.argv) == 1:
        # If no args, default to generate
        sys.argv.append('generate')

    args = parser.parse_args()

    if args.command == 'config':
        if args.config_command == 'show':
            show_config()
        elif args.config_command == 'init':
            init_config()
        else:
            parser.print_help()
    elif args.command == 'generate':
        return run_gptchangelog(args)
    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(app())
