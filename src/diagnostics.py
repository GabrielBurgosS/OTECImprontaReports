"""Bundle recent logs and snapshots into a zip the user can send for support.
The password never appears: logs are redacted and it is not stored in settings.json."""
import logging
import zipfile
from datetime import datetime
from pathlib import Path

from src.logging_setup import redact
from src.paths import logs_dir, screenshots_dir, settings_file

logger = logging.getLogger(__name__)

MAX_LOGS = 5
MAX_SNAPSHOTS = 20


def _newest(paths, count):
    return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)[:count]


def export_diagnostics(destination_folder: Path) -> Path:
    destination_folder.mkdir(parents=True, exist_ok=True)
    zip_path = destination_folder / f'Diagnostico OTEC {datetime.now():%Y-%m-%d %H%M}.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for log in _newest(logs_dir().glob('otec_*.log'), MAX_LOGS):
            bundle.writestr(f'logs/{log.name}', redact(log.read_text(encoding='utf-8', errors='replace')))
        for snapshot in _newest(screenshots_dir().glob('*.*'), MAX_SNAPSHOTS):
            bundle.write(snapshot, f'capturas/{snapshot.name}')
        if settings_file().exists():
            bundle.write(settings_file(), 'settings.json')
    logger.info('Diagnóstico exportado: %s', zip_path)
    return zip_path
