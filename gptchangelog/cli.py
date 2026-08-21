"""Command-line interface for deterministic, validated changelog generation."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, TextIO

import git
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm

from .config import init_config, load_openai_config, show_config
from .enhanced_git_utils import get_enhanced_commit_data
from .enhanced_openai_utils import (
    analyze_changelog_quality,
    generate_enhanced_changelog_result,
)
from .git_utils import ReleaseRange, get_repository_name, resolve_release_range
from .openai_client import (
    CODEX_PROVIDER,
    DEFAULT_MODEL_PROFILE,
    OPENAI_PROVIDER,
    ProviderConfigurationError,
    ProviderError,
    ProviderSettings,
    configure_provider,
    doctor_provider,
    has_codex_auth,
    normalize_profile,
    normalize_provider,
    resolve_model,
)
from .utils import (
    ChangelogError,
    get_package_version,
    prepend_changelog_to_file,
    validate_changelog_release,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GenerationResult:
    repo_name: str
    repo_path: str
    changelog: str
    next_version: str
    from_ref: Optional[str]
    to_ref: str
    provider: str
    model: str
    stats: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    compare_url: Optional[str] = None
    contributors: Optional[List[str]] = None
    entries: Optional[List[Dict[str, Any]]] = None
    used_fallback: bool = False


def _console() -> Console:
    """Return a diagnostics console that never contaminates stdout artifacts."""
    return Console(stderr=True)


def _diagnostic(args: argparse.Namespace, message: str, style: str = "") -> None:
    if getattr(args, "quiet", False):
        return
    _console().print(message, style=style or None, markup=False)


def _load_config(
    repo_path: Path, *, include_api_key: bool = True
) -> Dict[str, Optional[str]]:
    try:
        return load_openai_config(
            project_root=repo_path,
            include_model_source=True,
            include_api_key=include_api_key,
        )
    except FileNotFoundError:
        return {}


def resolve_provider_configuration(
    args: argparse.Namespace, repo_path: Path
) -> tuple[ProviderSettings, str, str]:
    """Resolve provider, profile, and model using documented precedence."""
    env_provider = os.environ.get("GPTCHANGELOG_PROVIDER")
    env_profile = os.environ.get("GPTCHANGELOG_PROFILE")
    env_model = os.environ.get("GPTCHANGELOG_MODEL")
    env_api_key = (os.environ.get("OPENAI_API_KEY") or "").strip() or None

    provider_override = args.provider or env_provider
    config = _load_config(repo_path, include_api_key=False)
    provider = normalize_provider(
        provider_override
        or config.get("provider")
        or (
            OPENAI_PROVIDER
            if (env_api_key or config.get("api_key"))
            else CODEX_PROVIDER
        )
    )
    if provider == OPENAI_PROVIDER:
        config = _load_config(repo_path, include_api_key=True)
    profile = normalize_profile(
        args.profile or env_profile or config.get("profile") or DEFAULT_MODEL_PROFILE
    )

    # A configured model belongs to its configured provider. Do not accidentally
    # reuse it when CLI/environment selection switches providers or profiles.
    configured_model: Optional[str] = None
    if (
        (not provider_override or provider == config.get("provider"))
        and not args.profile
        and not env_profile
    ):
        configured_model = config.get("model_override")
    model = resolve_model(
        provider,
        profile=profile,
        model=args.model or env_model or configured_model,
    )

    api_key = env_api_key or config.get("api_key")
    if provider == OPENAI_PROVIDER and not api_key:
        raise ProviderConfigurationError(
            "OpenAI authentication is unavailable. Set OPENAI_API_KEY, run "
            "`gptchangelog config init`, or select `--provider codex`."
        )
    if provider == CODEX_PROVIDER and not has_codex_auth():
        raise ProviderConfigurationError(
            "Codex authentication is unavailable. Install Codex CLI and run `codex login`."
        )

    settings = ProviderSettings(
        provider=provider,
        api_key=api_key if provider == OPENAI_PROVIDER else None,
        timeout_seconds=args.timeout,
        max_retries=args.max_retries,
    )
    return settings, profile, model


def _resolve_repository(repo_value: str) -> tuple[git.Repo, Path]:
    path = Path(repo_value).expanduser().resolve()
    try:
        repo = git.Repo(path)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError) as exc:
        raise ValueError(f"Not an accessible Git repository: {path}") from exc
    working_tree = repo.working_tree_dir
    if working_tree is None:
        raise ValueError(f"Bare Git repositories are not supported: {path}")
    return repo, Path(working_tree).resolve()


def _resolve_output_path(repo_path: Path, output: str) -> Optional[Path]:
    if output == "-":
        return None
    path = Path(output).expanduser()
    return path.resolve() if path.is_absolute() else (repo_path / path).resolve()


def _validate_current_version(version: str) -> str:
    value = version.strip()
    if not re.fullmatch(r"v?(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", value):
        raise ValueError(
            f"Invalid current version {version!r}; expected MAJOR.MINOR.PATCH with an optional v prefix."
        )
    return value


def _compare_url(repo: git.Repo, release_range: ReleaseRange) -> Optional[str]:
    if release_range.from_ref is None:
        return None
    try:
        remote = repo.remotes.origin.url.strip()
    except (AttributeError, IndexError, ValueError):
        return None

    match = re.match(
        r"(?:git@|https?://)(github\.com|gitlab\.com)(?::|/)(.+?)(?:\.git)?$", remote
    )
    if not match:
        return None
    host, repository = match.groups()
    repository = repository.removesuffix(".git")
    separator = "-/compare" if host == "gitlab.com" else "compare"
    return (
        f"https://{host}/{repository}/{separator}/"
        f"{release_range.from_sha}...{release_range.to_sha}"
    )


def _prepare_stats(stats: Mapping[str, Any]) -> Dict[str, Any]:
    date_range = stats.get("date_range")
    serialized_dates = None
    if date_range:
        serialized_dates = [
            value.isoformat() if hasattr(value, "isoformat") else str(value)
            for value in date_range
        ]
    return {
        "total_commits": stats.get("total_commits", stats.get("total")),
        "breaking_changes": stats.get("breaking_changes", 0),
        "total_files_changed": stats.get("total_files_changed", 0),
        "total_insertions": stats.get("total_insertions", 0),
        "total_deletions": stats.get("total_deletions", 0),
        "by_type": dict(stats.get("by_type", {})),
        "most_changed_components": [
            list(item) for item in stats.get("most_changed_components", [])
        ],
        "date_range": serialized_dates,
    }


def _contributor_identity_key(name: str) -> str:
    """Return a case- and whitespace-insensitive contributor identity key."""
    return "".join(name.casefold().split())


def _contributor_display_rank(name: str) -> tuple[int, int, int, str, str]:
    """Rank display-name candidates without depending on their input order."""
    words = name.split()
    alphabetic_words = [word for word in words if any(char.isalpha() for char in word)]
    title_cased = bool(alphabetic_words) and all(
        next(char for char in word if char.isalpha()).isupper()
        and any(char.islower() for char in word)
        for word in alphabetic_words
    )
    if title_cased:
        casing_quality = 3
    elif name != name.lower() and name != name.upper():
        casing_quality = 2
    elif name == name.lower():
        casing_quality = 1
    else:
        casing_quality = 0
    return (
        -int(len(words) > 1),
        -casing_quality,
        -len(words),
        name.casefold(),
        name,
    )


def canonicalize_contributors(names: Iterable[object]) -> List[str]:
    """Collapse case/spacing aliases and return readable names in stable order."""
    candidates: Dict[str, set[str]] = {}
    for value in names:
        if value is None:
            continue
        display_name = " ".join(str(value).split())
        if not display_name:
            continue
        identity = _contributor_identity_key(display_name)
        candidates.setdefault(identity, set()).add(display_name)

    preferred = [
        min(aliases, key=_contributor_display_rank) for aliases in candidates.values()
    ]
    return sorted(preferred, key=lambda name: (name.casefold(), name))


def _edit_changelog(changelog: str, args: argparse.Namespace) -> str:
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise RuntimeError("--interactive requires an interactive terminal.")
    if not Confirm.ask("Would you like to edit the changelog?", console=_console()):
        return changelog

    editor = shlex.split(os.environ.get("EDITOR", "vi"))
    if not editor:
        raise RuntimeError("EDITOR does not contain an executable command.")
    temporary_name: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".md", delete=False
        ) as temporary:
            temporary.write(changelog)
            temporary_name = temporary.name
        completed = subprocess.run(editor + [temporary_name], check=False)
        if completed.returncode != 0:
            raise RuntimeError(
                f"Editor exited with status {completed.returncode}; changelog was not saved."
            )
        edited = Path(temporary_name).read_text(encoding="utf-8")
        validate_changelog_release(edited)
        return edited
    finally:
        if temporary_name:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass


def _artifact_payload(result: GenerationResult) -> Dict[str, Any]:
    return {
        "repository": {"name": result.repo_name, "path": result.repo_path},
        "range": {"from": result.from_ref, "to": result.to_ref},
        "version": result.next_version,
        "changelog": result.changelog,
        "contributors": result.contributors or [],
        "stats": result.stats or {},
        "validation": result.validation or {},
        "provenance": {
            "entries": result.entries or [],
            "source_commit_count": (result.stats or {}).get("total_commits", 0),
            "covered_commit_count": len(
                {
                    commit_id
                    for entry in result.entries or []
                    for commit_id in entry.get("commit_ids", [])
                }
            ),
            "used_fallback": result.used_fallback,
        },
        "provider": result.provider,
        "model": result.model,
    }


def render_artifact(result: GenerationResult, output_format: str) -> str:
    if output_format == "json":
        return (
            json.dumps(
                _artifact_payload(result), ensure_ascii=False, indent=2, sort_keys=True
            )
            + "\n"
        )
    return result.changelog.rstrip() + "\n"


def _atomic_write_artifact(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.replace(temporary_name, path)
        temporary_name = None
    except OSError as exc:
        raise RuntimeError(f"Could not atomically write {path}: {exc}") from exc
    finally:
        if temporary_name:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass


def determine_ui_mode(
    requested: Optional[str],
    *,
    stdin: Optional[TextIO] = None,
    output: Optional[TextIO] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> str:
    mode = (requested or "auto").lower()
    if mode in {"plain", "textual"}:
        return mode

    input_stream = stdin or sys.stdin
    output_stream = output or sys.stderr
    environment = environ or os.environ
    if (
        not input_stream.isatty()
        or not output_stream.isatty()
        or environment.get("TERM", "").lower() == "dumb"
        or environment.get("CI", "").lower() in {"1", "true", "yes"}
    ):
        return "plain"
    try:
        import textual  # noqa: F401
    except ImportError:
        return "plain"
    return "textual"


def display_result(
    result: GenerationResult, ui_mode: str, args: argparse.Namespace
) -> str:
    if args.quiet:
        return "plain"
    if ui_mode == "textual":
        try:
            from .textual_ui import TextualDisplayData, display_textual_result

            display_textual_result(
                TextualDisplayData(
                    repo_name=result.repo_name,
                    changelog=result.changelog,
                    next_version=result.next_version,
                    stats=result.stats,
                    validation=result.validation,
                    compare_url=result.compare_url,
                    contributors=result.contributors,
                )
            )
            return "textual"
        except ImportError:
            _diagnostic(
                args,
                "Textual UI is unavailable; install `gptchangelog[tui]`. Falling back to plain output.",
                "yellow",
            )

    console = _console()
    console.print("Generated changelog", style="bold")
    console.print(Markdown(result.changelog))
    console.print(f"Next version: {result.next_version}", style="bold")
    if args.stats and result.stats:
        console.print(
            f"Commits: {result.stats.get('total_commits')} · "
            f"breaking: {result.stats.get('breaking_changes')} · "
            f"files: {result.stats.get('total_files_changed')}",
            style="cyan",
        )
    if args.quality_analysis and result.validation:
        valid = bool(result.validation.get("valid"))
        console.print(
            "Validation: passed" if valid else "Validation: failed",
            style="green" if valid else "red",
        )
        for error in result.validation.get("validation_errors", []):
            console.print(f"- {error}", style="red")
    return "plain"


def run_gptchangelog(args: argparse.Namespace) -> int:
    try:
        repo, repo_path = _resolve_repository(args.repo)
        release_range = resolve_release_range(repo, args.since, args.to)
        current_version = _validate_current_version(
            args.current_version or release_range.current_version
        )
        commits, raw_stats = get_enhanced_commit_data(
            release_range.from_sha,
            release_range.to_sha,
            repo_path=str(repo_path),
        )
    except (ValueError, git.GitError, OSError) as exc:
        _diagnostic(args, f"Git analysis failed: {exc}", "red")
        return 1

    if not commits:
        _diagnostic(args, "No commits found in the selected release range.", "yellow")
        return 0

    try:
        provider_settings, profile, model = resolve_provider_configuration(
            args, repo_path
        )
        configure_provider(provider_settings)
    except (ProviderConfigurationError, OSError) as exc:
        _diagnostic(args, f"Provider configuration failed: {exc}", "red")
        return 1

    if args.legacy:
        _diagnostic(
            args,
            "--legacy is deprecated; the validated structured generator is always used.",
            "yellow",
        )

    compare_url = None if args.no_compare_link else _compare_url(repo, release_range)
    contributors = None
    if not args.no_contributors:
        contributors = canonicalize_contributors(commit.author for commit in commits)
    extra_context: Dict[str, Any] = {
        "compare_url": compare_url,
        "contributors": contributors,
        "use_emojis": not args.no_emojis,
    }
    if args.section_order:
        extra_context["section_order"] = args.section_order

    _diagnostic(
        args,
        f"Generating {len(commits)} commits with {provider_settings.provider}/{model} ({profile}).",
        "cyan",
    )
    try:
        generation = generate_enhanced_changelog_result(
            commits,
            current_version,
            get_repository_name(repo),
            raw_stats,
            model=model,
            language=args.language,
            extra_context=extra_context,
            template_root=str(repo_path),
        )
        changelog = generation.changelog
        next_version = generation.version
        if args.interactive:
            changelog = _edit_changelog(changelog, args)
        validate_changelog_release(changelog, version=next_version)
        validation = analyze_changelog_quality(changelog)
        if not validation.get("valid"):
            raise ChangelogError(
                "; ".join(validation.get("validation_errors", []))
                or "Generated changelog validation failed."
            )
    except (ProviderError, ChangelogError, RuntimeError, ValueError, OSError) as exc:
        _diagnostic(args, f"Generation failed: {exc}", "red")
        return 1

    result = GenerationResult(
        repo_name=get_repository_name(repo),
        repo_path=str(repo_path),
        changelog=changelog,
        next_version=next_version,
        from_ref=release_range.from_ref,
        to_ref=release_range.to_ref,
        provider=provider_settings.provider,
        model=model,
        stats=_prepare_stats(raw_stats),
        validation=validation,
        compare_url=compare_url,
        contributors=contributors,
        entries=[entry.as_dict() for entry in generation.entries],
        used_fallback=generation.used_fallback,
    )
    artifact = render_artifact(result, args.format)
    output_value = args.output or ("-" if args.format == "json" else "CHANGELOG.md")
    output_path = _resolve_output_path(repo_path, output_value)

    if args.dry_run or output_path is None:
        sys.stdout.write(artifact)
        return 0

    if args.format == "json":
        if not args.check:
            try:
                _atomic_write_artifact(output_path, artifact)
            except RuntimeError as exc:
                _diagnostic(args, str(exc), "red")
                return 1
            _diagnostic(args, f"JSON artifact saved to {output_path}.", "green")
        else:
            _diagnostic(
                args,
                f"JSON artifact is valid; {output_path} was not modified.",
                "green",
            )
        return 0

    try:
        write_result = prepend_changelog_to_file(
            changelog,
            str(output_path),
            version=next_version,
            check=args.check,
            force=args.force,
        )
    except ChangelogError as exc:
        _diagnostic(args, f"Changelog was not written: {exc}", "red")
        return 1

    if args.check:
        _diagnostic(
            args, f"Changelog is valid; {output_path} was not modified.", "green"
        )
    else:
        display_result(result, determine_ui_mode(args.ui), args)
        action = "replaced" if write_result.replaced else "saved"
        _diagnostic(args, f"Changelog {action} in {output_path}.", "green")
    return 0


def _run_config_validate(args: argparse.Namespace) -> int:
    try:
        _repo, repo_path = _resolve_repository(args.repo)
        settings, profile, model = resolve_provider_configuration(args, repo_path)
        result = doctor_provider(settings)
    except (ProviderConfigurationError, ValueError, OSError) as exc:
        _console().print(f"Configuration invalid: {exc}", style="red", markup=False)
        return 1
    style = "green" if result.ok else "red"
    _console().print(
        f"Provider: {settings.provider}\nProfile: {profile}\nModel: {model}\n{result.message}",
        style=style,
        markup=False,
    )
    return 0 if result.ok else 1


def _add_provider_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", choices=[OPENAI_PROVIDER, CODEX_PROVIDER])
    parser.add_argument("--profile", choices=["balanced", "quality"])
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-retries", type=int, default=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate validated changelogs from Git history using AI"
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"gptchangelog {get_package_version()}",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    config_subparsers.add_parser("show", help="Show current configuration")
    config_subparsers.add_parser("init", help="Initialize configuration")
    validate_parser = config_subparsers.add_parser(
        "validate", help="Validate provider authentication and model resolution"
    )
    _add_provider_arguments(validate_parser)
    validate_parser.add_argument("--repo", default=".")

    generate = subparsers.add_parser("generate", help="Generate a changelog")
    generate.add_argument("--since", default=None, help="Starting commit, tag, or ref")
    generate.add_argument("--to", default="HEAD", help="Ending commit, tag, or ref")
    generate.add_argument("--repo", default=".", help="Target Git repository")
    generate.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output path, or - for stdout (default: CHANGELOG.md for Markdown, stdout for JSON)",
    )
    generate.add_argument("--format", choices=["markdown", "json"], default="markdown")
    generate.add_argument("--current-version", default=None)
    generate.add_argument(
        "--dry-run", action="store_true", help="Print without writing"
    )
    generate.add_argument(
        "--check", action="store_true", help="Validate without writing"
    )
    generate.add_argument(
        "--force", action="store_true", help="Replace an existing version"
    )
    generate.add_argument("--quiet", action="store_true", help="Suppress diagnostics")
    generate.add_argument("-i", "--interactive", action="store_true")
    _add_provider_arguments(generate)
    generate.add_argument("--language", choices=["en", "fr", "es"], default="en")
    generate.add_argument("--stats", action="store_true")
    generate.add_argument("--quality-analysis", action="store_true")
    generate.add_argument("--no-compare-link", action="store_true")
    generate.add_argument("--no-contributors", action="store_true")
    generate.add_argument("--section-order", default=None)
    generate.add_argument("--no-emojis", action="store_true")
    generate.add_argument("--ui", choices=["auto", "textual", "plain"], default="auto")
    generate.add_argument("--legacy", action="store_true", help=argparse.SUPPRESS)
    return parser


def _normalized_argv(argv: Optional[Sequence[str]]) -> List[str]:
    values = list(sys.argv[1:] if argv is None else argv)
    commands = {"config", "generate"}
    if not values:
        return ["generate"]
    if values[0] not in commands and values[0] not in {
        "-h",
        "--help",
        "-v",
        "--version",
    }:
        return ["generate", *values]
    return values


def app(argv: Optional[Sequence[str]] = None) -> int:
    debug = os.environ.get("GPTCHANGELOG_DEBUG", "").lower() in {"1", "true", "yes"}
    logging.basicConfig(level=logging.DEBUG if debug else logging.WARNING)
    parser = build_parser()
    args = parser.parse_args(_normalized_argv(argv))
    if args.command == "config":
        if args.config_command == "show":
            show_config()
            return 0
        if args.config_command == "init":
            init_config()
            return 0
        if args.config_command == "validate":
            return _run_config_validate(args)
        config_parser = next(
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ).choices["config"]
        config_parser.print_help()
        return 0
    if args.command == "generate":
        return run_gptchangelog(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(app())
