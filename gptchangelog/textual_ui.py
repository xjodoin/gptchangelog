from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TextualDisplayData:
    repo_name: str
    changelog: str
    next_version: str
    stats: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    compare_url: Optional[str] = None
    contributors: Optional[List[str]] = None


def display_textual_result(data: TextualDisplayData) -> None:
    """Render the changelog result using a Textual application."""

    try:
        from textual.app import App, ComposeResult
        from textual.containers import Container, Horizontal, VerticalScroll
        from textual.widgets import Footer, Header, Markdown, Static
    except ImportError as exc:  # pragma: no cover - handled by caller
        raise ImportError(
            "Textual is not installed. Install gptchangelog with the textual dependency "
            "or run with '--ui plain'."
        ) from exc

    class ResultApp(App[str]):
        CSS = """
        Screen {
            layout: vertical;
        }
        #body {
            layout: horizontal;
            height: 1fr;
        }
        #sidebar {
            width: 38%;
            min-width: 32;
            border: round $surface;
            padding: 1 1;
            scrollbar-gutter: stable;
        }
        #changelog {
            border: round $surface;
            padding: 1 1;
            height: 1fr;
        }
        """

        BINDINGS = [
            ("q", "quit", "Quit"),
            ("escape", "quit", "Quit"),
        ]

        def __init__(self, result: TextualDisplayData) -> None:
            super().__init__()
            self._result = result

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)

            sidebar_children = [Static(self._summary_text(), id="summary")]

            stats_text = self._stats_text()
            if stats_text:
                sidebar_children.append(Static(stats_text, id="stats"))

            quality_text = self._quality_text()
            if quality_text:
                sidebar_children.append(Static(quality_text, id="quality"))

            yield Container(
                Horizontal(
                    VerticalScroll(*sidebar_children, id="sidebar"),
                    VerticalScroll(Markdown(self._result.changelog), id="changelog"),
                ),
                id="body",
            )

            yield Footer()

        def _summary_text(self) -> str:
            lines = [
                f"[b]Repository:[/b] {self._result.repo_name}",
                f"[b]Next Version:[/b] {self._result.next_version}",
            ]

            if self._result.compare_url:
                lines.append(f"[link={self._result.compare_url}]Compare changes[/link]")

            if self._result.contributors:
                contributor_list = ", ".join(self._result.contributors[:10])
                if len(self._result.contributors) > 10:
                    contributor_list += ", …"
                lines.append(f"[b]Contributors:[/b] {contributor_list}")

            return "\n".join(lines)

        def _stats_text(self) -> Optional[str]:
            stats = self._result.stats or {}
            if not stats:
                return None

            parts: List[str] = ["[b]Commit Statistics[/b]"]
            total = stats.get("total_commits")
            if total is not None:
                parts.append(f"• Total commits: {total}")

            breaking = stats.get("breaking_changes")
            if breaking:
                parts.append(f"• Breaking changes: {breaking}")

            by_type = stats.get("by_type") or {}
            if by_type:
                type_snippets = ", ".join(
                    f"{kind} ({count})" for kind, count in sorted(by_type.items())
                )
                parts.append(f"• Types: {type_snippets}")

            components = stats.get("most_changed_components") or []
            if components:
                component_snippets = ", ".join(
                    f"{comp} ({count})" for comp, count in components[:5]
                )
                parts.append(f"• Hot components: {component_snippets}")

            return "\n".join(parts)

        def _quality_text(self) -> Optional[str]:
            metrics = self._result.quality_metrics or {}
            if not metrics:
                return None

            parts = ["[b]Quality Analysis[/b]"]
            score = metrics.get("quality_score")
            if score is not None:
                parts.append(f"Score: {score}/100")

            checklist = []
            if metrics.get("has_proper_header") is not None:
                checklist.append(
                    f"Header: {'✅' if metrics['has_proper_header'] else '❌'}"
                )
            if metrics.get("has_categories") is not None:
                checklist.append(
                    f"Categories: {'✅' if metrics['has_categories'] else '❌'}"
                )
            if metrics.get("has_bullet_points") is not None:
                checklist.append(
                    f"Bullets: {'✅' if metrics['has_bullet_points'] else '❌'}"
                )
            if checklist:
                parts.append(" • ".join(checklist))

            avg_bullet_length = metrics.get("avg_bullet_length")
            if avg_bullet_length is not None:
                parts.append(f"Average bullet length: {avg_bullet_length:.1f} chars")

            if metrics.get("has_breaking_changes"):
                parts.append("⚠️ Breaking changes detected")

            empty_sections = metrics.get("empty_sections")
            if empty_sections:
                parts.append(f"⚠️ Empty sections: {empty_sections}")

            return "\n".join(parts)

    ResultApp(data).run()
