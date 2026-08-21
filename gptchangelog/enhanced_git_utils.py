"""Enhanced Git utilities for better commit analysis and changelog generation."""

import logging
import os
import re
from collections import defaultdict, namedtuple
from datetime import datetime
from typing import Any, DefaultDict, Dict, List, Optional, Set, Tuple

import git

from .git_utils import (
    has_breaking_change_footer,
    iter_release_commits,
)

logger = logging.getLogger(__name__)

CommitInfo = namedtuple(
    "CommitInfo",
    [
        "hash",
        "message",
        "author",
        "date",
        "files_changed",
        "insertions",
        "deletions",
        "commit_type",
        "scope",
        "is_breaking",
        "issue_refs",
        "components",
    ],
)


class EnhancedCommitAnalyzer:
    """Enhanced commit analyzer with better categorization and grouping."""

    def __init__(self, repo_path: str = "."):
        self.repo = git.Repo(repo_path)
        self.repo_name = self._get_repository_name()
        self.short_commit_length_threshold = 6
        self.generic_commit_keywords = {
            "wip",
            "tmp",
            "temp",
            "minor",
            "misc",
            "change",
            "changes",
            "fix",
            "fixes",
            "cleanup",
            "clean",
            "typo",
            "update",
            "updates",
            "bump",
            "sync",
            "chore",
            "todo",
            "tests",
            "test",
        }
        self.generic_commit_patterns = [
            r"^(wip|draft|temp|tmp)\b",
            r"^(minor|small)\s+(fix|changes?)\b",
            r"^(quick|just)\s+(fix|change)",
            r"^bump(ing)?( deps?)?$",
            r"^sync(ing)?( submodules?)?$",
        ]
        self.skipped_commits: List[str] = []

        # Component patterns for better categorization
        self.component_patterns = {
            "frontend": r"(?i)(ui|frontend|web|client|css|html|js|react|vue|angular)",
            "backend": r"(?i)(api|server|backend|service|endpoint|controller)",
            "database": r"(?i)(db|database|migration|schema|sql|mongodb|postgres)",
            "auth": r"(?i)(auth|login|security|oauth|jwt|session)",
            "config": r"(?i)(config|settings|env|environment|setup)",
            "docs": r"(?i)(doc|readme|guide|tutorial|example)",
            "test": r"(?i)(test|spec|unittest|integration)",
            "build": r"(?i)(build|compile|webpack|grunt|gulp|ci|deploy)",
            "deps": r"(?i)(depend|package|requirements|pip|npm|yarn)",
        }

    def _get_repository_name(self) -> str:
        """Extract the repository name from a git repository."""
        try:
            remote_url = self.repo.remotes.origin.url
            name = os.path.basename(remote_url)
            if name.endswith(".git"):
                name = name[:-4]
            return name
        except (AttributeError, IndexError):
            return os.path.basename(os.path.abspath(self.repo.working_dir))

    def _detect_components(self, files_changed: List[str], message: str) -> Set[str]:
        """Detect which components are affected by changes."""
        components = set()

        # Analyze file paths
        for file_path in files_changed:
            file_lower = file_path.lower()
            for component, pattern in self.component_patterns.items():
                if re.search(pattern, file_path) or re.search(pattern, file_lower):
                    components.add(component)

        # Analyze commit message
        message_lower = message.lower()
        for component, pattern in self.component_patterns.items():
            if re.search(pattern, message_lower):
                components.add(component)

        return components

    def _detect_breaking_changes(self, message: str, files_changed: List[str]) -> bool:
        """Detect only explicit Conventional Commits breaking declarations.

        File names and natural-language descriptions are deliberately excluded:
        removal work, an API path, or an unreleased migration rewrite does not
        establish a public compatibility break.  Release authors must use an
        exclamation marker or a proper breaking-change footer to request a major
        version bump.
        """
        del files_changed  # Kept in the public method signature for compatibility.
        normalized = self._strip_ci_prefix(message.lstrip())

        if re.match(r"^[A-Za-z][\w-]*(?:\([^)]+\))?!\s*:", normalized):
            return True

        # Conventional Commits footers follow a blank line.  Requiring that
        # separator avoids treating a subject such as "breaking change: docs"
        # as a footer while accepting BREAKING CHANGE and BREAKING-CHANGE.
        footer_blocks = re.split(r"\n[ \t]*\n", normalized, maxsplit=1)
        return len(footer_blocks) == 2 and has_breaking_change_footer(footer_blocks[1])

    @staticmethod
    def _strip_ci_prefix(message: str) -> str:
        """Remove recognized CI control prefixes before parsing a subject."""
        prefix = re.compile(
            r"^(?:(?:skip[-_](?:tests?|ci)|ci[-_]skip|no[-_](?:tests?))"
            r"\s*(?:[-:|]\s*)|\[(?:skip ci|ci skip|skip tests?)\]\s*)",
            re.IGNORECASE,
        )
        normalized = message
        while True:
            stripped = prefix.sub("", normalized, count=1)
            if stripped == normalized:
                return normalized
            normalized = stripped.lstrip()

    def _extract_issue_references(self, message: str) -> List[str]:
        """Extract issue/PR references from commit message."""
        patterns = [
            r"#(\d+)",
            r"(?:fix|fixes|close|closes|resolve|resolves)\s+#(\d+)",
            r"(?:PR|pr)\s+#?(\d+)",
            r"(?:issue|Issue)\s+#?(\d+)",
        ]

        refs = []
        for pattern in patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            refs.extend([f"#{match}" for match in matches])

        return list(dict.fromkeys(refs))  # Deduplicate while preserving order

    def _parse_conventional_commit(
        self, message: str
    ) -> Tuple[Optional[str], Optional[str], str, bool]:
        """Enhanced conventional commit parsing."""
        # Pattern for conventional commit format
        pattern = r"^(?P<type>[A-Za-z][\w-]*)(\((?P<scope>[^)]+)\))?(?P<breaking>!)?\s*:\s*(?P<message>.+)$"

        normalized = self._strip_ci_prefix(message.strip())
        first_line = normalized.split("\n", 1)[0].strip()
        match = re.match(pattern, first_line)

        if match:
            commit_type = match.group("type").lower()
            scope = match.group("scope")
            breaking_marker = match.group("breaking")
            content = match.group("message")
            is_breaking = bool(breaking_marker) or self._detect_breaking_changes(
                normalized, []
            )
            return commit_type, scope, content, is_breaking

        return None, None, normalized, False

    @staticmethod
    def _is_documentation_path(file_path: str) -> bool:
        normalized = file_path.lower().replace("\\", "/")
        parts = normalized.split("/")
        return (
            normalized.endswith((".md", ".mdx", ".rst", ".adoc"))
            or any(part in {"doc", "docs", "documentation"} for part in parts)
            or parts[-1].startswith("readme")
        )

    @staticmethod
    def _is_test_path(file_path: str) -> bool:
        normalized = file_path.lower().replace("\\", "/")
        filename = normalized.rsplit("/", 1)[-1]
        parts = normalized.split("/")
        return (
            any(part in {"test", "tests", "spec", "specs"} for part in parts)
            or filename.startswith("test_")
            or filename.endswith(
                ("_test.py", ".test.js", ".test.ts", ".spec.js", ".spec.ts")
            )
        )

    def _infer_commit_type(self, message: str, files_changed: List[str]) -> str:
        """Infer commit type from message and file changes."""
        subject = self._strip_ci_prefix(message).split("\n", 1)[0].strip()
        message_lower = subject.lower()

        # Subject-led documentation and test work must win over generic verbs
        # such as "add".  The patterns intentionally require the documented or
        # tested artifact to be the subject's direct object, so a real feature
        # such as "Support cancellations and update documentation" stays a
        # feature.
        if re.search(
            r"^(?:docs?|documentation|readme)\b|"
            r"^(?:add|create|write|update|improve|expand|revise|clarify|harden)\b"
            r"(?!.*\band\b.*\b(?:docs?|documentation|readme|guide|specification)\b)"
            r".*\b(?:docs?|documentation|readme|guide|specification)\b\s*$|"
            r"^document\b",
            message_lower,
        ):
            return "docs"

        if re.search(
            r"^(?:tests?|testing)\b|"
            r"^(?:add|create|write|update|improve|expand)\s+"
            r"(?:(?:new|more|additional|comprehensive|unit|integration|regression|legacy)\s+)*"
            r"(?:tests?|testing|coverage)\b",
            message_lower,
        ):
            return "test"

        if files_changed and all(
            self._is_documentation_path(path) for path in files_changed
        ):
            return "docs"

        if files_changed and all(self._is_test_path(path) for path in files_changed):
            return "test"

        # Fix indicators
        if re.search(r"\b(fix|resolve|correct|patch|bug)\b", message_lower):
            return "fix"

        # Performance indicators
        if re.search(r"\b(perf|performance|optimize|speed)\b", message_lower):
            return "perf"

        # Refactor indicators
        if re.search(r"\b(refactor|restructure|reorganize|clean)\b", message_lower):
            return "refactor"

        # Build indicators
        if re.search(r"\b(build|compile|bundle|deploy)\b", message_lower):
            return "build"

        # Style indicators
        if re.search(r"\b(style|format|lint|prettier)\b", message_lower):
            return "style"

        # Feature indicators
        if re.search(
            r"\b(add|implement|create|introduce|new|enhance|support|enable)\b",
            message_lower,
        ):
            return "feat"

        # Documentation indicators
        if re.search(r"\b(docs?|documentation|readme|guide|example)\b", message_lower):
            return "docs"

        # Test indicators
        if re.search(r"\b(test|spec|coverage)\b", message_lower):
            return "test"

        if files_changed:
            if any(
                f in ["package.json", "requirements.txt", "Pipfile", "yarn.lock"]
                for f in files_changed
            ):
                return "chore"

        return "chore"  # Default fallback

    def analyze_commit(self, commit) -> CommitInfo:
        """Analyze a single commit and extract detailed information."""
        message = self._commit_message_as_text(commit.message).strip()
        files_changed = list(commit.stats.files.keys())

        # Parse conventional commit format
        commit_type, scope, clean_message, is_breaking_conv = (
            self._parse_conventional_commit(message)
        )

        # If not conventional, infer type
        if not commit_type:
            commit_type = self._infer_commit_type(message, files_changed)
            clean_message = message

        # Enhanced breaking change detection
        is_breaking = is_breaking_conv or self._detect_breaking_changes(
            message, files_changed
        )

        # Extract issue references
        issue_refs = self._extract_issue_references(message)

        # Detect components
        components = self._detect_components(files_changed, message)

        return CommitInfo(
            hash=commit.hexsha[:8],
            message=clean_message,
            author=commit.author.name,
            date=commit.committed_datetime,
            files_changed=files_changed,
            insertions=commit.stats.total["insertions"],
            deletions=commit.stats.total["deletions"],
            commit_type=commit_type,
            scope=scope,
            is_breaking=is_breaking,
            issue_refs=issue_refs,
            components=components,
        )

    def _is_noise_commit(self, message: str) -> bool:
        """Return True if a commit message is too short or generic to be useful."""
        if not message:
            return True

        first_line = message.strip().split("\n", 1)[0]
        if not first_line:
            return True

        normalized = re.sub(
            r"\s+", " ", self._strip_ci_prefix(first_line.strip()).lower()
        )

        # Preserve explicit conventional commit prefixes regardless of length
        if re.match(r"^\w+(?:\([^)]+\))?!?:", normalized):
            return False

        tokens = [re.sub(r"[^a-z0-9]+", "", token) for token in normalized.split()]
        tokens = [tok for tok in tokens if tok]

        if not tokens:
            return True

        if len(tokens) <= 2 and all(
            tok in self.generic_commit_keywords for tok in tokens
        ):
            return True

        for pattern in self.generic_commit_patterns:
            if re.match(pattern, normalized):
                return True

        if len(normalized) <= self.short_commit_length_threshold and len(tokens) == 1:
            return True

        return False

    @staticmethod
    def _commit_message_as_text(message: str | bytes) -> str:
        if isinstance(message, bytes):
            return message.decode("utf-8", errors="replace")
        return message

    def get_enhanced_commits(
        self, from_ref: Optional[str], to_ref: str = "HEAD"
    ) -> List[CommitInfo]:
        """Get detailed commit information for the specified range."""
        commits = []
        self.skipped_commits = []

        for commit in iter_release_commits(self.repo, from_ref, to_ref):
            message = self._commit_message_as_text(commit.message)
            if not message.strip():
                continue

            if self._is_noise_commit(message):
                self.skipped_commits.append(commit.hexsha[:8])
                continue

            commit_info = self.analyze_commit(commit)
            commits.append(commit_info)

        if self.skipped_commits:
            preview = ", ".join(self.skipped_commits[:5])
            if len(self.skipped_commits) > 5:
                preview += ", …"
            logger.info(
                "Skipped %d short or generic commits before analysis: %s",
                len(self.skipped_commits),
                preview,
            )

        return commits

    def group_related_commits(
        self, commits: List[CommitInfo]
    ) -> Dict[str, List[CommitInfo]]:
        """Group related commits by feature/component."""
        groups = defaultdict(list)

        for commit in commits:
            # Create a key based on components and type
            components_str = (
                "_".join(sorted(commit.components)) if commit.components else "general"
            )
            group_key = f"{commit.commit_type}_{components_str}"

            # Special grouping for features and fixes
            if commit.commit_type in ["feat", "fix"]:
                # Try to group by similar message patterns
                words = commit.message.lower().split()[:3]  # First 3 words
                semantic_key = f"{commit.commit_type}_{'_'.join(words)}"
                groups[semantic_key].append(commit)
            else:
                groups[group_key].append(commit)

        return dict(groups)

    def get_commit_statistics(self, commits: List[CommitInfo]) -> Dict[str, Any]:
        """Generate comprehensive statistics about the commits."""
        by_type: Dict[str, int] = defaultdict(int)
        by_author: Dict[str, int] = defaultdict(int)
        by_component: Dict[str, int] = defaultdict(int)
        total_files_changed: Set[str] = set()
        breaking_changes: int = 0
        total_insertions: int = 0
        total_deletions: int = 0

        if not commits:
            return {
                "total_commits": 0,
                "by_type": dict(by_type),
                "by_author": dict(by_author),
                "by_component": dict(by_component),
                "breaking_changes": 0,
                "total_files_changed": 0,
                "total_insertions": 0,
                "total_deletions": 0,
                "date_range": None,
                "most_active_authors": [],
                "most_changed_components": [],
            }

        # Calculate statistics
        for commit in commits:
            by_type[commit.commit_type] += 1
            by_author[commit.author] += 1
            total_insertions += commit.insertions
            total_deletions += commit.deletions
            total_files_changed.update(commit.files_changed)

            if commit.is_breaking:
                breaking_changes += 1

            for component in commit.components:
                by_component[component] += 1

        # Date range
        dates = [commit.date for commit in commits]
        date_range = (min(dates), max(dates)) if dates else None

        # Most active authors
        most_active_authors = sorted(
            by_author.items(), key=lambda x: x[1], reverse=True
        )[:5]

        # Most changed components
        most_changed_components = sorted(
            by_component.items(), key=lambda x: x[1], reverse=True
        )[:5]

        return {
            "total_commits": len(commits),
            "by_type": dict(by_type),
            "by_author": dict(by_author),
            "by_component": dict(by_component),
            "breaking_changes": breaking_changes,
            "total_files_changed": len(total_files_changed),
            "total_insertions": total_insertions,
            "total_deletions": total_deletions,
            "date_range": date_range,
            "most_active_authors": most_active_authors,
            "most_changed_components": most_changed_components,
        }


def get_enhanced_commit_data(
    from_ref: Optional[str], to_ref: str = "HEAD", repo_path: str = "."
) -> Tuple[List[CommitInfo], Dict[str, Any]]:
    """Get enhanced commit data and statistics."""
    analyzer = EnhancedCommitAnalyzer(repo_path)
    commits = analyzer.get_enhanced_commits(from_ref, to_ref)
    stats = analyzer.get_commit_statistics(commits)

    return commits, stats


def format_commits_for_ai(commits: List[CommitInfo], include_stats: bool = True) -> str:
    """Format commits for AI processing with enhanced context."""
    if not commits:
        return "No commits found."

    output = []

    # Group commits by type for better organization
    by_type = defaultdict(list)
    for commit in commits:
        by_type[commit.commit_type].append(commit)

    # Format commits by type
    for commit_type, type_commits in sorted(by_type.items()):
        output.append(f"\n--- {commit_type.upper()} COMMITS ---")

        for commit in type_commits:
            # Build commit line
            line_parts = [f"{commit_type}"]

            if commit.scope:
                line_parts[0] += f"({commit.scope})"

            if commit.is_breaking:
                line_parts[0] += "!"

            line_parts.append(f": {commit.message}")

            if commit.issue_refs:
                line_parts.append(f" ({', '.join(commit.issue_refs)})")

            if commit.components:
                line_parts.append(
                    f" [Components: {', '.join(sorted(commit.components))}]"
                )

            output.append("".join(line_parts))

    # Add statistics if requested
    if include_stats:
        component_counts: DefaultDict[str, int] = defaultdict(int)
        changed_files: Set[str] = set()
        insertions = 0
        deletions = 0
        breaking = 0
        for commit in commits:
            breaking += int(commit.is_breaking)
            changed_files.update(commit.files_changed)
            insertions += commit.insertions
            deletions += commit.deletions
            for component in commit.components:
                component_counts[component] += 1
        most_changed_components = sorted(
            component_counts.items(), key=lambda item: item[1], reverse=True
        )[:5]

        output.append("\n--- COMMIT STATISTICS ---")
        output.append(f"Total commits: {len(commits)}")
        output.append(f"Breaking changes: {breaking}")
        output.append(f"Files changed: {len(changed_files)}")
        output.append(f"Code changes: +{insertions} -{deletions}")

        if most_changed_components:
            components = [
                f"{component}({count})" for component, count in most_changed_components
            ]
            output.append(f"Main components: {', '.join(components)}")

    return "\n".join(output)
