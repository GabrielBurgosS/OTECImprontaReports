import requests

def check_internet_conn(url:str='https://www.otecimpronta.cl', timeout:float=5) -> bool:
    try:
        requests.head(url, timeout=timeout)
    except requests.RequestException:
        return False
    return True
    
if __name__ == '__main__':
    if check_internet_conn():
        print('Sip')
    else:
        print('Nop')
