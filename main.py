#!/usr/bin/env python3
"""
Telegram Video Downloader Bot
Main entry point for the application
"""
import os
import sys
import asyncio
import logging
import signal
import threading
from bot import TelegramVideoBot
from config import BOT_TOKEN, TEMP_DIR

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    
    try:
        import telegram
    except ImportError:
        missing_deps.append("python-telegram-bot")
    
    try:
        import yt_dlp
    except ImportError:
        missing_deps.append("yt-dlp")
    
    try:
        import validators
    except ImportError:
        missing_deps.append("validators")
    
    if missing_deps:
        logger.error(f"Missing dependencies: {', '.join(missing_deps)}")
        logger.error("Please install missing dependencies using pip:")
        for dep in missing_deps:
            logger.error(f"  pip install {dep}")
        return False
    
    return True

def check_ffmpeg():
    """Check if ffmpeg is available for video compression"""
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=10)
        if result.returncode == 0:
            logger.info("FFmpeg is available for video compression")
            return True
    except:
        pass
    
    logger.warning("FFmpeg not found. Video compression will be disabled.")
    logger.warning("Install FFmpeg for better video handling: https://ffmpeg.org/")
    return False

def setup_environment():
    """Setup the environment for the bot"""
    # Create temp directory if it doesn't exist
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR, exist_ok=True)
        logger.info(f"Created temporary directory: {TEMP_DIR}")
    
    # Check bot token
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        logger.error("Bot token not configured!")
        logger.error("Please set the BOT_TOKEN environment variable or update config.py")
        logger.error("Get your bot token from @BotFather on Telegram")
        return False
    
    return True

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}. Shutting down gracefully...")
    sys.exit(0)

def main():
    """Main function"""
    logger.info("Starting Telegram Video Downloader Bot...")
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check environment
    if not setup_environment():
        sys.exit(1)
    
    # Check optional dependencies
    check_ffmpeg()
    
    try:
        # Start simple HTTP server for Railway health check
        try:
            import http.server
            import socketserver
            
            class HealthHandler(http.server.SimpleHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/health' or self.path == '/':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(b'{"status":"healthy","service":"telegram-bot"}')
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def log_message(self, format, *args):
                    pass  # Suppress HTTP logs
            
            def start_health_server():
                try:
                    with socketserver.TCPServer(("", 8000), HealthHandler) as httpd:
                        httpd.serve_forever()
                except Exception as e:
                    logger.error(f"Health server error: {e}")
            
            health_thread = threading.Thread(target=start_health_server, daemon=True)
            health_thread.start()
            logger.info("Health check server started on port 8000 for Railway")
        except Exception as e:
            logger.warning(f"Could not start health server: {e}")
        
        # Create and run bot
        bot = TelegramVideoBot()
        logger.info("Bot initialized successfully")
        
        # Log supported platforms info
        logger.info("Bot supports downloading from:")
        logger.info("- YouTube, Instagram, Twitter/X, TikTok")
        logger.info("- Facebook, Reddit, Pinterest, Dailymotion")
        logger.info("- Vimeo, Terabox, and many more platforms")
        
        # Keep the process alive
        logger.info("Bot is running 24x7. Press Ctrl+C to stop.")
        logger.info("Bot will automatically restart if it crashes.")
        
        # Start the bot
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        # Don't exit immediately, try to restart
        logger.info("Attempting to restart in 5 seconds...")
        import time
        time.sleep(5)
        main()  # Restart

if __name__ == "__main__":
    main()
