#!/bin/bash
set -e

# Replivo deploy script — Railway deployment
# TODO: configure once Railway project is set up

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Replivo — Railway Deploy"
echo "========================"

# Check railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "Error: railway CLI not installed."
    echo "Install with: brew install railway"
    exit 1
fi

# Check logged in
if ! railway whoami &> /dev/null; then
    echo "Error: not logged in to Railway."
    echo "Run: railway login"
    exit 1
fi

echo ""
echo "Deploying to Railway..."
cd "$SCRIPT_DIR"
railway up

echo ""
echo "Deploy complete."
