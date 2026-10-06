class DownloaderError_FailedLogin(Exception):
    def __init__(self):
        super().__init__('Cannot log-in to otecimpronta.cl')

class DownloaderError_NotDownloadSpec(Exception):
    def __init__(self):
        super().__init__('Neither download nor participation specified')

class DownloaderError_NoInternetConnection(Exception):
    def __init__(self):
        super().__init__('No internet connection. Check your internet connection to continue')

class DownloaderError_NoCredentials(Exception):
    def __init__(self):
        super().__init__('No credentials found. Check OTEC_USERNAME and OTEC_PASSWORD in your .env file')

class DownloaderError_DownloadButtonNotFound(Exception):
    def __init__(self, id:int):
        super().__init__(f'Download button not found for course id={id}')

class DownloaderError_DownloadTimeout(Exception):
    def __init__(self, timeout:float):
        super().__init__(f'Download did not finish after {timeout} seconds')
