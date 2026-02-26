#!/bin/bash
set -e

echo "Starting Customer Support Agent (Claude Agent SDK)..."
echo "CLAUDE_CODE_USE_BEDROCK=${CLAUDE_CODE_USE_BEDROCK}"
echo "PORT=${PORT:-8080}"

# Run the Flask server
exec python runtime/app.py
