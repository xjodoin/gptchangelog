"""Compatibility API backed by the one-call structured generator."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .enhanced_git_utils import CommitInfo
from .enhanced_openai_utils import (
    DEFAULT_MODEL,
    EnhancedChangelogGenerator,
    determine_version_impact,
    increment_semver,
)
from .git_utils import analyze_commit_message


def process_commit_messages(
    raw_commit_messages: str,
    model: str = DEFAULT_MODEL,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Normalize commit whitespace without spending a separate model call."""
    del model, context
    return "\n".join(
        re.sub(r"\s+", " ", line).strip()
        for line in raw_commit_messages.splitlines()
        if line.strip()
    )


def _legacy_commits(commit_messages: str) -> List[CommitInfo]:
    commits: List[CommitInfo] = []
    for index, line in enumerate(commit_messages.splitlines(), start=1):
        message = line.strip()
        if not message or message.startswith("---"):
            continue
        commit_type, content, breaking = analyze_commit_message(message)
        _parsed_type, scope, _parsed_breaking = _legacy_conventional_fields(message)
        commits.append(
            CommitInfo(
                hash=f"legacy-{index:04d}",
                message=content,
                author="Unknown",
                date=datetime.now(),
                files_changed=[],
                insertions=0,
                deletions=0,
                commit_type=commit_type,
                scope=scope,
                is_breaking=breaking,
                issue_refs=list(dict.fromkeys(re.findall(r"#\d+", message))),
                components=set(),
            )
        )
    return commits


def _legacy_conventional_fields(
    message: str,
) -> Tuple[Optional[str], Optional[str], bool]:
    match = re.match(r"^(\w+)(?:\(([^)]+)\))?(!)?:", message)
    if not match:
        return None, None, False
    return match.group(1), match.group(2), bool(match.group(3))


def determine_next_version(
    current_version: str,
    commit_messages: str,
    model: str = DEFAULT_MODEL,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Determine SemVer locally; a model can never return a regressed version."""
    del model, context
    commits = _legacy_commits(commit_messages)
    if not commits:
        return current_version
    return increment_semver(current_version, determine_version_impact(commits))


def _legacy_stats(commits: List[CommitInfo]) -> Dict[str, Any]:
    by_type: Dict[str, int] = {}
    for commit in commits:
        by_type[commit.commit_type] = by_type.get(commit.commit_type, 0) + 1
    dates = [commit.date for commit in commits]
    return {
        "by_type": by_type,
        "breaking_changes": sum(int(commit.is_breaking) for commit in commits),
        "total_files_changed": 0,
        "total_insertions": 0,
        "total_deletions": 0,
        "most_changed_components": [],
        "date_range": (min(dates), max(dates)) if dates else None,
    }


def generate_changelog(
    commit_messages: str,
    next_version: str,
    model: str = DEFAULT_MODEL,
    context: Optional[Dict[str, Any]] = None,
    language: Optional[str] = "en",
    template_root: Optional[str] = None,
) -> str:
    """Generate localized Markdown through one structured model request."""
    del template_root
    commits = _legacy_commits(commit_messages)
    values = dict(context or {})
    values.setdefault("current_date", datetime.today().strftime("%Y-%m-%d"))
    generator = EnhancedChangelogGenerator(model, language or "en")
    return generator.generate_enhanced_changelog(commits, next_version, values)


def generate_changelog_and_next_version(
    raw_commit_messages: str,
    current_version: str,
    model: str = DEFAULT_MODEL,
    context: Optional[Dict[str, Any]] = None,
    language: Optional[str] = "en",
    template_root: Optional[str] = None,
) -> Tuple[str, str]:
    """Generate a changelog and deterministic version with one model call."""
    processed = process_commit_messages(raw_commit_messages)
    next_version = determine_next_version(current_version, processed)
    changelog = generate_changelog(
        processed,
        next_version,
        model,
        context,
        language=language,
        template_root=template_root,
    )
    return changelog, next_version
