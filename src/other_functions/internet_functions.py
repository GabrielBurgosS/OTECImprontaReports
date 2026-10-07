import requests

PLATFORM_URL = 'https://www.otecimpronta.cl'


def check_internet_conn(url: str = PLATFORM_URL, timeout: float = 5) -> bool:
    try:
        requests.head(url, timeout=timeout)
    except requests.RequestException:
        return False
    return True
