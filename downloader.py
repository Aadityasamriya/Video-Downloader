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

from config import MAX_DOWNLOAD_SIZE, DOWNLOAD_TIMEOUT
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
    
    def _get_ydl_opts(self, output_path: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Get yt-dlp options"""
        opts = {
            'outtmpl': output_path,
            'format': 'best[filesize<{}]'.format(MAX_DOWNLOAD_SIZE),
            'noplaylist': True,
            'no_warnings': False,
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'prefer_free_formats': True,
            'merge_output_format': 'mp4',
            # Add headers to avoid blocking
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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
                with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                    try:
                        info = ydl.extract_info(url, download=False)
                        return info
                    except Exception as e:
                        logger.error(f"Error extracting info for {url}: {e}")
                        return None
            
            info = await loop.run_in_executor(self.executor, _get_info)
            
            if info:
                # Extract useful information
                result = {
                    'title': info.get('title', 'Unknown Title'),
                    'duration': info.get('duration', 0),
                    'filesize': info.get('filesize', 0) or info.get('filesize_approx', 0),
                    'ext': info.get('ext', 'mp4'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', ''),
                    'formats': info.get('formats', []),
                    'thumbnail': info.get('thumbnail', ''),
                    'description': info.get('description', ''),
                    'view_count': info.get('view_count', 0),
                    'platform': info.get('extractor_key', 'Unknown')
                }
                return result
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
        
        return None
    
    async def download_video(self, url: str, progress_callback: Optional[Callable] = None) -> Optional[str]:
        """Download video/file from URL"""
        try:
            # Get video info first
            info = await self.get_video_info(url)
            if not info:
                return None
            
            # Check file size
            if info.get('filesize', 0) > MAX_DOWNLOAD_SIZE:
                raise Exception(f"File too large: {format_file_size(info['filesize'])}")
            
            # Generate output path
            title = sanitize_filename(info.get('title', 'download'))
            ext = info.get('ext', 'mp4')
            output_path = self.file_manager.get_temp_path(url, ext)
            
            # Prepare template for yt-dlp
            output_template = output_path.replace(f'.{ext}', '.%(ext)s')
            
            # Download
            loop = asyncio.get_event_loop()
            
            def _download():
                ydl_opts = self._get_ydl_opts(output_template, progress_callback)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        ydl.download([url])
                        
                        # Find the downloaded file
                        base_path = output_path.replace(f'.{ext}', '')
                        for possible_ext in ['mp4', 'webm', 'mkv', 'avi', 'mov', 'mp3', 'm4a', 'wav', ext]:
                            possible_path = f"{base_path}.{possible_ext}"
                            if os.path.exists(possible_path):
                                return possible_path
                        
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
    
    def __del__(self):
        """Cleanup executor"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
