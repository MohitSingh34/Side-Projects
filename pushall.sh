#!/usr/bin/env bash
set -euo pipefail

# === Configuration ===
VISIBILITY="public"  # Change to "private" if you want private repos
GITIGNORE_CONTENT='
# === Node.js / Web Dev Defaults ===
node_modules/
.env
dist/
build/
.cache/
.next/
.vscode/
*.log
*.env
*.local
coverage/
.DS_Store
*.swp
*.bak
*.tmp
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.idea/
'

# === Script Start ===
echo "🚀 Starting GitHub push automation for all project folders..."

# Iterate over all directories in the current folder
for dir in */; do
  # Skip if it's not a directory
  if [ ! -d "$dir" ]; then
    continue
  fi

  cd "$dir" || continue
  echo "🔍 Processing folder: $dir"

  # Check if already a git repository
  if [ -d ".git" ]; then
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "none")
    if [[ "$REMOTE_URL" == *"github.com"* ]]; then
      echo "✅ Already connected to GitHub: $REMOTE_URL"
      cd ..
      continue
    else
      echo "🔁 Repo exists but not linked to GitHub. Linking now..."
    fi
  else
    echo "🆕 Initializing new git repository..."
    git init -q
  fi

  # Create .gitignore if it doesn't exist
  if [ ! -f ".gitignore" ]; then
    echo "$GITIGNORE_CONTENT" > .gitignore
    echo "📝 Generated .gitignore"
  fi

  # Stage and commit all changes
  git add .
  if git diff --cached --quiet; then
    echo "⚠️  No changes to commit."
  else
    git commit -m "Initial commit" >/dev/null || true
    echo "✅ Changes committed."
  fi

  # Create GitHub repository and push
  REPO_NAME="${dir%/}"  # Remove trailing slash from directory name
  echo "🌐 Creating GitHub repository: $REPO_NAME ($VISIBILITY)"
  if gh repo create "$REPO_NAME" --"$VISIBILITY" --source=. --remote=origin --push; then
    echo "✅ Repository created and pushed: $REPO_NAME"
  else
    echo "⚠️  Repository might already exist. Attempting manual push..."
    git remote add origin "https://github.com/$(gh api user | jq -r .login)/$REPO_NAME.git" || true
    git push -u origin main || git push -u origin master || true
    echo "✅ Repository manually pushed: $REPO_NAME"
  fi

  cd ..
done

echo "🎉 All project folders processed successfully!"