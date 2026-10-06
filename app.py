"""Graphical entry point of OTEC Impronta Reports."""
import logging
import sys
from tkinter import messagebox

from src.errors import OTECError
from src.logging_setup import setup_logging
from src.paths import APP_NAME

logger = logging.getLogger('app')


def already_running() -> bool:
    """Allow a single window at a time (they would share settings and downloads)."""
    try:
        import win32api
        import win32event
        import winerror
    except ImportError:
        return False
    global _mutex  # keep the handle alive for the life of the process
    _mutex = win32event.CreateMutex(None, False, f'Local\\{APP_NAME}SingleInstance')
    return win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS


def main() -> int:
    setup_logging(console=sys.stderr is not None)
    if len(sys.argv) >= 2 and sys.argv[1] == '--self-test':
        from pathlib import Path
        from src.selftest import run
        return run(Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd() / 'autoprueba')
    if already_running():
        messagebox.showinfo('OTEC Impronta', 'El programa ya está abierto.')
        return 0
    try:
        from src.report_export.templates import TemplateCatalog
        from src.settings import Settings
        from src.ui.app import MainWindow
        settings = Settings.load()
        catalog = TemplateCatalog()
    except OTECError as e:
        logger.exception('Startup failed')
        messagebox.showerror('OTEC Impronta', e.user_message)
        return 1
    except Exception:
        logger.exception('Startup failed')
        messagebox.showerror('OTEC Impronta', 'No se pudo iniciar el programa. Revisa la carpeta de registros '
                                              'en %LOCALAPPDATA%\\OTECImpronta\\logs.')
        return 1
    window = MainWindow(settings, catalog)
    window.mainloop()
    logger.info('Programa cerrado')
    return 0


if __name__ == '__main__':
    sys.exit(main())
