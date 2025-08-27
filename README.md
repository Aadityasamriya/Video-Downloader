# 🎬 Telegram Video Downloader Bot

A powerful Telegram bot that can download videos and files from 1000+ platforms including YouTube, Instagram, Twitter/X, TikTok, Facebook, Reddit, Pinterest, Terabox, and many more.

## ✨ Features

- **Universal Download Support**: Downloads from YouTube, Instagram, Twitter/X, TikTok, Facebook, Reddit, Pinterest, Terabox, and 1000+ other platforms
- **Smart File Handling**: Automatically detects and sends files as video, audio, or document
- **File Compression**: Compresses large files to fit Telegram's 50MB limit using FFmpeg
- **Progress Tracking**: Real-time download progress updates
- **Rate Limiting**: 5 requests per minute per user to prevent abuse
- **User Statistics**: Track downloads, file sizes, and platform usage
- **Error Recovery**: Graceful handling of network issues and invalid links
- **Async Processing**: Handle multiple downloads simultaneously

## 🚀 Quick Deploy on Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

### Automatic Deployment:
1. Click the Railway button above
2. Connect your GitHub account
3. Fork this repository
4. Set your `BOT_TOKEN` environment variable
5. Deploy automatically!

### Manual Deployment:
1. Clone this repository
2. Connect to Railway: `railway login`
3. Create new project: `railway init`
4. Set environment variable: `railway variables set BOT_TOKEN=your_bot_token_here`
5. Deploy: `railway up`

## 🤖 Getting Your Bot Token

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Choose a name and username for your bot
4. Copy the bot token (format: `123456789:ABCdefGhIJKlmNoPQRsTuVwXyZ`)
5. Add it as `BOT_TOKEN` environment variable

## 📋 Bot Commands

- `/start` - Welcome message and instructions
- `/help` - Show supported platforms and usage guide
- `/stats` - View your personal download statistics
- **Send any link** - Bot will automatically download and send the file

## 🌐 Supported Platforms

- **Video Platforms**: YouTube, Dailymotion, Vimeo, Twitch
- **Social Media**: Instagram, Twitter/X, TikTok, Facebook, Reddit
- **File Sharing**: Terabox, Google Drive, Dropbox
- **Image Platforms**: Pinterest, Flickr, Imgur
- **And 1000+ more** powered by yt-dlp

## ⚙️ Configuration

### Environment Variables
- `BOT_TOKEN` - Your Telegram bot token (required)

### File Limits
- Maximum file size: 50MB (Telegram limit)
- Maximum download size: 500MB (compressed if larger)
- Rate limit: 5 requests per 60 seconds per user

## 🛠️ Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/telegram-video-bot.git
cd telegram-video-bot

# Install dependencies
pip install -r railway-requirements.txt

# Set environment variable
export BOT_TOKEN="your_bot_token_here"

# Run the bot
python main.py
```

## 📁 Project Structure

```
├── main.py              # Entry point and startup logic
├── bot.py               # Main bot class and command handlers
├── downloader.py        # Video downloading logic using yt-dlp
├── utils.py             # Utility functions and helpers
├── config.py            # Configuration settings
├── temp/                # Temporary download directory
├── railway-requirements.txt # Python dependencies
├── nixpacks.toml        # Nixpacks configuration
├── railway.json         # Railway deployment settings
└── Procfile             # Process definition
```

## 🔧 Advanced Features

### Rate Limiting
- Per-user rate limiting prevents spam
- Configurable limits in `config.py`
- Automatic cleanup of old requests

### File Management
- Automatic temporary file cleanup
- Safe filename sanitization
- Progress tracking with callbacks

### Error Handling
- Comprehensive logging system
- Graceful error recovery
- User-friendly error messages

## 📈 Monitoring

The bot includes built-in logging and monitoring:
- Download success/failure rates
- User statistics and usage patterns
- Performance metrics and error tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## ⚠️ Disclaimer

This bot is for educational and personal use only. Ensure you comply with the terms of service of the platforms you're downloading from and respect copyright laws.

---

**Made with ❤️ for the Telegram community**