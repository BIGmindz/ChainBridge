#!/usr/bin/env python3
"""
Script to securely update Kraken API credentials in .env file.
This script will prompt for your API key and secret, then update the .env file.
"""

import os
import getpass


def update_env_file():
    # Check if .env exists
    env_path = ".env"
    if not os.path.exists(env_path):
        print("Error: .env file not found in current directory")
        return

    # Prompt for credentials (securely)
    print("Enter your Kraken API credentials:")
    api_key = getpass.getpass("API_KEY: ")
    api_secret = getpass.getpass("API_SECRET: ")

    if not api_key or not api_secret:
        print("Error: Both API_KEY and API_SECRET are required")
        return

    # Read current .env content
    with open(env_path, "r") as f:
        lines = f.readlines()

    # Update or add the credentials
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("API_KEY="):
            lines[i] = f"API_KEY={api_key}\n"
            updated = True
        elif line.startswith("API_SECRET="):
            lines[i] = f"API_SECRET={api_secret}\n"
            updated = True

    # If not found, add them
    if not updated:
        lines.append(f"API_KEY={api_key}\n")  # type: ignore
        lines.append(f"API_SECRET={api_secret}\n")  # type: ignore

    # Write back to file
    with open(env_path, "w") as f:
        f.writelines(lines)

    print("✅ API credentials updated successfully in .env file")
    print("Note: The bot is configured for PAPER=false (live trading mode)")
    print("Make sure these are valid Kraken API credentials with trading permissions")


if __name__ == "__main__":
    update_env_file()
