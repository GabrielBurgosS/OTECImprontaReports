import os

from src.downloader.autodownloader import AutoDownloader
from src.data_process.report_maker import auto_report_maker
from src.other_functions.report_name_generator import generate_report_name
from src.read_config import get_config

download_list = [
    (17, True),
    (20, True)
]

if __name__ == "__main__":
    output_folder = get_config("output-folder") # type: ignore
    os.makedirs(output_folder, exist_ok=True)

    downloader = AutoDownloader(download_list)
    for download in downloader.downloads:
        if download['success']:
            df = auto_report_maker(download)
            name = generate_report_name(download) + '.xlsx'
            df.to_excel(os.path.join(output_folder, name), index=False)