import urllib3

def check_internet_conn():
    return True # TODO: Check a useful function to do this
    
if __name__ == '__main__':
    if check_internet_conn():
        print('Sip')
    else:
        print('Nop')