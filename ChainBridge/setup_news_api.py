#!/usr/bin/env python3
"""
Quick setup script to add NewsAPI key to .env file
Run this script and paste your NewsAPI key when prompted.
"""

import sys
from pathlib import Path


def setup_news_api():
    """Setup NewsAPI key in .env file"""
    env_file = Path(".env")

    print("🔧 NewsAPI Key Setup for BensonBot")
    print("=" * 40)

    # Check if .env exists
    if not env_file.exists():
        print("❌ .env file not found!")
        return False

    # Read current .env content
    with open(env_file, "r") as f:
        lines = f.readlines()

    # Get NewsAPI key from user
    print("\n📝 Please enter your NewsAPI key:")
    print("   (Get it from: https://newsapi.org/register)")
    print("   (Key format: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)")

    while True:
        api_key = input("NewsAPI Key: ").strip()

        if not api_key:
            print("❌ API key cannot be empty!")
            continue

        if len(api_key) < 20:
            print("❌ API key seems too short (should be ~32 characters)")
            continue

        # Confirm the key
        print(f"\n🔍 Your key: {api_key[:8]}...{api_key[-4:]}")
        confirm = input("Is this correct? (y/n): ").lower().strip()

        if confirm in ["y", "yes"]:
            break
        else:
            print("Let's try again...")

    # Update .env file
    updated_lines = []
    news_api_updated = False

    for line in lines:
        if line.strip().startswith("NEWS_API_KEY="):
            # Replace existing NEWS_API_KEY line
            updated_lines.append(f"NEWS_API_KEY={api_key}\n")
            news_api_updated = True
            print("✅ Updated existing NEWS_API_KEY")
        else:
            updated_lines.append(line)

    # If NEWS_API_KEY wasn't found, add it
    if not news_api_updated:
        updated_lines.append(f"\nNEWS_API_KEY={api_key}\n")
        print("✅ Added new NEWS_API_KEY")

    # Write back to .env file
    try:
        with open(env_file, "w") as f:
            f.writelines(updated_lines)

        print(f"\n🎉 Successfully saved NewsAPI key to {env_file}")
        print("\n📋 Current .env configuration:")

        # Show sanitized version of .env
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line and line[0] != "#":
                    key, value = line.split("=", 1)
                    if "API" in key or "SECRET" in key or "KEY" in key:
                        if value and len(value) > 8:
                            masked_value = f"{value[:4]}...{value[-4:]}"
                        else:
                            masked_value = "***" if value else "(empty)"
                        print(f"   {key}={masked_value}")
                    else:
                        print(f"   {line}")

        print("\n🚀 Ready to test live API integration!")
        return True

    except Exception as e:
        print(f"❌ Error saving to .env file: {e}")
        return False


def main():
    """Main function"""
    print("🤖 BensonBot NewsAPI Setup")
    print("=" * 50)

    # Setup API key
    if setup_news_api():
        print("\n✅ Setup complete! Your NewsAPI key has been saved.")
        print("🎯 You can now run the trading bot with live sentiment data!")
    else:
        print("\n❌ Setup failed. Please try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
