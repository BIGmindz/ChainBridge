#!/usr/bin/env python3
"""
Secure API Credential Setup Script

This script helps you securely enter your Kraken API credentials
and updates the .env file without exposing them in logs.
"""

import os
import sys
import getpass
from pathlib import Path


def setup_api_credentials():
    """Securely collect and store API credentials."""

    print("🔐 Kraken API Credential Setup")
    print("=" * 40)
    print()
    print("⚠️  IMPORTANT SECURITY NOTES:")
    print("• Your API credentials will be stored in .env file")
    print("• The .env file is ignored by git for security")
    print("• Never share your API credentials with anyone")
    print("• Only enable necessary permissions on Kraken")
    print()

    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Please ensure you're in the correct directory.")
        return False

    # Get API credentials securely
    print("Enter your Kraken API credentials:")
    print()

    # Use getpass to hide input
    api_key = getpass.getpass("API Key: ").strip()
    if not api_key:
        print("❌ API Key cannot be empty!")
        return False

    api_secret = getpass.getpass("API Secret: ").strip()
    if not api_secret:
        print("❌ API Secret cannot be empty!")
        return False

    # Confirm the credentials look valid
    if len(api_key) < 20:
        print("⚠️  WARNING: API Key seems short. Please verify it's correct.")
        confirm = input("Continue anyway? (y/N): ").lower().strip()
        if confirm != 'y':
            return False

    if len(api_secret) < 20:
        print("⚠️  WARNING: API Secret seems short. Please verify it's correct.")
        confirm = input("Continue anyway? (y/N): ").lower().strip()
        if confirm != 'y':
            return False

    # Read current .env file
    try:
        with open(env_file, 'r') as f:
            env_content = f.read()
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False

    # Update the API credentials in the .env file
    updated_content = env_content.replace(
        'API_KEY="your_api_key_here"',
        f'API_KEY="{api_key}"'
    ).replace(
        'API_SECRET="your_api_secret_here"',
        f'API_SECRET="{api_secret}"'
    )

    # Write back to .env file
    try:
        with open(env_file, 'w') as f:
            f.write(updated_content)
        print()
        print("✅ API credentials successfully updated!")
        print("📁 .env file has been updated with your credentials")
        print()
        print("🔒 Security Reminder:")
        print("• Keep your .env file secure and never commit it to git")
        print("• Regularly rotate your API credentials")
        print("• Only enable trading permissions, not withdrawal")
        print()
        return True

    except Exception as e:
        print(f"❌ Error writing to .env file: {e}")
        return False


def verify_credentials():
    """Verify that credentials were set correctly."""
    env_file = Path(".env")
    if not env_file.exists():
        return False

    try:
        with open(env_file, 'r') as f:
            content = f.read()

        has_api_key = 'API_KEY="' in content and 'your_api_key_here' not in content
        has_api_secret = 'API_SECRET="' in content and 'your_api_secret_here' not in content

        return has_api_key and has_api_secret
    except:
        return False


def main():
    """Main function."""
    # Change to the script's directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    print(f"Working directory: {os.getcwd()}")
    print()

    # Check if credentials are already set
    if verify_credentials():
        print("ℹ️  API credentials are already configured!")
        overwrite = input("Do you want to update them? (y/N): ").lower().strip()
        if overwrite != 'y':
            print("✅ Keeping existing credentials.")
            return 0

    # Setup credentials
    success = setup_api_credentials()

    if success:
        print("🎉 Setup complete! Your bot is now ready for live trading.")
        print()
        print("Next steps:")
        print("1. Verify your Kraken API permissions")
        print("2. Test with: python3 multi_signal_bot.py --once")
        print("3. Start trading: python3 multi_signal_bot.py")
        return 0
    else:
        print("❌ Setup failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())