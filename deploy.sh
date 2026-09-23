#!/bin/bash
# Self-Deployment script for CogniX / Claude
echo "Initiating self-deployment to GitHub..."

# Configure Git
git config --global user.name "CogniX Autonomous Agent"
git config --global user.email "cognix@hermes.bot"

# Set the remote URL using the environment variable PAT for authentication
# Make sure to strictly push to the hermes-bot repo, not the workspace
git remote set-url origin "https://${GITHUB_PAT}@github.com/bgmi1server/hermes-bot.git"

# Commit and Push
git add config.py
git commit -m "⚙️ Auto-patch: Self-modification via Telegram command"
git push origin HEAD:main

echo "Deployment pushed to GitHub successfully! Render will now auto-reboot."
