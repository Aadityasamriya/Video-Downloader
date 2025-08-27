"""
Telegram Bot for Video/File Downloading
"""
import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from telegram.error import TelegramError

from config import BOT_TOKEN, MESSAGES, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, MAX_FILE_SIZE, TEMP_DIR
from downloader import VideoDownloader
from utils import (
    RateLimiter, FileManager, UserStats, validate_url, 
    format_file_size, extract_platform_from_url, run_with_timeout
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramVideoBot:
    """Main Telegram Bot class"""
    
    def __init__(self):
        self.file_manager = FileManager(TEMP_DIR)
        self.downloader = VideoDownloader(self.file_manager)
        self.rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)
        self.user_stats = UserStats()
        self.active_downloads = {}  # Track active downloads per user
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) started the bot")
        
        await update.message.reply_text(
            MESSAGES["start"],
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(
            MESSAGES["help"],
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user_id = update.effective_user.id
        stats_text = self.user_stats.format_user_stats(user_id)
        
        await update.message.reply_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle URL messages from users"""
        user = update.effective_user
        user_id = user.id
        message_text = update.message.text.strip()
        
        # Check if user is already downloading
        if user_id in self.active_downloads:
            await update.message.reply_text(
                "⏳ **Please wait**\n\nYou already have an active download. Please wait for it to complete.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Validate URL
        if not validate_url(message_text):
            await update.message.reply_text(MESSAGES["invalid_link"], parse_mode=ParseMode.MARKDOWN)
            return
        
        # Check rate limit
        if not self.rate_limiter.is_allowed(user_id):
            reset_time = self.rate_limiter.get_reset_time(user_id)
            await update.message.reply_text(
                MESSAGES["rate_limit"].format(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Add to active downloads
        self.active_downloads[user_id] = True
        
        try:
            await self._process_download(update, context, message_text)
        finally:
            # Remove from active downloads
            if user_id in self.active_downloads:
                del self.active_downloads[user_id]
    
    async def _process_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
        """Process the download request"""
        user_id = update.effective_user.id
        platform = extract_platform_from_url(url)
        
        logger.info(f"Processing download for user {user_id}: {url} ({platform})")
        
        # Send initial processing message
        processing_msg = await update.message.reply_text(
            MESSAGES["processing"],
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Check if URL is supported
            is_supported = await run_with_timeout(
                self.downloader.is_supported_url(url), 30
            )
            
            if not is_supported:
                await processing_msg.edit_text(MESSAGES["invalid_link"], parse_mode=ParseMode.MARKDOWN)
                return
            
            # Get video info
            await processing_msg.edit_text(
                "🔍 **Analyzing Video...**\n\nGetting video information...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            video_info = await self.downloader.get_video_info(url)
            if not video_info:
                await processing_msg.edit_text(MESSAGES["invalid_link"], parse_mode=ParseMode.MARKDOWN)
                return
            
            # Check if multiple quality options are available
            available_formats = video_info.get('available_formats', [])
            
            if len(available_formats) > 1:
                # Show quality selection
                info_text = f"""📹 **Video Found**

📝 **Title:** {video_info.get('title', 'Unknown')[:50]}...
👤 **Uploader:** {video_info.get('uploader', 'Unknown')}
🌐 **Platform:** {platform}
⏱️ **Duration:** {self._format_duration(video_info.get('duration', 0))}

📺 **Select Quality:**"""
                
                keyboard = []
                for fmt in available_formats[:6]:  # Show max 6 options
                    quality_text = f"{fmt['quality']}p"
                    if fmt['filesize'] > 0:
                        quality_text += f" ({format_file_size(fmt['filesize'])})"
                    
                    callback_data = f"quality_{user_id}_{fmt['format_id']}"
                    keyboard.append([InlineKeyboardButton(quality_text, callback_data=callback_data)])
                
                # Add default best quality option
                keyboard.append([InlineKeyboardButton("🎯 Best Quality (Auto)", callback_data=f"quality_{user_id}_best")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await processing_msg.edit_text(info_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
                
                # Store URL for later use
                context.user_data[f'pending_url_{user_id}'] = url
                context.user_data[f'video_info_{user_id}'] = video_info
                return
            
            # No quality options or single format - proceed with download
            info_text = f"""📹 **Video Found**

📝 **Title:** {video_info.get('title', 'Unknown')[:50]}...
👤 **Uploader:** {video_info.get('uploader', 'Unknown')}
🌐 **Platform:** {platform}
📦 **Size:** {format_file_size(video_info.get('filesize', 0)) if video_info.get('filesize') else 'Unknown'}
⏱️ **Duration:** {self._format_duration(video_info.get('duration', 0))}

⬇️ **Starting download...**"""
            
            await processing_msg.edit_text(info_text, parse_mode=ParseMode.MARKDOWN)
            
            # Progress callback
            async def progress_callback(progress):
                try:
                    await processing_msg.edit_text(
                        info_text + f"\n\n📥 **Progress:** {progress}%",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass  # Ignore edit errors
            
            # Download the file  
            file_path = await self.downloader.download_video(url, progress_callback, None)
            
            if not file_path:
                await processing_msg.edit_text(
                    MESSAGES["error"].format(error="Failed to download the file. The link might be invalid or the content is not accessible."),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            await processing_msg.edit_text(
                info_text + "\n\n✅ **Download complete!** Preparing to send...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Check file size and compress if needed
            file_size = self.file_manager.get_file_size(file_path)
            original_size = file_size
            
            if file_size > MAX_FILE_SIZE:
                await processing_msg.edit_text(
                    info_text + "\n\n🔄 **File too large, compressing...**",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                compressed_path = self.downloader.compress_video(file_path)
                if compressed_path:
                    # Clean up original and use compressed
                    self.file_manager.cleanup_file(file_path)
                    file_path = compressed_path
                    file_size = self.file_manager.get_file_size(file_path)
                
                if file_size > MAX_FILE_SIZE:
                    await processing_msg.edit_text(
                        MESSAGES["error"].format(error=f"File is too large ({format_file_size(file_size)}) even after compression. Maximum size is {format_file_size(MAX_FILE_SIZE)}."),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    self.file_manager.cleanup_file(file_path)
                    return
            
            # Send the file
            await processing_msg.edit_text(
                info_text + "\n\n📤 **Uploading to Telegram...**",
                parse_mode=ParseMode.MARKDOWN
            )
            
            await self._send_file(update, file_path, video_info)
            
            # Update user stats
            self.user_stats.update_stats(user_id, original_size, platform)
            
            # Clean up
            self.file_manager.cleanup_file(file_path)
            
            # Delete processing message
            try:
                await processing_msg.delete()
            except:
                pass
            
        except Exception as e:
            logger.error(f"Download error for user {user_id}: {e}")
            try:
                await processing_msg.edit_text(
                    MESSAGES["error"].format(error=str(e)),
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    async def _send_file(self, update: Update, file_path: str, video_info: dict):
        """Send file to user"""
        try:
            file_size = self.file_manager.get_file_size(file_path)
            filename = os.path.basename(file_path)
            
            # Prepare caption
            caption = f"""✅ **Download Complete**

📝 **Title:** {video_info.get('title', 'Unknown')[:100]}
👤 **Uploader:** {video_info.get('uploader', 'Unknown')}
📦 **Size:** {format_file_size(file_size)}
⏱️ **Duration:** {self._format_duration(video_info.get('duration', 0))}

🤖 @YourBotUsername"""
            
            # Determine file type and send accordingly
            file_extension = filename.split('.')[-1].lower()
            
            with open(file_path, 'rb') as file:
                if file_extension in ['mp4', 'avi', 'mkv', 'mov', 'webm']:
                    # Send as video
                    await update.message.reply_video(
                        video=file,
                        caption=caption[:1024],  # Telegram caption limit
                        parse_mode=ParseMode.MARKDOWN,
                        filename=filename,
                        supports_streaming=True
                    )
                elif file_extension in ['mp3', 'm4a', 'wav', 'ogg']:
                    # Send as audio
                    await update.message.reply_audio(
                        audio=file,
                        caption=caption[:1024],
                        parse_mode=ParseMode.MARKDOWN,
                        filename=filename,
                        title=video_info.get('title', 'Unknown')[:100],
                        performer=video_info.get('uploader', 'Unknown')
                    )
                else:
                    # Send as document
                    await update.message.reply_document(
                        document=file,
                        caption=caption[:1024],
                        parse_mode=ParseMode.MARKDOWN,
                        filename=filename
                    )
            
        except TelegramError as e:
            logger.error(f"Telegram error sending file: {e}")
            await update.message.reply_text(
                MESSAGES["error"].format(error="Failed to upload file to Telegram. The file might be corrupted or too large."),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            await update.message.reply_text(
                MESSAGES["error"].format(error=f"Failed to send file: {str(e)}"),
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def handle_quality_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle quality selection callback"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        callback_data = query.data
        
        if not callback_data.startswith(f'quality_{user_id}_'):
            await query.edit_message_text("❌ **Error**\n\nInvalid selection.", parse_mode=ParseMode.MARKDOWN)
            return
        
        format_id = callback_data.replace(f'quality_{user_id}_', '')
        
        # Get stored URL and info
        url = context.user_data.get(f'pending_url_{user_id}')
        video_info = context.user_data.get(f'video_info_{user_id}')
        
        if not url or not video_info:
            await query.edit_message_text("❌ **Error**\n\nSession expired. Please send the link again.", parse_mode=ParseMode.MARKDOWN)
            return
        
        # Clean up stored data
        context.user_data.pop(f'pending_url_{user_id}', None)
        context.user_data.pop(f'video_info_{user_id}', None)
        
        platform = extract_platform_from_url(url)
        
        # Determine format selector
        if format_id == 'best':
            format_selector = None  # Use default best quality
            quality_text = "Best Quality (Auto)"
        else:
            format_selector = f"{format_id}+bestaudio/best"
            # Find quality details
            selected_format = next((f for f in video_info.get('available_formats', []) if f['format_id'] == format_id), None)
            quality_text = f"{selected_format['quality']}p" if selected_format else "Selected Quality"
        
        info_text = f"""📹 **Starting Download**

📝 **Title:** {video_info.get('title', 'Unknown')[:50]}...
👤 **Uploader:** {video_info.get('uploader', 'Unknown')}
🌐 **Platform:** {platform}
📺 **Quality:** {quality_text}

⬇️ **Downloading...**"""
        
        await query.edit_message_text(info_text, parse_mode=ParseMode.MARKDOWN)
        
        try:
            # Progress callback
            async def progress_callback(progress):
                try:
                    await query.edit_message_text(
                        info_text + f"\n\n📥 **Progress:** {progress}%",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            
            # Download the file with selected quality
            file_path = await self.downloader.download_video(url, progress_callback, format_selector)
            
            if not file_path:
                await query.edit_message_text(
                    "❌ **Download Failed**\n\nThe file could not be downloaded. Please try again with a different quality.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            await query.edit_message_text(
                info_text + "\n\n✅ **Download complete!** Preparing to send...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Check file size and compress if needed
            file_size = self.file_manager.get_file_size(file_path)
            original_size = file_size
            
            if file_size > MAX_FILE_SIZE:
                await query.edit_message_text(
                    info_text + "\n\n🔄 **File too large, compressing...**",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                compressed_path = self.downloader.compress_video(file_path)
                if compressed_path:
                    self.file_manager.cleanup_file(file_path)
                    file_path = compressed_path
                    file_size = self.file_manager.get_file_size(file_path)
                
                if file_size > MAX_FILE_SIZE:
                    await query.edit_message_text(
                        f"❌ **File Too Large**\n\nFile is {format_file_size(file_size)} even after compression. Maximum size is {format_file_size(MAX_FILE_SIZE)}.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    self.file_manager.cleanup_file(file_path)
                    return
            
            # Send the file
            await query.edit_message_text(
                info_text + "\n\n📤 **Uploading to Telegram...**",
                parse_mode=ParseMode.MARKDOWN
            )
            
            await self._send_file(update, file_path, video_info)
            
            # Update user stats
            self.user_stats.update_stats(user_id, original_size, platform)
            
            # Clean up
            self.file_manager.cleanup_file(file_path)
            
            # Delete processing message
            try:
                await query.delete_message()
            except:
                pass
                
        except Exception as e:
            logger.error(f"Quality selection download error: {e}")
            await query.edit_message_text(
                f"❌ **Error**\n\n{str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )

    def _format_duration(self, seconds: int) -> str:
        """Format duration in human readable format"""
        if seconds <= 0:
            return "Unknown"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.message:
            try:
                await update.message.reply_text(
                    MESSAGES["error"].format(error="An unexpected error occurred. Please try again later."),
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    async def _cleanup_job(self, context):
        """Periodic cleanup job"""
        try:
            self.file_manager.cleanup_old_files()
            logger.info("Periodic cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup job error: {e}")
    
    def run(self):
        """Run the bot"""
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CallbackQueryHandler(self.handle_quality_selection))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url))
        
        # Add error handler
        application.add_error_handler(self.error_handler)
        
        # Schedule cleanup task to run periodically
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(self._cleanup_job, interval=3600, first=60)  # Run every hour, start after 1 minute
        
        logger.info("Bot started successfully!")
        logger.info("Bot is running 24x7 - polling for updates...")
        
        # Run the bot with better stability settings
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            timeout=30,
            drop_pending_updates=True
        )
