import os
import platform
import logging
import re
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError, UnsupportedError
from pathlib import Path


YOUTUBE_FACEBOOK_URL_REGEX = re.compile(
    r'(https?://)?(www\.)?(youtube\.com|youtu\.be|facebook\.com)/(shorts/|reel/|watch\?v=|video/|v/|.+/videos/|.+/reels/)?'
)

def is_valid_video_url(url):
    return bool(YOUTUBE_FACEBOOK_URL_REGEX.match(url))

def auto_detect_ffmpeg(settings_manager):
    if platform.system() == 'Windows':
        ffmpeg_path = 'C:/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe'
        ffprobe_path = 'C:/ffmpeg-7.0.2-essentials_build/bin/ffprobe.exe'
    elif platform.system() == 'Linux':
        ffmpeg_path = '/usr/bin/ffmpeg'
        ffprobe_path = '/usr/bin/ffprobe'
    elif platform.system() == 'Darwin':
        ffmpeg_path = '/usr/local/bin/ffmpeg'
        ffprobe_path = '/usr/local/bin/ffprobe'
    else:
        ffmpeg_path = ''
        ffprobe_path = ''

    if os.path.isfile(ffmpeg_path) and os.path.isfile(ffprobe_path):
        settings_manager.ffmpeg_path = ffmpeg_path
        settings_manager.ffprobe_path = ffprobe_path
        logging.info(f"FFmpeg Path: {settings_manager.ffmpeg_path}")
        logging.info(f"FFprobe Path: {settings_manager.ffprobe_path}")
    else:
        logging.error("FFmpeg and FFprobe are not installed. Please install them.")

def is_valid_executable(path):
    if not os.path.isfile(path):
        return False
    if platform.system() == 'Windows':
        return path.endswith(".exe") and os.access(path, os.X_OK)
    return os.access(path, os.X_OK)