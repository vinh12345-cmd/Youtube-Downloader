import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import logging
from PIL import Image, ImageTk
from pytube import YouTube
import requests
import ttkbootstrap as tb
from settings_manager import SettingsManager
from utils import is_valid_video_url, auto_detect_ffmpeg, is_valid_executable, YOUTUBE_FACEBOOK_URL_REGEX
import os
from pathlib import Path
import platform
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError, UnsupportedError
import re
import asyncio
import aiohttp
import time
import itertools

ANSI_ESCAPE = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
class YouTubeDownloaderApp:
    translations = {
        'en': {
            'welcome': 'Welcome to the YouTube Downloader',
            'youtube_url': 'YouTube/Facebook Video URL:',
            'download_audio': 'Download Audio',
            'download_video': 'Download Video',
            'choose_language': 'Choose Language:',
            'choose_format': 'Choose Format:',
            'choose_audio_quality': 'Choose Audio Quality:',
            'choose_video_quality': 'Choose Video Quality:',
            'choose_save_path': 'Choose Save Path',
            'browse': 'Browse',
            'success': 'Download successful!',
            'error': 'An error occurred: ',
            'ffmpeg_path': 'Set FFmpeg Path:',
            'ffprobe_path': 'Set FFprobe Path:',
            'settings': 'Settings',
            'save': 'Save Settings',
            'cancel_download': 'Cancel Download',
            'paste': 'Paste',
            'choose audio format': 'Choose Audio Format:',
            'fetch_info': 'Fetch Video Info',
        },
        'vi': {
            'welcome': 'Chào mừng bạn đến với Trình tải xuống YouTube',
            'youtube_url': 'URL Video YouTube/Facebook:',
            'download_audio': 'Tải xuống âm thanh',
            'download_video': 'Tải xuống video',
            'choose_language': 'Chọn ngôn ngữ:',
            'choose_format': 'Chọn định dạng:',
            'choose_audio_quality': 'Chọn chất lượng âm thanh:',
            'choose_video_quality': 'Chọn chất lượng video:',
            'choose_save_path': 'Chọn Đường dẫn Lưu',
            'browse': 'Duyệt',
            'success': 'Tải xuống thành công!',
            'error': 'Đã xảy ra lỗi: ',
            'ffmpeg_path': 'Đặt Đường dẫn FFmpeg:',
            'ffprobe_path': 'Đặt Đường dẫn FFprobe:',
            'settings': 'Cài đặt',
            'save': 'Lưu Cài đặt',
            'cancel_download': 'Hủy Tải xuống',
            'paste': 'Dán',
            'choose audio format': 'Chọn định dạng âm thanh:',
            'fetch_info': 'Lấy thông tin video',
        }
    }

    audio_quality_mapping = {
        '128 kbps': '128',
        '192 kbps': '192',
        '320 kbps': '320',
    }

    video_quality_mapping = {
        '720p': '720',
        '1080p': '1080',
        '1440p': '1440',
        '2160p (4K)': '2160',
    }

    AUDIO_QUALITY_CHOICES = ['128 kbps', '192 kbps', '320 kbps']
    VIDEO_QUALITY_CHOICES = ['720p', '1080p', '1440p', '2160p (4K)']
    AUDIO_FORMAT_CHOICES = ['mp3', 'aac', 'wav', 'flac'] 

    def __init__(self, root):
        self.root = root
        self.settings_manager = SettingsManager()
        self.current_language = self.settings_manager.language
        self._stop_event = threading.Event()
        self.queue = queue.Queue()
        self.init_ui()
        auto_detect_ffmpeg(self.settings_manager)
        self.progress_window = None
        self.path_var.set(self.settings_manager.save_path)
        self.settings_manager.load_settings()
        self.switch_theme(self.settings_manager.theme)
        self.update_texts()
        self.settings_manager.save_settings()
        self.settings_manager.load_settings()

    def init_ui(self):
        style = tb.Style(theme=self.settings_manager.theme)

        try:
            self.root.iconbitmap('assets/favicon.ico')
        except Exception as e:
            logging.warning(f"Failed to set window icon: {str(e)}")
        self.root.wm_attributes("-toolwindow", False)
        self.root.after(10, lambda: self.root.attributes('-topmost', False))

        nav_frame = ttk.Frame(self.root)
        nav_frame.pack(side=tk.TOP, fill=tk.X)

        try:
            original_image = Image.open("assets/setting.png")
            resized_image = original_image.resize((12, 12), Image.LANCZOS) 
            self.settings_image = ImageTk.PhotoImage(resized_image)
        except Exception as e:
            logging.error(f"Failed to load settings image: {str(e)}")
            self.settings_image = None

        if self.settings_image:
            self.settings_button = ttk.Button(nav_frame, image=self.settings_image, command=self.open_settings_window)
        else:
            self.settings_button = ttk.Button(nav_frame, text=self.translations[self.current_language]['settings'],
                                              command=self.open_settings_window)
        self.settings_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.language_label = ttk.Label(nav_frame, text=self.translations[self.current_language]['choose_language'])
        self.language_label.pack(side=tk.LEFT, padx=5)
        language_var = tk.StringVar(value=self.current_language)
        ttk.Radiobutton(nav_frame, text="English", variable=language_var, value='en',
                        command=lambda: self.switch_language('en')).pack(side=tk.LEFT)
        ttk.Radiobutton(nav_frame, text="Tiếng Việt", variable=language_var, value='vi',
                        command=lambda: self.switch_language('vi')).pack(side=tk.LEFT)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=5)
        self.url_label = ttk.Label(url_frame, text="Video URL (YouTube/Facebook):")
        self.url_label.pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5)
        self.url_entry.bind("<KeyRelease>", lambda event: self.validate_inputs())
        self.url_entry.bind("<Control-v>", self.paste_url_event)

        self.paste_button = ttk.Button(url_frame, text=self.translations[self.current_language]['paste'], command=self.paste_url)
        self.paste_button.pack(side=tk.LEFT, padx=5)

        self.title_label = ttk.Label(main_frame, text="Title will appear here")
        self.title_label.pack(pady=5)
        self.thumbnail_label = ttk.Label(main_frame)
        self.thumbnail_label.pack(pady=5)

        quality_frame = ttk.Frame(main_frame)
        quality_frame.pack(fill=tk.X, pady=5)
        self.audio_quality_label = ttk.Label(quality_frame, text=self.translations[self.current_language]['choose_audio_quality'])
        self.audio_quality_label.pack(side=tk.LEFT)
        self.audio_quality_var = tk.StringVar(value=self.AUDIO_QUALITY_CHOICES[1])
        audio_quality_dropdown = ttk.Combobox(quality_frame, textvariable=self.audio_quality_var, values=self.AUDIO_QUALITY_CHOICES)
        audio_quality_dropdown.pack(side=tk.LEFT, padx=5)

        self.video_quality_label = ttk.Label(quality_frame, text=self.translations[self.current_language]['choose_video_quality'])
        self.video_quality_label.pack(side=tk.LEFT, padx=5)
        self.video_quality_var = tk.StringVar(value=self.VIDEO_QUALITY_CHOICES[1])
        video_quality_dropdown = ttk.Combobox(quality_frame, textvariable=self.video_quality_var, values=self.VIDEO_QUALITY_CHOICES)
        video_quality_dropdown.pack(side=tk.LEFT, padx=5)

        format_frame = ttk.Frame(main_frame)
        format_frame.pack(fill=tk.X, pady=5)

        self.audio_format_label = ttk.Label(format_frame, text="Choose Audio Format:")
        self.audio_format_label.pack(side=tk.LEFT, padx=5)
        self.audio_format_var = tk.StringVar(value=self.AUDIO_FORMAT_CHOICES[0])
        audio_format_dropdown = ttk.Combobox(format_frame, textvariable=self.audio_format_var, values=self.AUDIO_FORMAT_CHOICES)
        audio_format_dropdown.pack(side=tk.LEFT, padx=5)

        self.format_label = ttk.Label(format_frame, text=self.translations[self.current_language]['choose_format'])
        self.format_label.pack(side=tk.LEFT, padx=5)
        self.format_var = tk.StringVar(value='mp4')
        format_dropdown = ttk.Combobox(format_frame, textvariable=self.format_var, values=['mp4', 'avi', 'mkv'])
        format_dropdown.pack(side=tk.LEFT, padx=5)

        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=5)
        self.path_label = ttk.Label(path_frame, text=self.translations[self.current_language]['choose_save_path'])
        self.path_label.pack(side=tk.LEFT)
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=50)
        self.path_entry.pack(side=tk.LEFT, padx=5)
        self.browse_button = ttk.Button(path_frame, text=self.translations[self.current_language]['browse'],
                                        command=self.browse_folder)
        self.browse_button.pack(side=tk.LEFT, padx=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        self.download_audio_button = ttk.Button(button_frame, text=self.translations[self.current_language]['download_audio'],
                                                state=tk.DISABLED,
                                                command=lambda: self.download_content_async('audio'))
        self.download_audio_button.pack(side=tk.LEFT, padx=5)

        self.download_video_button = ttk.Button(button_frame, text=self.translations[self.current_language]['download_video'],
                                                state=tk.DISABLED,
                                                command=lambda: self.download_content_async('video'))
        self.download_video_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text=self.translations[self.current_language]['cancel_download'],
                                        command=self.stop_download, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.pack(pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.browse_button.config(command=self.browse_folder)
        
        

    def paste_url_event(self, event):
        self.paste_url()
        return "break" 

    def clear_video_info(self):
        self.title_label.config(text="")
        self.thumbnail_label.config(image="")

    def paste_url(self):
        try:
            clipboard_content = self.root.clipboard_get().strip()
            logging.debug(f"Pasted URL: {clipboard_content}")
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, clipboard_content)
            self.validate_inputs()
            self.clear_video_info()
            if self.settings_manager.fetch_info_enabled:
                self.fetch_video_info(clipboard_content)
        except tk.TclError:
            messagebox.showerror("Error", "Failed to paste from clipboard.")

    async def fetch_facebook_video_info(self, session, url):
        try:
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                title = info_dict.get('title', 'Unknown Title')
                thumbnail_url = info_dict.get('thumbnail', '')
                logging.debug(f"Fetched Facebook video info: Title - {title}, Thumbnail - {thumbnail_url}")
                logging.debug(f"Full info dict: {info_dict}")

                self.title_label.config(text=title)
                if thumbnail_url:
                    await self.download_and_display_thumbnail_async(session, thumbnail_url)
        except yt_dlp.utils.DownloadError as e:
            logging.error(f"Download error: {str(e)}")
            messagebox.showerror("Error", f"Failed to fetch Facebook video info: {str(e)}")
        except Exception as e:
            logging.error(f"Error fetching Facebook video info: {str(e)}")
            messagebox.showerror("Error", f"Failed to fetch Facebook video info: {str(e)}")

    async def fetch_video_info_async(self, url):
        async with aiohttp.ClientSession() as session:
            if "youtube.com" in url or "youtu.be" in url:
                yt = YouTube(url)
                title = yt.title
                thumbnail_url = yt.thumbnail_url
                logging.debug(f"Fetched YouTube video info: Title - {title}, Thumbnail - {thumbnail_url}")
                self.title_label.config(text=title)
                if thumbnail_url:
                    await self.download_and_display_thumbnail_async(session, thumbnail_url)
            elif "facebook.com" in url:
                await self.fetch_facebook_video_info(session, url)


    async def download_and_display_thumbnail_async(self, session, thumbnail_url):
        try:
            async with session.get(thumbnail_url) as response:
                img_data = await response.read()
                with open('thumbnail.jpg', 'wb') as handler:
                    handler.write(img_data)

                img = Image.open('thumbnail.jpg')
                img = img.resize((300, 250), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                self.thumbnail_label.config(image=photo)
                self.thumbnail_label.image = photo
        except Exception as e:
            logging.error(f"Error downloading or displaying thumbnail: {str(e)}")
            messagebox.showerror("Error", f"Failed to display thumbnail: {str(e)}")

    async def download_and_display_thumbnail_async(self, session, thumbnail_url):
        try:
            async with session.get(thumbnail_url) as response:
                img_data = await response.read()
                with open('thumbnail.jpg', 'wb') as handler:
                    handler.write(img_data)

                img = Image.open('thumbnail.jpg')
                img = img.resize((300, 250), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                self.thumbnail_label.config(image=photo)
                self.thumbnail_label.image = photo
        except Exception as e:
            logging.error(f"Error downloading or displaying thumbnail: {str(e)}")
            messagebox.showerror("Error", f"Failed to display thumbnail: {str(e)}")

    def start_spinner(self):
        self.spinner_running = True
        self.spinner_chars = itertools.cycle(['|', '/', '-', '\\'])
        self.update_spinner()

    def stop_spinner(self):
        self.spinner_running = False
        self.thumbnail_label.config(text="") 

    def update_spinner(self):
        if self.spinner_running:
            self.thumbnail_label.config(text=f"Loading {next(self.spinner_chars)}")
            self.root.after(100, self.update_spinner)

    def fetch_video_info(self, url):
        self.start_spinner()
        threading.Thread(target=self.run_async_fetch, args=(url,), daemon=True).start()

    def run_async_fetch(self, url):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.fetch_video_info_async(url))
        finally:
            loop.close()
        self.root.after(0, self.stop_spinner)

    def check_fetch_task(self):
        if self.fetch_task.done():
            self.stop_spinner()
            try:
                self.fetch_task.result()
            except Exception as e:
                logging.error(f"Error fetching video info: {str(e)}")
                tk.messagebox.showerror("Error", f"Failed to fetch video info: {str(e)}")
        else:
            self.root.after(100, self.check_fetch_task)

    def download_content_async(self, download_type):
        self._stop_event.clear()
        self.cancel_button.config(state=tk.NORMAL)
        self.show_progress_window() 
        threading.Thread(target=self.download_content, args=(download_type,), daemon=True).start()
        self.root.after(100, self.process_queue)

    def download_content(self, download_type):
        if not self.check_ffmpeg_ffprobe():
            return

        video_url = self.url_entry.get()

        if not is_valid_video_url(video_url):
            self.queue.put(f"error:Invalid URL. Please enter a valid YouTube or Facebook URL.")
            return

        format_choice = self.format_var.get()
        selected_audio_quality = self.audio_quality_var.get()
        selected_video_quality = self.video_quality_var.get()
        selected_audio_format = self.audio_format_var.get() 

        audio_quality = self.audio_quality_mapping[selected_audio_quality]
        video_quality = self.video_quality_mapping[selected_video_quality]

        try:
            ydl_opts = {
                'format': f'bestaudio[abr<={audio_quality}]' if download_type == 'audio' else f'bestvideo[height<={video_quality}]+bestaudio/best',
                'outtmpl': os.path.join(self.path_var.get(), '%(title)s.%(ext)s'),
                'ffmpeg_location': self.settings_manager.ffmpeg_path,
                'ffprobe_location': self.settings_manager.ffprobe_path,
                'progress_hooks': [self.ydl_hook],
                'continuedl': True,
                'noprogress': True,
            }

            if download_type == 'audio':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': selected_audio_format,
                    'preferredquality': audio_quality,
                }]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            self.queue.put("complete") 

        except DownloadError as e:
            self.queue.put(f"error:Download error: {str(e)}")
        except ExtractorError as e:
            self.queue.put(f"error:Extractor error: {str(e)}")
        except UnsupportedError as e:
            self.queue.put(f"error:Unsupported error: {str(e)}")
        except FileNotFoundError as e:
            self.queue.put(f"error:FFmpeg or FFprobe was not found.")
        except Exception as e:
            self.queue.put(f"error:An unexpected error occurred: {str(e)}")

    def ydl_hook(self, d):
        if self._stop_event.is_set():
            raise Exception("Download canceled by user.")

        if d['status'] == 'downloading':
            percent_str = ANSI_ESCAPE.sub('', d['_percent_str']).strip('%')
            try:
                percent = float(percent_str)
                self.queue.put(percent)

                elapsed_time = d.get('elapsed', 0)
                total_bytes = d.get('total_bytes', 0)
                downloaded_bytes = d.get('downloaded_bytes', 0)
                download_speed = d.get('speed', 0)

                logging.debug(f"Elapsed time: {elapsed_time}, Total bytes: {total_bytes}, Downloaded bytes: {downloaded_bytes}, Download speed: {download_speed}")

                if download_speed and total_bytes and downloaded_bytes:
                    remaining_bytes = total_bytes - downloaded_bytes
                    remaining_time = remaining_bytes / download_speed
                    self.queue.put(('speed', download_speed))
                    self.queue.put(('remaining_time', remaining_time))

                    downloaded_mb = downloaded_bytes / (1024 * 1024)
                    total_mb = total_bytes / (1024 * 1024)
                    self.queue.put(('size', downloaded_mb, total_mb))

            except ValueError as e:
                logging.error(f"Error converting percent to float: {percent_str} - {str(e)}")

    def update_progress(self, percent):
        if self.progress_window:
            self.progress_bar['value'] = percent
            self.progress_label.config(text=f"Downloading... {percent:.2f}%")

    def process_queue(self):
        try:
            data = self.queue.get_nowait()
            if isinstance(data, float):
                self.update_progress(data)
            elif isinstance(data, tuple):
                if data[0] == 'speed':
                    self.update_speed(data[1])
                elif data[0] == 'remaining_time':
                    self.update_remaining_time(data[1])
                elif data[0] == 'size':
                    self.update_size(data[1], data[2])
            elif data == "complete":
                self.download_complete()
            elif isinstance(data, str) and data.startswith("error"):
                self.display_error(data.split(":")[1])

        except queue.Empty:
            pass

        self.root.after(100, self.process_queue)

    def update_speed(self, speed):
        if self.progress_window:
            speed_kbps = speed / 1024
            self.speed_label.config(text=f"Speed: {speed_kbps:.2f} KB/s")

    def update_remaining_time(self, remaining_time):
        if self.progress_window:
            minutes, seconds = divmod(remaining_time, 60)
            self.remaining_time_label.config(text=f"Remaining Time: {int(minutes)}m {int(seconds)}s")

    def download_complete(self):
        if self.progress_window:
            self.progress_bar['value'] = 100
            self.progress_label.config(text="Download complete!")
            self.progress_window.after(500, self.progress_window.destroy)

    def show_progress_window(self):
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("Download Progress")
        self.progress_window.geometry("300x150")
        self.progress_label = ttk.Label(self.progress_window, text="Downloading... 0%")
        self.progress_label.pack(pady=10)
        self.progress_bar = ttk.Progressbar(self.progress_window, orient="horizontal", length=200, mode="determinate")
        self.progress_bar.pack(pady=10)

        speed_size_frame = ttk.Frame(self.progress_window)
        speed_size_frame.pack(pady=5)

        self.speed_label = ttk.Label(speed_size_frame, text="Speed: 0 KB/s")
        self.speed_label.pack(side=tk.LEFT, padx=5)

        self.size_label = ttk.Label(speed_size_frame, text="0 MB / 0 MB")
        self.size_label.pack(side=tk.LEFT, padx=5)

        self.remaining_time_label = ttk.Label(self.progress_window, text="Remaining Time: 0m 0s")
        self.remaining_time_label.pack(pady=5)

    def update_size(self, downloaded_mb, total_mb):
        if self.progress_window:
            self.size_label.config(text=f"{downloaded_mb:.2f} MB / {total_mb:.2f} MB")

    def stop_download(self):
        self._stop_event.set()
        if self.progress_window:
            self.progress_window.destroy()

    def switch_language(self, lang):
        self.current_language = lang
        self.settings_manager.language = lang
        self.settings_manager.save_settings()
        self.update_texts()

    def update_texts(self):
        self.root.title(self.translations[self.current_language]['welcome'])
        self.url_label.config(text=self.translations[self.current_language]['youtube_url'])
        self.download_audio_button.config(text=self.translations[self.current_language]['download_audio'])
        self.download_video_button.config(text=self.translations[self.current_language]['download_video'])
        self.language_label.config(text=self.translations[self.current_language]['choose_language'])
        self.format_label.config(text=self.translations[self.current_language]['choose_format'])
        self.audio_quality_label.config(text=self.translations[self.current_language]['choose_audio_quality'])
        self.video_quality_label.config(text=self.translations[self.current_language]['choose_video_quality'])
        self.path_label.config(text=self.translations[self.current_language]['choose_save_path'])
        self.browse_button.config(text=self.translations[self.current_language]['browse'])
        self.settings_button.config(text=self.translations[self.current_language]['settings'])
        self.cancel_button.config(text=self.translations[self.current_language]['cancel_download'])
        self.paste_button.config(text=self.translations[self.current_language]['paste'])
        self.audio_format_label.config(text=self.translations[self.current_language]['choose audio format'])

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.path_var.set(folder_selected)
            self.settings_manager.save_path = folder_selected 
            self.settings_manager.save_settings() 
        elif not self.path_var.get():
            default_path = str(Path.home() / "Downloads")
            self.path_var.set(default_path)
        self.validate_inputs()

    def open_settings_window(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title(self.translations[self.current_language]['settings'])

        ffmpeg_label = tk.Label(settings_window, text=self.translations[self.current_language]['ffmpeg_path'])
        ffmpeg_label.pack(pady=5)
        ffmpeg_var = tk.StringVar(value=self.settings_manager.ffmpeg_path)
        ffmpeg_entry = tk.Entry(settings_window, textvariable=ffmpeg_var, width=50)
        ffmpeg_entry.pack(pady=5)

        ffprobe_button = tk.Button(settings_window, text=self.translations[self.current_language]['browse'],
                                   command=lambda: self.browse_executable(ffmpeg_var))
        ffprobe_button.pack(pady=5)

        ffprobe_label = tk.Label(settings_window, text=self.translations[self.current_language]['ffprobe_path'])
        ffprobe_label.pack(pady=5)
        ffprobe_var = tk.StringVar(value=self.settings_manager.ffprobe_path)
        ffprobe_entry = tk.Entry(settings_window, textvariable=ffprobe_var, width=50)
        ffprobe_entry.pack(pady=5)

        ffprobe_button = tk.Button(settings_window, text=self.translations[self.current_language]['browse'],
                                   command=lambda: self.browse_executable(ffprobe_var))
        ffprobe_button.pack(pady=5)

        theme_label = ttk.Label(settings_window, text="Choose Theme:")
        theme_label.pack(pady=5)
        theme_var = tk.StringVar(value=self.settings_manager.theme)
        theme_dropdown = ttk.Combobox(settings_window, textvariable=theme_var, values=tb.Style().theme_names())
        theme_dropdown.pack(pady=5)

        fetch_info_var = tk.BooleanVar(value=self.settings_manager.fetch_info_enabled)
        fetch_info_checkbox = tk.Checkbutton(settings_window, text=self.translations[self.current_language]['fetch_info'],
                                             variable=fetch_info_var)
        fetch_info_checkbox.pack(pady=5)

        save_button = tk.Button(settings_window, text=self.translations[self.current_language]['save'],
                                command=lambda: self.save_settings(ffmpeg_var.get(), ffprobe_var.get(), theme_var.get(), fetch_info_var.get(), settings_window))
        save_button.pack(pady=10)

    def browse_executable(self, var):
        file_selected = filedialog.askopenfilename(filetypes=[("Executables", "*.exe"), ("All files", "*.*")])
        if file_selected:
            var.set(file_selected)

    def save_settings(self, ffmpeg, ffprobe, theme, fetch_info_enabled, window):
        if not self.is_valid_executable(ffmpeg):
            messagebox.showerror("Invalid Path", "The FFmpeg path is not a valid executable.")
            return
        if not self.is_valid_executable(ffprobe):
            messagebox.showerror("Invalid Path", "The FFprobe path is not a valid executable.")
            return
        self.settings_manager.ffmpeg_path = ffmpeg
        self.settings_manager.ffprobe_path = ffprobe
        self.settings_manager.theme = theme
        self.settings_manager.save_settings()
        self.switch_theme(theme)
        self.settings_manager.fetch_info_enabled = fetch_info_enabled
        window.destroy()

    def is_valid_executable(self, path):
        if not os.path.isfile(path):
            return False
        if platform.system() == 'Windows':
            return path.endswith(".exe") and os.access(path, os.X_OK)
        return os.access(path, os.X_OK)

    def validate_inputs(self):
        url = self.url_entry.get()
        path = self.path_var.get()
        if self.is_valid_input(url, path):
            self.toggle_buttons(state=tk.NORMAL)
        else:
            self.toggle_buttons(state=tk.DISABLED)

    def is_valid_input(self, url, path):
        return is_valid_video_url(url) and bool(path)

    def toggle_buttons(self, state):
        self.download_audio_button.config(state=state)
        self.download_video_button.config(state=state)

    def is_valid_youtube_url(self, url):
        return bool(YOUTUBE_FACEBOOK_URL_REGEX.match(url))

    def switch_theme(self, theme_name):
        try:
            style = tb.Style(theme=theme_name)
            self.root.update()
        except Exception as e:
            logging.error(f"Failed to apply theme {theme_name}: {str(e)}")

    def check_ffmpeg_ffprobe(self):
        if not self.is_valid_executable(self.settings_manager.ffmpeg_path):
            self.display_error("Please set a valid FFmpeg path in the settings.")
            return False
        if not self.is_valid_executable(self.settings_manager.ffprobe_path):
            self.display_error("Please set a valid FFprobe path in the settings.")
            return False
        return True

    def reset_progress_bar(self):
        self.progress['value'] = 0
        self.status_label.config(text="")

    def display_error(self, message):
        full_message = f"Error: {message.strip()}"

        style = tb.Style()
        style.configure("Error.TLabel", foreground="red")

        self.status_label.config(text=full_message, style="Error.TLabel")

    def on_close(self):
        if self._stop_event.is_set():
            if messagebox.askokcancel("Quit", "Do you want to quit while downloading?"):
                self.stop_download()
                self.root.destroy()
        else:
            self.root.destroy()

        self.settings_manager.save_settings()

        if not os.path.isfile(self.settings_manager.ffmpeg_path) or not os.path.isfile(self.settings_manager.ffprobe_path):
            logging.error("FFmpeg/FFprobe not found. Please install them.")
            self.status_label.config(text="FFmpeg/FFprobe not found. Please install from https://www.gyan.dev/ffmpeg/builds/",)
    def prompt_missing_ffmpeg(self):
        open_settings = messagebox.askyesno(
            "FFmpeg/FFprobe Not Found",
            "FFmpeg and/or FFprobe are not found or incorrectly configured. Do you want to open the settings window to set the correct paths?"
        )

        if open_settings:
            self.open_settings_window()
        else:
            self.display_error("FFmpeg and FFprobe are required for this application. Please configure them in the settings.")

    def check_url(url):
        if is_valid_video_url(url):
            print("Valid YouTube URL")
        else:
            print("Invalid YouTube URL")
