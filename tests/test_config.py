import configparser
import os
import stat

import pytest

import gptchangelog.config as config_module
from gptchangelog.config import _write_config_secure, init_config, load_openai_config
from gptchangelog.openai_client import (
    ProviderConfigurationError,
    get_default_model,
)


def _write_project_config(project_dir, lines):
    config_dir = project_dir / ".gptchangelog"
    config_dir.mkdir(parents=True)
    (config_dir / "config.ini").write_text("\n".join(lines), encoding="utf-8")


def test_load_openai_config_reads_backward_compatible_explicit_model(
    tmp_path, monkeypatch
):
    project_dir = tmp_path / "repo"
    _write_project_config(
        project_dir,
        ["[openai]", "provider = codex", "model = legacy-custom-model"],
    )
    monkeypatch.chdir(project_dir)

    config = load_openai_config()

    assert config == {
        "provider": "codex",
        "profile": "balanced",
        "api_key": None,
        "model": "legacy-custom-model",
    }


def test_load_openai_config_resolves_quality_profile(tmp_path, monkeypatch):
    project_dir = tmp_path / "repo"
    _write_project_config(
        project_dir,
        ["[openai]", "provider = openai", "profile = quality"],
    )
    monkeypatch.chdir(project_dir)

    config = load_openai_config()

    assert config["profile"] == "quality"
    assert config["model"] == "gpt-5.6-sol"


def test_load_openai_config_uses_explicit_project_root(tmp_path, monkeypatch):
    project_dir = tmp_path / "repo"
    unrelated_dir = tmp_path / "elsewhere"
    unrelated_dir.mkdir()
    _write_project_config(
        project_dir,
        ["[openai]", "provider = codex", "profile = quality"],
    )
    monkeypatch.chdir(unrelated_dir)

    config = load_openai_config(project_root=project_dir)

    assert config["provider"] == "codex"
    assert config["model"] == "gpt-5.6-sol"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits required")
def test_load_openai_config_rejects_insecure_stored_api_key(tmp_path, monkeypatch):
    project_dir = tmp_path / "repo"
    _write_project_config(
        project_dir,
        ["[openai]", "provider = openai", "api_key = secret-value"],
    )
    config_path = project_dir / ".gptchangelog" / "config.ini"
    config_path.chmod(0o644)
    monkeypatch.chdir(project_dir)

    with pytest.raises(ProviderConfigurationError) as error:
        load_openai_config()

    assert "permissions 0644" in str(error.value)
    assert f"chmod 600 {config_path}" in str(error.value)
    assert "secret-value" not in str(error.value)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits required")
def test_metadata_only_load_ignores_unrelated_insecure_api_key(tmp_path, monkeypatch):
    project_dir = tmp_path / "repo"
    _write_project_config(
        project_dir,
        ["[openai]", "provider = openai", "api_key = secret-value"],
    )
    config_path = project_dir / ".gptchangelog" / "config.ini"
    config_path.chmod(0o644)
    monkeypatch.chdir(project_dir)

    config = load_openai_config(include_api_key=False)

    assert config["provider"] == "openai"
    assert config["api_key"] is None


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits required")
def test_load_openai_config_accepts_secure_stored_api_key_and_model_source(
    tmp_path, monkeypatch
):
    project_dir = tmp_path / "repo"
    _write_project_config(
        project_dir,
        [
            "[openai]",
            "provider = openai",
            "api_key = secret-value",
            "model = explicit-model",
        ],
    )
    config_path = project_dir / ".gptchangelog" / "config.ini"
    config_path.chmod(0o600)
    monkeypatch.chdir(project_dir)

    config = load_openai_config(include_model_source=True)

    assert config["api_key"] == "secret-value"
    assert config["model_override"] == "explicit-model"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits required")
def test_load_openai_config_allows_insecure_permissions_without_stored_key(
    tmp_path, monkeypatch
):
    project_dir = tmp_path / "repo"
    _write_project_config(project_dir, ["[openai]", "provider = codex"])
    config_path = project_dir / ".gptchangelog" / "config.ini"
    config_path.chmod(0o644)
    monkeypatch.chdir(project_dir)

    config = load_openai_config()

    assert config["api_key"] is None


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("provider = mystery", "Unsupported provider"),
        ("profile = enormous", "Unsupported model profile"),
    ],
)
def test_load_openai_config_rejects_invalid_values(
    tmp_path, monkeypatch, line, message
):
    project_dir = tmp_path / "repo"
    _write_project_config(project_dir, ["[openai]", line])
    monkeypatch.chdir(project_dir)

    with pytest.raises(ProviderConfigurationError, match=message):
        load_openai_config()


def test_secure_config_writer_uses_owner_only_permissions(tmp_path):
    config = configparser.ConfigParser()
    config["openai"] = {"provider": "openai", "api_key": "secret"}
    path = tmp_path / "nested" / "config.ini"

    _write_config_secure(config, path)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert "secret" in path.read_text(encoding="utf-8")


def test_init_config_hides_and_does_not_store_api_key_by_default(tmp_path, monkeypatch):
    answers = iter(["p", "o", "", "", "n"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr(config_module.getpass, "getpass", lambda prompt="": "secret")

    init_config()

    config_path = tmp_path / ".gptchangelog" / "config.ini"
    content = config_path.read_text(encoding="utf-8")
    assert "secret" not in content
    assert "profile = balanced" in content
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600


def test_init_config_prefers_environment_key_without_prompting(tmp_path, monkeypatch):
    answers = iter(["p", "o", "q", ""])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "environment-secret")
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    def unexpected_prompt(prompt=""):
        raise AssertionError("getpass should not run when OPENAI_API_KEY is set")

    monkeypatch.setattr(config_module.getpass, "getpass", unexpected_prompt)

    init_config()

    config_path = tmp_path / ".gptchangelog" / "config.ini"
    content = config_path.read_text(encoding="utf-8")
    assert "environment-secret" not in content
    assert "profile = quality" in content
    assert "model =" not in content


def test_default_model_is_balanced_terra():
    assert get_default_model("openai") == "gpt-5.6-terra"
