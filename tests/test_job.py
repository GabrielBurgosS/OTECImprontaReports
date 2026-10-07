"""ReportJob workflow with a fake platform session (no browser, no internet)."""
import logging
import shutil
import threading
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.core import job as job_module
from src.core.job import CourseRequest, ReportJob, clean_course_name, report_file_name
from src.credentials import Credentials
from src.errors import Cancelled, CourseNotFoundError, LoginError, NoCredentialsError
from src.logging_setup import setup_logging
from src.report_export.templates import TemplateCatalog, TemplateInfo
from src.settings import Settings

FIXTURES = Path(__file__).parent / 'fixtures'
PASSWORD = 'Sup3r-Secreta!'


class FakeSession:
    names = {17: 'Curso de Capacitación: "Manejo de Paciente Crítico"', 18: 'Toma Espirometría'}
    grades_file = 'grades_sample.csv'
    fail_login = False
    cancel_after_name: threading.Event | None = None

    def __init__(self, credentials, download_dir, *args, **kwargs):
        self.download_dir = download_dir

    def __enter__(self):
        self.download_dir.mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, *exc):
        return False

    def login(self):
        logging.getLogger('fake').info('login con %s', PASSWORD)  # must be redacted in the log
        if self.fail_login:
            raise LoginError('rejected')

    def course_name(self, course_id):
        if course_id not in self.names:
            raise CourseNotFoundError(course_id)
        if self.cancel_after_name is not None:
            self.cancel_after_name.set()
        return self.names[course_id]

    def _copy(self, name):
        target = self.download_dir / f'{name}_{datetime.now():%H%M%S%f}.csv'
        shutil.copy(FIXTURES / name, target)
        return target

    def download_participation(self, course_id):
        return self._copy('part_sample.csv')

    def download_grades(self, course_id):
        return self._copy(self.grades_file)


@pytest.fixture
def fake_platform(monkeypatch):
    monkeypatch.setattr(job_module, 'PlatformSession', FakeSession)
    monkeypatch.setattr(job_module, 'check_internet_conn', lambda: True)
    FakeSession.fail_login = False
    FakeSession.cancel_after_name = None
    FakeSession.grades_file = 'grades_sample.csv'
    return FakeSession


@pytest.fixture
def settings(tmp_path):
    return Settings(output_dir=str(tmp_path / 'salida'))


@pytest.fixture
def catalog(tmp_path):
    folder = tmp_path / 'plantillas'
    folder.mkdir()
    return TemplateCatalog(folder)


def make_job(settings, catalog, **kwargs):
    return ReportJob(Credentials('usuario@otec.cl', PASSWORD), settings, catalog, **kwargs)


def test_plain_report_and_course_errors(fake_platform, settings, catalog):
    progress = []
    results = make_job(settings, catalog, on_progress=progress.append).run(
        [CourseRequest(17, 'datos'), CourseRequest(99, 'datos'), CourseRequest(18, 'datos')])

    assert [r.success for r in results] == [True, False, True]
    assert isinstance(results[1].error, CourseNotFoundError)
    assert 'No se encontró el curso 99' in results[1].error_message
    assert results[0].output_path.name == f'Datos Completos - Manejo de Paciente Crítico ({datetime.now():%d-%m}).xlsx'
    assert results[0].warnings == ['eva.solo@example.com aparece solo en el reporte de notas']
    df = pd.read_excel(results[0].output_path)
    assert len(df) == 5 and 'Prueba Final' in df.columns
    assert progress[-1].done == progress[-1].total
    assert settings.course_name(17).startswith('Curso de Capacitación')


def test_same_name_does_not_overwrite(fake_platform, settings, catalog):
    first = make_job(settings, catalog).run([CourseRequest(18, 'datos')])[0].output_path
    second = make_job(settings, catalog).run([CourseRequest(18, 'datos')])[0].output_path
    assert first != second and second.stem.endswith('(2)')


def test_missing_credentials(fake_platform, settings, catalog):
    with pytest.raises(NoCredentialsError):
        ReportJob(None, settings, catalog).run([CourseRequest(17, 'datos')])


def test_login_error_is_raised(fake_platform, settings, catalog):
    fake_platform.fail_login = True
    with pytest.raises(LoginError) as error:
        make_job(settings, catalog).run([CourseRequest(17, 'datos')])
    assert 'usuario o contraseña incorrectos' in error.value.user_message


def test_cancel_marks_remaining_courses(fake_platform, settings, catalog):
    cancel = threading.Event()
    fake_platform.cancel_after_name = cancel
    results = make_job(settings, catalog, cancel_event=cancel).run(
        [CourseRequest(17, 'datos'), CourseRequest(18, 'datos')])
    assert all(isinstance(r.error, Cancelled) for r in results)
    assert len(results) == 2


def test_ambiguous_grades_ask_the_user_and_are_remembered(fake_platform, settings, catalog, monkeypatch):
    fake_platform.grades_file = 'grades_modules.csv'
    asked = []

    class FakeWriter:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def fill(self, template_path, layout, data, mapping, attendance, output):
            output.write_bytes(b'xlsx')
            self.mapping = mapping
            FakeWriter.last = mapping

    monkeypatch.setattr(job_module, 'ExcelWriter', FakeWriter)
    monkeypatch.setattr(job_module, 'suggest_grade_mapping', _ambiguous)

    def resolver(request):
        asked.append(request)
        return {'Prueba Diag.': 'Prueba de Auto Diagnóstico', 'Prueba Final': 'Prueba Final'}

    make_job(settings, catalog, resolve_mapping=resolver).run([CourseRequest(17, 'final', 'zoom')])
    assert len(asked) == 1 and 'Prueba Módulo 1' in asked[0].quizzes
    assert FakeWriter.last['Prueba Final'] == 'Prueba Final'
    assert settings.grade_mapping(17) == {'Prueba Diag.': 'Prueba de Auto Diagnóstico', 'Prueba Final': 'Prueba Final'}

    # Second run: the remembered choice is used without asking again
    make_job(settings, catalog, resolve_mapping=resolver).run([CourseRequest(17, 'final', 'zoom')])
    assert len(asked) == 1


def _ambiguous(headers, quizzes, remembered=None):
    """Stand-in for suggest_grade_mapping that can never match on its own."""
    from src.report_export.templates import GradeMapping
    if remembered:
        return GradeMapping(dict(remembered), [])
    return GradeMapping({h: None for h in headers}, list(headers))


def test_password_never_reaches_the_log(fake_platform, settings, catalog):
    log_file = setup_logging(console=False)
    make_job(settings, catalog).run([CourseRequest(17, 'datos')])
    for handler in logging.getLogger().handlers:
        handler.flush()
    content = log_file.read_text(encoding='utf-8')
    assert 'login con ***' in content
    assert PASSWORD not in content
    assert PASSWORD not in repr(Credentials('u', PASSWORD))


@pytest.mark.parametrize('raw,clean', [
    ('Curso de Capacitación: "Toma Espirometría"', 'Toma Espirometría'),
    ('CAPREA', 'CAPREA'),
    ('Salud Ocupacional / Laboral: Ergonomía?', 'Salud Ocupacional Laboral Ergonomía'),
])
def test_clean_course_name(raw, clean):
    assert clean_course_name(raw) == clean


def test_report_file_name():
    template = TemplateInfo('final', 'Reporte Final', 'Reporte Final.xlsx', 'Reporte Final')
    name = report_file_name(template, '“Diversidad, Inclusión”', datetime(2026, 10, 6))
    assert name == 'Reporte Final - Diversidad, Inclusión (06-10).xlsx'


def test_settings_round_trip(tmp_path):
    path = tmp_path / 'settings.json'
    settings = Settings(username='ana', courses=[{'id': 17, 'template': 'final', 'attendance': 'zoom'}])
    settings.remember_grade_mapping(17, {'Prueba Final': 'Prueba Final'})
    settings.save(path)
    loaded = Settings.load(path)
    assert loaded == settings
    assert 'password' not in path.read_text(encoding='utf-8').lower()
