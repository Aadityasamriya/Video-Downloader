"""
Utility functions for the Telegram Video Downloader Bot
"""
import os
import tempfile
import logging
import validators
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter for user requests"""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.user_requests: Dict[int, List[datetime]] = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to make a request"""
        now = datetime.now()
        
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        
        # Remove old requests outside the time window
        cutoff_time = now - timedelta(seconds=self.time_window)
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if req_time > cutoff_time
        ]
        
        # Check if under the limit
        if len(self.user_requests[user_id]) < self.max_requests:
            self.user_requests[user_id].append(now)
            return True
        
        return False
    
    def get_reset_time(self, user_id: int) -> int:
        """Get seconds until rate limit resets"""
        if user_id not in self.user_requests or not self.user_requests[user_id]:
            return 0
        
        oldest_request = min(self.user_requests[user_id])
        reset_time = oldest_request + timedelta(seconds=self.time_window)
        now = datetime.now()
        
        if reset_time > now:
            return int((reset_time - now).total_seconds())
        return 0

class FileManager:
    """Manage temporary files and cleanup"""
    
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        self.ensure_temp_dir()
    
    def ensure_temp_dir(self):
        """Ensure temporary directory exists"""
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir, exist_ok=True)
    
    def get_temp_path(self, url: str, extension: Optional[str] = None) -> str:
        """Generate a unique temporary file path"""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        timestamp = int(datetime.now().timestamp())
        
        if extension:
            filename = f"download_{timestamp}_{url_hash}.{extension}"
        else:
            filename = f"download_{timestamp}_{url_hash}"
        
        return os.path.join(self.temp_dir, filename)
    
    def cleanup_file(self, file_path: str):
        """Safely remove a file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {e}")
    
    def cleanup_old_files(self, max_age_hours: int = 1):
        """Remove old temporary files"""
        try:
            now = datetime.now()
            cutoff_time = now - timedelta(hours=max_age_hours)
            
            for filename in os.listdir(self.temp_dir):
                if filename == '.gitkeep':
                    continue
                    
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    if file_time < cutoff_time:
                        self.cleanup_file(file_path)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except:
            return 0

def validate_url(url: str) -> bool:
    """Validate if the provided string is a valid URL"""
    return validators.url(url) is True

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes = size_bytes / 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:90] + ext
    
    return filename

def extract_platform_from_url(url: str) -> str:
    """Extract platform name from URL for logging/display"""
    platforms = {
        'youtube.com': 'YouTube',
        'youtu.be': 'YouTube',
        'instagram.com': 'Instagram',
        'twitter.com': 'Twitter',
        'x.com': 'Twitter/X',
        'tiktok.com': 'TikTok',
        'facebook.com': 'Facebook',
        'reddit.com': 'Reddit',
        'pinterest.com': 'Pinterest',
        'dailymotion.com': 'Dailymotion',
        'vimeo.com': 'Vimeo',
        'terabox.com': 'Terabox',
    }
    
    url_lower = url.lower()
    for domain, platform in platforms.items():
        if domain in url_lower:
            return platform
    
    return "Unknown Platform"

async def run_with_timeout(coro, timeout: int):
    """Run a coroutine with timeout"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise Exception(f"Operation timed out after {timeout} seconds")

class UserStats:
    """Track user statistics"""
    
    def __init__(self):
        self.user_stats: Dict[int, Dict] = {}
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get statistics for a user"""
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {
                'downloads': 0,
                'total_size': 0,
                'first_use': datetime.now(),
                'last_use': datetime.now(),
                'platforms': set()
            }
        return self.user_stats[user_id]
    
    def record_download(self, user_id: int, platform: str, file_size: int):
        """Record a download for user statistics"""
        stats = self.get_user_stats(user_id)
        stats['downloads'] += 1
        stats['total_size'] += file_size
        stats['last_use'] = datetime.now()
        stats['platforms'].add(platform)
    
    def update_stats(self, user_id: int, file_size: int, platform: str):
        """Update user statistics (legacy method)"""
        self.record_download(user_id, platform, file_size)
    
    def format_user_stats(self, user_id: int) -> str:
        """Format user statistics for display"""
        stats = self.get_user_stats(user_id)
        
        return f"""📊 **Your Statistics**

🔢 Total Downloads: {stats['downloads']}
📦 Total Size: {format_file_size(stats['total_size'])}
📅 Member Since: {stats['first_use'].strftime('%Y-%m-%d')}
🕒 Last Used: {stats['last_use'].strftime('%Y-%m-%d %H:%M')}
🌐 Platforms Used: {len(stats['platforms'])}
"""
