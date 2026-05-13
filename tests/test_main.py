from gptchangelog import __main__


def test_main_returns_cli_exit_code(monkeypatch):
    monkeypatch.setattr("gptchangelog.cli.app", lambda: 7)

    assert __main__.main() == 7
