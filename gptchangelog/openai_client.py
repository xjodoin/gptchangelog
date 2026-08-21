"""Provider adapters for OpenAI Responses and Codex CLI.

The Codex adapter intentionally delegates authentication and token refresh to the
official ``codex`` executable. It never reads Codex credential files directly.
"""

import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Literal, Mapping, Optional, Sequence, cast

from openai import OpenAI

ProviderName = Literal["openai", "codex"]
ModelProfile = Literal["fast", "balanced", "quality"]
ReasoningEffort = Literal["minimal", "low", "medium", "high", "xhigh"]

OPENAI_PROVIDER: ProviderName = "openai"
CODEX_PROVIDER: ProviderName = "codex"

BALANCED_MODEL = "gpt-5.6-terra"
QUALITY_MODEL = "gpt-5.6-sol"
OPENAI_DEFAULT_MODEL = BALANCED_MODEL
CODEX_DEFAULT_MODEL = BALANCED_MODEL
DEFAULT_MODEL_PROFILE: ModelProfile = "balanced"

MODEL_PROFILES: Mapping[ProviderName, Mapping[ModelProfile, str]] = {
    OPENAI_PROVIDER: {
        "fast": BALANCED_MODEL,
        "balanced": BALANCED_MODEL,
        "quality": QUALITY_MODEL,
    },
    CODEX_PROVIDER: {
        "fast": BALANCED_MODEL,
        "balanced": BALANCED_MODEL,
        "quality": QUALITY_MODEL,
    },
}


class ProviderError(RuntimeError):
    """Raised when a configured provider cannot complete a request."""


class ProviderConfigurationError(ValueError, RuntimeError):
    """Raised for an unsupported provider, profile, or provider setting."""


class StructuredResponseError(ProviderError):
    """Raised when a provider does not return a JSON object as requested."""


@dataclass(frozen=True)
class ProviderSettings:
    provider: ProviderName
    api_key: Optional[str] = None
    timeout_seconds: float = 120.0
    max_retries: int = 2
    codex_executable: str = "codex"


@dataclass(frozen=True)
class ProviderDoctorResult:
    provider: ProviderName
    ok: bool
    message: str


_provider_settings = ProviderSettings(provider=OPENAI_PROVIDER)


def configure_provider(settings: ProviderSettings) -> None:
    """Set process-local provider settings used by generation helpers."""

    global _provider_settings
    if settings.timeout_seconds <= 0:
        raise ProviderConfigurationError("Provider timeout must be greater than zero.")
    if settings.max_retries < 0:
        raise ProviderConfigurationError("Provider max_retries cannot be negative.")

    _provider_settings = replace(
        settings, provider=normalize_provider(settings.provider)
    )
    get_openai_client.cache_clear()


def get_provider_settings() -> ProviderSettings:
    return _provider_settings


def normalize_provider(provider: Optional[str]) -> ProviderName:
    normalized = OPENAI_PROVIDER if provider is None else provider.strip().lower()
    if normalized not in {OPENAI_PROVIDER, CODEX_PROVIDER}:
        raise ProviderConfigurationError(
            f"Unsupported provider {provider!r}; expected 'openai' or 'codex'."
        )
    return cast(ProviderName, normalized)


def normalize_profile(profile: Optional[str]) -> ModelProfile:
    normalized = DEFAULT_MODEL_PROFILE if profile is None else profile.strip().lower()
    if normalized not in {"fast", "balanced", "quality"}:
        raise ProviderConfigurationError(
            f"Unsupported model profile {profile!r}; expected fast, balanced, or quality."
        )
    return cast(ModelProfile, normalized)


def get_profile_model(provider: ProviderName, profile: Optional[str] = None) -> str:
    normalized_provider = normalize_provider(provider)
    normalized_profile = normalize_profile(profile)
    return MODEL_PROFILES[normalized_provider][normalized_profile]


def get_default_model(provider: ProviderName) -> str:
    return get_profile_model(provider, DEFAULT_MODEL_PROFILE)


def resolve_model(
    provider: ProviderName,
    *,
    profile: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """Resolve an explicit model override before the selected profile."""

    normalized_provider = normalize_provider(provider)
    normalized_profile = normalize_profile(profile)
    if model is not None:
        explicit_model = model.strip()
        if not explicit_model:
            raise ProviderConfigurationError("An explicit model cannot be empty.")
        return explicit_model
    return MODEL_PROFILES[normalized_provider][normalized_profile]


@lru_cache(maxsize=8)
def get_openai_client(
    api_key: Optional[str] = None,
    timeout_seconds: float = 120.0,
    max_retries: int = 2,
) -> OpenAI:
    kwargs: Dict[str, Any] = {
        "timeout": timeout_seconds,
        "max_retries": max_retries,
    }
    if api_key:
        kwargs["api_key"] = api_key
    return OpenAI(**kwargs)


def extract_response_text(response: Any) -> str:
    """Extract output text from a Responses API object without SDK internals."""

    if response is None:
        return ""

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text.strip()
    if isinstance(output_text, list):
        joined = "\n".join(part for part in output_text if isinstance(part, str))
        if joined.strip():
            return joined.strip()

    payload = response.model_dump() if hasattr(response, "model_dump") else response
    if not isinstance(payload, Mapping):
        return str(response).strip()

    texts = []
    for item in payload.get("output", []) or []:
        item_payload = item if isinstance(item, Mapping) else {}
        for content in item_payload.get("content", []) or []:
            content_payload = content if isinstance(content, Mapping) else {}
            text_value = content_payload.get("text")
            if isinstance(text_value, str):
                texts.append(text_value)
            elif isinstance(text_value, Mapping):
                value = text_value.get("value")
                if isinstance(value, str):
                    texts.append(value)
    return "\n".join(texts).strip()


def create_text_response(
    model: str,
    instructions: str,
    prompt: str,
    reasoning: Optional[ReasoningEffort] = None,
) -> str:
    settings = get_provider_settings()
    if settings.provider == CODEX_PROVIDER:
        return _create_codex_response(
            model=model,
            instructions=instructions,
            prompt=prompt,
            settings=settings,
            reasoning=reasoning,
        )

    request: Dict[str, Any] = {
        "model": model,
        "instructions": instructions,
        "input": prompt,
        "store": False,
    }
    if reasoning:
        request["reasoning"] = {"effort": reasoning}

    try:
        response = _openai_client_for(settings).responses.create(**request)
    except Exception as exc:
        raise ProviderError(f"OpenAI response failed: {exc}") from exc

    text = extract_response_text(response)
    if not text:
        raise ProviderError("OpenAI returned an empty response.")
    return text


def create_structured_response(
    model: str,
    instructions: str,
    prompt: str,
    json_schema: Mapping[str, Any],
    reasoning: Optional[ReasoningEffort] = None,
) -> Dict[str, Any]:
    """Generate and decode a strict JSON object matching ``json_schema``."""

    if not isinstance(json_schema, Mapping) or not json_schema:
        raise ProviderConfigurationError("A non-empty JSON schema is required.")

    settings = get_provider_settings()
    if settings.provider == CODEX_PROVIDER:
        text = _create_codex_response(
            model=model,
            instructions=instructions,
            prompt=prompt,
            settings=settings,
            json_schema=json_schema,
            reasoning=reasoning,
        )
    else:
        request: Dict[str, Any] = {
            "model": model,
            "instructions": instructions,
            "input": prompt,
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": _schema_name(json_schema),
                    "schema": dict(json_schema),
                    "strict": True,
                }
            },
        }
        if reasoning:
            request["reasoning"] = {"effort": reasoning}
        try:
            response = _openai_client_for(settings).responses.create(**request)
        except Exception as exc:
            raise ProviderError(f"OpenAI structured response failed: {exc}") from exc
        text = extract_response_text(response)

    if not text:
        raise StructuredResponseError("The provider returned an empty response.")
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StructuredResponseError(
            f"The provider returned invalid JSON: {exc.msg}."
        ) from exc
    if not isinstance(decoded, dict):
        raise StructuredResponseError("The provider JSON response must be an object.")
    return decoded


def _openai_client_for(settings: ProviderSettings) -> OpenAI:
    return get_openai_client(
        settings.api_key,
        settings.timeout_seconds,
        settings.max_retries,
    )


def _schema_name(schema: Mapping[str, Any]) -> str:
    title = schema.get("title")
    candidate = title if isinstance(title, str) else "gptchangelog_response"
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", candidate).strip("_")
    return (normalized or "gptchangelog_response")[:64]


def _create_codex_response(
    *,
    model: str,
    instructions: str,
    prompt: str,
    settings: ProviderSettings,
    json_schema: Optional[Mapping[str, Any]] = None,
    reasoning: Optional[ReasoningEffort] = None,
) -> str:
    """Invoke the supported Codex CLI in a temporary read-only workspace."""

    with tempfile.TemporaryDirectory(prefix="gptchangelog-codex-") as temp_dir:
        temp_path = Path(temp_dir)
        output_path = temp_path / "last-message.txt"
        command = [
            settings.codex_executable,
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--color",
            "never",
            "--cd",
            temp_dir,
            "--model",
            model,
            "--output-last-message",
            str(output_path),
        ]

        if reasoning:
            command.extend(["--config", f'model_reasoning_effort="{reasoning}"'])
        if json_schema is not None:
            schema_path = temp_path / "response-schema.json"
            schema_path.write_text(json.dumps(dict(json_schema)), encoding="utf-8")
            command.extend(["--output-schema", str(schema_path)])
        command.append("-")

        combined_prompt = _codex_prompt(
            instructions, prompt, structured=json_schema is not None
        )
        _run_codex(command, combined_prompt, settings)

        try:
            output = output_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ProviderError(
                "Codex completed without writing its final response."
            ) from exc
        if not output:
            raise ProviderError("Codex returned an empty response.")
        return output


def _codex_prompt(instructions: str, prompt: str, *, structured: bool) -> str:
    response_requirement = (
        "Return only the JSON object required by the supplied output schema."
        if structured
        else "Return only the requested final text."
    )
    return (
        "Complete this generation task directly without using shell commands or tools.\n"
        f"{response_requirement}\n\n"
        "Instructions:\n"
        f"{instructions.strip()}\n\n"
        "Input data:\n"
        f"{prompt.strip()}\n"
    )


def _run_codex(command: Sequence[str], prompt: str, settings: ProviderSettings) -> None:
    attempts = settings.max_retries + 1
    last_error = "Codex execution failed."

    for attempt in range(attempts):
        try:
            completed = subprocess.run(
                list(command),
                input=prompt,
                capture_output=True,
                text=True,
                timeout=settings.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ProviderError(
                f"Codex executable {settings.codex_executable!r} was not found. "
                "Install Codex CLI and run `codex login`."
            ) from exc
        except subprocess.TimeoutExpired:
            last_error = f"Codex timed out after {settings.timeout_seconds:g} seconds."
            transient = True
        else:
            if completed.returncode == 0:
                return
            detail = (completed.stderr or completed.stdout or "unknown error").strip()
            last_error = f"Codex exited with status {completed.returncode}: {detail}"
            transient = _is_transient_error(detail)

        if not transient or attempt == attempts - 1:
            raise ProviderError(last_error)
        time.sleep(min(2**attempt, 4))

    raise ProviderError(last_error)


def _is_transient_error(detail: str) -> bool:
    normalized = detail.lower()
    return any(
        marker in normalized
        for marker in (
            "timed out",
            "timeout",
            "temporarily unavailable",
            "rate limit",
            "429",
            "500",
            "502",
            "503",
            "504",
            "connection reset",
            "connection refused",
        )
    )


def codex_login_status(
    env: Optional[Mapping[str, str]] = None,
    *,
    executable: str = "codex",
    timeout_seconds: float = 10.0,
) -> ProviderDoctorResult:
    """Ask Codex CLI for login state without inspecting credential files."""

    command_env = os.environ.copy()
    if env is not None:
        command_env.update(env)
    try:
        completed = subprocess.run(
            [executable, "login", "status"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=command_env,
        )
    except FileNotFoundError:
        return ProviderDoctorResult(
            provider=CODEX_PROVIDER,
            ok=False,
            message="Codex CLI is not installed or is not on PATH.",
        )
    except subprocess.TimeoutExpired:
        return ProviderDoctorResult(
            provider=CODEX_PROVIDER,
            ok=False,
            message="`codex login status` timed out.",
        )

    detail = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode == 0:
        return ProviderDoctorResult(
            provider=CODEX_PROVIDER,
            ok=True,
            message=detail or "Codex login is available.",
        )
    return ProviderDoctorResult(
        provider=CODEX_PROVIDER,
        ok=False,
        message=detail or "Codex is not logged in; run `codex login`.",
    )


def has_codex_auth(env: Optional[Mapping[str, str]] = None) -> bool:
    return codex_login_status(env).ok


def doctor_provider(settings: ProviderSettings) -> ProviderDoctorResult:
    provider = normalize_provider(settings.provider)
    if provider == CODEX_PROVIDER:
        return codex_login_status(executable=settings.codex_executable)
    if settings.api_key or os.environ.get("OPENAI_API_KEY"):
        return ProviderDoctorResult(
            provider=OPENAI_PROVIDER,
            ok=True,
            message="OpenAI API key is configured.",
        )
    return ProviderDoctorResult(
        provider=OPENAI_PROVIDER,
        ok=False,
        message="OPENAI_API_KEY is not configured.",
    )
