import json
import logging
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ChangelogError(Exception):
    """Base class for changelog validation and persistence failures."""


class ChangelogValidationError(ChangelogError):
    """Raised when generated or existing changelog content is unsafe to use."""


class DuplicateReleaseError(ChangelogValidationError):
    """Raised when the target release already exists and replacement is disabled."""


class ReleaseNotFoundError(ChangelogValidationError):
    """Raised when forced replacement targets a release that does not exist."""


class NonMonotonicReleaseError(ChangelogValidationError):
    """Raised when a new release would regress semantic-version ordering."""


class ChangelogWriteError(ChangelogError):
    """Raised when a changelog cannot be read or atomically persisted."""


class UnsafeChangelogTargetError(ChangelogWriteError):
    """Raised when the changelog target is unsafe for direct replacement."""


@dataclass(frozen=True)
class ChangelogWriteResult:
    """Outcome of preparing or writing a changelog release."""

    filepath: str
    version: str
    content: str
    changed: bool
    written: bool
    checked: bool
    replaced: bool


_RELEASE_HEADER_RE = re.compile(
    r"^## \[([^\]\s]+)\] - (\d{4}-\d{2}-\d{2})[ \t]*$", re.MULTILINE
)
_LEVEL_TWO_HEADER_RE = re.compile(r"^##[ \t]+.+$", re.MULTILINE)
_BRACKETED_LEVEL_TWO_HEADER_RE = re.compile(r"^##[ \t]+\[[^\]\r\n]+\].*$", re.MULTILINE)
_UNRELEASED_HEADER_RE = re.compile(
    r"^##[ \t]+\[Unreleased\](?:[ \t]+-[ \t]+\d{4}-\d{2}-\d{2})?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
_PLACEHOLDER_RE = re.compile(
    r"(?<!\\)\$(?:\{[A-Za-z_][A-Za-z0-9_]*\}|[A-Za-z_][A-Za-z0-9_]*)"
)
_CODE_FENCE_RE = re.compile(r"^[ \t]*(?:`{3,}|~{3,})", re.MULTILINE)
_CHANGELOG_HEADER_RE = re.compile(r"\A(?:\ufeff)?# Changelog[ \t]*(?:\r?\n|\Z)")
_SEMVER_RE = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)

SemVer = tuple[int, int, int, Optional[tuple[str, ...]]]


def _canonical_version(version_value: str) -> str:
    """Normalize the optional conventional ``v`` prefix for comparisons."""
    stripped = version_value.strip()
    return stripped[1:] if stripped.startswith("v") else stripped


def _parse_semver(version_value: str) -> Optional[SemVer]:
    match = _SEMVER_RE.fullmatch(version_value)
    if match is None:
        return None

    major, minor, patch, prerelease, _build = match.groups()
    prerelease_identifiers = tuple(prerelease.split(".")) if prerelease else None
    if prerelease_identifiers and any(
        identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0")
        for identifier in prerelease_identifiers
    ):
        return None

    return int(major), int(minor), int(patch), prerelease_identifiers


def _compare_semver(left: SemVer, right: SemVer) -> int:
    """Compare SemVer precedence, intentionally ignoring build metadata."""
    left_core = left[:3]
    right_core = right[:3]
    if left_core != right_core:
        return 1 if left_core > right_core else -1

    left_prerelease = left[3]
    right_prerelease = right[3]
    if left_prerelease is None or right_prerelease is None:
        if left_prerelease is right_prerelease:
            return 0
        return 1 if left_prerelease is None else -1

    for left_identifier, right_identifier in zip(left_prerelease, right_prerelease):
        if left_identifier == right_identifier:
            continue
        left_numeric = left_identifier.isdigit()
        right_numeric = right_identifier.isdigit()
        if left_numeric and right_numeric:
            return 1 if int(left_identifier) > int(right_identifier) else -1
        if left_numeric != right_numeric:
            return -1 if left_numeric else 1
        return 1 if left_identifier > right_identifier else -1

    if len(left_prerelease) == len(right_prerelease):
        return 0
    return 1 if len(left_prerelease) > len(right_prerelease) else -1


def validate_changelog_release(changelog: str, *, version: Optional[str] = None) -> str:
    """Validate one generated release and return the version in its heading.

    Generated content must start with exactly one Keep a Changelog release
    heading. Markdown fences and unresolved ``string.Template`` placeholders
    are rejected before any file operation occurs.
    """
    if not isinstance(changelog, str) or not changelog.strip():
        raise ChangelogValidationError("Generated changelog is empty.")

    if _CODE_FENCE_RE.search(changelog):
        raise ChangelogValidationError(
            "Generated changelog contains a Markdown code fence."
        )

    placeholder = _PLACEHOLDER_RE.search(changelog)
    if placeholder:
        raise ChangelogValidationError(
            f"Generated changelog contains unresolved placeholder: {placeholder.group(0)}"
        )

    normalized = changelog.lstrip("\ufeff\r\n")
    first_line = normalized.splitlines()[0]
    first_header = _RELEASE_HEADER_RE.fullmatch(first_line)
    if first_header is None:
        raise ChangelogValidationError(
            "Generated changelog must start with '## [VERSION] - YYYY-MM-DD'."
        )

    release_headers = list(_BRACKETED_LEVEL_TWO_HEADER_RE.finditer(normalized))
    if len(release_headers) != 1:
        raise ChangelogValidationError(
            "Generated changelog must contain exactly one release heading."
        )

    generated_version, release_date = first_header.groups()
    if _parse_semver(generated_version) is None:
        raise ChangelogValidationError(
            "Generated release heading must use canonical SemVer, optionally "
            "prefixed with 'v' (for example, [v1.2.3] or [1.2.3-rc.1])."
        )

    try:
        date.fromisoformat(release_date)
    except ValueError as exc:
        raise ChangelogValidationError(
            f"Generated changelog has an invalid release date: {release_date}"
        ) from exc

    if version is not None and _canonical_version(version) != _canonical_version(
        generated_version
    ):
        raise ChangelogValidationError(
            f"Generated release version {generated_version!r} does not match "
            f"target version {version!r}."
        )

    return generated_version


def _section_end(content: str, heading_end: int) -> int:
    next_heading = _LEVEL_TWO_HEADER_RE.search(content, heading_end)
    return next_heading.start() if next_heading else len(content)


def _release_matches(content: str, target_version: str) -> List[re.Match[str]]:
    canonical_target = _canonical_version(target_version)
    return [
        match
        for match in _RELEASE_HEADER_RE.finditer(content)
        if _canonical_version(match.group(1)) == canonical_target
    ]


def _highest_existing_semver(content: str) -> Optional[tuple[str, SemVer]]:
    highest: Optional[tuple[str, SemVer]] = None
    for match in _RELEASE_HEADER_RE.finditer(content):
        parsed = _parse_semver(match.group(1))
        if parsed is not None and (
            highest is None or _compare_semver(parsed, highest[1]) > 0
        ):
            highest = match.group(1), parsed
    return highest


def _normalize_release(changelog: str) -> str:
    return changelog.lstrip("\ufeff\r\n").rstrip() + "\n"


def _build_changelog_content(
    original: Optional[str],
    release: str,
    target_version: str,
    *,
    force: bool,
) -> tuple[str, bool]:
    """Build final content and report whether an existing release was replaced."""
    if original is None:
        if force:
            raise ReleaseNotFoundError(
                f"Cannot force-replace release {target_version!r}: the changelog "
                "does not exist yet. Run without force to create it."
            )
        return (
            "# Changelog\n\n"
            "All notable changes to this project will be documented in this file.\n\n"
            "## [Unreleased]\n\n"
            f"{release}",
            False,
        )

    if not _CHANGELOG_HEADER_RE.match(original):
        raise ChangelogValidationError(
            "Existing changelog must start with a '# Changelog' header."
        )

    matches = _release_matches(original, target_version)
    if matches and not force:
        raise DuplicateReleaseError(
            f"Release {target_version!r} already exists in the changelog. "
            "Use force=True to replace it."
        )

    if matches:
        # Collapse pre-existing duplicates of the target version while replacing
        # the first occurrence. This makes a forced write idempotent and repairs
        # files created by the former prepend-only implementation.
        rebuilt = original
        spans = [
            (match.start(), _section_end(original, match.end())) for match in matches
        ]
        for start, end in reversed(spans[1:]):
            rebuilt = rebuilt[:start] + rebuilt[end:]

        first_start, first_end = spans[0]
        # Removed later spans do not affect the first span offsets.
        tail = rebuilt[first_end:].lstrip("\r\n")
        rebuilt = rebuilt[:first_start] + release
        if tail:
            rebuilt += f"\n{tail}"
        return rebuilt, True

    if force:
        raise ReleaseNotFoundError(
            f"Cannot force-replace release {target_version!r}: that version does "
            "not exist in the changelog. Run without force to add a newer release."
        )

    target_semver = _parse_semver(target_version)
    if target_semver is None:  # The generated release was validated before this call.
        raise ChangelogValidationError(
            f"Target version {target_version!r} is not canonical SemVer."
        )
    highest = _highest_existing_semver(original)
    if highest is not None and _compare_semver(target_semver, highest[1]) <= 0:
        raise NonMonotonicReleaseError(
            f"Release {target_version!r} must be newer than existing release "
            f"{highest[0]!r}; refusing to insert a version regression."
        )

    unreleased = _UNRELEASED_HEADER_RE.search(original)
    if unreleased:
        insertion_point = _section_end(original, unreleased.end())
    else:
        first_level_two = _LEVEL_TWO_HEADER_RE.search(original)
        insertion_point = first_level_two.start() if first_level_two else len(original)

    before = original[:insertion_point].rstrip()
    after = original[insertion_point:].lstrip("\r\n")
    rebuilt = f"{before}\n\n{release}"
    if after:
        rebuilt += f"\n{after}"
    return rebuilt, False


def _atomic_write_text(filepath: Path, content: str) -> None:
    """Atomically replace ``filepath`` while leaving the original on failure."""
    temporary_path: Optional[str] = None
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        existing_mode = (
            stat.S_IMODE(filepath.stat().st_mode) if filepath.exists() else None
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=filepath.parent,
            prefix=f".{filepath.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        if existing_mode is not None:
            os.chmod(temporary_path, existing_mode)
        os.replace(temporary_path, filepath)
        temporary_path = None
    except OSError as exc:
        raise ChangelogWriteError(
            f"Could not atomically write changelog {filepath}: {exc}"
        ) from exc
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            except OSError:
                logger.warning(
                    "Could not remove temporary changelog file %s", temporary_path
                )


def get_package_version():
    """Get the package version from importlib.metadata or fallback to version file."""
    try:
        return version("gptchangelog")
    except PackageNotFoundError:
        # Fallback to reading from the package's __init__.py
        script_dir = os.path.dirname(os.path.abspath(__file__))
        init_file = os.path.join(script_dir, "__init__.py")

        if os.path.exists(init_file):
            with open(init_file, "r") as f:
                content = f.read()
                version_match = re.search(
                    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]', content
                )
                if version_match:
                    return version_match.group(1)

        return "0.1.0"  # Default fallback version


def render_prompt(
    template_path,
    context,
    *,
    project_root: Optional[Union[str, os.PathLike[str]]] = None,
    template_root: Optional[Union[str, os.PathLike[str]]] = None,
):
    """
    Render a prompt template with the provided context.

    Args:
        template_path: Path to the template file, relative to the package directory
        context: Dictionary of values to substitute in the template

    Returns:
        The rendered prompt string
    """
    # Check if an environment variable override is provided
    env_template_path = os.environ.get("GPTCHANGELOG_TEMPLATE_PATH")
    if env_template_path:
        full_template_path = Path(env_template_path)
    else:
        # First, check for a project-specific template.
        resolved_project_root = (
            Path(project_root) if project_root is not None else Path.cwd()
        )
        resolved_template_root = (
            Path(template_root)
            if template_root is not None
            else resolved_project_root / ".gptchangelog" / "templates"
        )
        project_template = resolved_template_root / Path(template_path).name

        # Next, check for a package template.
        package_template = Path(__file__).resolve().parent / template_path

        if project_template.exists():
            full_template_path = project_template
        else:
            full_template_path = package_template

    try:
        with open(full_template_path, "r") as template_file:
            template_content = template_file.read()

        template = Template(template_content)
        return template.safe_substitute(context)
    except FileNotFoundError:
        logger.error(f"Template file not found: {template_path}")
        # Create a simple fallback template based on the context
        fallback = f"Context:\n"
        for key, value in context.items():
            if key == "commit_messages":
                fallback += f"\nCommit Messages:\n{value}\n"
            else:
                fallback += f"\n{key}: {value}"

        return fallback


def resolve_template_path(
    base_name: str,
    language: Optional[str] = "en",
    enhanced: bool = True,
    *,
    project_root: Optional[Union[str, os.PathLike[str]]] = None,
    template_root: Optional[Union[str, os.PathLike[str]]] = None,
) -> str:
    """
    Resolve a template path with i18n and enhanced fallbacks.

    Args:
        base_name: Base template name without prefixes/suffixes (e.g., "changelog_prompt", "commits_prompt", "version_prompt")
        language: ISO language code (e.g., "en", "fr", "es")
        enhanced: If True, prefers enhanced template variants

    Returns:
        Relative template path to use with render_prompt (e.g., "templates/enhanced_changelog_prompt.txt")
    """
    lang = (language or "en").lower()

    # Build candidate relative paths in priority order
    candidates: List[str] = []

    if enhanced:
        if lang != "en":
            candidates.append(f"templates/{lang}_enhanced_{base_name}.txt")
            candidates.append(
                f"templates/{lang}_{base_name}.txt"
            )  # fallback to non-enhanced localized
        candidates.append(f"templates/enhanced_{base_name}.txt")
    else:
        if lang != "en":
            candidates.append(f"templates/{lang}_{base_name}.txt")
        candidates.append(f"templates/{base_name}.txt")

    # Check existence in project and package locations
    resolved_project_root = (
        Path(project_root) if project_root is not None else Path.cwd()
    )
    project_templates_dir = (
        Path(template_root)
        if template_root is not None
        else resolved_project_root / ".gptchangelog" / "templates"
    )
    package_dir = Path(__file__).resolve().parent

    for rel_path in candidates:
        project_candidate = project_templates_dir / Path(rel_path).name
        package_candidate = package_dir / rel_path
        if project_candidate.exists() or package_candidate.exists():
            return rel_path

    # Final fallback to English defaults
    return (
        f"templates/enhanced_{base_name}.txt"
        if enhanced
        else f"templates/{base_name}.txt"
    )


def prepend_changelog_to_file(
    changelog: str,
    filepath: Union[str, os.PathLike[str]] = "CHANGELOG.md",
    *,
    version: Optional[str] = None,
    check: bool = False,
    force: bool = False,
) -> ChangelogWriteResult:
    """Safely insert or replace one generated changelog release.

    ``check=True`` performs validation and returns the proposed full file content
    without writing. Existing versions are rejected unless ``force=True``; a
    forced operation replaces the existing section instead of duplicating it.
    All validation, read, and write failures propagate as :class:`ChangelogError`
    subclasses so callers cannot mistakenly report success.
    """
    target_version = validate_changelog_release(changelog, version=version)
    release = _normalize_release(changelog)
    target = Path(filepath)

    if target.is_symlink():
        raise UnsafeChangelogTargetError(
            f"Refusing to use symlink changelog target {target}. Choose a regular "
            "file path so validation and atomic replacement address the same file."
        )

    try:
        original = target.read_text(encoding="utf-8") if target.exists() else None
    except (OSError, UnicodeError) as exc:
        raise ChangelogWriteError(f"Could not read changelog {target}: {exc}") from exc

    content, replaced = _build_changelog_content(
        original, release, target_version, force=force
    )
    changed = original != content
    written = False
    if not check and changed:
        _atomic_write_text(target, content)
        written = True

    return ChangelogWriteResult(
        filepath=str(target),
        version=target_version,
        content=content,
        changed=changed,
        written=written,
        checked=check,
        replaced=replaced,
    )


def get_project_metadata():
    """
    Get metadata about the current project from package files.

    Returns:
        Dictionary with project metadata
    """
    metadata = {
        "name": "",
        "version": get_package_version(),
        "description": "",
    }

    # Try to get from setup.py, pyproject.toml, or package.json
    cwd = os.getcwd()

    # Check for package.json (Node.js projects)
    package_json = os.path.join(cwd, "package.json")
    if os.path.exists(package_json):
        try:
            with open(package_json, "r") as f:
                pkg_data = json.load(f)
                metadata["name"] = pkg_data.get("name", "")
                metadata["version"] = pkg_data.get("version", metadata["version"])
                metadata["description"] = pkg_data.get("description", "")
        except Exception:
            pass

    # Check for pyproject.toml (modern Python projects)
    pyproject_toml = os.path.join(cwd, "pyproject.toml")
    if os.path.exists(pyproject_toml) and not metadata["name"]:
        try:
            with open(pyproject_toml, "r") as f:
                content = f.read()
                name_match = re.search(r'name\s*=\s*[\'"]([^\'"]*)[\'"]', content)
                if name_match:
                    metadata["name"] = name_match.group(1)

                # Only override version if we couldn't get it from package_version()
                if metadata["version"] == "0.1.0":
                    version_match = re.search(
                        r'version\s*=\s*[\'"]([^\'"]*)[\'"]', content
                    )
                    if version_match:
                        metadata["version"] = version_match.group(1)

                description_match = re.search(
                    r'description\s*=\s*[\'"]([^\'"]*)[\'"]', content
                )
                if description_match:
                    metadata["description"] = description_match.group(1)
        except Exception:
            pass

    # If all else fails, use the directory name as the project name
    if not metadata["name"]:
        metadata["name"] = os.path.basename(cwd)

    return metadata


def format_commit_for_changelog(commit_message):
    """
    Format a single commit message for inclusion in the changelog.

    Args:
        commit_message: The commit message to format

    Returns:
        Formatted commit message suitable for changelog
    """
    # Handle conventional commit format
    match = re.match(r"^(\w+)(\([^)]+\))?(!)?:\s+(.+)$", commit_message)

    if match:
        commit_type, scope, breaking, message = match.groups()
        scope = scope or ""

        # Process the message based on commit type
        if commit_type == "feat":
            prefix = "Added"
        elif commit_type == "fix":
            prefix = "Fixed"
        elif commit_type == "refactor":
            prefix = "Improved"
        elif commit_type == "docs":
            prefix = "Documentation"
        elif commit_type == "style":
            prefix = "Style"
        elif commit_type == "perf":
            prefix = "Performance"
        elif commit_type == "test":
            prefix = "Tests"
        elif commit_type == "chore":
            prefix = "Maintenance"
        else:
            prefix = "Changed"

        # Add scope if present
        if scope:
            return f"{prefix} {scope.strip('()')}: {message}"
        else:
            return f"{prefix}: {message}"

    # Return the original message if it's not in conventional commit format
    return commit_message


def cache_api_response(func):
    """
    Decorator to cache API responses to reduce API calls.

    Args:
        func: The function to cache

    Returns:
        Wrapped function with caching
    """
    cache: Dict[str, Any] = {}

    def wrapper(*args, **kwargs):
        # Create a cache key from the function arguments
        key = str(args) + str(sorted(kwargs.items()))

        if key in cache:
            logger.debug(f"Using cached result for {func.__name__}")
            return cache[key]

        result = func(*args, **kwargs)
        cache[key] = result
        return result

    return wrapper
