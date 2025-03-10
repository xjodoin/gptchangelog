import git
import os
import re
from typing import Tuple, List, Optional


def get_repository_name(repo: git.Repo) -> str:
    """Extract the repository name from a git repository."""
    try:
        # Try to get the name from the remote URL
        remote_url = repo.remotes.origin.url
        # Extract repo name from URL
        name = os.path.basename(remote_url)
        # Remove .git extension if present
        if name.endswith('.git'):
            name = name[:-4]
        return name
    except (AttributeError, IndexError):
        # Fallback to directory name
        return os.path.basename(os.path.abspath(repo.working_dir))


def get_latest_tag(repo: git.Repo) -> str:
    """Get the latest tag from the repository."""
    try:
        # Try to get the most recent tag that points to the current branch
        tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
        if tags:
            return tags[-1].name
        # Fallback to describe command which finds the most appropriate tag
        return repo.git.describe("--tags", "--abbrev=0")
    except git.GitCommandError:
        # If no tags exist, use the initial commit
        return repo.git.rev_list("--max-parents=0", "HEAD")


def parse_conventional_commit(message: str) -> Tuple[Optional[str], str, bool]:
    """
    Parse a conventional commit message.

    Returns a tuple of (type, message, is_breaking_change)
    """
    # Regular expression for conventional commit format
    pattern = r'^(?P<type>\w+)(\((?P<scope>[\w-]+)\))?(?P<breaking>!)?: (?P<message>.+)$'

    # Check for breaking change in footer
    has_breaking_footer = "BREAKING CHANGE:" in message

    # Parse the first line for conventional commit format
    first_line = message.split('\n', 1)[0].strip()
    match = re.match(pattern, first_line)

    if match:
        commit_type = match.group('type')
        breaking_marker = match.group('breaking')
        content = match.group('message')
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
    if re.search(r'\badd(ed|ing)?\b|\bimplemented|implement(ing)?\b|\bnew\b|\bfeature\b', content_lower):
        inferred_type = 'feat'
    elif re.search(r'\bfix(ed|ing)?\b|\bbugs?\b|\bissues?\b|\bsolve[ds]?\b|\bresolve[ds]?\b', content_lower):
        inferred_type = 'fix'
    elif re.search(r'\brefactor\b|\bclean\b|\brestructur\b|\bimprove[ds]?\b', content_lower):
        inferred_type = 'refactor'
    elif re.search(r'\bdocument\b|\bdoc\b|\bexample\b|\breadme\b', content_lower):
        inferred_type = 'docs'
    elif re.search(r'\btest\b|\bspec\b|\bassert\b', content_lower):
        inferred_type = 'test'
    elif re.search(r'\bbuild\b|\bpackage\b|\bcompile\b|\brelease\b', content_lower):
        inferred_type = 'build'
    elif re.search(r'\bdepend\b|\bupgrade\b|\bupdate\b|\bbump\b', content_lower):
        inferred_type = 'chore'
    else:
        inferred_type = 'chore'  # Default if we can't determine

    # Check for breaking changes in text
    if not is_breaking:
        is_breaking = bool(re.search(r'\bbreak(ing)?\b|\bbackward.{1,10}incompatible\b', content_lower))

    return inferred_type, content, is_breaking


def get_commit_messages_since(
        latest_commit: str,
        to_commit: str = "HEAD",
        repo_path: str = ".",
        min_length: int = 10
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
    for commit in repo.iter_commits(f"{latest_commit}..{to_commit}", no_merges=True):
        message = commit.message.strip()

        if len(message) >= min_length:
            # Parse and analyze the commit message
            commit_type, content, is_breaking = analyze_commit_message(message)

            # Format with conventional commit style
            prefix = f"{commit_type}{'!' if is_breaking else ''}: "

            # Add issue/PR references if present
            issue_match = re.search(r'(#\d+)', message)
            issue_ref = f" ({issue_match.group(1)})" if issue_match else ""

            # Build formatted message
            formatted_message = f"{prefix}{content}{issue_ref}"

            commit_data.append(formatted_message)

    # Join the commit messages with newlines
    return latest_commit, "\n".join(commit_data)


def get_commit_stats(
        from_ref: str,
        to_ref: str = "HEAD",
        repo_path: str = "."
) -> dict:
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
    stats = {
        'total': 0,
        'by_type': {},
        'by_author': {},
        'breaking_changes': 0,
        'files_changed': set(),
    }

    # Get the commits in the range
    for commit in repo.iter_commits(f"{from_ref}..{to_ref}", no_merges=True):
        message = commit.message.strip()
        commit_type, _, is_breaking = analyze_commit_message(message)

        # Update stats
        stats['total'] += 1
        stats['by_type'][commit_type] = stats['by_type'].get(commit_type, 0) + 1
        stats['by_author'][commit.author.name] = stats['by_author'].get(commit.author.name, 0) + 1

        if is_breaking:
            stats['breaking_changes'] += 1

        # Get files changed
        for file in commit.stats.files:
            stats['files_changed'].add(file)

    stats['files_changed'] = list(stats['files_changed'])
    return stats