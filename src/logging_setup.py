"""Logging for the app: one file per run, secrets redacted, uncaught errors captured."""
import logging
import platform
import queue
import sys
import threading
from datetime import datetime
from logging.handlers import QueueHandler
from pathlib import Path

from src.paths import APP_VERSION, logs_dir

LOG_FORMAT = '%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s'
KEEP_LOG_FILES = 30

_secrets: set[str] = set()


def register_secret(value: str | None) -> None:
    """Any registered value is replaced by *** in every log record."""
    if value and len(value) >= 3:
        _secrets.add(value)


def redact(text: str) -> str:
    for secret in sorted(_secrets, key=len, reverse=True):
        text = text.replace(secret, '***')
    return text


class SecretFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if _secrets:
            record.msg = redact(record.getMessage())
            record.args = None
            if record.exc_info and not record.exc_text:
                record.exc_text = logging.Formatter().formatException(record.exc_info)
            if record.exc_text:
                record.exc_text = redact(record.exc_text)
        return True


def _cleanup_old_logs(folder: Path) -> None:
    logs = sorted(folder.glob('otec_*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in logs[KEEP_LOG_FILES:]:
        try:
            old.unlink()
        except OSError:
            pass


def setup_logging(console: bool = True) -> Path:
    """Configure the root logger and return the path of this run's log file."""
    folder = logs_dir()
    log_path = folder / f'otec_{datetime.now():%Y-%m-%d_%H%M%S}.log'

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    file_handler.addFilter(SecretFilter())
    root.addHandler(file_handler)

    if console and sys.stderr is not None:
        stream = logging.StreamHandler()
        stream.setLevel(logging.INFO)
        stream.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        stream.addFilter(SecretFilter())
        root.addHandler(stream)

    # Third-party libraries are very chatty at DEBUG
    for noisy in ('selenium', 'urllib3', 'PIL', 'keyring'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    def log_uncaught(exc_type, exc, tb):
        logging.getLogger('uncaught').critical('Error no controlado', exc_info=(exc_type, exc, tb))

    sys.excepthook = log_uncaught
    threading.excepthook = lambda args: log_uncaught(args.exc_type, args.exc_value, args.exc_traceback)

    _cleanup_old_logs(folder)
    logging.getLogger(__name__).info('OTEC Impronta Reports v%s | Python %s | %s',
                                     APP_VERSION, platform.python_version(), platform.platform())
    return log_path


def attach_queue(log_queue: queue.Queue, level: int = logging.INFO) -> logging.Handler:
    """Send log records to a queue so the UI thread can display them."""
    handler = QueueHandler(log_queue)
    handler.setLevel(level)
    handler.addFilter(SecretFilter())
    logging.getLogger().addHandler(handler)
    return handler


def current_log_file() -> Path | None:
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.FileHandler):
            return Path(handler.baseFilename)
    return None
