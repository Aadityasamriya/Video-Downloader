#!/bin/bash

# Telegram Video Downloader Bot - Railway Startup Script
echo "🚀 Starting Telegram Video Downloader Bot for Railway..."

# Set production environment
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Create temp directory
mkdir -p temp

# Verify BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Error: BOT_TOKEN environment variable is required"
    exit 1
fi

echo "✅ BOT_TOKEN configured"
echo "📦 Starting bot with Railway optimizations..."

# Start the bot
exec python main.py