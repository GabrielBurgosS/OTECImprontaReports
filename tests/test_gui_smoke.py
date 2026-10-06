"""Drive the real main window: generate reports in the worker thread with a fake platform
and the real Excel writer, answer the grade mapping question, and check the results view."""
from pathlib import Path

import pytest

from src.core import job as job_module
from src.credentials import Credentials
from src.report_export.templates import GradeMapping, TemplateCatalog
from src.settings import Settings
from tests.test_job import FakeSession
from tests.test_template_writer import _excel_available

pytestmark = pytest.mark.skipif(not _excel_available(), reason='Microsoft Excel is not available')


def test_generate_from_the_window(monkeypatch, tmp_path):
    from src.ui import app as ui_app

    monkeypatch.setattr(job_module, 'PlatformSession', FakeSession)
    monkeypatch.setattr(job_module, 'check_internet_conn', lambda: True)
    # Course 18 needs the user to choose the quizzes; course 17 is matched automatically
    real_suggest = job_module.suggest_grade_mapping

    def suggest(headers, quizzes, remembered=None):
        if remembered:
            return real_suggest(headers, quizzes, remembered)
        result = real_suggest(headers, quizzes)
        return GradeMapping({h: None for h in headers}, list(headers)) if suggest.force else result
    suggest.force = False
    monkeypatch.setattr(job_module, 'suggest_grade_mapping', suggest)
    monkeypatch.setattr(ui_app.credential_store, 'load', lambda username: Credentials('user', 'clave-de-prueba'))
    monkeypatch.setattr(ui_app, 'fetch_course_names', lambda *a, **k: {})
    FakeSession.fail_login = False
    FakeSession.cancel_after_name = None
    FakeSession.grades_file = 'grades_sample.csv'

    settings = Settings(output_dir=str(tmp_path / 'salida'),
                        courses=[{'id': 17, 'template': 'final', 'attendance': 'presencial'},
                                 {'id': 18, 'template': 'semanal', 'attendance': 'none'},
                                 {'id': 99, 'template': 'datos', 'attendance': 'none'}])
    catalog_dir = tmp_path / 'plantillas'
    catalog_dir.mkdir()
    window = ui_app.MainWindow(settings, TemplateCatalog(catalog_dir))
    asked = []

    def answer(request):
        asked.append(request.course_id)
        return {'Prueba Diag.': 'Prueba de Auto Diagnóstico', 'Prueba Final': 'Prueba Final'}

    window._ask_mapping = answer
    outcome = {}
    original_finished = window._on_finished

    def finished(results):
        original_finished(results)
        outcome['results'] = results
        window.after(500, window.destroy)

    window._on_finished = finished
    window._on_failed = lambda e: (outcome.update(error=e), window.destroy())

    def start():
        suggest.force = True
        window._generate()

    window.after(300, start)
    window.after(120_000, window.destroy)  # safety net
    window.mainloop()

    assert 'error' not in outcome, outcome.get('error')
    results = outcome['results']
    assert [r.success for r in results] == [True, True, False]
    assert 'No se encontró el curso 99' in results[2].error_message
    assert asked == [17, 18]
    assert all(Path(r.output_path).exists() for r in results[:2])
    assert results[0].output_path.name.startswith('Reporte Final - Manejo de Paciente Crítico')
    assert settings.grade_mapping(18)['Prueba Final'] == 'Prueba Final'
