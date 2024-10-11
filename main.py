import tkinter as tk
from youtube_downloader import YouTubeDownloaderApp
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    try:
        root = tk.Tk()
        app = YouTubeDownloaderApp(root)
        root.mainloop()
    except tk.TclError as e:
        logging.error(f"Tkinter error: {str(e)}")
        tk.messagebox.showerror("Tkinter Error", f"Tkinter encountered an error: {str(e)}")
    except Exception as e:
        logging.error(f"Error during app launch: {str(e)}")
        tk.messagebox.showerror("Error", f"Failed to launch the app: {str(e)}")
