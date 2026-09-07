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