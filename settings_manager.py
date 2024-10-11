import json
import os
import logging
from tkinter import messagebox

class SettingsManager:
    SETTINGS_FILE = "settings.json"

    def __init__(self):
        self.ffmpeg_path = ''
        self.ffprobe_path = ''
        self.save_path = ''
        self.theme = 'cosmo'
        self.language = 'en'
        self.fetch_info_enabled = True 
        self.load_settings()

    def load_settings(self):
        try:
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    self.ffmpeg_path = settings.get('ffmpeg_path', '')
                    self.ffprobe_path = settings.get('ffprobe_path', '')
                    self.save_path = settings.get('save_path', '')
                    self.theme = settings.get('theme', 'cosmo')
                    self.language = settings.get('language', 'en')
                    self.fetch_info_enabled = settings.get('fetch_info_enabled', True)
            else:
                logging.info(f"Settings file not found. Using default settings.")
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error loading settings: {str(e)}")
            messagebox.showerror("Error", "Failed to load settings. Default settings will be used.")

    def save_settings(self):
        settings = {
            'ffmpeg_path': self.ffmpeg_path,
            'ffprobe_path': self.ffprobe_path,
            'save_path': self.save_path,
            'theme': self.theme,
            'language': self.language,
            'fetch_info_enabled': self.fetch_info_enabled,
        }
        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(settings, f)
            logging.info(f"Settings saved to {self.SETTINGS_FILE}")
        except IOError as e:
            logging.error(f"Error saving settings: {str(e)}")
            messagebox.showerror("Error", "Failed to save settings.")