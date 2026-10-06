from pathlib import Path

from selenium import webdriver


def get_driver_options(download_dir: Path, show_browser: bool = False) -> webdriver.ChromeOptions:
    options = webdriver.ChromeOptions()
    options.add_experimental_option('prefs', {
        'download.default_directory': str(download_dir.resolve()),  # Download path
        'download.prompt_for_download': False,  # No download dialog shown
        'download.directory_upgrade': True,
        'safebrowsing.enabled': True,
    })
    options.page_load_strategy = 'eager'
    options.add_argument('--window-size=1600,1000')
    if not show_browser:
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
    return options
