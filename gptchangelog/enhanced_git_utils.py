"""Enhanced Git utilities for better commit analysis and changelog generation."""

import git
import os
import re
from typing import Tuple, List, Optional, Dict, Any, Set, DefaultDict
from datetime import datetime
from collections import defaultdict, namedtuple

CommitInfo = namedtuple('CommitInfo', [
    'hash', 'message', 'author', 'date', 'files_changed', 
    'insertions', 'deletions', 'commit_type', 'scope', 
    'is_breaking', 'issue_refs', 'components'
])


class EnhancedCommitAnalyzer:
    """Enhanced commit analyzer with better categorization and grouping."""
    
    def __init__(self, repo_path: str = "."):
        self.repo = git.Repo(repo_path)
        self.repo_name = self._get_repository_name()
        
        # Component patterns for better categorization
        self.component_patterns = {
            'frontend': r'(?i)(ui|frontend|web|client|css|html|js|react|vue|angular)',
            'backend': r'(?i)(api|server|backend|service|endpoint|controller)',
            'database': r'(?i)(db|database|migration|schema|sql|mongodb|postgres)',
            'auth': r'(?i)(auth|login|security|oauth|jwt|session)',
            'config': r'(?i)(config|settings|env|environment|setup)',
            'docs': r'(?i)(doc|readme|guide|tutorial|example)',
            'test': r'(?i)(test|spec|unittest|integration)',
            'build': r'(?i)(build|compile|webpack|grunt|gulp|ci|deploy)',
            'deps': r'(?i)(depend|package|requirements|pip|npm|yarn)',
        }
        
        # Breaking change indicators
        self.breaking_indicators = [
            r'breaking[\s-]?change',
            r'backward[\s-]?incompatible',
            r'major[\s-]?refactor',
            r'api[\s-]?change',
            r'remove.*support',
            r'drop.*support',
            r'deprecate.*remove',
        ]

    def _get_repository_name(self) -> str:
        """Extract the repository name from a git repository."""
        try:
            remote_url = self.repo.remotes.origin.url
            name = os.path.basename(remote_url)
            if name.endswith('.git'):
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
        """Enhanced detection of breaking changes."""
        # Check conventional commit format
        if '!' in message.split(':', 1)[0]:
            return True
        
        # Check for breaking change footer
        if 'BREAKING CHANGE:' in message:
            return True
        
        # Check message content for breaking change indicators
        message_lower = message.lower()
        for pattern in self.breaking_indicators:
            if re.search(pattern, message_lower):
                return True
        
        # Check file changes for breaking patterns
        breaking_files = [
            r'.*api.*',
            r'.*schema.*',
            r'.*interface.*',
            r'.*contract.*',
        ]
        
        for file_path in files_changed:
            for pattern in breaking_files:
                if re.search(pattern, file_path.lower()):
                    # Additional check: look for removals or major changes
                    if any(word in message_lower for word in ['remove', 'delete', 'drop', 'deprecate']):
                        return True
        
        return False

    def _extract_issue_references(self, message: str) -> List[str]:
        """Extract issue/PR references from commit message."""
        patterns = [
            r'#(\d+)',
            r'(?:fix|fixes|close|closes|resolve|resolves)\s+#(\d+)',
            r'(?:PR|pr)\s+#?(\d+)',
            r'(?:issue|Issue)\s+#?(\d+)',
        ]
        
        refs = []
        for pattern in patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            refs.extend([f"#{match}" for match in matches])
        
        return list(set(refs))  # Remove duplicates

    def _parse_conventional_commit(self, message: str) -> Tuple[Optional[str], Optional[str], str, bool]:
        """Enhanced conventional commit parsing."""
        # Pattern for conventional commit format
        pattern = r'^(?P<type>\w+)(\((?P<scope>[^)]+)\))?(?P<breaking>!)?\s*:\s*(?P<message>.+)$'
        
        first_line = message.split('\n', 1)[0].strip()
        match = re.match(pattern, first_line)
        
        if match:
            commit_type = match.group('type')
            scope = match.group('scope')
            breaking_marker = match.group('breaking')
            content = match.group('message')
            is_breaking = bool(breaking_marker) or 'BREAKING CHANGE:' in message
            return commit_type, scope, content, is_breaking
        
        return None, None, message.strip(), False

    def _infer_commit_type(self, message: str, files_changed: List[str]) -> str:
        """Infer commit type from message and file changes."""
        message_lower = message.lower()
        
        # Feature indicators
        if re.search(r'\b(add|implement|create|introduce|new)\b', message_lower):
            return 'feat'
        
        # Fix indicators
        if re.search(r'\b(fix|resolve|correct|patch|bug)\b', message_lower):
            return 'fix'
        
        # Documentation indicators
        if re.search(r'\b(doc|readme|guide|example)\b', message_lower):
            return 'docs'
        
        # Test indicators
        if re.search(r'\b(test|spec|coverage)\b', message_lower):
            return 'test'
        
        # Build indicators
        if re.search(r'\b(build|compile|bundle|deploy)\b', message_lower):
            return 'build'
        
        # Performance indicators
        if re.search(r'\b(perf|performance|optimize|speed)\b', message_lower):
            return 'perf'
        
        # Refactor indicators
        if re.search(r'\b(refactor|restructure|reorganize|clean)\b', message_lower):
            return 'refactor'
        
        # Style indicators
        if re.search(r'\b(style|format|lint|prettier)\b', message_lower):
            return 'style'
        
        # Check file extensions for type hints
        if files_changed:
            if any(f.endswith(('.md', '.rst', '.txt')) for f in files_changed):
                return 'docs'
            if any('test' in f.lower() or f.endswith(('.test.js', '.spec.js', '_test.py')) for f in files_changed):
                return 'test'
            if any(f in ['package.json', 'requirements.txt', 'Pipfile', 'yarn.lock'] for f in files_changed):
                return 'chore'
        
        return 'chore'  # Default fallback

    def analyze_commit(self, commit) -> CommitInfo:
        """Analyze a single commit and extract detailed information."""
        message = commit.message.strip()
        files_changed = list(commit.stats.files.keys())
        
        # Parse conventional commit format
        commit_type, scope, clean_message, is_breaking_conv = self._parse_conventional_commit(message)
        
        # If not conventional, infer type
        if not commit_type:
            commit_type = self._infer_commit_type(message, files_changed)
            clean_message = message
        
        # Enhanced breaking change detection
        is_breaking = is_breaking_conv or self._detect_breaking_changes(message, files_changed)
        
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
            insertions=commit.stats.total['insertions'],
            deletions=commit.stats.total['deletions'],
            commit_type=commit_type,
            scope=scope,
            is_breaking=is_breaking,
            issue_refs=issue_refs,
            components=components
        )

    def get_enhanced_commits(self, from_ref: str, to_ref: str = "HEAD") -> List[CommitInfo]:
        """Get detailed commit information for the specified range."""
        commits = []
        
        try:
            for commit in self.repo.iter_commits(f"{from_ref}..{to_ref}", no_merges=True):
                # Skip very small commits (likely typos or trivial changes)
                if len(commit.message.strip()) < 10:
                    continue
                
                commit_info = self.analyze_commit(commit)
                commits.append(commit_info)
        except Exception as e:
            print(f"Error analyzing commits: {e}")
        
        return commits

    def group_related_commits(self, commits: List[CommitInfo]) -> Dict[str, List[CommitInfo]]:
        """Group related commits by feature/component."""
        groups = defaultdict(list)
        
        for commit in commits:
            # Create a key based on components and type
            components_str = '_'.join(sorted(commit.components)) if commit.components else 'general'
            group_key = f"{commit.commit_type}_{components_str}"
            
            # Special grouping for features and fixes
            if commit.commit_type in ['feat', 'fix']:
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
                'total_commits': 0,
                'by_type': dict(by_type),
                'by_author': dict(by_author),
                'by_component': dict(by_component),
                'breaking_changes': 0,
                'total_files_changed': 0,
                'total_insertions': 0,
                'total_deletions': 0,
                'date_range': None,
                'most_active_authors': [],
                'most_changed_components': [],
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
            by_author.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Most changed components
        most_changed_components = sorted(
            by_component.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return {
            'total_commits': len(commits),
            'by_type': dict(by_type),
            'by_author': dict(by_author),
            'by_component': dict(by_component),
            'breaking_changes': breaking_changes,
            'total_files_changed': len(total_files_changed),
            'total_insertions': total_insertions,
            'total_deletions': total_deletions,
            'date_range': date_range,
            'most_active_authors': most_active_authors,
            'most_changed_components': most_changed_components,
        }


def get_enhanced_commit_data(from_ref: str, to_ref: str = "HEAD", repo_path: str = ".") -> Tuple[List[CommitInfo], Dict[str, Any]]:
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
                line_parts.append(f" [Components: {', '.join(sorted(commit.components))}]")
            
            output.append(''.join(line_parts))
    
    # Add statistics if requested
    if include_stats:
        analyzer = EnhancedCommitAnalyzer()
        stats = analyzer.get_commit_statistics(commits)
        
        output.append("\n--- COMMIT STATISTICS ---")
        output.append(f"Total commits: {stats['total_commits']}")
        output.append(f"Breaking changes: {stats['breaking_changes']}")
        output.append(f"Files changed: {stats['total_files_changed']}")
        output.append(f"Code changes: +{stats['total_insertions']} -{stats['total_deletions']}")
        
        if stats['most_changed_components']:
            components = [f"{comp}({count})" for comp, count in stats['most_changed_components']]
            output.append(f"Main components: {', '.join(components)}")
    
    return '\n'.join(output)
