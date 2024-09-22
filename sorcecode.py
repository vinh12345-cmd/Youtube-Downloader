import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import yt_dlp
import os
import json

SETTINGS_FILE = "settings.json"

translations = {
    'en': {
        'welcome': 'Welcome to the YouTube Downloader',
        'youtube_url': 'YouTube Video URL:',
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
    },
    'vi': {
        'welcome': 'Chào mừng bạn đến với Trình tải xuống YouTube',
        'youtube_url': 'URL Video YouTube:',
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
    }
}

current_language = 'en'

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

ffmpeg_path = ''
ffprobe_path = ''
save_path = ''


def save_settings_to_file():
    global ffmpeg_path, ffprobe_path, save_path 
    settings = {
        'ffmpeg_path': ffmpeg_path,
        'ffprobe_path': ffprobe_path,
        'save_path': save_path  
    }
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)


def load_settings():
    global ffmpeg_path, ffprobe_path, save_path
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            ffmpeg_path = settings.get('ffmpeg_path', '')
            ffprobe_path = settings.get('ffprobe_path', '')
            save_path = settings.get('save_path', '')
            path_var.set(save_path) 


def download_audio():
    download_content('audio')


def download_video():
    download_content('video')


def download_content(download_type):
    video_url = url_entry.get()
    global save_path  

    if not video_url:
        messagebox.showerror("Error", translations[current_language]['error'] + " Please enter a valid YouTube URL")
        return

    if not save_path:
        messagebox.showerror("Error", translations[current_language]['error'] + " Please choose a save path")
        return

    format_choice = format_var.get()
    selected_audio_quality = audio_quality_var.get()
    selected_video_quality = video_quality_var.get()

    audio_quality = audio_quality_mapping[selected_audio_quality]
    video_quality = video_quality_mapping[selected_video_quality]

    try:
        ydl_opts = {
            'format': f'bestaudio[abr<={audio_quality}]' if download_type == 'audio' else f'bestvideo[height<={video_quality}]+bestaudio/best',
            'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),  
            'ffmpeg_location': ffmpeg_path,
            'ffprobe_location': ffprobe_path,
        }

        if download_type == 'audio':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': audio_quality,
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        messagebox.showinfo("Success", translations[current_language]['success'])

    except Exception as e:
        messagebox.showerror("Error", translations[current_language]['error'] + str(e))


def switch_language(lang):
    global current_language
    current_language = lang
    update_texts()


def update_texts():
    root.title(translations[current_language]['welcome'])
    url_label.config(text=translations[current_language]['youtube_url'])
    download_audio_button.config(text=translations[current_language]['download_audio'])
    download_video_button.config(text=translations[current_language]['download_video'])
    language_label.config(text=translations[current_language]['choose_language'])
    format_label.config(text=translations[current_language]['choose_format'])
    audio_quality_label.config(text=translations[current_language]['choose_audio_quality'])
    video_quality_label.config(text=translations[current_language]['choose_video_quality'])
    path_label.config(text=translations[current_language]['choose_save_path'])
    browse_button.config(text=translations[current_language]['browse'])
    settings_button.config(text=translations[current_language]['settings'])


def browse_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        path_var.set(folder_selected)  
        global save_path
        save_path = folder_selected  
        save_settings_to_file()  


def open_settings_window():
    settings_window = tk.Toplevel(root)
    settings_window.title(translations[current_language]['settings'])

    ffmpeg_label = tk.Label(settings_window, text=translations[current_language]['ffmpeg_path'])
    ffmpeg_label.pack(pady=5)
    ffmpeg_var = tk.StringVar(value=ffmpeg_path)
    ffmpeg_entry = tk.Entry(settings_window, textvariable=ffmpeg_var, width=50)
    ffmpeg_entry.pack(pady=5)
    ffmpeg_button = tk.Button(settings_window, text=translations[current_language]['browse'], command=lambda: browse_executable(ffmpeg_var))
    ffmpeg_button.pack(pady=5)

    ffprobe_label = tk.Label(settings_window, text=translations[current_language]['ffprobe_path'])
    ffprobe_label.pack(pady=5)
    ffprobe_var = tk.StringVar(value=ffprobe_path)
    ffprobe_entry = tk.Entry(settings_window, textvariable=ffprobe_var, width=50)
    ffprobe_entry.pack(pady=5)
    ffprobe_button = tk.Button(settings_window, text=translations[current_language]['browse'], command=lambda: browse_executable(ffprobe_var))
    ffprobe_button.pack(pady=5)

    save_button = tk.Button(settings_window, text=translations[current_language]['save'], command=lambda: save_settings(ffmpeg_var.get(), ffprobe_var.get(), settings_window))
    save_button.pack(pady=10)


def browse_executable(var):
    file_selected = filedialog.askopenfilename(filetypes=[("Executables", "*.exe"), ("All files", "*.*")])
    if file_selected:
        var.set(file_selected)


def save_settings(ffmpeg, ffprobe, window):
    global ffmpeg_path, ffprobe_path
    ffmpeg_path = ffmpeg
    ffprobe_path = ffprobe
    save_settings_to_file()
    window.destroy()


def validate_inputs():
    if url_entry.get() and path_var.get():
        download_audio_button.config(state=tk.NORMAL)
        download_video_button.config(state=tk.NORMAL)
    else:
        download_audio_button.config(state=tk.DISABLED)
        download_video_button.config(state=tk.DISABLED)


root = tk.Tk()
root.title(translations[current_language]['welcome'])
root.iconbitmap("favicon.ico")

nav_frame = tk.Frame(root)
nav_frame.pack(side=tk.TOP, fill=tk.X)

settings_button = tk.Button(nav_frame, text=translations[current_language]['settings'], command=open_settings_window)
settings_button.pack(side=tk.LEFT, padx=10, pady=10)

language_label = tk.Label(nav_frame, text=translations[current_language]['choose_language'])
language_label.pack(side=tk.LEFT, padx=5)
language_var = tk.StringVar(value='en')
tk.Radiobutton(nav_frame, text="English", variable=language_var, value='en', command=lambda: switch_language('en')).pack(side=tk.LEFT)
tk.Radiobutton(nav_frame, text="Tiếng Việt", variable=language_var, value='vi', command=lambda: switch_language('vi')).pack(side=tk.LEFT)

url_label = tk.Label(root, text=translations[current_language]['youtube_url'])
url_label.pack(pady=10)
url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)
url_entry.bind("<KeyRelease>", lambda event: validate_inputs())

format_label = tk.Label(root, text=translations[current_language]['choose_format'])
format_label.pack(pady=5)
format_var = tk.StringVar(value='mp4')
format_dropdown = ttk.Combobox(root, textvariable=format_var, values=['mp4', 'avi', 'mkv'])
format_dropdown.pack(pady=5)

audio_quality_label = tk.Label(root, text=translations[current_language]['choose_audio_quality'])
audio_quality_label.pack(pady=5)
audio_quality_var = tk.StringVar(value='192 kbps')
audio_quality_dropdown = ttk.Combobox(root, textvariable=audio_quality_var, values=['128 kbps', '192 kbps', '320 kbps'])
audio_quality_dropdown.pack(pady=5)

video_quality_label = tk.Label(root, text=translations[current_language]['choose_video_quality'])
video_quality_label.pack(pady=5)
video_quality_var = tk.StringVar(value='1080p')
video_quality_dropdown = ttk.Combobox(root, textvariable=video_quality_var, values=['720p', '1080p', '1440p', '2160p (4K)'])
video_quality_dropdown.pack(pady=5)

path_label = tk.Label(root, text=translations[current_language]['choose_save_path'])
path_label.pack(pady=5)
path_var = tk.StringVar()
path_entry = tk.Entry(root, textvariable=path_var, width=50)
path_entry.pack(pady=5)

browse_button = tk.Button(root, text=translations[current_language]['browse'], command=browse_folder)
browse_button.pack(pady=5)

download_audio_button = tk.Button(root, text=translations[current_language]['download_audio'], state=tk.DISABLED, command=download_audio)
download_audio_button.pack(pady=10)

download_video_button = tk.Button(root, text=translations[current_language]['download_video'], state=tk.DISABLED, command=download_video)
download_video_button.pack(pady=10)

load_settings()

root.mainloop()
