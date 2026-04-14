import json

from gptchangelog.openai_client import _collect_codex_sse_text, read_codex_auth


def test_read_codex_auth_reads_access_token(tmp_path, monkeypatch):
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    auth_file = codex_home / "auth.json"
    auth_file.write_text(
        json.dumps(
            {
                "tokens": {
                    "access_token": "access-token",
                    "refresh_token": "refresh-token",
                    "account_id": "acct_123",
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    auth = read_codex_auth()

    assert auth is not None
    assert auth.access_token == "access-token"
    assert auth.refresh_token == "refresh-token"
    assert auth.account_id == "acct_123"


def test_collect_codex_sse_text_joins_deltas():
    lines = [
        "event: response.output_text.delta",
        'data: {"type":"response.output_text.delta","delta":"Hello"}',
        "",
        "event: response.output_text.delta",
        'data: {"type":"response.output_text.delta","delta":" world"}',
        "",
        "event: response.output_text.done",
        'data: {"type":"response.output_text.done","text":"Hello world"}',
        "",
    ]

    assert _collect_codex_sse_text(lines) == "Hello world"
