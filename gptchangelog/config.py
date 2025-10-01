import configparser
import os


def load_openai_config(config_file_name="config.ini"):
    # First, check for per-project config
    project_config_dir = os.path.join(os.getcwd(), '.gptchangelog')
    project_config_file = os.path.join(project_config_dir, config_file_name)

    # Then, check for global config
    home_dir = os.path.expanduser("~")
    global_config_dir = os.path.join(home_dir, ".config", "gptchangelog")
    global_config_file = os.path.join(global_config_dir, config_file_name)

    if os.path.exists(project_config_file):
        config_file = project_config_file
    elif os.path.exists(global_config_file):
        config_file = global_config_file
    else:
        raise FileNotFoundError(
            "Configuration file not found. Please run 'gptchangelog config init' to initialize the configuration."
        )

    config = configparser.ConfigParser()
    config.read(config_file)

    api_key = config["openai"]["api_key"]
    model = config["openai"].get("model", "gpt-5-mini")
    max_context_tokens = int(config["openai"].get("max_context_tokens", "200000"))

    return api_key, model, max_context_tokens


def init_config():
    # Ask the user whether to initialize global config or project config
    while True:
        config_type = input("Initialize configuration for (g)lobal or (p)roject? [G/p]: ").strip().lower()
        if config_type in ['', 'g', 'p']:
            break
        else:
            print("Please enter 'g' for global or 'p' for project.")

    if config_type == '' or config_type == 'g':
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "gptchangelog")
    else:
        config_dir = os.path.join(os.getcwd(), '.gptchangelog')

    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    config_file = os.path.join(config_dir, 'config.ini')

    config = configparser.ConfigParser()

    # Prompt the user for OpenAI API key
    api_key = input("Enter your OpenAI API key: ").strip()
    if not api_key:
        print("API key is required.")
        return

    # Use defaults for model and max_context_tokens, but allow the user to change them
    default_model = "gpt-5-mini"
    default_max_tokens = "200000"

    model = input(f"Enter the model to use [default: {default_model}]: ").strip() or default_model
    max_context_tokens = input(f"Enter max context tokens [default: {default_max_tokens}]: ").strip() or default_max_tokens

    config['openai'] = {
        'api_key': api_key,
        'model': model,
        'max_context_tokens': max_context_tokens,
    }

    with open(config_file, 'w') as configfile:
        config.write(configfile)

    print(f"Configuration saved to {config_file}")


def show_config():
    # Check for project config
    project_config_dir = os.path.join(os.getcwd(), '.gptchangelog')
    project_config_file = os.path.join(project_config_dir, 'config.ini')

    # Check for global config
    home_dir = os.path.expanduser("~")
    global_config_dir = os.path.join(home_dir, ".config", "gptchangelog")
    global_config_file = os.path.join(global_config_dir, 'config.ini')

    configs = []

    if os.path.exists(project_config_file):
        configs.append(('Project', project_config_file))

    if os.path.exists(global_config_file):
        configs.append(('Global', global_config_file))

    if not configs:
        print("No configuration files found.")
        return

    for config_type, config_file in configs:
        print(f"{config_type} configuration ({config_file}):")
        config = configparser.ConfigParser()
        config.read(config_file)
        if 'openai' in config:
            print("[openai]")
            for key in config['openai']:
                # Don't display the API key
                if key == 'api_key':
                    print(f"{key} = [HIDDEN]")
                else:
                    print(f"{key} = {config['openai'][key]}")
        print()
