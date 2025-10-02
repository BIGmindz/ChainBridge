import yaml

CONFIG_PATH = "config/config.yaml"


def load_config(path):
    with open(path, "r") as f:
        content = yaml.safe_load(f)
    return content


def test_poll_seconds():
    config = load_config(CONFIG_PATH)
    raw_poll_seconds = config.get("poll_seconds", 60)
    print(f"[DEBUG] Raw poll_seconds value: {raw_poll_seconds}")
    try:
        poll_seconds = int(raw_poll_seconds)
        print(f"[DEBUG] Converted poll_seconds value: {poll_seconds}")
    except (ValueError, TypeError):
        poll_seconds = 60
        print("[WARNING] poll_seconds was invalid. Defaulting to 60 seconds.")


if __name__ == "__main__":
    test_poll_seconds()
