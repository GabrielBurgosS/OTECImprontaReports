"""Report generation workflow shared by the GUI and the command line."""
import logging
import re
import shutil
import threading
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from src.credentials import Credentials
from src.data_process.course_data import CourseData, load_course_data
from src.downloader.platform_session import PlatformSession
from src.errors import (BrowserError, Cancelled, EmptyCourseError, GradeMappingCancelled, NoCredentialsError,
                        NoInternetError, OTECError, user_message)
from src.other_functions.file_functions import safe_filename, unique_path
from src.other_functions.internet_functions import check_internet_conn
from src.paths import downloads_dir
from src.report_export.template_writer import ATTENDANCE_LABELS, ATTENDANCE_NONE, ExcelWriter
from src.report_export.templates import GRADE, TemplateCatalog, TemplateInfo, TemplateLayout, suggest_grade_mapping
from src.settings import Settings

logger = logging.getLogger(__name__)

STEPS_PER_COURSE = 4  # name, participation, grades, excel


@dataclass
class CourseRequest:
    course_id: int
    template_id: str
    attendance: str = ATTENDANCE_NONE


@dataclass
class CourseResult:
    request: CourseRequest
    course_name: str | None = None
    output_path: Path | None = None
    error: BaseException | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.error is None and self.output_path is not None

    @property
    def error_message(self) -> str:
        return user_message(self.error) if self.error else ''


@dataclass
class Progress:
    done: int
    total: int
    message: str

    @property
    def fraction(self) -> float:
        return self.done / self.total if self.total else 0.0


@dataclass
class MappingRequest:
    """Asked to the user when a template grade column cannot be matched automatically."""
    course_id: int
    course_name: str
    template_name: str
    headers: list[str]
    quizzes: list[str]
    suggestion: dict


MappingResolver = Callable[[MappingRequest], dict | None]


def clean_course_name(course_name: str) -> str:
    course_name = re.sub(r'curso de capacitaci[oó]n', '', course_name, flags=re.IGNORECASE)
    return safe_filename(course_name.strip(' -:"“”'))


def report_file_name(template: TemplateInfo, course_name: str, when: datetime | None = None) -> str:
    when = when or datetime.now()
    return safe_filename(f'{template.prefix} - {clean_course_name(course_name)} ({when:%d-%m})') + '.xlsx'


class ReportJob:
    def __init__(self, credentials: Credentials | None, settings: Settings, catalog: TemplateCatalog,
                 on_progress: Callable[[Progress], None] | None = None,
                 cancel_event: threading.Event | None = None,
                 resolve_mapping: MappingResolver | None = None):
        self.credentials = credentials
        self.settings = settings
        self.catalog = catalog
        self.on_progress = on_progress
        self.cancel_event = cancel_event or threading.Event()
        self.resolve_mapping = resolve_mapping
        self._done = 0
        self._total = 1

    # -- progress helpers -------------------------------------------------
    def _step(self, message: str, advance: bool = True) -> None:
        if self.cancel_event.is_set():
            raise Cancelled()
        logger.info(message)
        if advance:
            self._done += 1
        if self.on_progress:
            self.on_progress(Progress(min(self._done, self._total), self._total, message))

    # -- public API -------------------------------------------------------
    def run(self, requests: list[CourseRequest]) -> list[CourseResult]:
        """Generate one report per request. Login/browser/internet problems raise; per-course
        problems are returned inside each CourseResult."""
        if not requests:
            raise OTECError('No courses requested', 'Agrega al menos un curso a la lista.')
        if self.credentials is None:
            raise NoCredentialsError()
        layouts = {r.template_id: self.catalog.layout(r.template_id) for r in requests}
        output_dir = Path(self.settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self._done, self._total = 0, 1 + STEPS_PER_COURSE * len(requests)
        logger.info('=== Generación de reportes: %s ===', ', '.join(
            f'curso {r.course_id} → {self.catalog.get(r.template_id).name} ({ATTENDANCE_LABELS[r.attendance]})'
            for r in requests))
        logger.info('Carpeta de salida: %s', output_dir)
        self._step('Revisando la conexión a internet...', advance=False)
        if not check_internet_conn():
            raise NoInternetError('Connectivity check failed')

        run_dir = downloads_dir() / f'run_{datetime.now():%Y%m%d_%H%M%S}'
        results: list[CourseResult] = []
        with ExitStack() as stack:
            session = stack.enter_context(PlatformSession(
                self.credentials, run_dir, self.settings.show_browser,
                self.settings.download_timeout, self.cancel_event))
            self._step('Iniciando sesión en la plataforma...', advance=False)
            session.login()
            self._step('Sesión iniciada')
            writer: ExcelWriter | None = None

            for index, request in enumerate(requests):
                result = CourseResult(request)
                results.append(result)
                try:
                    template = self.catalog.get(request.template_id)
                    layout = layouts[request.template_id]
                    if writer is None and layout is not None:
                        writer = stack.enter_context(ExcelWriter())
                    self._process(session, writer, request, template, layout, output_dir, result)
                except Cancelled as e:
                    result.error = e
                    self._mark_remaining(requests[index + 1:], results, e)
                    logger.warning('Proceso cancelado por el usuario')
                    break
                except (NoInternetError, BrowserError) as e:
                    result.error = e
                    logger.error('Curso %s: %s', request.course_id, e)
                    self._mark_remaining(requests[index + 1:], results, e)
                    break
                except OTECError as e:
                    result.error = e
                    logger.error('Curso %s: %s', request.course_id, e)
                except Exception as e:
                    result.error = e
                    logger.exception('Curso %s: error inesperado', request.course_id)
                finally:
                    self._done = 1 + STEPS_PER_COURSE * (index + 1)

        self.settings.save()
        if all(r.success for r in results):
            shutil.rmtree(run_dir, ignore_errors=True)
        else:
            logger.info('Archivos descargados conservados para diagnóstico en %s', run_dir)
        ok = sum(r.success for r in results)
        logger.info('=== Terminado: %s de %s reportes generados ===', ok, len(results))
        return results

    @staticmethod
    def _mark_remaining(remaining, results, error) -> None:
        for request in remaining:
            results.append(CourseResult(request, error=error))

    def _process(self, session: PlatformSession, writer: ExcelWriter | None, request: CourseRequest,
                 template: TemplateInfo, layout: TemplateLayout | None, output_dir: Path,
                 result: CourseResult) -> None:
        cid = request.course_id
        self._step(f'Curso {cid}: obteniendo nombre...')
        result.course_name = session.course_name(cid)
        self.settings.remember_course_name(cid, result.course_name)

        self._step(f'Curso {cid}: descargando participación...')
        participation_csv = session.download_participation(cid)

        self._step(f'Curso {cid}: descargando notas...')
        needs_grades = layout is None or bool(layout.headers(GRADE))
        try:
            grades_csv = session.download_grades(cid)
        except OTECError as e:
            if needs_grades:
                raise
            grades_csv = None
            result.warnings.append('No se pudieron descargar las notas; la columna ID quedó vacía.')
            logger.warning('Curso %s: sin notas (%s)', cid, e)

        data = load_course_data(participation_csv, grades_csv)
        if data.students.empty:
            raise EmptyCourseError(cid)
        result.warnings.extend(data.warnings)

        self._step(f'Curso {cid}: generando Excel "{template.name}"...')
        output = unique_path(output_dir / report_file_name(template, result.course_name))
        if layout is None:
            _write_plain(data, output)
        else:
            mapping = self._grade_mapping(request, result, template, layout, data)
            writer.fill(template.path, layout, data, mapping, request.attendance, output)
        result.output_path = output

    def _grade_mapping(self, request: CourseRequest, result: CourseResult, template: TemplateInfo,
                       layout: TemplateLayout, data: CourseData) -> dict:
        headers = layout.headers(GRADE)
        if not headers:
            return {}
        suggestion = suggest_grade_mapping(headers, data.quizzes, self.settings.grade_mapping(request.course_id))
        if not suggestion.ambiguous:
            return suggestion.mapping
        if self.resolve_mapping is None:
            for header in suggestion.ambiguous:
                result.warnings.append(f'No se pudo identificar qué prueba va en "{header}"; la columna quedó vacía.')
            return suggestion.mapping
        logger.info('Curso %s: se pide al usuario elegir las pruebas para %s', request.course_id, suggestion.ambiguous)
        chosen = self.resolve_mapping(MappingRequest(request.course_id, result.course_name, template.name,
                                                     headers, data.quizzes, suggestion.mapping))
        if chosen is None:
            raise GradeMappingCancelled()
        self.settings.remember_grade_mapping(request.course_id, chosen)
        return chosen


def _write_plain(data: CourseData, output: Path) -> None:
    df = data.students.copy()
    df['% de Participación'] = df['% de Participación'].round(2)
    df.to_excel(output, index=False)
    logger.info('Reporte guardado: %s', output.name)


# -- helpers used by the UI ----------------------------------------------------
def test_login(credentials: Credentials, settings: Settings) -> None:
    """Raise LoginError/NoInternetError/BrowserError if the credentials cannot log in."""
    if not check_internet_conn():
        raise NoInternetError('Connectivity check failed')
    with PlatformSession(credentials, downloads_dir() / 'login_test', settings.show_browser) as session:
        session.login()


def fetch_course_names(credentials: Credentials, settings: Settings, course_ids: list[int],
                       cancel_event: threading.Event | None = None) -> dict[int, str | OTECError]:
    """Log in once and return the platform name of each course (or the error found)."""
    if not check_internet_conn():
        raise NoInternetError('Connectivity check failed')
    names: dict[int, str | OTECError] = {}
    with PlatformSession(credentials, downloads_dir() / 'names', settings.show_browser,
                         cancel_event=cancel_event) as session:
        session.login()
        for course_id in course_ids:
            if cancel_event is not None and cancel_event.is_set():
                break
            try:
                names[course_id] = session.course_name(course_id)
                settings.remember_course_name(course_id, names[course_id])
            except OTECError as e:
                names[course_id] = e
    settings.save()
    return names
