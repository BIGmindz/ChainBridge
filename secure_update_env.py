#!/usr/bin/env python3
"""
Secure .env updater.
This script prompts for API credentials without echoing them, updates the .env file,
and ensures strict file permissions are set (0600).
It does NOT print secret values.
"""

import getpass
import os
from pathlib import Path

def update_env(env_path='.env'):
    env_file = Path(env_path)
    if not env_file.exists():
        print("Error: .env file not found in current directory.")
        return 1

    api_key = getpass.getpass("API_KEY: ").strip()
    api_secret = getpass.getpass("API_SECRET: ").strip()

    if not api_key or not api_secret:
        print("Error: Both API_KEY and API_SECRET are required.")
        return 1

    # Read current content
    content = env_file.read_text().splitlines()
    updated = []
    found_key = found_secret = False

    for line in content:
        if line.startswith('API_KEY='):
            updated.append(f'API_KEY={api_key}')
            found_key = True
        elif line.startswith('API_SECRET='):
            updated.append(f'API_SECRET={api_secret}')
            found_secret = True
        else:
            updated.append(line)

    if not found_key:
        updated.append(f'API_KEY={api_key}')
    if not found_secret:
        updated.append(f'API_SECRET={api_secret}')

    env_file.write_text("\n".join(updated) + "\n")

    # Secure permissions
    try:
        os.chmod(env_file, 0o600)
    except Exception:
        pass

    print("✔ API credentials updated; file permissions set to 600 (if supported).")
    print("⚠ Treat these credentials as compromised if they were previously committed; rotate them immediately.")

    return 0

if __name__ == "__main__":
    raise SystemExit(update_env())
