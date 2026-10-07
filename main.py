"""Command line entry point (technical use). The GUI lives in app.py.

Edit download_list and run:  python main.py
Each entry is (course id, template id, attendance) where template id is one of
'inicial', 'semanal', 'part', 'final', 'datos' and attendance is 'none', 'zoom' or 'presencial'.
"""
import logging
import sys

from src import credentials as credential_store
from src.core.job import CourseRequest, ReportJob
from src.errors import OTECError
from src.logging_setup import setup_logging
from src.report_export.templates import TemplateCatalog
from src.settings import Settings

download_list = [
    (17, 'final', 'zoom'),
    (20, 'semanal', 'none'),
]

if __name__ == '__main__':
    log_file = setup_logging()
    settings = Settings.load()
    job = ReportJob(credential_store.load(settings.username), settings, TemplateCatalog())
    try:
        results = job.run([CourseRequest(*entry) for entry in download_list])
    except OTECError as e:
        logging.error(e.user_message)
        sys.exit(1)
    for result in results:
        status = f'OK  {result.output_path}' if result.success else f'ERROR  {result.error_message}'
        print(f'Curso {result.request.course_id}: {status}')
        for warning in result.warnings:
            print(f'    aviso: {warning}')
    print(f'\nRegistro completo: {log_file}')
