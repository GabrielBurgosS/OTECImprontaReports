"""Browser session against the otecimpronta.cl Moodle platform."""
import logging
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.credentials import Credentials
from src.downloader.options import get_driver_options
from src.downloader.selenium_webdriver import WebDriverInstance
from src.errors import (BrowserError, CourseNotFoundError, DownloadButtonNotFoundError,
                        LoginError, NoInternetError, OTECError)
from src.other_functions.file_functions import wait_for_new_download
from src.paths import screenshots_dir

logger = logging.getLogger(__name__)

BASE_URL = 'https://www.otecimpronta.cl'
NETWORK_ERRORS = ('ERR_INTERNET_DISCONNECTED', 'ERR_NAME_NOT_RESOLVED', 'ERR_CONNECTION',
                  'ERR_NETWORK_CHANGED', 'ERR_TIMED_OUT', 'ERR_ADDRESS_UNREACHABLE')
ELEMENT_TIMEOUT = 20


class PlatformSession:
    """
    Usage:
        with PlatformSession(credentials, download_dir) as session:
            session.login()
            name = session.course_name(17)
            csv = session.download_participation(17)
    """

    def __init__(self, credentials: Credentials, download_dir: Path, show_browser: bool = False,
                 download_timeout: float = 60, cancel_event: threading.Event | None = None):
        self.credentials = credentials
        self.download_dir = download_dir
        self.show_browser = show_browser
        self.download_timeout = download_timeout
        self.cancel_event = cancel_event
        self.web: WebDriverInstance | None = None

    def __enter__(self) -> 'PlatformSession':
        self.download_dir.mkdir(parents=True, exist_ok=True)
        logger.info('Abriendo Google Chrome (%s)...', 'visible' if self.show_browser else 'oculto')
        try:
            self.web = WebDriverInstance(get_driver_options(self.download_dir, self.show_browser))
        except WebDriverException as e:
            raise BrowserError(f'Could not start Chrome: {e.msg}') from e
        caps = self.web.driver.capabilities
        logger.debug('Chrome %s | ChromeDriver %s', caps.get('browserVersion'),
                     caps.get('chrome', {}).get('chromedriverVersion', '?').split(' ')[0])
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.web is not None:
            try:
                self.web.close()
            except WebDriverException:
                logger.debug('Chrome was already closed', exc_info=True)
            self.web = None

    @property
    def driver(self):
        return self.web.driver

    @contextmanager
    def _step(self, label: str):
        """Translate Selenium failures into app errors and keep a snapshot for diagnosis."""
        try:
            yield
        except OTECError:
            self.snapshot(label)
            raise
        except WebDriverException as e:
            self.snapshot(label)
            message = e.msg or str(e)
            if any(code in message for code in NETWORK_ERRORS):
                raise NoInternetError(f'{label}: {message}') from e
            raise OTECError(f'{label}: {message}') from e

    def snapshot(self, label: str) -> None:
        """Save a screenshot and the page HTML in logs/capturas for troubleshooting."""
        if self.web is None:
            return
        stem = screenshots_dir() / f'{datetime.now():%Y-%m-%d_%H%M%S}_{label}'
        try:
            self.driver.save_screenshot(str(stem.with_suffix('.png')))
            stem.with_suffix('.html').write_text(self.driver.page_source, encoding='utf-8')
            logger.info('Captura de diagnóstico guardada: %s.png', stem.name)
        except Exception:  # diagnostics must never hide the original error
            logger.debug('Could not save snapshot', exc_info=True)

    def login(self) -> None:
        logger.info('Iniciando sesión en la plataforma...')
        with self._step('login'):
            self.web.navigate(f'{BASE_URL}/login/index.php')
            WebDriverWait(self.driver, ELEMENT_TIMEOUT).until(
                EC.presence_of_element_located((By.ID, 'username')))
            self.web.send_text_to_element(By.ID, 'username', self.credentials.username)
            self.web.send_text_to_element(By.ID, 'password', self.credentials.password)
            self.web.click_element(By.ID, 'loginbtn')
            try:
                # Moodle redirects away from /login/ only when the credentials are accepted
                WebDriverWait(self.driver, ELEMENT_TIMEOUT).until(
                    lambda d: '/login/' not in d.current_url or d.find_elements(By.ID, 'loginerrormessage'))
            except TimeoutException:
                pass
            if '/login/' in self.driver.current_url:
                raise LoginError('Moodle rejected the credentials')
        logger.info('Sesión iniciada')

    def course_name(self, course_id: int) -> str:
        with self._step(f'nombre_curso_{course_id}'):
            self.web.navigate(f'{BASE_URL}/report/view.php?courseid={course_id}')
            headers = self.driver.find_elements(By.CLASS_NAME, 'h2')
            name = headers[0].text.split('\n')[0].strip() if headers else ''
            if not name:
                raise CourseNotFoundError(course_id)
        logger.info('Curso %s: %s', course_id, name)
        return name

    def download_participation(self, course_id: int) -> Path:
        url = f'{BASE_URL}/report/progress/index.php?course={course_id}'
        return self._download(course_id, 'participación', url, (By.PARTIAL_LINK_TEXT, 'UTF-8.csv'),
                              f'part ID{course_id}')

    def download_grades(self, course_id: int) -> Path:
        url = f'{BASE_URL}/grade/export/txt/index.php?id={course_id}'
        return self._download(course_id, 'notas', url, (By.ID, 'id_submitbutton'), f'grad ID{course_id}')

    def _download(self, course_id: int, report: str, url: str, locator: tuple, file_prefix: str) -> Path:
        logger.info('Descargando %s del curso %s...', report, course_id)
        with self._step(f'descarga_{file_prefix.replace(" ", "_")}'):
            before = {p.name for p in self.download_dir.iterdir()}
            self.web.navigate(url)
            try:
                button = WebDriverWait(self.driver, ELEMENT_TIMEOUT).until(
                    EC.presence_of_element_located(locator))
            except TimeoutException:
                raise DownloadButtonNotFoundError(course_id, report)
            # A JS click works even when the element is off-screen or covered
            self.driver.execute_script('arguments[0].scrollIntoView({block: "center"}); arguments[0].click();', button)
            downloaded = wait_for_new_download(self.download_dir, before, self.download_timeout, self.cancel_event)
        target = self.download_dir / f'{file_prefix} {datetime.now():%d-%m (%H%M%S)}.csv'
        downloaded.rename(target)
        logger.debug('Descargado %s', target.name)
        return target
