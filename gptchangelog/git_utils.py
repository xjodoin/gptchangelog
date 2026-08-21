import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, cast

import git

CommitStats = Dict[str, Any]
_SEMVER_TAG_RE = re.compile(r"v?(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)")
_BREAKING_FOOTER_RE = re.compile(r"(?m)^\s*BREAKING(?: |-)?CHANGE:")
_NEGATED_BREAKING_PATTERNS = (
    re.compile(
        r"\bnon[-\s]+breaking(?:[-\s]+api)?(?:[-\s]+change)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bnot\s+(?:a\s+)?breaking(?:\s+api)?\s+change\b",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class ReleaseRange:
    """A validated release range.

    ``from_ref`` is ``None`` for an initial release.  In that case callers must
    walk ``to_ref`` directly instead of constructing ``from_ref..to_ref``;
    doing so includes the repository's root commit.
    """

    from_ref: Optional[str]
    to_ref: str
    from_sha: Optional[str]
    to_sha: str
    current_version: str


def validate_ref(repo: git.Repo, ref: str) -> str:
    """Validate and resolve a commit-ish, raising GitCommandError on failure."""
    if not ref or not ref.strip():
        raise ValueError("Git reference must not be empty")
    return repo.git.rev_parse("--verify", f"{ref}^{{commit}}")


def has_breaking_change_footer(message: str) -> bool:
    """Return whether a message contains an actual Conventional Commits footer."""
    return bool(_BREAKING_FOOTER_RE.search(message))


def remove_negated_breaking_phrases(message: str) -> str:
    """Remove compatibility phrases that must not trigger breaking heuristics."""
    result = message
    for pattern in _NEGATED_BREAKING_PATTERNS:
        result = pattern.sub("", result)
    return result


def _require_ancestor(
    repo: git.Repo, from_sha: str, to_sha: str, from_label: str, to_label: str
) -> None:
    """Reject ranges whose baseline is not in the target's history."""
    try:
        repo.git.merge_base("--is-ancestor", from_sha, to_sha)
    except git.GitCommandError as exc:
        if exc.status == 1:
            raise ValueError(
                f"Invalid release range: {from_label!r} is not an ancestor of "
                f"{to_label!r}. Choose a baseline reachable from the target."
            ) from exc
        raise


def iter_release_commits(repo: git.Repo, from_ref: Optional[str], to_ref: str) -> Any:
    """Iterate a validated release range, including root for initial releases."""
    to_sha = validate_ref(repo, to_ref)
    if from_ref is None:
        return repo.iter_commits(to_sha, no_merges=True)
    from_sha = validate_ref(repo, from_ref)
    _require_ancestor(repo, from_sha, to_sha, from_ref, to_ref)
    return repo.iter_commits(f"{from_sha}..{to_sha}", no_merges=True)


def _version_from_tag(tag: Optional[str]) -> str:
    if not tag:
        return "0.0.0"
    match = _SEMVER_TAG_RE.fullmatch(tag.strip())
    return tag if match else "0.0.0"


def _commit_message_as_text(message: str | bytes) -> str:
    if isinstance(message, bytes):
        return message.decode("utf-8", errors="replace")
    return message


def get_repository_name(repo: git.Repo) -> str:
    """Extract the repository name from a git repository."""
    try:
        # Try to get the name from the remote URL
        remote_url = repo.remotes.origin.url
        # Extract repo name from URL
        name = os.path.basename(remote_url)
        # Remove .git extension if present
        if name.endswith(".git"):
            name = name[:-4]
        return name
    except (AttributeError, IndexError):
        # Fallback to directory name
        return os.path.basename(os.path.abspath(repo.working_dir))


def get_latest_tag(repo: git.Repo, to_ref: str = "HEAD") -> Optional[str]:
    """Return the nearest semantic-version tag reachable from ``to_ref``.

    Non-version deployment/build tags, tags on unrelated branches, and tags
    newer than ``to_ref`` are ignored. Invalid target references propagate.
    """
    validate_ref(repo, to_ref)
    reachable = repo.git.tag("--merged", to_ref).splitlines()
    semantic_tags = [tag for tag in reachable if _SEMVER_TAG_RE.fullmatch(tag)]
    if not semantic_tags:
        return None

    match_arguments: List[str] = []
    for tag in semantic_tags:
        match_arguments.extend(["--match", tag])
    try:
        return repo.git.describe(
            "--tags", "--abbrev=0", *match_arguments, to_ref
        ).strip()
    except git.GitCommandError:
        # At least one matching tag is reachable, so this is not the normal
        # no-tag case and must not be disguised as an initial release.
        raise


def resolve_commit_range(
    repo: git.Repo, since: Optional[str] = None, to_ref: str = "HEAD"
) -> ReleaseRange:
    """Resolve refs and the current semantic version for a release."""
    to_sha = validate_ref(repo, to_ref)
    from_ref = since if since is not None else get_latest_tag(repo, to_ref)
    from_sha = None
    if from_ref is not None:
        from_sha = validate_ref(repo, from_ref)
        _require_ancestor(repo, from_sha, to_sha, from_ref, to_ref)
    return ReleaseRange(
        from_ref=from_ref,
        to_ref=to_ref,
        from_sha=from_sha,
        to_sha=to_sha,
        current_version=_version_from_tag(from_ref),
    )


def resolve_release_range(
    repo: git.Repo, since: Optional[str] = None, to_ref: str = "HEAD"
) -> ReleaseRange:
    """Backward-compatible release-oriented name for ``resolve_commit_range``."""
    return resolve_commit_range(repo, since, to_ref)


def parse_conventional_commit(message: str) -> Tuple[Optional[str], str, bool]:
    """
    Parse a conventional commit message.

    Returns a tuple of (type, message, is_breaking_change)
    """
    # Regular expression for conventional commit format
    pattern = (
        r"^(?P<type>\w+)(\((?P<scope>[\w-]+)\))?(?P<breaking>!)?: (?P<message>.+)$"
    )

    # Check for breaking change in footer
    has_breaking_footer = has_breaking_change_footer(message)

    # Parse the first line for conventional commit format
    first_line = message.split("\n", 1)[0].strip()
    match = re.match(pattern, first_line)

    if match:
        commit_type = match.group("type")
        breaking_marker = match.group("breaking")
        content = match.group("message")
        is_breaking = bool(breaking_marker) or has_breaking_footer
        return commit_type, content, is_breaking

    # Not a conventional commit
    return None, message.strip(), has_breaking_footer


def analyze_commit_message(message: str) -> Tuple[str, str, bool]:
    """
    Analyze a commit message to determine its type, even if it's not in
    conventional commit format.

    Returns a tuple of (inferred_type, cleaned_message, is_breaking_change)
    """
    commit_type, content, is_breaking = parse_conventional_commit(message)

    # If it's already a conventional commit, just return
    if commit_type:
        return commit_type, content, is_breaking

    # Try to infer the type from the content
    content_lower = content.lower()

    # Check for various patterns to infer the type
    if re.search(
        r"\badd(ed|ing)?\b|\bimplemented|implement(ing)?\b|\bnew\b|\bfeature\b",
        content_lower,
    ):
        inferred_type = "feat"
    elif re.search(
        r"\bfix(ed|ing)?\b|\bbugs?\b|\bissues?\b|\bsolve[ds]?\b|\bresolve[ds]?\b",
        content_lower,
    ):
        inferred_type = "fix"
    elif re.search(
        r"\brefactor\b|\bclean\b|\brestructur\b|\bimprove[ds]?\b", content_lower
    ):
        inferred_type = "refactor"
    elif re.search(r"\bdocument\b|\bdoc\b|\bexample\b|\breadme\b", content_lower):
        inferred_type = "docs"
    elif re.search(r"\btest\b|\bspec\b|\bassert\b", content_lower):
        inferred_type = "test"
    elif re.search(r"\bbuild\b|\bpackage\b|\bcompile\b|\brelease\b", content_lower):
        inferred_type = "build"
    elif re.search(r"\bdepend\b|\bupgrade\b|\bupdate\b|\bbump\b", content_lower):
        inferred_type = "chore"
    else:
        inferred_type = "chore"  # Default if we can't determine

    # Check for breaking changes in text
    if not is_breaking:
        breaking_content = remove_negated_breaking_phrases(content_lower)
        is_breaking = bool(
            re.search(
                r"\bbreak(ing)?\b|\bbackward.{1,10}incompatible\b",
                breaking_content,
            )
        )

    return inferred_type, content, is_breaking


def get_commit_messages_since(
    latest_commit: Optional[str],
    to_commit: str = "HEAD",
    repo_path: str = ".",
    min_length: int = 10,
) -> Tuple[str, str]:
    """
    Get commit messages between two git references.

    Args:
        latest_commit: The starting reference (commit hash, tag, etc.)
        to_commit: The ending reference (defaults to HEAD)
        repo_path: Path to the git repository
        min_length: Minimum length of commit messages to include

    Returns:
        A tuple of (from_ref, commit_messages_text)
    """
    repo = git.Repo(repo_path)
    commit_data = []

    # Get the commits in the range
    for commit in iter_release_commits(repo, latest_commit, to_commit):
        message = _commit_message_as_text(commit.message).strip()

        if len(message) >= min_length:
            # Parse and analyze the commit message
            commit_type, content, is_breaking = analyze_commit_message(message)

            # Format with conventional commit style
            prefix = f"{commit_type}{'!' if is_breaking else ''}: "

            # Add issue/PR references if present
            issue_match = re.search(r"(#\d+)", message)
            issue_ref = f" ({issue_match.group(1)})" if issue_match else ""

            # Build formatted message
            formatted_message = f"{prefix}{content}{issue_ref}"

            commit_data.append(formatted_message)

    # Join the commit messages with newlines
    return latest_commit or "", "\n".join(commit_data)


def get_commit_stats(
    from_ref: Optional[str], to_ref: str = "HEAD", repo_path: str = "."
) -> CommitStats:
    """
    Get statistics about commits between two git references.

    Args:
        from_ref: The starting reference (commit hash, tag, etc.)
        to_ref: The ending reference (defaults to HEAD)
        repo_path: Path to the git repository

    Returns:
        A dictionary with statistics about the commits
    """
    repo = git.Repo(repo_path)
    by_type: Dict[str, int] = {}
    by_author: Dict[str, int] = {}
    files_changed: Set[str] = set()
    stats: CommitStats = {
        "total": 0,
        "by_type": by_type,
        "by_author": by_author,
        "breaking_changes": 0,
        "files_changed": files_changed,
    }

    # Get the commits in the range
    for commit in iter_release_commits(repo, from_ref, to_ref):
        message = _commit_message_as_text(commit.message).strip()
        commit_type, _, is_breaking = analyze_commit_message(message)

        # Update stats
        stats["total"] = cast(int, stats["total"]) + 1
        by_type[commit_type] = by_type.get(commit_type, 0) + 1
        author_name = commit.author.name or "Unknown"
        by_author[author_name] = by_author.get(author_name, 0) + 1

        if is_breaking:
            stats["breaking_changes"] = cast(int, stats["breaking_changes"]) + 1

        # Get files changed
        for file in commit.stats.files:
            files_changed.add(os.fspath(file))

    stats["files_changed"] = list(files_changed)
    return stats
