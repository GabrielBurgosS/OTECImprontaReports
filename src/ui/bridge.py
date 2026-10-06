"""Run work in background threads and deliver results on the Tk thread.

Tkinter is not thread-safe: worker threads never touch widgets, they only enqueue
callables that the UI thread executes every POLL_MS.
"""
import logging
import queue
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)

POLL_MS = 100


class UiBridge:
    def __init__(self, root):
        self.root = root
        self._calls: queue.Queue = queue.Queue()
        self.root.after(POLL_MS, self._poll)

    def call_soon(self, fn: Callable, *args) -> None:
        """Schedule fn(*args) on the UI thread. Safe from any thread."""
        self._calls.put((fn, args))

    def ask(self, fn: Callable, *args) -> Any:
        """From a worker thread: run fn(*args) on the UI thread and wait for its return value."""
        done = threading.Event()
        box = {}

        def wrapper():
            try:
                box['value'] = fn(*args)
            finally:
                done.set()

        self.call_soon(wrapper)
        done.wait()
        return box.get('value')

    def run(self, target: Callable, on_done: Callable | None = None,
            on_error: Callable[[BaseException], None] | None = None, name: str = 'worker') -> threading.Thread:
        def body():
            try:
                result = target()
            except BaseException as e:  # reported to the UI, never lost
                logger.debug('Background task %s failed', name, exc_info=True)
                if on_error:
                    self.call_soon(on_error, e)
            else:
                if on_done:
                    self.call_soon(on_done, result)

        thread = threading.Thread(target=body, name=name, daemon=True)
        thread.start()
        return thread

    def _poll(self) -> None:
        # Reschedule first: a callback may open a modal dialog with its own event loop
        self.root.after(POLL_MS, self._poll)
        while True:
            try:
                fn, args = self._calls.get_nowait()
            except queue.Empty:
                return
            try:
                fn(*args)
            except Exception:
                logger.exception('UI callback failed')
