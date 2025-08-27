#!/bin/bash

# Telegram Video Downloader Bot - Deployment Script
# This script helps deploy the bot to various platforms

echo "🚀 Telegram Video Downloader Bot Deployment"
echo "==========================================="

# Check if BOT_TOKEN is provided
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Error: BOT_TOKEN environment variable is required"
    echo "💡 Get your token from @BotFather on Telegram"
    echo "💡 Then run: export BOT_TOKEN='your_token_here'"
    exit 1
fi

echo "✅ BOT_TOKEN found"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r railway-requirements.txt

# Create temp directory
echo "📁 Setting up temporary directory..."
mkdir -p temp

# Check if FFmpeg is available
if command -v ffmpeg >/dev/null 2>&1; then
    echo "✅ FFmpeg is available for video compression"
else
    echo "⚠️  FFmpeg not found - video compression disabled"
    echo "💡 Install FFmpeg for better video handling"
fi

echo "🎬 Starting Telegram Video Downloader Bot..."
echo "📱 Your bot is ready to receive video links!"
echo "🔗 Send any video link from supported platforms to your bot"

# Start the bot
python main.py