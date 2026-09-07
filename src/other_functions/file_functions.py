from glob import glob
import time
from typing import Literal
import os

from src.other_functions.date_functions import get_cur_date_string
from src.read_config import get_config

# First parameters
folder_name = get_config("download-folder")
download_path = os.path.join(os.getcwd(), folder_name) # type: ignore

# Name Functions
def generate_download_name(type:Literal['part','grades'] , id:int)->str:
    """
    Generates a name from the date and the type of data.
    """
    if type == 'part':
        main_name = 'part'
    elif type == 'grades':
        main_name = 'grad'
    return f'{main_name} ID{id} {get_cur_date_string()}.csv'

# Global File Functions
def rename_file(file_path:str, new_name:str):
    """
    Function to rename a file into a new specified name.
    ### Params:
    - ```file_path: str```: Path for the file that is wanted to be renamed.
    - ```new_name: str```: New name for the file
    """
    # Checking if the file exists
    if os.path.isfile(file_path):
        # Obtain the directory path
        directory = os.path.dirname(file_path)
        # Create the new path
        new_path = os.path.join(directory, new_name)
        # Rename the path of the file
        os.rename(file_path, new_path)
    else:
        print(f'File {file_path} not found.')

# Download Folder Functions
def check_download_folder():
    """
    Function to check if the download folder *"path"* exists in the main folder.\\
    If do not exist, then creates the folder.
    """
    if not os.path.exists(download_path):
        os.mkdir(download_path)
        print('- Download folder not found.')
        print('-- New download folder created. --')

def count_csv_downloads() -> int:
    """
    Function to count all the csv files in the download folder. Returns a int number with the number counted.
    """
    csv_files = [f for f in os.listdir(download_path) if f.endswith('.csv')]
    return len(csv_files)

def get_downloads() -> list[str]:
    """
    Returns a list of all the downloads paths on the download folder.
    """
    return glob(os.path.join(download_path, '*'))

def get_last_download() -> str:
    """
    Returns the path of the last download in the download folder.
    """
    return max(get_downloads(), key=os.path.getctime)

# Download File Functions
def rename_last_download(new_name):
    """
    Function to rename the last download.
    ### Params:
    - ```new_name: str```: New name for the file.
    """
    rename_file(get_last_download(), new_name)

def auto_rename_last_download(type:Literal['part','grades'] , id:int):
    rename_last_download(generate_download_name(type, id))
    return 

# Aditional Functions
def wait_for_download(initial_count:int):
    """
    Function to force the driver to wait until the download is ready.
    """
    while count_csv_downloads() == initial_count:
        time.sleep(0.5)

if __name__ == '__main__':
    print(get_last_download())