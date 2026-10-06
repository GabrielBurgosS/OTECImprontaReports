import os
import subprocess
from pathlib import Path

import customtkinter as ctk

FONT_TITLE = ('Segoe UI', 18, 'bold')
FONT_HEADER = ('Segoe UI', 22, 'bold')
FONT_SMALL = ('Segoe UI', 11)
MUTED = ('gray40', 'gray65')
OK_COLOR = ('#2E7D32', '#66BB6A')
ERROR_COLOR = ('#C62828', '#EF5350')
WARN_COLOR = ('#B26A00', '#FFB74D')
TEXT_COLOR = ('gray10', 'gray90')
# Secondary buttons: outlined, readable in both light and dark mode
OUTLINE = dict(fg_color='transparent', border_width=1, text_color=TEXT_COLOR, hover_color=('gray85', 'gray25'))


def apply_theme() -> None:
    ctk.set_appearance_mode('system')
    ctk.set_default_color_theme('green')  # matches the green of the report templates


def open_path(path: Path) -> None:
    """Open a file or folder with its default Windows program."""
    os.startfile(str(path))


def reveal_in_explorer(path: Path) -> None:
    subprocess.Popen(['explorer', '/select,', str(path)])
