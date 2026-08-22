import os

import pytest

from gptchangelog import utils
from gptchangelog.utils import (
    ChangelogValidationError,
    ChangelogWriteError,
    DuplicateReleaseError,
    NonMonotonicReleaseError,
    ReleaseNotFoundError,
    UnsafeChangelogTargetError,
    prepend_changelog_to_file,
    render_prompt,
    resolve_template_path,
    validate_changelog_release,
)

RELEASE = """## [1.2.0] - 2026-08-21

### Added
- Add safe changelog writes.
"""


@pytest.mark.parametrize(
    "content, message",
    [
        ("", "empty"),
        ("```markdown\n## [1.2.0] - 2026-08-21\n```", "code fence"),
        ("## [1.2.0] - 2026-08-21\n\n- Keep $next_version", "placeholder"),
        ("# [1.2.0] - 2026-08-21", "must start"),
        ("## 1.2.0 - 2026-08-21", "must start"),
        ("## [1.2.0] - 2026-02-30", "invalid release date"),
        (
            "## [1.2.0] - 2026-08-21\n\n## [1.2.0] - 2026-08-21",
            "exactly one",
        ),
        (
            "## [1.2.0] - 2026-08-21\n\n## [1.3.0] missing-date",
            "exactly one",
        ),
        ("## [1.2] - 2026-08-21", "canonical SemVer"),
        ("## [release-1.2.0] - 2026-08-21", "canonical SemVer"),
        ("## [01.2.0] - 2026-08-21", "canonical SemVer"),
        ("## [1.2.0-01] - 2026-08-21", "canonical SemVer"),
    ],
)
def test_validate_generated_release_rejects_unsafe_markdown(content, message):
    with pytest.raises(ChangelogValidationError, match=message):
        validate_changelog_release(content)


def test_validate_generated_release_checks_explicit_version():
    assert validate_changelog_release(RELEASE, version="v1.2.0") == "1.2.0"

    with pytest.raises(ChangelogValidationError, match="does not match"):
        validate_changelog_release(RELEASE, version="1.3.0")


def test_validate_generated_release_accepts_semver_variants():
    release = "## [v2.0.0-rc.1+build.9] - 2026-08-21\n"

    assert validate_changelog_release(release) == "v2.0.0-rc.1+build.9"


def test_new_file_gets_keep_a_changelog_preamble_and_unreleased(tmp_path):
    target = tmp_path / "docs" / "CHANGELOG.md"

    result = prepend_changelog_to_file(RELEASE, target)

    assert result.filepath == str(target)
    assert result.version == "1.2.0"
    assert result.changed is True
    assert result.written is True
    assert result.checked is False
    assert result.replaced is False
    assert target.read_text(encoding="utf-8") == result.content
    assert result.content.startswith(
        "# Changelog\n\n"
        "All notable changes to this project will be documented in this file.\n\n"
        "## [Unreleased]\n\n"
        "## [1.2.0] - 2026-08-21\n"
    )


def test_release_is_inserted_after_unreleased_content(tmp_path):
    target = tmp_path / "CHANGELOG.md"
    target.write_text(
        "# Changelog\n\n"
        "Intro that must stay unchanged.\n\n"
        "## [Unreleased]\n\n"
        "### Changed\n"
        "- Pending work.\n\n"
        "## [1.1.0] - 2026-08-01\n\n"
        "- Previous release.\n",
        encoding="utf-8",
    )

    result = prepend_changelog_to_file(RELEASE, target)

    content = target.read_text(encoding="utf-8")
    assert "Intro that must stay unchanged." in content
    assert content.index("- Pending work.") < content.index("## [1.2.0]")
    assert content.index("## [1.2.0]") < content.index("## [1.1.0]")
    assert result.replaced is False


def test_duplicate_version_is_rejected_without_modifying_file(tmp_path):
    target = tmp_path / "CHANGELOG.md"
    original = "# Changelog\n\n## [Unreleased]\n\n" + RELEASE
    target.write_text(original, encoding="utf-8")

    with pytest.raises(DuplicateReleaseError, match="already exists"):
        prepend_changelog_to_file(RELEASE, target)

    assert target.read_text(encoding="utf-8") == original


def test_force_replaces_release_and_is_idempotent(tmp_path):
    target = tmp_path / "CHANGELOG.md"
    target.write_text(
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [v1.2.0] - 2026-08-20\n\n"
        "- Old text.\n\n"
        "## [1.1.0] - 2026-08-01\n\n"
        "- Previous release.\n",
        encoding="utf-8",
    )

    first = prepend_changelog_to_file(RELEASE, target, force=True)
    second = prepend_changelog_to_file(RELEASE, target, force=True)

    content = target.read_text(encoding="utf-8")
    assert first.replaced is True
    assert first.written is True
    assert second.replaced is True
    assert second.changed is False
    assert second.written is False
    assert content.count("## [1.2.0]") == 1
    assert "Old text" not in content
    assert "## [1.1.0]" in content


def test_force_collapses_existing_duplicate_target_sections(tmp_path):
    target = tmp_path / "CHANGELOG.md"
    target.write_text(
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.2.0] - 2026-08-19\n\n- Old one.\n\n"
        "## [1.2.0] - 2026-08-20\n\n- Old two.\n\n"
        "## [1.1.0] - 2026-08-01\n\n- Previous.\n",
        encoding="utf-8",
    )

    prepend_changelog_to_file(RELEASE, target, force=True)

    content = target.read_text(encoding="utf-8")
    assert content.count("## [1.2.0]") == 1
    assert "Old one" not in content
    assert "Old two" not in content
    assert "## [1.1.0]" in content


def test_check_returns_proposed_content_without_writing(tmp_path):
    target = tmp_path / "CHANGELOG.md"

    result = prepend_changelog_to_file(RELEASE, target, check=True)

    assert result.changed is True
    assert result.written is False
    assert result.checked is True
    assert "## [Unreleased]" in result.content
    assert not target.exists()


@pytest.mark.parametrize("check", [False, True])
def test_symlink_target_is_rejected_even_in_check_mode(tmp_path, check):
    real_target = tmp_path / "REAL_CHANGELOG.md"
    original = "# Changelog\n\n## [Unreleased]\n"
    real_target.write_text(original, encoding="utf-8")
    symlink_target = tmp_path / "CHANGELOG.md"
    symlink_target.symlink_to(real_target)

    with pytest.raises(UnsafeChangelogTargetError, match="symlink.*regular file"):
        prepend_changelog_to_file(RELEASE, symlink_target, check=check)

    assert real_target.read_text(encoding="utf-8") == original


def test_broken_symlink_target_is_rejected(tmp_path):
    target = tmp_path / "CHANGELOG.md"
    target.symlink_to(tmp_path / "missing.md")

    with pytest.raises(UnsafeChangelogTargetError, match="symlink"):
        prepend_changelog_to_file(RELEASE, target, check=True)


def test_new_release_must_be_newer_than_all_existing_semver_releases(tmp_path):
    target = tmp_path / "CHANGELOG.md"
    original = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.3.0] - 2026-08-20\n\n- Newer.\n\n"
        "## [1.1.0] - 2026-08-01\n\n- Older.\n"
    )
    target.write_text(original, encoding="utf-8")

    with pytest.raises(NonMonotonicReleaseError, match="newer than.*1.3.0"):
        prepend_changelog_to_file(RELEASE, target)

    assert target.read_text(encoding="utf-8") == original


def test_semver_prerelease_precedence_is_enforced(tmp_path):
    target = tmp_path / "CHANGELOG.md"
    target.write_text(
        "# Changelog\n\n" "## [Unreleased]\n\n" "## [1.2.0-rc.2] - 2026-08-20\n",
        encoding="utf-8",
    )
    older_prerelease = "## [1.2.0-rc.1] - 2026-08-21\n"

    with pytest.raises(NonMonotonicReleaseError):
        prepend_changelog_to_file(older_prerelease, target)

    stable_release = prepend_changelog_to_file(RELEASE, target)
    assert stable_release.written is True


@pytest.mark.parametrize("existing", [False, True])
def test_force_requires_target_version_to_already_exist(tmp_path, existing):
    target = tmp_path / "CHANGELOG.md"
    if existing:
        target.write_text(
            "# Changelog\n\n## [Unreleased]\n\n## [1.1.0] - 2026-08-01\n",
            encoding="utf-8",
        )

    with pytest.raises(ReleaseNotFoundError, match="force-replace.*does not exist"):
        prepend_changelog_to_file(RELEASE, target, force=True)

    if not existing:
        assert not target.exists()


def test_atomic_replace_failure_preserves_original(tmp_path, monkeypatch):
    target = tmp_path / "CHANGELOG.md"
    original = "# Changelog\n\n## [Unreleased]\n"
    target.write_text(original, encoding="utf-8")

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(utils.os, "replace", fail_replace)

    with pytest.raises(ChangelogWriteError, match="simulated replace failure"):
        prepend_changelog_to_file(RELEASE, target)

    assert target.read_text(encoding="utf-8") == original
    assert list(tmp_path.glob(".CHANGELOG.md.*.tmp")) == []


def test_atomic_replace_preserves_existing_permissions(tmp_path):
    target = tmp_path / "CHANGELOG.md"
    target.write_text("# Changelog\n\n## [Unreleased]\n", encoding="utf-8")
    target.chmod(0o640)

    prepend_changelog_to_file(RELEASE, target)

    assert os.stat(target).st_mode & 0o777 == 0o640


def test_existing_file_without_changelog_header_is_rejected(tmp_path):
    target = tmp_path / "CHANGELOG.md"
    original = "Release notes\n"
    target.write_text(original, encoding="utf-8")

    with pytest.raises(ChangelogValidationError, match="# Changelog"):
        prepend_changelog_to_file(RELEASE, target)

    assert target.read_text(encoding="utf-8") == original


def test_release_is_prepended_to_headerless_release_history(tmp_path):
    target = tmp_path / "CHANGELOG.md"
    original = "## [1.1.0] - 2026-08-01\n\n- Previous release.\n"
    target.write_text(original, encoding="utf-8")

    result = prepend_changelog_to_file(RELEASE, target)

    assert result.written is True
    assert result.content.startswith("## [1.2.0] - 2026-08-21\n")
    assert not result.content.startswith("\n")
    assert result.content.count("## [1.2.0]") == 1
    assert result.content.endswith(original)


def test_prompt_helpers_use_explicit_project_root(tmp_path, monkeypatch):
    project = tmp_path / "project"
    template_dir = project / ".gptchangelog" / "templates"
    template_dir.mkdir(parents=True)
    (template_dir / "enhanced_demo.txt").write_text("Hello $name", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    path = resolve_template_path("demo", project_root=project)

    assert path == "templates/enhanced_demo.txt"
    assert render_prompt(path, {"name": "Ada"}, project_root=project) == "Hello Ada"


def test_prompt_helpers_accept_explicit_template_root(tmp_path):
    template_dir = tmp_path / "custom-templates"
    template_dir.mkdir()
    (template_dir / "enhanced_demo.txt").write_text("Hi $name", encoding="utf-8")

    path = resolve_template_path("demo", template_root=template_dir)

    assert path == "templates/enhanced_demo.txt"
    assert render_prompt(path, {"name": "Lin"}, template_root=template_dir) == "Hi Lin"
