import os
import re
import yaml

CONFIG_PATH = "config/config.yaml"


def load_config(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config not found at {path}")

    with open(path, "r") as f:
        content = f.read()

    def replace_env_vars(match):
        var_name = match.group(1)
        value = os.getenv(var_name, "")
        return f'"{value}"' if value == "" else value

    content = re.sub(r"\$\{([^}]+)\}", replace_env_vars, content)
    print("[DEBUG] Raw configuration content after substitution:")
    print(content)

    return yaml.safe_load(content) or {}


if __name__ == "__main__":
    config = load_config(CONFIG_PATH)
    print("[DEBUG] Loaded configuration:")
    print(config)
