# 1) Go to your projects folder (adjust if you use a different location)
cd ~/Documents || cd ~
mkdir -p Projects && cd Projects

# 2) If you DON'T already have ChainBridge locally, clone it:
git clone https://github.com/BIGmindz/ChainBridge.git
cd ChainBridge

# If you DO have it locally already, just:
# cd ~/Documents/Projects/ChainBridge

# 3) Make sure you're on the default branch and up to date
git fetch --all --prune
git checkout main 2>/dev/null || git checkout master
git pull --ff-only

# 4) Create a short-lived docs branch
git checkout -b docs/readme-refresh

# 5) Back up the current README (just in case)
cp README.md README.before-$(date +%Y%m%d).md

# 6) OVERWRITE the README with what you copied from ChatGPT
#    (You must have the new README in your clipboard)
pbpaste > README.md

# 7) Review the diff (quick sanity check)
git --no-pager diff -- README.md

# 8) Commit and push the branch
git add README.md
git commit -m "docs(readme): refresh README with architecture, flows, ops, and roadmap"
git push -u origin docs/readme-refresh

# 9) Open a Pull Request (uses GitHub CLI)
gh pr create --fill --base main --head docs/readme-refresh --title "README refresh" --draft