import configparser
import os
from typing import Dict, Optional

from .openai_client import (
    CODEX_PROVIDER,
    OPENAI_PROVIDER,
    get_default_model,
    has_codex_auth,
    normalize_provider,
)


def _resolve_config_file(config_file_name: str = "config.ini") -> str:
    project_config_dir = os.path.join(os.getcwd(), ".gptchangelog")
    project_config_file = os.path.join(project_config_dir, config_file_name)

    home_dir = os.path.expanduser("~")
    global_config_dir = os.path.join(home_dir, ".config", "gptchangelog")
    global_config_file = os.path.join(global_config_dir, config_file_name)

    if os.path.exists(project_config_file):
        return project_config_file
    if os.path.exists(global_config_file):
        return global_config_file

    raise FileNotFoundError(
        "Configuration file not found. Please run 'gptchangelog config init' to initialize the configuration."
    )


def load_openai_config(config_file_name: str = "config.ini") -> Dict[str, Optional[str]]:
    config_file = _resolve_config_file(config_file_name)

    config = configparser.ConfigParser()
    config.read(config_file)

    openai_section = config["openai"]
    provider = normalize_provider(openai_section.get("provider"))
    model = openai_section.get("model", get_default_model(provider))
    api_key = openai_section.get("api_key")

    return {
        "provider": provider,
        "api_key": api_key.strip() if api_key and api_key.strip() else None,
        "model": model.strip() if model and model.strip() else get_default_model(provider),
    }


def init_config() -> None:
    while True:
        config_type = input("Initialize configuration for (g)lobal or (p)roject? [G/p]: ").strip().lower()
        if config_type in {"", "g", "p"}:
            break
        print("Please enter 'g' for global or 'p' for project.")

    if config_type in {"", "g"}:
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "gptchangelog")
    else:
        config_dir = os.path.join(os.getcwd(), ".gptchangelog")

    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "config.ini")

    provider = _prompt_provider()
    default_model = get_default_model(provider)

    config = configparser.ConfigParser()
    config["openai"] = {
        "provider": provider,
        "model": input(f"Enter the model to use [default: {default_model}]: ").strip() or default_model,
    }

    if provider == OPENAI_PROVIDER:
        api_key = input("Enter your OpenAI API key: ").strip()
        if not api_key:
            print("API key is required when provider=openai.")
            return
        config["openai"]["api_key"] = api_key
    elif not has_codex_auth():
        print("No Codex login detected. Run `codex login` first, then re-run `gptchangelog config init`.")
        return

    with open(config_file, "w", encoding="utf-8") as configfile:
        config.write(configfile)

    print(f"Configuration saved to {config_file}")


def _prompt_provider() -> str:
    prompt = "Choose provider: (o)penai API key or (c)odex ChatGPT subscription? [O/c]: "
    while True:
        choice = input(prompt).strip().lower()
        if choice in {"", "o"}:
            return OPENAI_PROVIDER
        if choice == "c":
            return CODEX_PROVIDER
        print("Please enter 'o' for OpenAI API or 'c' for Codex subscription.")


def show_config() -> None:
    project_config_dir = os.path.join(os.getcwd(), ".gptchangelog")
    project_config_file = os.path.join(project_config_dir, "config.ini")

    home_dir = os.path.expanduser("~")
    global_config_dir = os.path.join(home_dir, ".config", "gptchangelog")
    global_config_file = os.path.join(global_config_dir, "config.ini")

    configs = []
    if os.path.exists(project_config_file):
        configs.append(("Project", project_config_file))
    if os.path.exists(global_config_file):
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
            if key == "api_key":
                print(f"{key} = [HIDDEN]")
            else:
                print(f"{key} = {config['openai'][key]}")
        print()
