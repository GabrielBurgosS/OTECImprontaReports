"""Render the main window and dialogs with sample data and save screenshots (dev only, needs Pillow).

Usage: python tools/screenshot_ui.py <output folder>
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('OTEC_DATA_DIR', tempfile.mkdtemp(prefix='otec_ui_'))

from PIL import ImageGrab  # noqa: E402

from src.core.job import CourseRequest, CourseResult, MappingRequest  # noqa: E402
from src.errors import CourseNotFoundError  # noqa: E402
from src.logging_setup import setup_logging  # noqa: E402
from src.report_export.templates import TemplateCatalog  # noqa: E402
from src.settings import Settings  # noqa: E402
from src.ui import app as ui_app  # noqa: E402
from src.ui.dialogs import AccountDialog, GradeMappingDialog, SettingsDialog  # noqa: E402

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
OUT.mkdir(parents=True, exist_ok=True)

setup_logging(console=False)
settings = Settings(output_dir=str(Path.home() / 'Documents' / 'Reportes OTEC'), username='',
                    courses=[{'id': 17, 'template': 'final', 'attendance': 'zoom'},
                             {'id': 20, 'template': 'semanal', 'attendance': 'none'},
                             {'id': 18, 'template': 'part', 'attendance': 'presencial'}],
                    course_names={'17': 'Manejo de Paciente Crítico Gineco-Obstétrico',
                                  '20': 'Diversidad, Inclusión y Perspectiva de Género',
                                  '18': 'Deberes, Derechos y Obligaciones de los Funcionarios(as)'})
ui_app.credential_store.load = lambda username: None  # never read real credentials here
window = ui_app.MainWindow(settings, TemplateCatalog())


def grab(widget, name):
    widget.lift()
    widget.attributes('-topmost', True)
    widget.update()
    widget.after(250)
    widget.update()
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    w, h = widget.winfo_width(), widget.winfo_height()
    ImageGrab.grab((x, y, x + w, y + h), all_screens=True).save(OUT / f'{name}.png')


def results():
    reqs = [CourseRequest(17, 'final', 'zoom'), CourseRequest(20, 'semanal'), CourseRequest(99, 'final')]
    res = [CourseResult(reqs[0], settings.course_name(17),
                        Path('Reporte Final - Manejo de Paciente Crítico Gineco-Obstétrico (06-10).xlsx'),
                        warnings=['ana.perez@example.com aparece solo en el reporte de notas']),
           CourseResult(reqs[1], settings.course_name(20),
                        Path('Reporte Semanal - Diversidad, Inclusión y Perspectiva de Género (06-10).xlsx')),
           CourseResult(reqs[2], error=CourseNotFoundError(99))]
    window._show_results(res)
    window.tabs.set('Resultados')
    window.progress.set(1)
    window.status.configure(text='✓ 2 reporte(s) generado(s)  ·  ✗ 1 con error')


def step(i=0):
    if i == 0:
        grab(window, '1_principal')
        results()
        window.after(600, step, 1)
    elif i == 1:
        grab(window, '2_resultados')
        dialog = AccountDialog(window, window.bridge, settings, None)
        dialog.after(700, lambda: (grab(dialog, '3_cuenta'), dialog.destroy(), window.after(300, step, 2)))
    elif i == 2:
        req = MappingRequest(18, settings.course_name(18), 'Reporte Final', ['Prueba Diag.', 'Prueba Final'],
                             ['Prueba de Auto Diagnóstico', 'Prueba Módulo 1', 'Prueba Módulo 2', 'Prueba Final'],
                             {'Prueba Diag.': 'Prueba de Auto Diagnóstico', 'Prueba Final': None})
        dialog = GradeMappingDialog(window, req)
        dialog.center_on(window)
        dialog.after(700, lambda: (grab(dialog, '4_pruebas'), dialog.destroy(), window.after(300, step, 3)))
    elif i == 3:
        dialog = SettingsDialog(window, window.bridge, settings, window.catalog)
        dialog.center_on(window)
        dialog.after(900, lambda: (grab(dialog, '5_ajustes_general'), dialog.destroy(), window.after(300, step, 4)))
    elif i == 4:
        dialog = SettingsDialog(window, window.bridge, settings, window.catalog)
        dialog.center_on(window)
        dialog.children  # noqa
        tabs = [w for w in dialog.winfo_children() if w.__class__.__name__ == 'CTkTabview'][0]
        tabs.set('Plantillas')
        dialog.after(900, lambda: (grab(dialog, '6_ajustes_plantillas'), dialog.destroy(), window.after(300, window.destroy)))


window.after(1500, step)
window.mainloop()
print('screenshots in', OUT)
