#!/usr/bin/env bash
# Push all changes to GitHub repository

echo "📊 Preparing to push changes to GitHub..."

# Current directory
cd "$(dirname "$0")"

# Check if git is initialized
if [ ! -d .git ]; then
    echo "❌ Error: Not a git repository."
    exit 1
fi

# Check current branch
current_branch=$(git rev-parse --abbrev-ref HEAD)
echo "🔍 Current branch: $current_branch"

# Add all files
echo "📝 Adding files to git..."
git add .

# Commit changes
echo "💾 Committing changes..."
git commit -m "System update: New Listings Radar, RegionCryptoMapper fix, System Monitor

- Added New Listings Radar module for detecting new coin listings
- Fixed RegionCryptoMapper with proper process() method
- Implemented comprehensive System Monitor
- Added restart_system.sh script for easy system restart
- Updated documentation with latest changes
- Enhanced overall system stability and monitoring"

# Push to remote repository
echo "🚀 Pushing to GitHub repository..."
git push origin $current_branch

echo "✅ All changes have been pushed to GitHub!"
echo "Repository: https://github.com/BIGmindz/Multiple-signal-decision-bot"
echo "Branch: $current_branch"