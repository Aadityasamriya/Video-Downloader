"""
Configuration settings for the Telegram Video Downloader Bot
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
# Railway and other cloud platforms use their own environment variables
load_dotenv(override=True)

# Bot Token from BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token_here")

# File size limits (in bytes)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB for Telegram
MAX_DOWNLOAD_SIZE = 500 * 1024 * 1024  # 500MB max download

# Temporary directory for downloads
TEMP_DIR = "./temp"

# Download timeout in seconds
DOWNLOAD_TIMEOUT = 300  # 5 minutes

# Rate limiting settings
RATE_LIMIT_REQUESTS = 5  # Max requests per user
RATE_LIMIT_WINDOW = 60   # Time window in seconds

# Supported platforms (for user information)
SUPPORTED_PLATFORMS = [
    "YouTube", "Instagram", "Twitter/X", "TikTok", "Facebook",
    "Reddit", "Pinterest", "Dailymotion", "Vimeo", "Terabox",
    "And many more platforms supported by yt-dlp"
]

# Bot messages
MESSAGES = {
    "start": """
🎬 **Video Downloader Bot** 🎬

Welcome! I can download videos and files from many platforms including:
• YouTube
• Instagram  
• Twitter/X
• TikTok
• Facebook
• Reddit
• Pinterest
• Terabox
• And many more!

📝 **How to use:**
Just send me any video link and I'll download it for you!

📋 **Commands:**
/start - Show this message
/help - Get help and supported platforms
/stats - Show your usage statistics

⚠️ **Note:** Files larger than 50MB will be compressed or split.
    """,
    
    "help": """
📚 **Help & Supported Platforms**

🔗 **Supported platforms:**
{}

📝 **How to use:**
1. Copy any video/file link
2. Send it to me
3. Wait for download to complete
4. Receive your file!

⚠️ **Limitations:**
• Max file size: 50MB (larger files will be compressed)
• Max download size: 500MB
• Rate limit: 5 requests per minute

🛠️ **Supported formats:**
• Video: MP4, AVI, MKV, etc.
• Audio: MP3, M4A, WAV, etc.
• Documents: PDF, ZIP, etc.
    """.format("\n".join([f"• {platform}" for platform in SUPPORTED_PLATFORMS])),
    
    "invalid_link": "❌ **Invalid Link**\n\nThe link you provided doesn't contain any downloadable content or is not supported.",
    
    "download_start": "⬇️ **Download Started**\n\nProcessing your link... Please wait.",
    
    "download_progress": "📥 **Downloading...** {progress}%",
    
    "download_complete": "✅ **Download Complete**\n\nUploading to Telegram...",
    
    "rate_limit": "⏰ **Rate Limit Exceeded**\n\nPlease wait before sending another request. Limit: {} requests per {} seconds.",
    
    "file_too_large": "📦 **File Too Large**\n\nThe file is larger than 50MB. Attempting to compress...",
    
    "error": "❌ **Error Occurred**\n\n{error}",
    
    "processing": "🔄 **Processing...**\n\nAnalyzing your link and preparing download..."
}
