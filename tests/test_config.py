from gptchangelog.config import load_openai_config


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
