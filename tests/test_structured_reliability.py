"""Regression coverage for complete structured changelog source assignments."""

from datetime import datetime, timezone

import pytest

from gptchangelog import enhanced_openai_utils, openai_client
from gptchangelog.enhanced_git_utils import CommitInfo
from gptchangelog.enhanced_openai_utils import (
    ChangelogValidationError,
    EnhancedChangelogGenerator,
    generate_enhanced_changelog_and_version,
    generate_enhanced_changelog_result,
)


def _commit(commit_id: str, message: str, commit_type: str) -> CommitInfo:
    return CommitInfo(
        hash=commit_id,
        message=message,
        author="Test User",
        date=datetime.now(timezone.utc),
        files_changed=["src/example.py"],
        insertions=1,
        deletions=0,
        commit_type=commit_type,
        scope=None,
        is_breaking=False,
        issue_refs=[],
        components={"backend"},
    )


def _stats(commits):
    return {
        "by_type": {commit.commit_type: 1 for commit in commits},
        "breaking_changes": 0,
        "total_files_changed": len(commits),
        "total_insertions": len(commits),
        "total_deletions": 0,
        "most_changed_components": [("backend", len(commits))],
        "date_range": (commits[-1].date, commits[0].date),
    }


def _assignment_payload(assignments, topic_descriptions):
    return {
        "summary": "A concise release summary.",
        "assignments": assignments,
        "topic_descriptions": topic_descriptions,
    }


def _two_assignments():
    return {
        "feat001": {"category": "feat", "topic": "topic_1"},
        "fix0001": {"category": "fix", "topic": "topic_1"},
    }


def _two_topic_descriptions():
    return {
        "feat": {"topic_1": "Adds a useful feature"},
        "fix": {"topic_1": "Fixes an edge case"},
    }


def test_schema_requires_an_assignment_property_for_every_source_id():
    commits = [
        _commit("feat001", "feat: add capability", "feat"),
        _commit("fix0001", "fix: repair edge case", "fix"),
    ]
    schema = enhanced_openai_utils._release_schema(commits)
    assignments = schema["properties"]["assignments"]

    assert schema["required"] == ["summary", "assignments", "topic_descriptions"]
    assert assignments["additionalProperties"] is False
    assert assignments["required"] == ["feat001", "fix0001"]
    assert set(assignments["properties"]) == {"feat001", "fix0001"}
    assert assignments["properties"]["feat001"]["properties"]["category"]["enum"] == [
        "feat"
    ]
    assert assignments["properties"]["fix0001"]["properties"]["category"]["enum"] == [
        "fix"
    ]


def test_schema_bounds_topic_slots_without_allowing_commit_omission():
    commits = [
        _commit(f"feat{index:03d}", f"feat: capability {index}", "feat")
        for index in range(25)
    ]

    schema = enhanced_openai_utils._release_schema(commits)
    assignments = schema["properties"]["assignments"]
    topic_schema = assignments["properties"]["feat000"]["properties"]["topic"]

    assert len(assignments["required"]) == 25
    assert topic_schema["enum"] == [f"topic_{index}" for index in range(1, 13)]


def test_assignment_contract_rejects_terra_like_cross_category_output():
    commits = [
        _commit("feat001", "feat: add capability", "feat"),
        _commit("fix0001", "fix: repair edge case", "fix"),
    ]
    assignments = _two_assignments()
    assignments["fix0001"]["category"] = "feat"

    with pytest.raises(ChangelogValidationError, match="expected 'fix'"):
        enhanced_openai_utils._validated_payload(
            _assignment_payload(assignments, _two_topic_descriptions()), commits
        )


@pytest.mark.parametrize(
    ("assignments", "message"),
    [
        (
            {
                "feat001": {"category": "feat", "topic": "topic_1"},
                "unknown": {"category": "fix", "topic": "topic_1"},
            },
            "unknown commit IDs",
        ),
        ({"feat001": {"category": "feat", "topic": "topic_1"}}, "omitted commit IDs"),
    ],
)
def test_assignment_contract_rejects_unknown_and_missing_source_ids(
    assignments, message
):
    commits = [
        _commit("feat001", "feat: add capability", "feat"),
        _commit("fix0001", "fix: repair edge case", "fix"),
    ]

    with pytest.raises(ChangelogValidationError, match=message):
        enhanced_openai_utils._validated_payload(
            _assignment_payload(assignments, _two_topic_descriptions()), commits
        )


def test_assignments_group_same_category_topic_with_one_shared_description():
    commits = [
        _commit("feat001", "feat: add capability", "feat"),
        _commit("feat002", "feat: improve capability", "feat"),
        _commit("fix0001", "fix: repair edge case", "fix"),
    ]
    assignments = _two_assignments()
    assignments["feat002"] = {"category": "feat", "topic": "topic_1"}

    _summary, entries = enhanced_openai_utils._validated_payload(
        _assignment_payload(assignments, _two_topic_descriptions()), commits
    )

    assert entries[0] == {
        "category": "feat",
        "description": "Adds a useful feature",
        "commit_ids": ["feat001", "feat002"],
    }
    assert entries[1]["commit_ids"] == ["fix0001"]


def test_structured_request_and_rich_result_preserve_provenance(monkeypatch):
    commits = [
        _commit("feat001", "feat: add capability", "feat"),
        _commit("fix0001", "fix: repair edge case", "fix"),
    ]
    calls = []

    def structured_response(**kwargs):
        calls.append(kwargs)
        return _assignment_payload(_two_assignments(), _two_topic_descriptions())

    monkeypatch.setattr(
        openai_client, "create_structured_response", structured_response
    )

    result = generate_enhanced_changelog_result(
        commits,
        "1.2.3",
        "example",
        _stats(commits),
        extra_context={"current_date": "2026-08-21"},
    )

    assert len(calls) == 1
    assignments = calls[0]["json_schema"]["properties"]["assignments"]
    assert assignments["required"] == ["feat001", "fix0001"]
    assert '"category_partitions"' in calls[0]["prompt"]
    assert '"topic_slot_limits"' in calls[0]["prompt"]
    assert result.version == "1.3.0"
    assert result.summary == "A concise release summary."
    assert result.used_fallback is False
    assert result.entries[0].commit_ids == ("feat001",)
    assert result.entries[0].as_dict()["commit_ids"] == ["feat001"]


def test_tuple_api_remains_compatible_with_legacy_entry_payload(monkeypatch):
    commits = [_commit("feat001", "feat: add capability", "feat")]
    monkeypatch.setattr(
        openai_client,
        "create_structured_response",
        lambda **_kwargs: {
            "summary": "A concise release summary.",
            "entries": [
                {"description": "Adds a useful feature", "commit_ids": ["feat001"]}
            ],
        },
    )

    changelog, version = generate_enhanced_changelog_and_version(
        commits, "1.2.3", "example", _stats(commits)
    )

    assert version == "1.3.0"
    assert "Adds a useful feature" in changelog


def test_provider_error_remains_fail_closed(monkeypatch):
    commits = [_commit("feat001", "feat: add capability", "feat")]
    monkeypatch.setattr(
        openai_client,
        "create_structured_response",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("provider unavailable")),
    )

    with pytest.raises(RuntimeError, match="provider unavailable"):
        EnhancedChangelogGenerator().generate_enhanced_changelog_result(
            commits, "1.3.0", {"current_date": "2026-08-21"}
        )
