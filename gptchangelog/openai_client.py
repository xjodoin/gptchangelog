import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Literal, Optional, Tuple

import httpx
from openai import OpenAI

ProviderName = Literal["openai", "codex"]

OPENAI_PROVIDER = "openai"
CODEX_PROVIDER = "codex"
OPENAI_DEFAULT_MODEL = "gpt-5.2"
CODEX_DEFAULT_MODEL = "gpt-5.4-mini"
CODEX_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"


@dataclass(frozen=True)
class ProviderSettings:
    provider: ProviderName
    api_key: Optional[str] = None
    codex_access_token: Optional[str] = None
    codex_responses_url: str = CODEX_RESPONSES_URL


@dataclass(frozen=True)
class CodexAuthState:
    access_token: str
    refresh_token: Optional[str] = None
    account_id: Optional[str] = None


_provider_settings = ProviderSettings(provider=OPENAI_PROVIDER)


def configure_provider(settings: ProviderSettings) -> None:
    global _provider_settings
    _provider_settings = settings
    get_openai_client.cache_clear()


def get_provider_settings() -> ProviderSettings:
    return _provider_settings


def get_default_model(provider: ProviderName) -> str:
    return CODEX_DEFAULT_MODEL if provider == CODEX_PROVIDER else OPENAI_DEFAULT_MODEL


def normalize_provider(provider: Optional[str]) -> ProviderName:
    normalized = (provider or OPENAI_PROVIDER).strip().lower()
    if normalized == CODEX_PROVIDER:
        return CODEX_PROVIDER
    return OPENAI_PROVIDER


def resolve_codex_home(env: Optional[dict[str, str]] = None) -> Path:
    env = env or os.environ
    configured = (env.get("CODEX_HOME") or "").strip()
    if not configured:
        return Path.home() / ".codex"
    if configured == "~":
        return Path.home()
    if configured.startswith("~/"):
        return Path.home() / configured[2:]
    return Path(configured).expanduser()


def read_codex_auth(env: Optional[dict[str, str]] = None) -> Optional[CodexAuthState]:
    auth_path = resolve_codex_home(env) / "auth.json"
    try:
        payload = json.loads(auth_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

    tokens = payload.get("tokens") if isinstance(payload, dict) else None
    if not isinstance(tokens, dict):
        return None

    access_token = tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        return None

    refresh_token = tokens.get("refresh_token")
    account_id = tokens.get("account_id")
    return CodexAuthState(
        access_token=access_token.strip(),
        refresh_token=refresh_token.strip() if isinstance(refresh_token, str) and refresh_token.strip() else None,
        account_id=account_id.strip() if isinstance(account_id, str) and account_id.strip() else None,
    )


def has_codex_auth(env: Optional[dict[str, str]] = None) -> bool:
    return read_codex_auth(env) is not None


@lru_cache(maxsize=4)
def get_openai_client(api_key: Optional[str] = None) -> OpenAI:
    if api_key:
        return OpenAI(api_key=api_key)
    return OpenAI()


def _collect_text_from_output(output_items: Any) -> List[str]:
    texts: List[str] = []
    if not output_items:
        return texts

    for item in output_items:
        content_list = getattr(item, "content", None)
        if content_list is None and isinstance(item, dict):
            content_list = item.get("content")

        if not content_list:
            continue

        for content in content_list:
            text_obj = getattr(content, "text", None)
            if text_obj and hasattr(text_obj, "value") and text_obj.value:
                texts.append(text_obj.value)
                continue

            if isinstance(content, dict):
                text_data = content.get("text")
                if isinstance(text_data, dict) and text_data.get("value"):
                    texts.append(text_data["value"])
                    continue

                for key in ("value", "content", "text"):
                    value = content.get(key)
                    if isinstance(value, str):
                        texts.append(value)
                        break

    return texts


def extract_response_text(response: Any) -> str:
    if response is None:
        return ""

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text.strip()
    if isinstance(output_text, list):
        joined = "\n".join(part for part in output_text if isinstance(part, str))
        if joined.strip():
            return joined.strip()

    texts = _collect_text_from_output(getattr(response, "output", None))
    if texts:
        return "\n".join(texts).strip()

    if hasattr(response, "model_dump"):
        payload = response.model_dump()
        texts = _collect_text_from_output(payload.get("output"))  # type: ignore[arg-type]
        if texts:
            return "\n".join(texts).strip()

    return str(response).strip()


def create_text_response(model: str, instructions: str, prompt: str) -> str:
    settings = get_provider_settings()
    if settings.provider == CODEX_PROVIDER:
        return _create_codex_text_response(
            model=model,
            instructions=instructions,
            prompt=prompt,
            settings=settings,
        )

    response = get_openai_client(settings.api_key).responses.create(
        model=model,
        instructions=instructions,
        input=prompt,
    )
    return extract_response_text(response)


def _create_codex_text_response(
    model: str,
    instructions: str,
    prompt: str,
    settings: ProviderSettings,
) -> str:
    auth = _resolve_codex_auth(settings)
    headers = {
        "Authorization": f"Bearer {auth.access_token}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "instructions": instructions,
        "store": False,
        "stream": True,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt,
                    }
                ],
            }
        ],
    }

    with httpx.stream(
        "POST",
        settings.codex_responses_url,
        headers=headers,
        json=payload,
        timeout=120,
    ) as response:
        if response.status_code >= 400:
            raise RuntimeError(_format_codex_error(response))

        text = _collect_codex_sse_text(response.iter_lines())
        if text:
            return text

        raise RuntimeError("Codex returned an empty response.")


def _resolve_codex_auth(settings: ProviderSettings) -> CodexAuthState:
    if settings.codex_access_token:
        return CodexAuthState(access_token=settings.codex_access_token)

    auth = read_codex_auth()
    if auth is None:
        raise RuntimeError(
            "No Codex login found. Run `codex login` or `codex`, choose 'Sign in with ChatGPT', then retry."
        )
    return auth


def _format_codex_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = response.text.strip()

    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error") or payload
        return f"Codex backend error ({response.status_code}): {detail}"

    return f"Codex backend error ({response.status_code}): {payload or response.reason_phrase}"


def _collect_codex_sse_text(lines: Iterable[str]) -> str:
    chunks: List[str] = []
    fallback_text: Optional[str] = None

    for _event_name, payload in _iter_sse_events(lines):
        if payload == "[DONE]":
            break

        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type")
        if event_type == "response.output_text.delta":
            delta = event.get("delta")
            if isinstance(delta, str):
                chunks.append(delta)
        elif event_type == "response.output_text.done":
            text = event.get("text")
            if isinstance(text, str):
                fallback_text = text
        elif event_type == "response.failed":
            detail = event.get("response", {}).get("error") if isinstance(event.get("response"), dict) else None
            raise RuntimeError(f"Codex generation failed: {detail or event}")

    return "".join(chunks).strip() or (fallback_text or "").strip()


def _iter_sse_events(lines: Iterable[str]) -> Iterator[Tuple[Optional[str], str]]:
    event_name: Optional[str] = None
    data_lines: List[str] = []

    for raw_line in lines:
        line = raw_line.rstrip("\r")
        if not line:
            if data_lines:
                yield event_name, "\n".join(data_lines)
                event_name = None
                data_lines = []
            continue

        if line.startswith("event:"):
            event_name = line[len("event:"):].strip() or None
            continue
        if line.startswith("data:"):
            data_lines.append(line[len("data:"):].lstrip())

    if data_lines:
        yield event_name, "\n".join(data_lines)
