"""Configuration loading and secure interactive initialization."""

import configparser
import getpass
import os
import shlex
import stat
import tempfile
from pathlib import Path
from typing import Dict, Optional, Union

from .openai_client import (
    CODEX_PROVIDER,
    DEFAULT_MODEL_PROFILE,
    OPENAI_PROVIDER,
    ProviderConfigurationError,
    ProviderName,
    get_profile_model,
    has_codex_auth,
    normalize_profile,
    normalize_provider,
    resolve_model,
)

PathLike = Union[str, os.PathLike[str]]


def _resolve_config_file(
    config_file_name: str = "config.ini",
    *,
    project_root: Optional[PathLike] = None,
) -> str:
    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd()
    project_config_file = root / ".gptchangelog" / config_file_name
    global_config_file = Path.home() / ".config" / "gptchangelog" / config_file_name

    if project_config_file.exists():
        return str(project_config_file)
    if global_config_file.exists():
        return str(global_config_file)

    raise FileNotFoundError(
        "Configuration file not found. Please run 'gptchangelog config init' to initialize the configuration."
    )


def load_openai_config(
    config_file_name: str = "config.ini",
    *,
    project_root: Optional[PathLike] = None,
    include_model_source: bool = False,
    include_api_key: bool = True,
) -> Dict[str, Optional[str]]:
    config_file = _resolve_config_file(config_file_name, project_root=project_root)
    config = configparser.ConfigParser()
    try:
        loaded = config.read(config_file)
    except configparser.Error as exc:
        raise ProviderConfigurationError(
            f"Invalid configuration in {config_file}: {exc}"
        ) from exc
    if not loaded or "openai" not in config:
        raise ProviderConfigurationError(
            f"Configuration {config_file} must contain an [openai] section."
        )

    section = config["openai"]
    api_key_value = section.get("api_key") if include_api_key else None
    api_key = (
        api_key_value.strip()
        if api_key_value is not None and api_key_value.strip()
        else None
    )
    _validate_stored_api_key_permissions(Path(config_file), api_key)

    provider = normalize_provider(section.get("provider"))
    profile = normalize_profile(section.get("profile", DEFAULT_MODEL_PROFILE))
    configured_model = section.get("model")
    model = resolve_model(
        provider,
        profile=profile,
        model=configured_model if configured_model is not None else None,
    )

    result = {
        "provider": provider,
        "profile": profile,
        "api_key": api_key,
        "model": model,
    }
    if include_model_source:
        result["model_override"] = (
            configured_model.strip()
            if configured_model is not None and configured_model.strip()
            else None
        )
    return result


def _validate_stored_api_key_permissions(
    config_file: Path, api_key: Optional[str]
) -> None:
    if os.name != "posix" or api_key is None:
        return

    permissions = stat.S_IMODE(config_file.stat().st_mode)
    if permissions & (stat.S_IRWXG | stat.S_IRWXO):
        command_path = shlex.quote(str(config_file))
        raise ProviderConfigurationError(
            f"Configuration {config_file} contains a stored api_key but has insecure "
            f"permissions {permissions:04o}. Run `chmod 600 {command_path}` and retry."
        )


def init_config() -> None:
    config_type = _prompt_config_scope()
    if config_type == "g":
        config_dir = Path.home() / ".config" / "gptchangelog"
    else:
        config_dir = Path.cwd() / ".gptchangelog"
    config_file = config_dir / "config.ini"

    provider = _prompt_provider()
    profile = _prompt_profile()
    profile_model = get_profile_model(provider, profile)
    custom_model = input(
        f"Custom model override [profile default: {profile_model}]: "
    ).strip()

    config = configparser.ConfigParser()
    config["openai"] = {"provider": provider, "profile": profile}
    if custom_model:
        config["openai"]["model"] = custom_model

    if provider == OPENAI_PROVIDER:
        env_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if env_key:
            print("Using OPENAI_API_KEY from the environment; it will not be stored.")
        else:
            api_key = getpass.getpass(
                "Enter your OpenAI API key (input hidden): "
            ).strip()
            if not api_key:
                print(
                    "No API key entered. Set OPENAI_API_KEY before generating a changelog."
                )
            elif _confirm_store_api_key():
                config["openai"]["api_key"] = api_key
            else:
                print(
                    "API key not stored. Export OPENAI_API_KEY before generating a changelog."
                )
    elif not has_codex_auth():
        print(
            "No Codex login detected. Run `codex login` first, then re-run `gptchangelog config init`."
        )
        return

    _write_config_secure(config, config_file)
    print(f"Configuration saved to {config_file}")


def _prompt_config_scope() -> str:
    while True:
        config_type = (
            input("Initialize configuration for (g)lobal or (p)roject? [G/p]: ")
            .strip()
            .lower()
        )
        if config_type in {"", "g"}:
            return "g"
        if config_type == "p":
            return "p"
        print("Please enter 'g' for global or 'p' for project.")


def _prompt_provider() -> ProviderName:
    prompt = (
        "Choose provider: (o)penai API key or (c)odex ChatGPT subscription? [O/c]: "
    )
    while True:
        choice = input(prompt).strip().lower()
        if choice in {"", "o"}:
            return OPENAI_PROVIDER
        if choice == "c":
            return CODEX_PROVIDER
        print("Please enter 'o' for OpenAI API or 'c' for Codex subscription.")


def _prompt_profile() -> str:
    while True:
        choice = (
            input("Choose model profile: (b)alanced or (q)uality? [B/q]: ")
            .strip()
            .lower()
        )
        if choice in {"", "b", "balanced"}:
            return "balanced"
        if choice in {"q", "quality"}:
            return "quality"
        print("Please enter 'b' for balanced or 'q' for quality.")


def _confirm_store_api_key() -> bool:
    return input(
        "Store the API key in this 0600 config file? [y/N]: "
    ).strip().lower() in {"y", "yes"}


def _write_config_secure(config: configparser.ConfigParser, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        os.chmod(temporary_path, 0o600)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as config_file:
            config.write(config_file)
            config_file.flush()
            os.fsync(config_file.fileno())
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.close(file_descriptor)
        except OSError:
            pass
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise


def show_config() -> None:
    configs = []
    project_config_file = Path.cwd() / ".gptchangelog" / "config.ini"
    global_config_file = Path.home() / ".config" / "gptchangelog" / "config.ini"
    if project_config_file.exists():
        configs.append(("Project", project_config_file))
    if global_config_file.exists():
        configs.append(("Global", global_config_file))

    if not configs:
        print("No configuration files found.")
        return

    for config_type, config_file in configs:
        print(f"{config_type} configuration ({config_file}):")
        config = configparser.ConfigParser()
        config.read(config_file)
        if "openai" not in config:
            print()
            continue

        print("[openai]")
        for key in config["openai"]:
            value = "[HIDDEN]" if key == "api_key" else config["openai"][key]
            print(f"{key} = {value}")
        print()
