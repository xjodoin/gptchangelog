"""Enhanced OpenAI utilities for better changelog generation."""

import logging
import re
from datetime import datetime
from typing import Tuple, Dict, List, Any, Optional
from collections import defaultdict

import openai
from openai import OpenAIError

from .utils import render_prompt, estimate_tokens
from .enhanced_git_utils import CommitInfo, format_commits_for_ai

logger = logging.getLogger(__name__)


class EnhancedChangelogGenerator:
    """Enhanced changelog generator with better AI integration."""
    
    def __init__(self, model: str = "gpt-4o", max_tokens: int = 80000):
        self.model = model
        self.max_tokens = max_tokens
        
        # Changelog templates for different types
        self.changelog_categories = {
            'feat': {'title': '✨ Features', 'emoji': '✨', 'priority': 1},
            'fix': {'title': '🐛 Bug Fixes', 'emoji': '🐛', 'priority': 2},
            'perf': {'title': '⚡ Performance', 'emoji': '⚡', 'priority': 3},
            'refactor': {'title': '🔄 Changes', 'emoji': '🔄', 'priority': 4},
            'docs': {'title': '📚 Documentation', 'emoji': '📚', 'priority': 5},
            'test': {'title': '🧪 Testing', 'emoji': '🧪', 'priority': 6},
            'build': {'title': '🏗️ Build', 'emoji': '🏗️', 'priority': 7},
            'ci': {'title': '👷 CI/CD', 'emoji': '👷', 'priority': 8},
            'style': {'title': '💄 Style', 'emoji': '💄', 'priority': 9},
            'chore': {'title': '🔧 Maintenance', 'emoji': '🔧', 'priority': 10},
        }

    def _create_enhanced_context(self, commits: List[CommitInfo], current_version: str, 
                               project_name: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced context for AI prompts."""
        # Group commits by type
        commits_by_type = defaultdict(list)
        for commit in commits:
            commits_by_type[commit.commit_type].append(commit)
        
        # Create component impact summary
        component_impact = {}
        for commit in commits:
            for component in commit.components:
                if component not in component_impact:
                    component_impact[component] = {'commits': 0, 'types': set()}
                component_impact[component]['commits'] += 1
                component_impact[component]['types'].add(commit.commit_type)
        
        # Convert types to lists for JSON serialization
        for component in component_impact:
            component_impact[component]['types'] = list(component_impact[component]['types'])
        
        return {
            'project_name': project_name,
            'current_version': current_version,
            'current_date': datetime.today().strftime("%Y-%m-%d"),
            'total_commits': len(commits),
            'commit_types': dict(stats['by_type']),
            'breaking_changes': stats['breaking_changes'],
            'files_changed': stats['total_files_changed'],
            'insertions': stats['total_insertions'],
            'deletions': stats['total_deletions'],
            'main_components': [comp for comp, count in stats['most_changed_components']],
            'component_impact': component_impact,
            'commits_by_type': {k: len(v) for k, v in commits_by_type.items()},
            'date_range': f"{stats['date_range'][0].strftime('%Y-%m-%d')} to {stats['date_range'][1].strftime('%Y-%m-%d')}" if stats['date_range'] else None,
        }

    def _determine_version_impact(self, commits: List[CommitInfo]) -> Tuple[str, str]:
        """Determine version impact level and justification."""
        has_breaking = any(commit.is_breaking for commit in commits)
        has_features = any(commit.commit_type == 'feat' for commit in commits)
        has_fixes = any(commit.commit_type == 'fix' for commit in commits)
        
        if has_breaking:
            impact = 'major'
            justification = f"Contains {sum(1 for c in commits if c.is_breaking)} breaking change(s)"
        elif has_features:
            impact = 'minor'
            feature_count = sum(1 for c in commits if c.commit_type == 'feat')
            justification = f"Adds {feature_count} new feature(s)"
        elif has_fixes:
            impact = 'patch'
            fix_count = sum(1 for c in commits if c.commit_type == 'fix')
            justification = f"Contains {fix_count} bug fix(es)"
        else:
            impact = 'patch'
            justification = "Contains maintenance and minor updates"
        
        return impact, justification

    def _group_similar_commits(self, commits: List[CommitInfo]) -> Dict[str, List[CommitInfo]]:
        """Group similar commits for better changelog organization."""
        groups = defaultdict(list)
        
        for commit in commits:
            # Create grouping key based on commit type and components
            components_key = '_'.join(sorted(commit.components)) if commit.components else 'general'
            
            # Special handling for different commit types
            if commit.commit_type in ['feat', 'fix']:
                # For features and fixes, try to group by semantic similarity
                words = commit.message.lower().split()[:2]  # First 2 words
                if len(words) >= 2:
                    semantic_key = f"{commit.commit_type}_{components_key}_{words[0]}"
                else:
                    semantic_key = f"{commit.commit_type}_{components_key}"
                groups[semantic_key].append(commit)
            else:
                # For other types, group by type and component
                group_key = f"{commit.commit_type}_{components_key}"
                groups[group_key].append(commit)
        
        return dict(groups)

    def process_commits_intelligently(self, commits: List[CommitInfo], context: Dict[str, Any]) -> str:
        """Process commits with intelligent grouping and analysis."""
        if not commits:
            return "No commits to process."
        
        # Format commits for AI with enhanced context
        formatted_commits = format_commits_for_ai(commits, include_stats=True)
        
        # Prepare enhanced context for the AI prompt
        enhanced_context = {
            **context,
            'commit_messages': formatted_commits,
            'commit_analysis': {
                'grouped_commits': self._group_similar_commits(commits),
                'version_impact': self._determine_version_impact(commits),
            }
        }
        
        prompt = render_prompt("templates/enhanced_commits_prompt.txt", enhanced_context)
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert software analyst specializing in commit analysis and changelog generation. "
                            "You excel at understanding code changes, grouping related modifications, identifying "
                            "breaking changes, and creating clear, user-focused descriptions of software updates."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.3,
                max_tokens=4000,
            )
            return response.choices[0].message.content
        except OpenAIError as e:
            logger.error(f"OpenAI API error in commit processing: {e}")
            return formatted_commits  # Fallback to original formatting

    def determine_smart_version(self, commits: List[CommitInfo], current_version: str, 
                              context: Dict[str, Any]) -> str:
        """Determine next version with enhanced intelligence."""
        if not commits:
            return current_version
        
        # Enhanced version analysis
        version_impact, justification = self._determine_version_impact(commits)
        
        # Prepare context for version determination
        version_context = {
            **context,
            'commit_messages': format_commits_for_ai(commits, include_stats=False),
            'version_impact': version_impact,
            'impact_justification': justification,
            'current_version': current_version,
        }
        
        prompt = render_prompt("templates/enhanced_version_prompt.txt", version_context)
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a semantic versioning expert. You analyze software changes to determine "
                            "the appropriate version increment following semantic versioning principles. "
                            "You consider breaking changes, new features, and bug fixes to make version decisions."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.2,
                max_tokens=1000,
            )
            
            response_text = response.choices[0].message.content
            
            # Extract version from response
            version_pattern = r'(?:Version:\s*)?v?(\d+\.\d+\.\d+)'
            match = re.search(version_pattern, response_text)
            
            if match:
                new_version = match.group(1)
                # Preserve 'v' prefix if original had it
                if current_version.startswith('v'):
                    return f"v{new_version}"
                return new_version
            
            # Fallback to manual version increment
            return self._fallback_version_increment(current_version, version_impact)
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error in version determination: {e}")
            return self._fallback_version_increment(current_version, version_impact)

    def _fallback_version_increment(self, current_version: str, impact: str) -> str:
        """Fallback method for version increment."""
        # Handle 'v' prefix
        has_v_prefix = current_version.startswith('v')
        version_number = current_version[1:] if has_v_prefix else current_version
        
        try:
            parts = list(map(int, version_number.split('.')))
            while len(parts) < 3:
                parts.append(0)
            
            if impact == 'major':
                parts[0] += 1
                parts[1] = 0
                parts[2] = 0
            elif impact == 'minor':
                parts[1] += 1
                parts[2] = 0
            else:  # patch
                parts[2] += 1
            
            new_version = '.'.join(map(str, parts))
            return f"v{new_version}" if has_v_prefix else new_version
            
        except Exception:
            return current_version

    def generate_enhanced_changelog(self, commits: List[CommitInfo], next_version: str, 
                                  context: Dict[str, Any]) -> str:
        """Generate an enhanced changelog with better organization and content."""
        if not commits:
            return f"## [{next_version}] - {context.get('current_date', datetime.now().strftime('%Y-%m-%d'))}\n\nNo changes to report."
        
        # Process commits and group them intelligently
        processed_commits = self.process_commits_intelligently(commits, context)
        
        # Enhanced changelog context
        changelog_context = {
            **context,
            'next_version': next_version,
            'processed_commits': processed_commits,
            'categories': self.changelog_categories,
        }
        
        prompt = render_prompt("templates/enhanced_changelog_prompt.txt", changelog_context)
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a technical writer specializing in software changelogs. You create "
                            "clear, well-organized, and user-friendly changelogs that help users understand "
                            "what has changed in software releases. You focus on impact and benefits rather "
                            "than technical implementation details."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.4,
                max_tokens=6000,
            )
            
            changelog = response.choices[0].message.content
            
            # Post-process the changelog
            return self._post_process_changelog(changelog, next_version, context)
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error in changelog generation: {e}")
            return self._generate_fallback_changelog(commits, next_version, context)

    def _post_process_changelog(self, changelog: str, next_version: str, context: Dict[str, Any]) -> str:
        """Post-process the generated changelog for consistency and quality."""
        lines = changelog.split('\n')
        processed_lines = []
        
        for line in lines:
            # Ensure proper header format
            if line.startswith('##') and next_version in line:
                if not re.search(r'## \[.*\] - \d{4}-\d{2}-\d{2}', line):
                    line = f"## [{next_version}] - {context.get('current_date', datetime.now().strftime('%Y-%m-%d'))}"
            
            # Clean up bullet points
            line = re.sub(r'^[-*]\s+', '- ', line)
            
            # Ensure consistent emoji usage
            for commit_type, category in self.changelog_categories.items():
                if line.startswith(f"### {category['title']}"):
                    break
                elif line.startswith(f"### {category['title'].split(' ', 1)[1]}"):
                    line = f"### {category['title']}"
                    break
            
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)

    def _generate_fallback_changelog(self, commits: List[CommitInfo], next_version: str, 
                                   context: Dict[str, Any]) -> str:
        """Generate a basic fallback changelog."""
        date = context.get('current_date', datetime.now().strftime('%Y-%m-%d'))
        changelog = [f"## [{next_version}] - {date}\n"]
        
        # Group commits by type
        by_type = defaultdict(list)
        for commit in commits:
            by_type[commit.commit_type].append(commit)
        
        # Add sections for each type with commits
        for commit_type in sorted(by_type.keys(), key=lambda x: self.changelog_categories.get(x, {}).get('priority', 999)):
            if commit_type in self.changelog_categories:
                section_title = self.changelog_categories[commit_type]['title']
                changelog.append(f"### {section_title}")
                
                for commit in by_type[commit_type]:
                    message = commit.message
                    if commit.issue_refs:
                        message += f" ({', '.join(commit.issue_refs)})"
                    changelog.append(f"- {message}")
                
                changelog.append("")  # Empty line between sections
        
        return '\n'.join(changelog)


def generate_enhanced_changelog_and_version(
    commits: List[CommitInfo],
    current_version: str,
    project_name: str,
    stats: Dict[str, Any],
    model: str = "gpt-4o",
    max_tokens: int = 80000
) -> Tuple[str, str]:
    """Generate enhanced changelog and version using the new system."""
    
    generator = EnhancedChangelogGenerator(model, max_tokens)
    
    # Create enhanced context
    context = generator._create_enhanced_context(commits, current_version, project_name, stats)
    
    # Determine next version
    next_version = generator.determine_smart_version(commits, current_version, context)
    
    # Generate changelog
    changelog = generator.generate_enhanced_changelog(commits, next_version, context)
    
    return changelog, next_version


def analyze_changelog_quality(changelog: str) -> Dict[str, Any]:
    """Analyze the quality of a generated changelog."""
    lines = changelog.split('\n')
    
    quality_metrics = {
        'has_proper_header': bool(re.search(r'## \[.*\] - \d{4}-\d{2}-\d{2}', changelog)),
        'has_categories': len(re.findall(r'### ', changelog)) > 0,
        'has_bullet_points': len(re.findall(r'^- ', changelog, re.MULTILINE)) > 0,
        'has_emojis': len(re.findall(r'[^\w\s]', changelog)) > 0,
        'line_count': len([line for line in lines if line.strip()]),
        'empty_sections': len(re.findall(r'###[^\n]*\n\s*###', changelog)),
        'avg_bullet_length': 0,
        'has_breaking_changes': 'breaking' in changelog.lower() or '⚠️' in changelog,
    }
    
    # Calculate average bullet point length
    bullets = re.findall(r'^- (.+)$', changelog, re.MULTILINE)
    if bullets:
        quality_metrics['avg_bullet_length'] = sum(len(bullet) for bullet in bullets) / len(bullets)
    
    # Overall quality score (0-100)
    score = 0
    if quality_metrics['has_proper_header']:
        score += 20
    if quality_metrics['has_categories']:
        score += 20
    if quality_metrics['has_bullet_points']:
        score += 20
    if quality_metrics['line_count'] > 5:
        score += 15
    if quality_metrics['avg_bullet_length'] > 20:
        score += 15
    if quality_metrics['empty_sections'] == 0:
        score += 10
    
    quality_metrics['quality_score'] = score
    
    return quality_metrics
