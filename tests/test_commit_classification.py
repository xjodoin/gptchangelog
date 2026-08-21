import pytest

from gptchangelog.enhanced_git_utils import EnhancedCommitAnalyzer


@pytest.fixture
def analyzer(tmp_path):
    import git

    git.Repo.init(tmp_path)
    return EnhancedCommitAnalyzer(str(tmp_path))


def test_unreleased_alert_rule_cleanup_is_not_breaking(analyzer):
    message = """fix(alert-rules): restrict questionnaire score to sum-scored questionnaires (TK-2578)

The score_path value kind is removed. The score JSON only ever holds a value
for SUM questionnaires, so the speculative API option had no reachable use
case. Migration 0033 is regenerated rather than superseded, as it has not been
applied anywhere.
"""
    files = [
        "alert_system/docs/ALERT_RULE_API.md",
        "alert_system/migrations/0033_historicalquestionnairescoredatasource.py",
        "alert_system/models.py",
        "alert_system/serializers.py",
    ]

    assert analyzer._detect_breaking_changes(message, files) is False


@pytest.mark.parametrize(
    "message",
    [
        "breaking change: remove legacy behavior",
        "Remove support for an unreleased API option",
        "Drop an unused schema field",
        "docs: explain a non-breaking API change",
        "This is not a breaking change",
        "refactor: make a backward incompatible-looking internal cleanup",
    ],
)
def test_natural_language_and_file_names_do_not_imply_breaking(analyzer, message):
    assert (
        analyzer._detect_breaking_changes(
            message, ["api/schema.py", "contracts/interface.py"]
        )
        is False
    )


@pytest.mark.parametrize(
    "message",
    [
        "feat!: remove the legacy API",
        "feat(auth)!: reject legacy tokens",
        "skip-test - feat(api)!: replace the endpoint",
        "feat: replace authentication\n\nBREAKING CHANGE: old tokens are rejected",
        "fix: replace authentication\n\nBREAKING-CHANGE: old tokens are rejected",
    ],
)
def test_explicit_conventional_breaking_markers_are_honored(analyzer, message):
    assert analyzer._detect_breaking_changes(message, []) is True


@pytest.mark.parametrize(
    ("message", "expected_type", "expected_scope", "expected_subject"),
    [
        (
            "skip-test - fix(migrations): resolve pending triggers before index creation",
            "fix",
            "migrations",
            "resolve pending triggers before index creation",
        ),
        (
            "[skip ci] docs(dexcom): harden the integration spec",
            "docs",
            "dexcom",
            "harden the integration spec",
        ),
        (
            "CI-SKIP: FEAT(api): expose report status",
            "feat",
            "api",
            "expose report status",
        ),
    ],
)
def test_ci_prefixes_are_removed_before_conventional_parsing(
    analyzer, message, expected_type, expected_scope, expected_subject
):
    commit_type, scope, subject, is_breaking = analyzer._parse_conventional_commit(
        message
    )

    assert commit_type == expected_type
    assert scope == expected_scope
    assert subject == expected_subject
    assert is_breaking is False


@pytest.mark.parametrize(
    ("subject", "files", "expected"),
    [
        (
            "Add comprehensive ONCO report question key documentation",
            ["doc/onco_report_question_keys.md", "questionnaire/tests/test_onco.py"],
            "docs",
        ),
        (
            "Add DSQ interoperability documentation outlining detailed tasks",
            ["doc/dsq/01-comprendre-le-dsq.md", "doc/dsq/02-plan.md"],
            "docs",
        ),
        (
            "Add tests for legacy non-mapping input handling and improve serializer input validation",
            ["decision_tree/serializers.py", "decision_tree/tests/test_workflow.py"],
            "test",
        ),
        (
            "Add tests for legacy message handling with media attachments",
            ["assistant/services/chat.py", "assistant/tests/test_chat.py"],
            "test",
        ),
        (
            "Add questionnaire schema validation and integration tests",
            ["questionnaire/schema.py", "questionnaire/tests/test_schema.py"],
            "feat",
        ),
        (
            "Support online meeting cancellations and enhance documentation",
            ["calendar/views.py", "calendar/tests/test_cancellation.py"],
            "feat",
        ),
        (
            "Enhance Mermaid workflow generation and add comprehensive tests",
            ["questionnaire/mermaid.py", "questionnaire/tests/test_mermaid.py"],
            "feat",
        ),
    ],
)
def test_greybox_subjects_use_documented_or_tested_artifact_as_primary_signal(
    analyzer, subject, files, expected
):
    assert analyzer._infer_commit_type(subject, files) == expected


def test_file_evidence_requires_all_files_to_match(analyzer):
    assert analyzer._infer_commit_type("Revise prose", ["docs/guide.md"]) == "docs"
    assert analyzer._infer_commit_type("Exercise edge case", ["tests/test_api.py"]) == (
        "test"
    )
    assert (
        analyzer._infer_commit_type(
            "Enable schema workflow",
            ["schema/workflow.py", "tests/test_workflow.py"],
        )
        == "feat"
    )
