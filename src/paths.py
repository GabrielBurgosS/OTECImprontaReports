"""Filesystem locations used by the app, valid both from source and from the PyInstaller build."""
import ctypes
import os
import sys
import uuid
from pathlib import Path

APP_NAME = 'OTECImpronta'
APP_DISPLAY_NAME = 'OTEC Impronta · Generador de Reportes'
APP_VERSION = '1.0.0'


def is_frozen() -> bool:
    return getattr(sys, 'frozen', False)


def resource_dir() -> Path:
    """Read-only files shipped with the app (bundled templates, icon)."""
    if is_frozen():
        return Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def user_data_dir() -> Path:
    """Per-user writable folder. OTEC_DATA_DIR overrides it (used by tests)."""
    override = os.getenv('OTEC_DATA_DIR')
    base = Path(override) if override else Path(os.getenv('LOCALAPPDATA', Path.home())) / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def _subdir(name: str) -> Path:
    path = user_data_dir() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    return _subdir('logs')


def screenshots_dir() -> Path:
    return _subdir('logs/capturas')


def downloads_dir() -> Path:
    return _subdir('descargas')


def templates_dir() -> Path:
    return _subdir('plantillas')


def settings_file() -> Path:
    return user_data_dir() / 'settings.json'


def bundled_templates_dir() -> Path:
    return resource_dir() / 'assets' / 'plantillas'


def icon_file() -> Path:
    return resource_dir() / 'assets' / 'icon.ico'


def documents_dir() -> Path:
    """The user's Documents folder, following OneDrive redirection when present."""
    folderid_documents = uuid.UUID('{FDD39AD0-238F-46AF-ADB4-6C85480369C7}')
    try:
        guid = ctypes.create_string_buffer(folderid_documents.bytes_le)
        path_ptr = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(guid, 0, None, ctypes.byref(path_ptr)) == 0:
            path = Path(path_ptr.value)
            ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            return path
    except (AttributeError, OSError):
        pass
    return Path.home() / 'Documents'


def default_output_dir() -> Path:
    return documents_dir() / 'Reportes OTEC'
