from gptchangelog.config import load_openai_config
from gptchangelog.openai_client import get_default_model


def test_load_openai_config_reads_provider_and_model(tmp_path, monkeypatch):
    project_dir = tmp_path / "repo"
    config_dir = project_dir / ".gptchangelog"
    config_dir.mkdir(parents=True)
    (config_dir / "config.ini").write_text(
        "\n".join(
            [
                "[openai]",
                "provider = codex",
                "model = gpt-5.4-mini",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(project_dir)

    config = load_openai_config()

    assert config == {
        "provider": "codex",
        "api_key": None,
        "model": "gpt-5.4-mini",
    }


def test_openai_default_model_is_current_flagship():
    assert get_default_model("openai") == "gpt-5.5"
