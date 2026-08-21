import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import gptchangelog.openai_client as provider_module
from gptchangelog.openai_client import (
    BALANCED_MODEL,
    CODEX_PROVIDER,
    OPENAI_PROVIDER,
    QUALITY_MODEL,
    ProviderConfigurationError,
    ProviderError,
    ProviderSettings,
    StructuredResponseError,
    codex_login_status,
    configure_provider,
    create_structured_response,
    get_default_model,
    get_profile_model,
    has_codex_auth,
    normalize_provider,
    resolve_model,
)


@pytest.fixture(autouse=True)
def reset_provider():
    configure_provider(ProviderSettings(provider=OPENAI_PROVIDER, api_key="test"))
    yield
    configure_provider(ProviderSettings(provider=OPENAI_PROVIDER, api_key="test"))


def test_model_profiles_use_requested_terra_and_sol_models():
    assert get_default_model(OPENAI_PROVIDER) == BALANCED_MODEL == "gpt-5.6-terra"
    assert get_default_model(CODEX_PROVIDER) == BALANCED_MODEL
    assert get_profile_model(OPENAI_PROVIDER, "quality") == QUALITY_MODEL
    assert QUALITY_MODEL == "gpt-5.6-sol"


def test_explicit_model_takes_precedence_over_profile():
    assert (
        resolve_model(OPENAI_PROVIDER, profile="quality", model="custom-model")
        == "custom-model"
    )


@pytest.mark.parametrize("value", ["azure", "", "unknown"])
def test_normalize_provider_rejects_unknown_values(value):
    with pytest.raises(ProviderConfigurationError, match="Unsupported provider"):
        normalize_provider(value)


def test_structured_openai_response_uses_strict_responses_schema(monkeypatch):
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(output_text='{"summary":"Safe release"}')

    fake_client = SimpleNamespace(responses=FakeResponses())
    monkeypatch.setattr(
        provider_module, "_openai_client_for", lambda settings: fake_client
    )

    schema = {
        "title": "Release Notes",
        "type": "object",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
        "additionalProperties": False,
    }
    result = create_structured_response(
        "gpt-5.6-terra", "Summarize", "commit data", schema, reasoning="medium"
    )

    assert result == {"summary": "Safe release"}
    assert calls == [
        {
            "model": "gpt-5.6-terra",
            "instructions": "Summarize",
            "input": "commit data",
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "Release_Notes",
                    "schema": schema,
                    "strict": True,
                }
            },
            "reasoning": {"effort": "medium"},
        }
    ]


def test_structured_response_rejects_non_object_json(monkeypatch):
    monkeypatch.setattr(
        provider_module,
        "_create_codex_response",
        lambda **kwargs: '["not", "an", "object"]',
    )
    configure_provider(ProviderSettings(provider=CODEX_PROVIDER))

    with pytest.raises(StructuredResponseError, match="must be an object"):
        create_structured_response(
            "gpt-5.6-terra", "instructions", "prompt", {"type": "object"}
        )


def test_codex_structured_response_uses_cli_output_schema(monkeypatch):
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["prompt"] = kwargs["input"]
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text('{"summary":"Codex release"}', encoding="utf-8")
        schema_path = Path(command[command.index("--output-schema") + 1])
        observed["schema"] = json.loads(schema_path.read_text(encoding="utf-8"))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(provider_module.subprocess, "run", fake_run)
    configure_provider(
        ProviderSettings(
            provider=CODEX_PROVIDER,
            max_retries=0,
            codex_executable="codex-test",
        )
    )
    schema = {"type": "object", "properties": {"summary": {"type": "string"}}}

    result = create_structured_response(
        "gpt-5.6-sol", "Write release notes", "commit data", schema
    )

    assert result == {"summary": "Codex release"}
    assert observed["command"][:2] == ["codex-test", "exec"]
    assert "--ephemeral" in observed["command"]
    assert ["--sandbox", "read-only"] == observed["command"][
        observed["command"].index("--sandbox") : observed["command"].index("--sandbox")
        + 2
    ]
    assert observed["schema"] == schema
    assert "Write release notes" in observed["prompt"]
    assert "commit data" in observed["prompt"]


def test_codex_failure_propagates_without_retry_for_auth_error(monkeypatch):
    attempts = []

    def fake_run(command, **kwargs):
        attempts.append(command)
        return subprocess.CompletedProcess(command, 1, "", "not logged in")

    monkeypatch.setattr(provider_module.subprocess, "run", fake_run)
    configure_provider(ProviderSettings(provider=CODEX_PROVIDER, max_retries=3))

    with pytest.raises(ProviderError, match="not logged in"):
        provider_module.create_text_response("gpt-5.6-terra", "Do", "work")
    assert len(attempts) == 1


def test_has_codex_auth_uses_login_status_command(monkeypatch):
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["env"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, "Logged in using ChatGPT", "")

    monkeypatch.setattr(provider_module.subprocess, "run", fake_run)

    assert has_codex_auth({"CODEX_HOME": "/secure/codex"}) is True
    assert observed["command"] == ["codex", "login", "status"]
    assert observed["env"]["CODEX_HOME"] == "/secure/codex"


def test_codex_login_status_handles_missing_cli(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(provider_module.subprocess, "run", missing)

    result = codex_login_status()

    assert result.ok is False
    assert "not installed" in result.message
