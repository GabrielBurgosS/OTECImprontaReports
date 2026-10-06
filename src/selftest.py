"""Installation self-test: `OTEC Reportes.exe --self-test <folder>`.

Checks the pieces the app needs on this computer without logging in anywhere:
Excel + every bundled template, the Windows Credential Manager and Google Chrome.
Writes selftest.txt into <folder> and returns 0 when everything works.
"""
import logging
import traceback
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def _sample_data():
    from src.data_process.course_data import CourseData
    students = pd.DataFrame({
        'ID': ['11111111-1', '22222222-2', '33333333-3'],
        'Nombre': ['Ana Prueba', 'Bruno Prueba', 'Carla Prueba'],
        'Dirección de correo': ['ana@example.com', 'bruno@example.com', 'carla@example.com'],
        'Participación': ['4 elementos', '2 elementos', '0 elementos'],
        '% de Participación': [1.0, 0.5, 0.0],
        'Prueba de Auto Diagnóstico': [7.0, 4.6, 0.0],
        'Prueba Final': [6.5, 3.2, 0.0],
    })
    return CourseData(students, ['Prueba de Auto Diagnóstico', 'Prueba Final'])


def check_templates(folder: Path) -> str:
    from src.report_export.template_writer import ExcelWriter
    from src.report_export.templates import GRADE, TemplateCatalog, suggest_grade_mapping
    catalog = TemplateCatalog()
    data = _sample_data()
    written = []
    with ExcelWriter() as writer:
        for template in catalog.templates:
            layout = catalog.layout(template.id)
            if layout is None:
                continue
            attendance = 'presencial' if layout.has_attendance else 'none'
            mapping = suggest_grade_mapping(layout.headers(GRADE), data.quizzes).mapping
            output = folder / f'selftest_{template.id}.xlsx'
            output.unlink(missing_ok=True)
            writer.fill(template.path, layout, data, mapping, attendance, output)
            written.append(output.name)
    return f'{len(written)} plantillas llenadas: {", ".join(written)}'


def check_keyring() -> str:
    import keyring
    backend = keyring.get_keyring()
    name = type(backend).__module__ + '.' + type(backend).__name__
    if 'fail' in name.lower() or 'null' in name.lower():
        raise RuntimeError(f'No hay un almacén de credenciales disponible ({name})')
    return name


def check_chrome(folder: Path) -> str:
    from src.downloader.options import get_driver_options
    from src.downloader.selenium_webdriver import WebDriverInstance
    web = WebDriverInstance(get_driver_options(folder, show_browser=False))
    try:
        web.navigate('about:blank')
        return f"Chrome {web.driver.capabilities.get('browserVersion')}"
    finally:
        web.close()


def run(folder: Path) -> int:
    folder.mkdir(parents=True, exist_ok=True)
    lines, ok = [], True
    for label, check in (('Excel y plantillas', lambda: check_templates(folder)),
                         ('Administrador de credenciales', check_keyring),
                         ('Google Chrome', lambda: check_chrome(folder))):
        try:
            lines.append(f'[OK]    {label}: {check()}')
        except Exception as e:
            ok = False
            logger.exception('Self-test %s failed', label)
            lines.append(f'[FALLA] {label}: {e}\n{traceback.format_exc()}')
    lines.append('RESULTADO: ' + ('TODO CORRECTO' if ok else 'HAY PROBLEMAS'))
    (folder / 'selftest.txt').write_text('\n'.join(lines), encoding='utf-8')
    logger.info('Self-test: %s', 'OK' if ok else 'FAILED')
    return 0 if ok else 1
