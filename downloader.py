"""
Video/File downloader using yt-dlp for multiple platforms
"""
import os
import yt_dlp
import tempfile
from typing import Optional, Dict, Any, Callable
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import subprocess
import json

from config import MAX_DOWNLOAD_SIZE, DOWNLOAD_TIMEOUT, LARGE_FILE_THRESHOLD
from utils import FileManager, format_file_size, sanitize_filename

logger = logging.getLogger(__name__)

class DownloadProgress:
    """Track download progress"""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
        self.last_progress = 0
    
    def __call__(self, d):
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes']:
                progress = int((d['downloaded_bytes'] / d['total_bytes']) * 100)
                if progress != self.last_progress and progress % 10 == 0:  # Update every 10%
                    self.last_progress = progress
                    if self.progress_callback:
                        asyncio.create_task(self.progress_callback(progress))

class VideoDownloader:
    """Main downloader class using yt-dlp"""
    
    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    def _get_ydl_opts(self, output_path: str, progress_callback: Optional[Callable] = None, format_selector: Optional[str] = None) -> Dict[str, Any]:
        """Get yt-dlp options"""
        # Use best available format under size limit if no specific format requested
        if not format_selector:
            format_selector = f'(best[height<=1080][filesize<{MAX_DOWNLOAD_SIZE}]/best[filesize<{MAX_DOWNLOAD_SIZE}]/best)'
            
        opts = {
            'outtmpl': output_path,
            'format': format_selector,
            'noplaylist': True,
            'no_warnings': False,
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': False,
            'no_check_certificate': True,
            'prefer_free_formats': True,
            'merge_output_format': 'mp4',
            'socket_timeout': 60,
            'retries': 5,
            'fragment_retries': 10,
            'extractor_retries': 3,
            # Add headers to avoid blocking
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            },
            # Platform-specific configurations
            'extractor_args': {
                'instagram': {
                    'include_stories': False,
                    'include_feed': True
                },
                'twitter': {
                    'legacy_api': True
                },
                'youtube': {
                    'skip_dash_manifest': False,
                    'player_skip_initial_attempt': True
                }
            }
        }
        
        if progress_callback:
            opts['progress_hooks'] = [DownloadProgress(progress_callback)]
        
        return opts
    
    async def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get video information without downloading"""
        try:
            loop = asyncio.get_event_loop()
            
            def _get_info():
                ydl_opts = {
                    'quiet': True, 
                    'no_warnings': True,
                    'socket_timeout': 30,
                    'retries': 3,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        info = ydl.extract_info(url, download=False)
                        return info
                    except Exception as e:
                        logger.error(f"Error extracting info for {url}: {e}")
                        return None
            
            info = await loop.run_in_executor(self.executor, _get_info)
            
            if info:
                # Get available quality formats
                available_formats = []
                formats = info.get('formats', [])
                
                for fmt in formats:
                    if fmt.get('vcodec') != 'none' and fmt.get('height'):  # Video formats only
                        quality = fmt.get('height', 0)
                        filesize = fmt.get('filesize') or fmt.get('filesize_approx') or 0
                        format_note = fmt.get('format_note', '')
                        
                        if quality >= 144 and filesize < MAX_DOWNLOAD_SIZE:  # Reasonable quality and size
                            available_formats.append({
                                'format_id': fmt.get('format_id'),
                                'quality': quality,
                                'filesize': filesize,
                                'ext': fmt.get('ext', 'mp4'),
                                'note': format_note
                            })
                
                # Sort by quality (highest first)
                available_formats.sort(key=lambda x: x['quality'], reverse=True)
                
                # Extract useful information
                result = {
                    'title': info.get('title', 'Unknown Title'),
                    'duration': info.get('duration', 0),
                    'filesize': info.get('filesize', 0) or info.get('filesize_approx', 0),
                    'ext': info.get('ext', 'mp4'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', ''),
                    'formats': info.get('formats', []),
                    'available_formats': available_formats,
                    'thumbnail': info.get('thumbnail', ''),
                    'description': info.get('description', ''),
                    'view_count': info.get('view_count', 0),
                    'platform': info.get('extractor_key', 'Unknown')
                }
                return result
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
        
        return None
    
    async def download_video(self, url: str, progress_callback: Optional[Callable] = None, format_selector: Optional[str] = None) -> Optional[str]:
        """Download video/file from URL"""
        try:
            # Get video info first
            info = await self.get_video_info(url)
            if not info:
                return None
            
            # Check file size - allow larger files now
            estimated_size = info.get('filesize', 0) or info.get('filesize_approx', 0)
            if estimated_size > MAX_DOWNLOAD_SIZE:
                raise Exception(f"File too large: {format_file_size(estimated_size)}. Maximum allowed: {format_file_size(MAX_DOWNLOAD_SIZE)}")
            
            # Generate output path
            title = sanitize_filename(info.get('title', 'download'))
            ext = info.get('ext', 'mp4')
            output_path = self.file_manager.get_temp_path(url, ext)
            
            # Prepare template for yt-dlp
            output_template = output_path.replace(f'.{ext}', '.%(ext)s')
            
            # Download
            loop = asyncio.get_event_loop()
            
            def _download():
                ydl_opts = self._get_ydl_opts(output_template, progress_callback, format_selector)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        ydl.download([url])
                        
                        # Find the downloaded file
                        base_path = output_path.replace(f'.{ext}', '')
                        downloaded_files = []
                        
                        # Check for common video/audio extensions
                        for possible_ext in ['mp4', 'webm', 'mkv', 'avi', 'mov', 'mp3', 'm4a', 'wav', 'flv', 'm4v', ext]:
                            possible_path = f"{base_path}.{possible_ext}"
                            if os.path.exists(possible_path):
                                downloaded_files.append(possible_path)
                        
                        if downloaded_files:
                            # Return the largest file (usually the main content)
                            return max(downloaded_files, key=lambda f: os.path.getsize(f) if os.path.exists(f) else 0)
                        
                        return None
                        
                    except Exception as e:
                        logger.error(f"yt-dlp download error: {e}")
                        return None
            
            # Run download with timeout
            file_path = await asyncio.wait_for(
                loop.run_in_executor(self.executor, _download),
                timeout=DOWNLOAD_TIMEOUT
            )
            
            if file_path and os.path.exists(file_path):
                logger.info(f"Successfully downloaded: {file_path}")
                return file_path
            else:
                logger.error("Download completed but file not found")
                return None
                
        except asyncio.TimeoutError:
            logger.error(f"Download timeout for {url}")
            raise Exception("Download timed out. The file might be too large or the connection is slow.")
        except Exception as e:
            logger.error(f"Download error for {url}: {e}")
            raise
    
    async def is_supported_url(self, url: str) -> bool:
        """Check if URL is supported by yt-dlp"""
        try:
            info = await self.get_video_info(url)
            return info is not None
        except:
            return False
    
    def compress_video(self, input_path: str, max_size_mb: int = 45) -> Optional[str]:
        """Compress video to reduce file size"""
        try:
            output_path = input_path.replace('.', '_compressed.')
            
            # Use ffmpeg to compress
            cmd = [
                'ffmpeg', '-i', input_path,
                '-vcodec', 'libx264',
                '-crf', '28',  # Compression level
                '-preset', 'fast',
                '-vf', 'scale=-2:720',  # Reduce to 720p max
                '-acodec', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',  # Overwrite output file
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(output_path):
                # Check if compressed file is smaller
                original_size = os.path.getsize(input_path)
                compressed_size = os.path.getsize(output_path)
                
                if compressed_size < original_size:
                    logger.info(f"Compressed {format_file_size(original_size)} -> {format_file_size(compressed_size)}")
                    return output_path
                else:
                    # If compression didn't help, remove compressed file
                    os.remove(output_path)
            
        except Exception as e:
            logger.error(f"Compression error: {e}")
        
        return None
    
    def split_large_file(self, input_path: str, max_size: int = 45 * 1024 * 1024) -> list[str]:
        """Split large files into smaller chunks for Telegram"""
        try:
            file_size = os.path.getsize(input_path)
            if file_size <= max_size:
                return [input_path]
            
            base_name = os.path.splitext(input_path)[0]
            base_ext = os.path.splitext(input_path)[1]
            split_files = []
            
            # Calculate number of parts needed
            num_parts = (file_size + max_size - 1) // max_size
            
            with open(input_path, 'rb') as input_file:
                for i in range(num_parts):
                    part_filename = f"{base_name}_part{i+1:03d}{base_ext}"
                    with open(part_filename, 'wb') as part_file:
                        chunk = input_file.read(max_size)
                        if chunk:
                            part_file.write(chunk)
                            split_files.append(part_filename)
                            logger.info(f"Created part {i+1}/{num_parts}: {part_filename}")
            
            return split_files
            
        except Exception as e:
            logger.error(f"Error splitting file: {e}")
            return [input_path]
    
    def get_platform_specific_opts(self, url: str) -> Dict[str, Any]:
        """Get platform-specific yt-dlp options"""
        platform_opts = {}
        
        if 'instagram.com' in url:
            platform_opts.update({
                'http_headers': {
                    'User-Agent': 'Instagram 76.0.0.15.395 Android (24/7.0; 640dpi; 1440x2560; samsung; SM-G930F; herolte; samsungexynos8890; en_US; 138226743)',
                    'X-IG-App-ID': '936619743392459'
                }
            })
        elif 'twitter.com' in url or 'x.com' in url:
            platform_opts.update({
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://twitter.com/'
                }
            })
        elif 'terabox.com' in url or '1024tera.com' in url:
            platform_opts.update({
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.terabox.com/'
                }
            })
        
        return platform_opts
    
    def __del__(self):
        """Cleanup executor"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
