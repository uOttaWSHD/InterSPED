#!/bin/bash
# Quick start script for JobScraper API

echo "🚀 Starting JobScraper API..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Please create .env file with your YELLOWCAKE_API_KEY"
    echo "Example:"
    echo "  cp .env.example .env"
    echo "  # Edit .env and add your API key"
    exit 1
fi

# Check if YELLOWCAKE_API_KEY is set
if grep -q "your_api_key_here" .env; then
    echo "⚠️  Please set your YELLOWCAKE_API_KEY in .env file"
    exit 1
fi

echo "✅ Environment configured"
echo "📦 Starting server with uv..."
echo ""

uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
