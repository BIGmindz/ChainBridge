import yaml

content = """
poll_seconds: ""
"""


def test_poll_seconds():
    config = yaml.safe_load(content) or {}
    raw_poll_seconds = config.get("poll_seconds", "60")
    print(f"[DEBUG] Raw poll_seconds value: {raw_poll_seconds}")
    try:
        config["poll_seconds"] = int(raw_poll_seconds)
        print(f"[DEBUG] Converted poll_seconds value: {config['poll_seconds']}")
    except (ValueError, TypeError):
        config["poll_seconds"] = 60
        print("[WARNING] poll_seconds was invalid. Defaulting to 60 seconds.")


if __name__ == "__main__":
    test_poll_seconds()
