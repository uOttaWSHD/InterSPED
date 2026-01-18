#!/bin/bash
# Interview Coach System - Startup Script

cd "$(dirname "$0")"

echo "🚀 Starting AI Interview Coach System..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Create .env from .env.example or use default Cerebras settings"
    exit 1
fi

# Clean up old environment
echo "🧹 Cleaning up old environment..."
rm -rf .venv __pycache__ src/__pycache__ 2>/dev/null

# Sync dependencies
echo "📦 Installing dependencies..."
uv sync --quiet

# Set up environment
echo "⚙️  Setting up environment..."
if command -v fish &> /dev/null; then
    source $HOME/.local/bin/env.fish 2>/dev/null || true
fi

# Start the system
echo "✨ Starting agents..."
echo "🌐 Web UI will be available at: http://localhost:8000"
echo ""

uv run sam run configs/
