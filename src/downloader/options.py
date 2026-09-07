import os
from selenium import webdriver

from src.read_config import get_config

def get_driver_settings():
    # Getting global downloader config
    folder_name, no_ui, eager = get_config("download-folder", 'no-ui', 'eager')
    no_ui = get_config("no-ui")

    # Settings
    download_path = os.path.join(os.getcwd(), folder_name)
    downloader_options = webdriver.ChromeOptions()
    # Download path configuration
    prefs = {"download.default_directory": download_path,  # Download path
            "download.prompt_for_download": False,  # No download dialog shown
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True}

    # Initial configuration
    downloader_options.add_experimental_option("prefs", prefs)

    if eager:
        downloader_options.page_load_strategy = "eager"
    # -- If no-ui is on:
    if no_ui:
        downloader_options.add_argument('--headless')  # Headless execution
        downloader_options.add_argument('--disable-gpu')  # GPU aceleration off
        downloader_options.add_experimental_option("detach", False)
    return downloader_options