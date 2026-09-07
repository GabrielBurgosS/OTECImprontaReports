from tqdm import tqdm

from src.downloader.downloader_functions import ( 
    get_course_dictionary, 
    get_name,
    wd_download_grades,
    wd_download_participation,
    wd_login,
    )
from src.downloader.exceptions import *
from src.downloader.options import get_driver_settings
from src.other_functions.file_functions import (
    auto_rename_last_download,
    check_download_folder,
    count_csv_downloads,
    get_last_download,
    wait_for_download,
    )
from src.other_functions.internet_functions import check_internet_conn
from src.read_config import get_credentials
from src.downloader.selenium_webdriver import WebDriver

credentials = get_credentials()
    
# Main Class
class AutoDownloader:
    def __init__(self, download_list:list[tuple[int, bool]]):
        print(' -- Initializing AutoDownloader --\n')
        self.__download_list__ = download_list
        self.options = get_driver_settings()
        self.downloads = []
        self.__downloads_counter__ = count_csv_downloads()
        self.__launch_auto_download__()

    def __launch_auto_download__(self):
        self.__first_check__()
        print('Creating webdriver...')
        with WebDriver(self.options) as driver:
            self.driver = driver
            print('Driver created:', driver,'\n')
            self.__login__()
            self.__start_downloads__()
        self.summary()

    def __login__(self):
        
        wd_login(self.driver)
        
    def __first_check__(self):
        print('First check...')
        try:
            print(' - Checking download folder...', end=' ')
            check_download_folder()
            print('✓\n - Checking download list...', end=' ')
            if not self.__download_list__:
                raise ( DownloaderError_NotDownloadSpec )
            print('✓\n - Checking credentials...', end=' ')
            if not credentials:
                raise ( DownloaderError_NoCredentials )
            print('✓\n - Checking internet connection...', end=' ')
            if not check_internet_conn():
                raise ( DownloaderError_NoInternetConnection )
            print('✓')
        except Exception as e:
            print(f'AutoDownloader cannot start. Error {e} found.')
            raise e
        else:
            print('AutoDownloader is ready to start.\n')

    def __start_downloads__(self):
        print('Starting downloads...')
        pbar = tqdm(total=len(self.__download_list__), desc='Downloading', unit='downloads') # PBAR
        for i,course in enumerate(self.__download_list__, start=1):
            # Final info dictionary
            course_info = get_course_dictionary(course)
            try:
                # First parameters
                id = course_info['info']['id']
                final_report = course[1]
                # Getting course name
                pbar.set_description(f'Getting name from id={id}')
                course_info['info']['name'] = get_name(self.driver, id)
                # Downloads
                pbar.set_description(f'Downloading participation from id={id}')
                course_info['downloads']['participation'] = self.__download__(id, wd_download_participation)
                if final_report:
                    pbar.set_description(f'Downloading grades from id={id}')
                    course_info['downloads']['grades'] = self.__download__(id, wd_download_grades)
            # Exception management
            except Exception as e:
                course_info['error'] = e
                course_info['success'] = False
                print(f'Course {id} stopped. Error found.')
            else:
                course_info['success'] = True
                print(f'Course {id} downloaded succesfully.')
            finally:
                self.downloads.append(course_info)
                pbar.update(1)
        pbar.close()
        print(' - Downloads Ready')

    def __download__(self, id:int, download_function) -> str:
        # Downloading
        download_function(self.driver, id)
        wait_for_download(self.__downloads_counter__)
        self.__downloads_counter__+=1
        # Naming
        report_type = 'part' if download_function == wd_download_participation else 'grades'
        auto_rename_last_download(report_type, id)
        return get_last_download()

    def __iter__(self):
        return iter(self.downloads)

    def summary(self):
        print()
        print(' --- Summary ---'.upper())
        print(len(self.downloads), 'courses downloaded\n')
        for i, course in enumerate(self.downloads, start=1):
            type = course["info"]["type"]
            print(f'Download {i}: ID{course['info']['id']} - Type:{type}')
            if course['success']:
                print(f'    Name         : {course["info"]["name"]}')
                print('    Downloads:')
                print(f'        Participation: {course['downloads']['participation'].split('\\')[-1]}')
                print(f'        Grades       : {course["downloads"]["grades"].split('\\')[-1] if type == "final" else None}')
            else:
                print('    Error Found')
                print('    Error: \n\n', course['error'])
            if i != len(self.downloads):
                print(' -'*30)

if __name__ == '__main__':
    AutoDownloader([(14,True),(15,False)])