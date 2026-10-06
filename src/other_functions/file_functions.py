import re
import threading
import time
from pathlib import Path

from src.errors import Cancelled, DownloadTimeoutError

PARTIAL_SUFFIXES = ('.crdownload', '.tmp', '.part')


def wait_for_new_download(folder: Path, before: set[str], timeout: float,
                          cancel_event: threading.Event | None = None) -> Path:
    """
    Wait until a new .csv appears in *folder* (compared with the *before* file names)
    and Chrome has no partial download left. Returns the new file.
    """
    deadline = time.monotonic() + timeout
    while True:
        if cancel_event is not None and cancel_event.is_set():
            raise Cancelled()
        names = {p.name for p in folder.iterdir()}
        new_csv = [folder / n for n in names - before if n.lower().endswith('.csv')]
        partial = any(n.endswith(PARTIAL_SUFFIXES) for n in names)
        if new_csv and not partial:
            return max(new_csv, key=lambda p: p.stat().st_mtime)
        if time.monotonic() > deadline:
            raise DownloadTimeoutError(timeout)
        time.sleep(0.5)


def safe_filename(name: str) -> str:
    """Remove characters Windows does not allow in file names."""
    name = re.sub(r'[<>:"/\|?*\x00-\x1f“”]', '', name)
    return re.sub(r'\s+', ' ', name).strip().rstrip('.')


def unique_path(path: Path) -> Path:
    """Return *path*, or *path* with ' (2)', ' (3)'... if it already exists."""
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f'{path.stem} ({counter}){path.suffix}')
        if not candidate.exists():
            return candidate
        counter += 1
