from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rich.markup import escape


@dataclass
class TextualDisplayData:
    repo_name: str
    changelog: str
    next_version: str
    stats: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
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
            "Textual is not installed. Install `gptchangelog[tui]` "
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

            validation_text = self._validation_text()
            if validation_text:
                sidebar_children.append(Static(validation_text, id="validation"))

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
                f"[b]Repository:[/b] {escape(self._result.repo_name)}",
                f"[b]Next Version:[/b] {escape(self._result.next_version)}",
            ]

            if self._result.compare_url:
                lines.append(f"[b]Compare:[/b] {escape(self._result.compare_url)}")

            if self._result.contributors:
                contributor_list = ", ".join(
                    escape(name) for name in self._result.contributors[:10]
                )
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
                    f"{escape(str(kind))} ({count})"
                    for kind, count in sorted(by_type.items())
                )
                parts.append(f"• Types: {type_snippets}")

            components = stats.get("most_changed_components") or []
            if components:
                component_snippets = ", ".join(
                    f"{escape(str(comp))} ({count})" for comp, count in components[:5]
                )
                parts.append(f"• Hot components: {component_snippets}")

            return "\n".join(parts)

        def _validation_text(self) -> Optional[str]:
            validation = self._result.validation or {}
            if not validation:
                return None

            valid = bool(validation.get("valid"))
            parts = ["[b]Validation[/b]", "✅ Passed" if valid else "❌ Failed"]
            parts.append(f"Sections: {validation.get('section_count', 0)}")
            parts.append(f"Entries: {validation.get('entry_count', 0)}")
            for error in validation.get("validation_errors", []):
                parts.append(f"• {error}")

            return "\n".join(parts)

    ResultApp(data).run()
