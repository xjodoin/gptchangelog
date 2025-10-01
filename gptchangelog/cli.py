import argparse
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import git
import openai
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress
from rich.prompt import Confirm

from .config import init_config, load_openai_config, show_config
from .enhanced_git_utils import get_enhanced_commit_data
from .enhanced_openai_utils import analyze_changelog_quality, generate_enhanced_changelog_and_version
from .git_utils import get_commit_messages_since, get_latest_tag, get_repository_name
from .openai_utils import generate_changelog_and_next_version
from .utils import get_package_version, prepend_changelog_to_file

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
console = Console()


@dataclass
class GenerationResult:
    repo_name: str
    changelog: str
    next_version: str
    stats: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    compare_url: Optional[str] = None
    contributors: Optional[List[str]] = None


def run_gptchangelog(args):
    repo_path = os.path.abspath(os.path.expanduser(getattr(args, "repo", ".")))
    original_cwd = os.getcwd()

    try:
        os.chdir(repo_path)
    except OSError as exc:
        logger.error(f"Repository path is not accessible: {repo_path} ({exc})")
        return 1

    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        model = os.environ.get("GPTCHANGELOG_MODEL")
        max_tokens = os.environ.get("GPTCHANGELOG_MAX_TOKENS")

        if not api_key or not model or not max_tokens:
            try:
                config_api_key, config_model, config_max_tokens = load_openai_config()
                api_key = api_key or config_api_key
                model = model or config_model
                max_tokens = max_tokens or config_max_tokens
            except FileNotFoundError as exc:
                logger.error(exc)
                return 1

        if args.model:
            model = args.model
        if args.max_tokens:
            max_tokens = args.max_tokens

        model = model or "gpt-5-mini"
        max_tokens = int(max_tokens or 200000)

        if not api_key:
            logger.error("No OpenAI API key found. Set it in config or use OPENAI_API_KEY environment variable.")
            return 1

        openai.api_key = api_key

        try:
            repo = git.Repo(".")
            repo_name = get_repository_name(repo)
            resolved_repo_path = repo.working_tree_dir or repo_path
        except git.InvalidGitRepositoryError:
            logger.error("Specified path is not a git repository.")
            return 1

        from_commit = args.since
        to_commit = args.to or "HEAD"

        if from_commit is None:
            try:
                from_commit = get_latest_tag(repo)
                console.print(f"[green]Using latest tag: {from_commit}[/green]")
            except Exception as exc:
                logger.error(f"Failed to get latest tag: {exc}")
                from_commit = repo.git.rev_list("--max-parents=0", "HEAD")
                console.print(f"[yellow]No tags found, using initial commit: {from_commit[:8]}...[/yellow]")

        current_version = args.current_version or from_commit

        stats_raw: Optional[Dict[str, Any]] = None
        compare_url: Optional[str] = None
        contributor_names: Optional[List[str]] = None

        if args.legacy:
            console.print("[cyan]Using legacy changelog generation...[/cyan]")

            with Progress() as progress:
                task = progress.add_task("[cyan]Fetching commit messages...", total=100)
                progress.update(task, advance=50)

                commit_range = f"{from_commit}..{to_commit}"
                try:
                    _, commit_messages = get_commit_messages_since(
                        latest_commit=from_commit,
                        to_commit=to_commit,
                        repo_path=resolved_repo_path,
                    )

                    if not commit_messages:
                        console.print("[yellow]No new commit messages found.[/yellow]")
                        return 0

                    num_commits = len(commit_messages.strip().split("\n"))
                    console.print(f"[green]Found {num_commits} commits in range {commit_range}[/green]")
                    progress.update(task, advance=50)
                except Exception as exc:
                    logger.error(f"Failed to fetch commit messages: {exc}")
                    return 1

            with Progress() as progress:
                task = progress.add_task("[cyan]Generating changelog...", total=100)
                context = {
                    "project_name": repo_name,
                    "current_date": datetime.today().strftime("%Y-%m-%d"),
                }
                progress.update(task, advance=25)

                try:
                    language = args.language
                    if language != "en":
                        console.print(f"[blue]Generating changelog in {language}[/blue]")

                    changelog, next_version = generate_changelog_and_next_version(
                        commit_messages,
                        current_version,
                        model,
                        max_tokens,
                        context,
                        language=language,
                    )
                    progress.update(task, advance=75)
                except Exception as exc:
                    logger.error(f"Failed to generate changelog: {exc}")
                    return 1
        else:
            console.print("[cyan]Using enhanced changelog generation...[/cyan]")

            with Progress(transient=True, console=console) as progress:
                task = progress.add_task("[cyan]Analyzing commits with enhanced parser...", total=100)
                progress.update(task, completed=20)

                try:
                    commits, stats_raw = get_enhanced_commit_data(
                        from_commit,
                        to_commit,
                        repo_path=resolved_repo_path,
                    )

                    if not commits:
                        console.print("[yellow]No commits found in the specified range.[/yellow]")
                        return 0

                    console.print(f"[green]Analyzed {len(commits)} commits with enhanced parser[/green]")
                    progress.update(task, completed=60)

                    if args.stats:
                        console.print()
                        console.print("[bold cyan]📊 Commit Statistics:[/bold cyan]")
                        console.print(f"[green]Total commits:[/green] {stats_raw['total_commits']}")
                        console.print(f"[yellow]Breaking changes:[/yellow] {stats_raw['breaking_changes']}")
                        console.print(f"[blue]Files changed:[/blue] {stats_raw['total_files_changed']}")
                        console.print(f"[magenta]Code changes:[/magenta] +{stats_raw['total_insertions']} -{stats_raw['total_deletions']} lines")

                        if stats_raw['most_changed_components']:
                            components = [
                                f"{component}({count})"
                                for component, count in stats_raw['most_changed_components'][:5]
                            ]
                            console.print(f"[cyan]Main components:[/cyan] {', '.join(components)}")
                        console.print()

                    progress.update(task, completed=100)
                except Exception as exc:
                    logger.error(f"Failed to analyze commits: {exc}")
                    return 1

            language = args.language
            if language != "en":
                console.print(f"[blue]Generating changelog in {language}[/blue]")

            with console.status("[cyan]Generating enhanced changelog...[/cyan]", spinner="dots"):
                try:
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

                    if not args.no_contributors:
                        try:
                            contributor_names = sorted({str(commit.author) for commit in commits})
                        except Exception:
                            contributor_names = None

                    extra_context = {
                        "compare_url": compare_url,
                        "contributors": contributor_names,
                        "use_emojis": not args.no_emojis,
                    }
                    if args.section_order:
                        extra_context["section_order"] = args.section_order

                    changelog, next_version = generate_enhanced_changelog_and_version(
                        commits,
                        current_version,
                        repo_name,
                        stats_raw,
                        model=model,
                        max_tokens=max_tokens,
                        language=language,
                        extra_context=extra_context,
                    )
                except Exception as exc:
                    logger.error(f"Failed to generate enhanced changelog: {exc}")
                    return 1

            console.print("[green]Enhanced changelog generated.[/green]")

        if args.interactive:
            should_edit = Confirm.ask("Would you like to edit the changelog?")
            if should_edit:
                temp_file = os.path.join(os.getcwd(), ".temp_changelog.md")
                with open(temp_file, "w") as file:
                    file.write(changelog)

                editor = os.environ.get("EDITOR", "vim")
                console.print("[dim]Opening editor...[/dim]")
                os.system(f"{editor} {temp_file}")

                with open(temp_file, "r") as file:
                    changelog = file.read()

                os.unlink(temp_file)
                console.print("[green]Loaded edited changelog.[/green]")

        ui_mode = determine_ui_mode(args.ui)

        quality_metrics = None
        if args.quality_analysis:
            quality_metrics = analyze_changelog_quality(changelog)
        elif ui_mode == "textual":
            try:
                quality_metrics = analyze_changelog_quality(changelog)
            except Exception:
                quality_metrics = None

        stats_for_display = None
        if stats_raw and (args.stats or ui_mode == "textual"):
            stats_for_display = _prepare_stats(stats_raw)

        result = GenerationResult(
            repo_name=repo_name,
            changelog=changelog,
            next_version=next_version,
            stats=stats_for_display,
            quality_metrics=quality_metrics,
            compare_url=compare_url,
            contributors=contributor_names,
        )

        display_result(result, ui_mode, args)

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
    finally:
        os.chdir(original_cwd)


def determine_ui_mode(requested: Optional[str]) -> str:
    mode = (requested or "auto").lower()
    if mode == "plain":
        return "plain"
    if mode == "textual":
        return "textual"

    try:
        import importlib

        importlib.import_module("textual")
    except ImportError:
        return "plain"
    return "textual"


def _prepare_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_commits": stats.get("total_commits"),
        "breaking_changes": stats.get("breaking_changes"),
        "by_type": dict(stats.get("by_type", {})),
        "most_changed_components": stats.get("most_changed_components", []),
    }


def display_result(result: GenerationResult, ui_mode: str, args) -> str:
    if ui_mode == "textual":
        try:
            from .textual_ui import TextualDisplayData, display_textual_result

            display_textual_result(
                TextualDisplayData(
                    repo_name=result.repo_name,
                    changelog=result.changelog,
                    next_version=result.next_version,
                    stats=result.stats,
                    quality_metrics=result.quality_metrics,
                    compare_url=result.compare_url,
                    contributors=result.contributors,
                )
            )
            return "textual"
        except ImportError as exc:
            console.print(
                f"[yellow]Textual UI unavailable ({exc}). Falling back to plain output.[/yellow]"
            )

    console.print()
    console.print("[bold]Generated Changelog:[/bold]")
    console.print(Markdown(result.changelog))
    console.print()
    console.print(f"[bold]Next version:[/bold] {result.next_version}")

    if result.compare_url:
        console.print(f"[blue]Compare:[/blue] {result.compare_url}")
    if result.contributors:
        names = ", ".join(result.contributors[:10])
        if len(result.contributors) > 10:
            names += ", …"
        console.print(f"[blue]Contributors:[/blue] {names}")

    if args.stats and result.stats:
        console.print()
        console.print("[bold cyan]📊 Commit Statistics:[/bold cyan]")
        console.print(f"[green]Total commits:[/green] {result.stats.get('total_commits')}")
        console.print(f"[yellow]Breaking changes:[/yellow] {result.stats.get('breaking_changes')}")
        by_type = result.stats.get("by_type") or {}
        if by_type:
            type_summary = ", ".join(f"{t} ({c})" for t, c in sorted(by_type.items()))
            console.print(f"[blue]Types:[/blue] {type_summary}")
        components = result.stats.get("most_changed_components") or []
        if components:
            component_summary = ", ".join(f"{comp} ({count})" for comp, count in components[:5])
            console.print(f"[magenta]Hot components:[/magenta] {component_summary}")

    if args.quality_analysis and result.quality_metrics:
        metrics = result.quality_metrics
        console.print()
        console.print("[bold cyan]📊 Changelog Quality Analysis:[/bold cyan]")
        console.print(f"[green]Quality Score:[/green] {metrics['quality_score']}/100")
        console.print(
            f"[blue]Structure:[/blue] {'✓' if metrics['has_proper_header'] else '✗'} Header, "
            f"{'✓' if metrics['has_categories'] else '✗'} Categories, "
            f"{'✓' if metrics['has_bullet_points'] else '✗'} Bullets"
        )
        console.print(
            f"[yellow]Content:[/yellow] {metrics['line_count']} lines, "
            f"{metrics['avg_bullet_length']:.1f} avg chars per bullet"
        )
        if metrics.get("has_breaking_changes"):
            console.print("[red]⚠️ Contains breaking changes[/red]")
        if metrics.get("empty_sections"):
            console.print(f"[orange]⚠️ {metrics['empty_sections']} empty sections detected[/orange]")

        if metrics.get("quality_score", 100) < 70:
            console.print()
            console.print("[bold yellow]💡 Quality Improvement Suggestions:[/bold yellow]")
            if not metrics.get("has_proper_header"):
                console.print("- Add proper version header with date")
            if not metrics.get("has_categories"):
                console.print("- Organize changes into categories")
            if metrics.get("avg_bullet_length", 0) < 20:
                console.print("- Add more descriptive bullet points")
            if metrics.get("empty_sections"):
                console.print("- Remove empty sections")

    return "plain"


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

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # 'config' sub-command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_subparsers = config_parser.add_subparsers(
        dest="config_command", help="Config commands"
    )

    # 'config show' sub-command
    config_subparsers.add_parser("show", help="Show current configuration")

    # 'config init' sub-command
    config_subparsers.add_parser("init", help="Initialize configuration")

    # 'generate' sub-command
    generate_parser = subparsers.add_parser("generate", help="Generate changelog")

    # Commit range options
    generate_parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Starting point (commit hash, tag, or reference). Defaults to the most recent tag.",
    )
    generate_parser.add_argument(
        "--to",
        type=str,
        default="HEAD",
        help="Ending point (commit hash, tag, or reference). Defaults to HEAD.",
    )
    generate_parser.add_argument(
        "--repo",
        type=str,
        default=".",
        help="Path to the git repository to analyze. Defaults to the current working directory.",
    )

    # Output options
    generate_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="CHANGELOG.md",
        help="Output file for the changelog. Defaults to CHANGELOG.md.",
    )
    generate_parser.add_argument(
        "--current-version",
        type=str,
        default=None,
        help="Current version to use (overrides auto-detection from git tags).",
    )
    generate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate changelog but don't save it to file.",
    )
    generate_parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Enable interactive mode to review and edit the changelog before saving.",
    )
    generate_parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="OpenAI model to use (overrides the one in config).",
    )
    generate_parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum context tokens to use (overrides the one in config).",
    )
    generate_parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Language for the changelog (default: English).",
    )
    generate_parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use legacy changelog generation (default is enhanced mode).",
    )
    generate_parser.add_argument(
        "--quality-analysis",
        action="store_true",
        help="Show quality metrics for the generated changelog.",
    )
    generate_parser.add_argument(
        "--stats",
        action="store_true",
        help="Display detailed commit statistics and analysis.",
    )
    generate_parser.add_argument(
        "--no-compare-link",
        action="store_true",
        help="Do not include a compare link in the changelog header.",
    )
    generate_parser.add_argument(
        "--no-contributors",
        action="store_true",
        help="Do not include a contributors summary.",
    )
    generate_parser.add_argument(
        "--section-order",
        type=str,
        default=None,
        help="Custom section order as a comma-separated list (e.g., '⚠️ Breaking Changes,✨ Features,🐛 Bug Fixes').",
    )
    generate_parser.add_argument(
        "--no-emojis",
        action="store_true",
        help="Do not include emojis in section titles.",
    )
    generate_parser.add_argument(
        "--ui",
        choices=["auto", "textual", "plain"],
        default="auto",
        help="Choose the output experience ('textual' for TUI, 'plain' for standard console).",
    )

    # Set generate as the default command
    if len(sys.argv) > 1 and sys.argv[1] not in [
        "config",
        "generate",
        "-v",
        "--version",
        "-h",
        "--help",
    ]:
        sys.argv.insert(1, "generate")
    elif len(sys.argv) == 1:
        sys.argv.append("generate")

    args = parser.parse_args()

    if args.command == "config":
        if args.config_command == "show":
            show_config()
        elif args.config_command == "init":
            init_config()
        else:
            parser.print_help()
    elif args.command == "generate":
        return run_gptchangelog(args)
    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(app())
