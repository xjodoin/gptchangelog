import json
from types import SimpleNamespace

import git

import gptchangelog.cli as cli
from gptchangelog.enhanced_openai_utils import (
    EnhancedGenerationResult,
    NormalizedReleaseEntry,
)
from gptchangelog.openai_client import ProviderSettings


def _repository(tmp_path):
    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "CLI Test")
        config.set_value("user", "email", "cli@example.com")
    (tmp_path / "feature.txt").write_text("feature", encoding="utf-8")
    repo.index.add(["feature.txt"])
    repo.index.commit("feat: add release output")
    return repo


def _fake_generation(monkeypatch):
    monkeypatch.setattr(
        cli,
        "resolve_provider_configuration",
        lambda args, repo_path: (
            ProviderSettings(provider="codex"),
            "balanced",
            "gpt-5.6-terra",
        ),
    )
    monkeypatch.setattr(
        cli,
        "generate_enhanced_changelog_result",
        lambda *args, **kwargs: EnhancedGenerationResult(
            changelog=(
                "## [0.1.0] - 2026-08-21\n\nA useful release.\n\n"
                "### ✨ Features\n- Adds release output.\n"
            ),
            version="0.1.0",
            summary="A useful release.",
            entries=(
                NormalizedReleaseEntry(
                    category="feat",
                    description="Adds release output.",
                    commit_ids=("abc1234",),
                ),
            ),
            used_fallback=False,
        ),
    )


class _Stream:
    def __init__(self, tty):
        self.tty = tty

    def isatty(self):
        return self.tty


def test_auto_ui_requires_interactive_streams():
    assert (
        cli.determine_ui_mode(
            "auto",
            stdin=_Stream(True),
            output=_Stream(False),
            environ={"TERM": "xterm"},
        )
        == "plain"
    )
    assert (
        cli.determine_ui_mode(
            "auto", stdin=_Stream(True), output=_Stream(True), environ={"TERM": "dumb"}
        )
        == "plain"
    )


def test_explicit_ui_mode_is_respected():
    assert cli.determine_ui_mode("plain") == "plain"
    assert cli.determine_ui_mode("textual") == "textual"


def test_contributors_collapse_case_and_spacing_aliases():
    assert cli.canonicalize_contributors(
        ["olivierneu", " Olivier   Neu ", "OLIVIERNEU", "Jane Doe"]
    ) == ["Jane Doe", "Olivier Neu"]


def test_contributor_order_and_display_are_input_order_independent():
    contributors = ["zoe smith", "alice", "ZoeSmith", "ALICE", "Bob Ray"]

    expected = ["alice", "Bob Ray", "zoe smith"]
    assert cli.canonicalize_contributors(contributors) == expected
    assert cli.canonicalize_contributors(reversed(contributors)) == expected


def test_contributors_keep_distinct_names_and_ignore_empty_values():
    assert cli.canonicalize_contributors(
        ["Alice Stone", "Alice Jones", "  ", None]
    ) == ["Alice Jones", "Alice Stone"]


def test_json_dry_run_keeps_stdout_machine_readable(tmp_path, monkeypatch, capsys):
    _repository(tmp_path)
    _fake_generation(monkeypatch)

    result = cli.app(
        [
            "generate",
            "--repo",
            str(tmp_path),
            "--dry-run",
            "--format",
            "json",
            "--ui",
            "plain",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["version"] == "0.1.0"
    assert payload["model"] == "gpt-5.6-terra"
    assert payload["range"] == {"from": None, "to": "HEAD"}
    assert payload["validation"]["valid"] is True
    assert payload["provenance"] == {
        "covered_commit_count": 1,
        "entries": [
            {
                "category": "feat",
                "commit_ids": ["abc1234"],
                "description": "Adds release output.",
            }
        ],
        "source_commit_count": 1,
        "used_fallback": False,
    }
    assert "Generating 1 commits" in captured.err
    assert not (tmp_path / "CHANGELOG.md").exists()


def test_generation_uses_canonical_contributors(tmp_path, monkeypatch, capsys):
    _repository(tmp_path)
    _fake_generation(monkeypatch)
    monkeypatch.setattr(
        cli,
        "get_enhanced_commit_data",
        lambda *args, **kwargs: (
            [
                SimpleNamespace(author="olivierneu"),
                SimpleNamespace(author="Olivier Neu"),
                SimpleNamespace(author="Jane Doe"),
            ],
            {"total_commits": 3},
        ),
    )
    captured_context = {}

    def generate(*args, **kwargs):
        captured_context.update(kwargs["extra_context"])
        return EnhancedGenerationResult(
            changelog=(
                "## [0.1.0] - 2026-08-21\n\nA useful release.\n\n"
                "### ✨ Features\n- Adds release output.\n"
            ),
            version="0.1.0",
            summary="A useful release.",
            entries=(),
            used_fallback=False,
        )

    monkeypatch.setattr(cli, "generate_enhanced_changelog_result", generate)

    result = cli.app(
        ["generate", "--repo", str(tmp_path), "--format", "json", "--quiet"]
    )

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert captured_context["contributors"] == ["Jane Doe", "Olivier Neu"]
    assert payload["contributors"] == ["Jane Doe", "Olivier Neu"]


def test_relative_output_is_written_inside_target_repository(tmp_path, monkeypatch):
    _repository(tmp_path)
    _fake_generation(monkeypatch)

    result = cli.app(
        [
            "generate",
            "--repo",
            str(tmp_path),
            "--output",
            "docs/CHANGELOG.md",
            "--ui",
            "plain",
            "--quiet",
        ]
    )

    output = tmp_path / "docs" / "CHANGELOG.md"
    assert result == 0
    assert output.exists()
    assert "## [Unreleased]" in output.read_text(encoding="utf-8")
    assert "## [0.1.0]" in output.read_text(encoding="utf-8")


def test_check_does_not_create_output(tmp_path, monkeypatch):
    _repository(tmp_path)
    _fake_generation(monkeypatch)

    result = cli.app(["generate", "--repo", str(tmp_path), "--check", "--quiet"])

    assert result == 0
    assert not (tmp_path / "CHANGELOG.md").exists()


def test_invalid_ref_fails_before_provider_resolution(tmp_path, monkeypatch):
    _repository(tmp_path)

    def unexpected(*args, **kwargs):
        raise AssertionError("provider resolution must not run for an invalid range")

    monkeypatch.setattr(cli, "resolve_provider_configuration", unexpected)

    assert (
        cli.app(
            [
                "generate",
                "--repo",
                str(tmp_path),
                "--since",
                "missing-ref",
                "--quiet",
            ]
        )
        == 1
    )


def test_provider_override_does_not_reuse_other_provider_model(tmp_path, monkeypatch):
    config_dir = tmp_path / ".gptchangelog"
    config_dir.mkdir()
    (config_dir / "config.ini").write_text(
        "[openai]\nprovider = codex\nprofile = balanced\nmodel = codex-only\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GPTCHANGELOG_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    args = SimpleNamespace(
        provider=None,
        profile=None,
        model=None,
        timeout=10.0,
        max_retries=0,
    )

    settings, profile, model = cli.resolve_provider_configuration(args, tmp_path)

    assert settings.provider == "openai"
    assert profile == "balanced"
    assert model == "gpt-5.6-terra"


def test_cli_profile_overrides_config_model(tmp_path, monkeypatch):
    config_dir = tmp_path / ".gptchangelog"
    config_dir.mkdir()
    (config_dir / "config.ini").write_text(
        "[openai]\nprovider = openai\nprofile = quality\nmodel = custom-quality-model\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    args = SimpleNamespace(
        provider=None,
        profile="balanced",
        model=None,
        timeout=10.0,
        max_retries=0,
    )

    _settings, profile, model = cli.resolve_provider_configuration(args, tmp_path)

    assert profile == "balanced"
    assert model == "gpt-5.6-terra"


def test_app_does_not_mutate_process_arguments(monkeypatch):
    monkeypatch.setattr(cli.sys, "argv", ["gptchangelog", "--help"])
    original = list(cli.sys.argv)
    assert cli._normalized_argv([]) == ["generate"]
    assert cli.sys.argv == original
