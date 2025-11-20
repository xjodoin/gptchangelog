"""Enhanced OpenAI utilities for better changelog generation."""

import logging
import re
from datetime import datetime
from typing import Tuple, Dict, List, Any, Optional, cast
from collections import defaultdict

import openai
from openai import OpenAIError

from .utils import render_prompt, estimate_tokens, resolve_template_path
from .enhanced_git_utils import CommitInfo, format_commits_for_ai

logger = logging.getLogger(__name__)


class EnhancedChangelogGenerator:
    """Enhanced changelog generator with better AI integration."""
    
    def __init__(self, model: str = "gpt-5-mini", max_tokens: int = 200000, language: str = "en"):
        self.model = model
        self.max_tokens = max_tokens
        self.language = (language or "en").lower()
        
        # Changelog templates for different types
        self.changelog_categories: Dict[str, Dict[str, Any]] = {
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
        component_impact: Dict[str, Dict[str, Any]] = {}
        for commit in commits:
            for component in commit.components:
                if component not in component_impact:
                    component_impact[component] = {'commits': 0, 'types': set()}
                component_impact[component]['commits'] += 1
                component_impact[component]['types'].add(commit.commit_type)
        
        # Build a serializable copy for JSON (convert sets to lists)
        component_impact_serializable = {
            comp: {'commits': data['commits'], 'types': list(data['types'])}
            for comp, data in component_impact.items()
        }
        
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
            'component_impact': component_impact_serializable,
            'commits_by_type': {k: len(v) for k, v in commits_by_type.items()},
            'date_range': f"{stats['date_range'][0].strftime('%Y-%m-%d')} to {stats['date_range'][1].strftime('%Y-%m-%d')}" if stats['date_range'] else None,
        }

    # --- OpenAI helpers -------------------------------------------------
    def _max_response_tokens(self) -> int:
        """Cap response tokens to a reasonable size while honoring global max."""
        # keep headroom for prompt; most changelogs fit in 800-1200 tokens
        return max(300, min(1200, self.max_tokens // 4))

    def _trim_text_to_tokens(self, text: str, budget: int) -> str:
        """Trim text so prompt stays under the model context budget."""
        if estimate_tokens(text, self.model) <= budget:
            return text

        # simple line-wise trim from the start to keep the most recent items
        lines = text.splitlines()
        out_lines: List[str] = []
        total = 0
        # work from the end (latest commits are more relevant)
        for line in reversed(lines):
            total += estimate_tokens(line + "\n", self.model)
            if total > budget:
                break
            out_lines.append(line)
        out_lines.reverse()
        return "\n".join(out_lines)

    def _chat_complete(self, prompt: str, system: str) -> str:
        """Centralized OpenAI call with safe defaults and token limits."""
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self._max_response_tokens(),
                temperature=0.2,
                seed=1,
            )
            return response.choices[0].message.content or ""
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            return ""

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

        # Trim commit text to fit context window
        prompt_budget = max(1000, self.max_tokens - self._max_response_tokens() - 1500)
        formatted_commits = self._trim_text_to_tokens(formatted_commits, prompt_budget)
        
        # Prepare enhanced context for the AI prompt
        commit_analysis = {
            'grouped_commits': self._group_similar_commits(commits),
            'version_impact': self._determine_version_impact(commits),
        }

        def _summarize_commit_analysis() -> str:
            summary: List[str] = []
            vi = commit_analysis['version_impact']
            summary.append(f"Version impact: {vi[0]} ({vi[1]})")

            groups = commit_analysis['grouped_commits']
            if groups:
                summary.append("Grouped highlights:")
                for key, group in list(groups.items())[:8]:
                    summary.append(f"- {key}: {len(group)} commits")
            return "\n".join(summary)

        enhanced_context = {
            **context,
            'commit_messages': formatted_commits,
            'commit_analysis': commit_analysis,
            'commit_analysis_text': _summarize_commit_analysis(),
        }
        
        # i18n-aware template resolution for enhanced commits prompt
        commits_template = resolve_template_path("commits_prompt", self.language, enhanced=True)
        prompt = render_prompt(commits_template, enhanced_context)
        
        content = self._chat_complete(
            prompt,
            (
                "You are an expert software analyst specializing in commit analysis and changelog generation. "
                "You excel at understanding code changes, grouping related modifications, identifying breaking "
                "changes, and creating clear, user-focused descriptions of software updates."
            ),
        )
        return content if isinstance(content, str) and content else formatted_commits

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
        
        # i18n-aware template resolution for enhanced version prompt
        version_template = resolve_template_path("version_prompt", self.language, enhanced=True)
        prompt = render_prompt(version_template, version_context)
        
        response_text = self._chat_complete(
            prompt,
            (
                "You are a semantic versioning expert. You analyze software changes to determine "
                "the appropriate version increment following semantic versioning principles. "
                "You consider breaking changes, new features, and bug fixes to make version decisions."
            ),
        )
            
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
            
        except Exception:
            logger.error("Failed to parse version from model response; falling back.")
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
        
        # i18n-aware template resolution for enhanced changelog prompt
        changelog_template = resolve_template_path("changelog_prompt", self.language, enhanced=True)
        prompt = render_prompt(changelog_template, changelog_context)
        
        changelog = self._chat_complete(
            prompt,
            (
                "You are a technical writer specializing in software changelogs. You create "
                "clear, well-organized, and user-friendly changelogs that help users understand "
                "what has changed in software releases. You focus on impact and benefits rather "
                "than technical implementation details."
            ),
        )

        if changelog:
            return self._post_process_changelog(changelog, next_version, context)

        return self._generate_fallback_changelog(commits, next_version, context)

    def _post_process_changelog(self, changelog: str, next_version: str, context: Dict[str, Any]) -> str:
        """Post-process the generated changelog: fix header, enforce section order, remove empty sections, dedupe bullets, synthesize summary."""
        # Normalize line endings and bullet prefix
        raw_lines = re.sub(r'^[-*]\s+', '- ', changelog, flags=re.MULTILINE).splitlines()

        # Ensure header
        date_str = context.get('current_date', datetime.now().strftime('%Y-%m-%d'))
        header_line = f"## [{next_version}] - {date_str}"

        lines: List[str] = [ln for ln in raw_lines if ln is not None]
        if not lines or not lines[0].startswith('##'):
            lines = [header_line, ""] + lines
        else:
            # Replace header with canonical format
            if re.search(r'## \[.*\]', lines[0]):
                lines[0] = header_line
            else:
                lines[0] = header_line

        # Parse sections
        sections: Dict[str, List[str]] = {}
        current_section: Optional[str] = None
        bullet_seen: Dict[str, set] = {}
        summary_lines: List[str] = []
        seen_section = False

        def norm_bullet(b: str) -> str:
            return re.sub(r'\s+', ' ', b.strip().lower())

        for ln in lines[1:]:  # skip header
            if ln.startswith('### '):
                seen_section = True
                current_section = ln.strip()[4:]
                if current_section not in sections:
                    sections[current_section] = []
                    bullet_seen[current_section] = set()
                continue

            if not seen_section:
                # Preserve user-written summary paragraphs under the header
                if ln.strip():
                    summary_lines.append(ln.rstrip())
                continue

            if ln.startswith('- '):
                if current_section is None:
                    # Create a generic section if bullets appear before any header
                    current_section = '🔧 Maintenance'  # default bucket
                    if current_section not in sections:
                        sections[current_section] = []
                        bullet_seen[current_section] = set()
                key = norm_bullet(ln)
                if key not in bullet_seen[current_section]:
                    sections[current_section].append(ln.strip())
                    bullet_seen[current_section].add(key)
            else:
                # Keep free-form text inside sections (notes/migration guidance)
                if current_section is None:
                    current_section = '🔧 Maintenance'
                    sections.setdefault(current_section, [])
                    bullet_seen.setdefault(current_section, set())
                if ln.strip():
                    sections[current_section].append(ln.rstrip())

        # Remove empty sections (no bullets)
        sections = {title: bullets for title, bullets in sections.items() if any(bullets)}

        # Map possible headings without emojis to canonical with emojis
        title_map: Dict[str, str] = {}
        for key, meta in self.changelog_categories.items():
            title_map[meta['title']] = meta['title']
            # Allow mapping of titles without emoji to canonical title
            no_emoji = meta['title'].split(' ', 1)[1] if ' ' in meta['title'] else meta['title']
            title_map[no_emoji] = meta['title']
        title_map["Breaking Changes"] = "⚠️ Breaking Changes"
        title_map["Removed"] = "🗑️ Removed"
        title_map["Deprecated"] = "⚠️ Deprecated"

        # Default canonical section order
        default_order: List[str] = [
            "⚠️ Breaking Changes",
            "✨ Features",
            "🐛 Bug Fixes",
            "⚡ Performance",
            "🔄 Changes",
            "🗑️ Removed",
            "⚠️ Deprecated",
            "📚 Documentation",
            "🔧 Maintenance",
        ]

        # Prepare custom order from context if provided
        order_input = context.get('section_order')
        custom_order: List[str] = []
        if isinstance(order_input, str):
            custom_order = [s.strip() for s in order_input.split(',') if s.strip()]
        elif isinstance(order_input, list):
            custom_order = [str(s).strip() for s in order_input if str(s).strip()]

        # Map custom titles to canonical (with emoji) if possible
        mapped_custom: List[str] = []
        for t in custom_order:
            mapped_custom.append(title_map.get(t, t))
        order: List[str] = mapped_custom if mapped_custom else default_order

        # Normalize section titles to canonical
        norm_sections: Dict[str, List[str]] = {}
        for title, bullets in sections.items():
            canonical = title_map.get(title, title)
            norm_sections.setdefault(canonical, [])
            norm_sections[canonical].extend(bullets)
        sections = norm_sections

        # Build final content
        out: List[str] = [header_line]

        # Add or synthesize a brief summary after header
        if summary_lines:
            out.extend(["", *summary_lines])
        elif len(lines) < 2 or lines[1].startswith('###'):
            total = context.get('total_commits', 0) or 0
            by_type = context.get('commit_types', {}) or {}

            def fmt_count(count: int, singular: str) -> Optional[str]:
                if not count:
                    return None
                label = singular if count == 1 else f"{singular}s"
                return f"{count} {label}"

            # Build summary segments for relevant stats only
            summary_segments: List[str] = []
            total_text = fmt_count(total, "commit")
            if total_text:
                summary_segments.append(total_text)

            detail_parts: List[str] = []
            if isinstance(by_type, dict):
                for key, label in (("feat", "feature"), ("fix", "fix"), ("perf", "performance update")):
                    part = fmt_count(int(by_type.get(key, 0) or 0), label)
                    if part:
                        detail_parts.append(part)

            summary_line = ""
            if summary_segments:
                summary_line = summary_segments[0]
                if detail_parts:
                    if len(detail_parts) == 1:
                        summary_line += f" including {detail_parts[0]}"
                    else:
                        summary_line += " including " + ", ".join(detail_parts[:-1]) + f" and {detail_parts[-1]}"
                summary_line += "."

            comps = context.get('main_components', []) or []
            component_line = ""
            if comps:
                displayed = ", ".join(str(c) for c in comps[:3])
                if len(comps) > 3:
                    displayed += ", …"
                component_line = f"Key areas: {displayed}."

            summary_text = " ".join(filter(None, [summary_line, component_line]))

            if summary_text:
                out.extend(["", summary_text])
            else:
                out.append("")  # still ensure blank line separator
        else:
            out.append("")  # ensure a blank line before sections

        # Optional compare link and contributors
        compare_url = context.get('compare_url')
        if compare_url:
            out.extend([f"[Compare changes]({compare_url})"])
        contributors = context.get('contributors')
        if contributors:
            if isinstance(contributors, list):
                names = ', '.join([str(n) for n in contributors][:10])
                out.extend([f"Contributors: {names}"])
        # Blank line before sections
        out.append("")

        # Emit sections in canonical or custom order, skipping empties
        use_emojis = bool(context.get('use_emojis', True))
        for sec in order:
            bullets = sections.get(sec, [])
            if not bullets:
                continue
            title_to_emit = sec if use_emojis else re.sub(r'^[^\w\s]\s*', '', sec)
            out.append(f"### {title_to_emit}")
            for b in bullets:
                if b.lstrip().startswith('- '):
                    out.append(f"- {b.lstrip('- ').strip()}")
                else:
                    out.append(b)
            out.append("")

        # Include any extra sections not covered by canonical order
        for sec, bullets in sections.items():
            if sec in order or not bullets:
                continue
            out.append(f"### {sec}")
            for b in bullets:
                if b.lstrip().startswith('- '):
                    out.append(f"- {b.lstrip('- ').strip()}")
                else:
                    out.append(b)
            out.append("")

        # Collapse multiple blank lines
        final_lines: List[str] = []
        prev_blank = False
        for ln in out:
            is_blank = (ln.strip() == "")
            if is_blank and prev_blank:
                continue
            final_lines.append(ln.rstrip())
            prev_blank = is_blank

        return '\n'.join(final_lines)

    def _priority(self, commit_type: str) -> int:
        """Return sorting priority for a commit type."""
        meta = self.changelog_categories.get(commit_type)
        return meta['priority'] if meta else 999

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
        for commit_type in sorted(by_type.keys(), key=self._priority):
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
    model: str = "gpt-5-mini",
    max_tokens: int = 200000,
    language: str = "en",
    extra_context: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """Generate enhanced changelog and version using the new system."""
    
    generator = EnhancedChangelogGenerator(model, max_tokens, language)
    
    # Create enhanced context
    context = generator._create_enhanced_context(commits, current_version, project_name, stats)
    if extra_context:
        # Merge optional extras such as compare_url, contributors, use_emojis, section_order
        context = {**context, **extra_context}
    
    # Determine next version
    next_version = generator.determine_smart_version(commits, current_version, context)
    
    # Generate changelog
    changelog = generator.generate_enhanced_changelog(commits, next_version, context)
    
    return changelog, next_version


def analyze_changelog_quality(changelog: str) -> Dict[str, Any]:
    """Analyze the quality of a generated changelog."""
    lines = changelog.split('\n')

    def _emoji_present(text: str) -> bool:
        # Basic emoji range check (covers common symbols)
        return bool(re.search(r'[\U0001F300-\U0001FAFF]', text))

    # Parse structure for empty sections and duplicates
    headings: List[str] = []
    bullets_by_heading: Dict[str, List[str]] = {}
    current = None
    summary_present = False

    for idx, ln in enumerate(lines[1:], start=1):  # after header
        if ln.startswith('### '):
            current = ln[4:].strip()
            headings.append(current)
            bullets_by_heading.setdefault(current, [])
        elif ln.startswith('- '):
            if current is None:
                current = 'Uncategorized'
                headings.append(current)
                bullets_by_heading.setdefault(current, [])
            bullets_by_heading[current].append(re.sub(r'\s+', ' ', ln[2:].strip().lower()))
        elif ln.strip() and current is None and idx == 1:
            # text directly after header counts as summary
            summary_present = True

    empty_sections = [h for h, b in bullets_by_heading.items() if not b]

    # Duplicate bullet detection per section
    duplicate_bullets = 0
    for vals in bullets_by_heading.values():
        seen = set()
        for b in vals:
            if b in seen:
                duplicate_bullets += 1
            seen.add(b)

    bullet_matches = re.findall(r'^- (.+)$', changelog, re.MULTILINE)

    quality_metrics = {
        'has_proper_header': bool(re.search(r'## \[.*\] - \d{4}-\d{2}-\d{2}', changelog)),
        'has_categories': len(headings) > 0,
        'has_bullet_points': len(bullet_matches) > 0,
        'has_emojis': _emoji_present(changelog),
        'line_count': len([line for line in lines if line.strip()]),
        'empty_sections': len(empty_sections),
        'duplicate_bullets': duplicate_bullets,
        'avg_bullet_length': 0.0,
        'has_breaking_changes': 'breaking' in changelog.lower() or '⚠️' in changelog,
        'has_summary': summary_present,
    }

    # Calculate average bullet point length
    bullets = bullet_matches
    if bullets:
        quality_metrics['avg_bullet_length'] = sum(len(bullet) for bullet in bullets) / len(bullets)

    # Overall quality score (0-100)
    score = 0
    if quality_metrics['has_proper_header']:
        score += 15
    if quality_metrics['has_summary']:
        score += 10
    if quality_metrics['has_categories']:
        score += 15
    if quality_metrics['has_bullet_points']:
        score += 15
    if quality_metrics['line_count'] > 5:
        score += 10
    if quality_metrics['avg_bullet_length'] > 20:
        score += 15
    if quality_metrics['empty_sections'] == 0:
        score += 10
    if quality_metrics['duplicate_bullets'] == 0:
        score += 10
    if quality_metrics['has_emojis']:
        score += 5

    quality_metrics['quality_score'] = score

    return quality_metrics
