#!/bin/bash
# Secure API Credential Setup (Bash Version)
# Alternative to the Python script for users who prefer bash

echo "🔐 Kraken API Credential Setup (Bash)"
echo "====================================="
echo
echo "⚠️  IMPORTANT SECURITY NOTES:"
echo "• Your API credentials will be stored in .env file"
echo "• The .env file is ignored by git for security"
echo "• Never share your API credentials with anyone"
echo "• Only enable necessary permissions on Kraken"
echo

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please ensure you're in the correct directory."
    exit 1
fi

echo "Enter your Kraken API credentials:"
echo

# Read API key (hidden input)
read -s -p "API Key: " api_key
echo
if [ -z "$api_key" ]; then
    echo "❌ API Key cannot be empty!"
    exit 1
fi

# Read API secret (hidden input)
read -s -p "API Secret: " api_secret
echo
if [ -z "$api_secret" ]; then
    echo "❌ API Secret cannot be empty!"
    exit 1
fi

# Basic validation
if [ ${#api_key} -lt 20 ]; then
    echo "⚠️  WARNING: API Key seems short. Please verify it's correct."
    read -p "Continue anyway? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

if [ ${#api_secret} -lt 20 ]; then
    echo "⚠️  WARNING: API Secret seems short. Please verify it's correct."
    read -p "Continue anyway? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update .env file
sed -i.bak "s/API_KEY=\"your_api_key_here\"/API_KEY=\"$api_key\"/g" .env
sed -i.bak "s/API_SECRET=\"your_api_secret_here\"/API_SECRET=\"$api_secret\"/g" .env

# Remove backup file
rm .env.bak

echo
echo "✅ API credentials successfully updated!"
echo "📁 .env file has been updated with your credentials"
echo
echo "🔒 Security Reminder:"
echo "• Keep your .env file secure and never commit it to git"
echo "• Regularly rotate your API credentials"
echo "• Only enable trading permissions, not withdrawal"
echo
echo "🎉 Setup complete! Your bot is now ready for live trading."