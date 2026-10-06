import time

from selenium.webdriver.common.by import By

from src.downloader.selenium_webdriver import WebDriverInstance
from src.read_config import get_credentials
from src.downloader.exceptions import DownloaderError_DownloadButtonNotFound, DownloaderError_FailedLogin
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

credentials = get_credentials()

# Functions
def wd_login(driver:WebDriverInstance):
    """
    Logs in to the OTECImpronta.cl website using the given WebDriverInstance.

    Parameters:
    driver (WebDriverInstance): The WebDriverInstance to use for logging in.

    Raises:
    DownloaderError_FailedLogin: If the login attempt fails.
    """
    print('Trying to login...')
    try:
        driver.navigate('https://www.otecimpronta.cl/my/courses.php')
        # Log in credentials
        driver.send_text_to_element(By.ID, "username", credentials['OTEC_USERNAME'])
        driver.send_text_to_element(By.ID, "password", credentials['OTEC_PASSWORD'])
        # Log in click
        driver.click_element(By.ID, "loginbtn")
        # Moodle redirects away from /login/ only when the credentials are accepted
        WebDriverWait(driver.driver, 10).until(lambda d: '/login/' not in d.current_url)
    except (WebDriverException, TimeoutException) as e:
        print(' - Login failed')
        raise DownloaderError_FailedLogin from e
    print(' - Logged in\n')

def wd_download_from_link(driver:WebDriverInstance, link:str, by:By, value_search:str):
    driver.navigate(link)
    wait = WebDriverWait(driver.driver, 10)
    elemento = wait.until(EC.presence_of_element_located((by, value_search)))
    driver.driver.execute_script("arguments[0].click();", elemento)
    
def wd_download_participation(driver:WebDriverInstance, id:int):
    link = f'https://www.otecimpronta.cl/report/progress/index.php?course={id}'
    button_text = 'Descargar en formato de hoja de cálculo (UTF-8.csv)'
    driver.navigate(link)
    # Ciclo para intentar encontrar el elemento de descarga de participación
    driver.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1) # Pausa para que el DOM se asiente
    for i in range(5):
        try:
            # Intentamos localizar el elemento
            driver.click_element(By.LINK_TEXT, button_text)
            return
        except WebDriverException:
            print("Elemento de descarga de participación no encontrado.")
        # 2. Si no se encuentra o no es visible, sube un poco
        print("Desplazando 100px hacia arriba...")
        driver.driver.execute_script(f"window.scrollBy(0, -{100});")
        time.sleep(0.5) # Breve pausa para la animación del scroll
    raise DownloaderError_DownloadButtonNotFound(id)

def wd_download_grades(driver:WebDriverInstance, id:int):
    link = f'https://www.otecimpronta.cl/grade/export/txt/index.php?id={id}'
    button_id = 'id_submitbutton'
    wd_download_from_link(driver, link, By.ID, button_id)

def get_name(driver:WebDriverInstance, id:int) -> str:
    # Specific link
    driver.navigate(f'https://www.otecimpronta.cl/report/view.php?courseid={id}')
    return driver.get_element(By.CLASS_NAME, 'h2').text.split('\n')[0]

def get_course_dictionary(course: tuple[int,bool])-> dict:
    dicc = {'success':None,
            'info':{'type': 'final' if course[1] else 'weekly',
                    'id': course[0],
                    'name': None},
            'error':None,
            'downloads':{'participation':None,
                         'grades':None}
                         }
    return dicc