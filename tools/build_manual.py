"""Render docs/MANUAL_DE_USUARIO.md to docs/MANUAL_DE_USUARIO.pdf through Microsoft Word (dev only)."""
import time
from pathlib import Path

import markdown
from win32com.client import DispatchEx

WD_PICTURE, WD_LINKED_PICTURE = 3, 4
DOCS = Path(__file__).resolve().parent.parent / 'docs'
CSS = """
body { font-family: 'Segoe UI', Calibri, sans-serif; font-size: 10.5pt; color: #222; }
h1 { color: #1B5E20; font-size: 22pt; border-bottom: 3px solid #2E7D32; padding-bottom: 4px; }
h2 { color: #2E7D32; font-size: 15pt; margin-top: 18pt; }
h3 { color: #33691E; font-size: 12pt; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; }
th { background: #2E7D32; color: white; text-align: left; padding: 4pt 6pt; }
td { border: 1px solid #C8E6C9; padding: 4pt 6pt; vertical-align: top; }
code { font-family: Consolas, monospace; background: #F1F8E9; }
pre { background: #F1F8E9; padding: 6pt; }
blockquote { border-left: 4px solid #FFA726; margin-left: 0; padding: 2pt 10pt; background: #FFF8E1; }
img { border: 1px solid #BDBDBD; }
"""


def main():
    source = DOCS / 'MANUAL_DE_USUARIO.md'
    body = markdown.markdown(source.read_text(encoding='utf-8'), extensions=['tables', 'fenced_code'])
    html = DOCS / '_manual.html'
    html.write_text(f'<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>',
                    encoding='utf-8')
    pdf = DOCS / 'MANUAL_DE_USUARIO.pdf'
    word = DispatchEx('Word.Application')
    word.Visible = False
    word.DisplayAlerts = 0
    document = None
    try:
        document = word.Documents.Open(str(html), ReadOnly=True, AddToRecentFiles=False)
        section = document.Sections(1).PageSetup
        section.TopMargin = section.BottomMargin = 50
        section.LeftMargin = section.RightMargin = 55
        usable = section.PageWidth - section.LeftMargin - section.RightMargin
        for shape in document.InlineShapes:
            if shape.Type not in (WD_PICTURE, WD_LINKED_PICTURE):  # skip <hr> lines
                continue
            if shape.LinkFormat is not None:  # embed the screenshots instead of linking them
                shape.LinkFormat.SavePictureWithDocument = True
            shape.LockAspectRatio = True
            if shape.Width > usable:
                shape.Width = usable
        document.ExportAsFixedFormat(str(pdf), 17)  # wdExportFormatPDF
    finally:
        if document is not None:
            document.Close(False)
        word.Quit()
        for _ in range(20):  # Word releases the file a moment after quitting
            try:
                html.unlink(missing_ok=True)
                break
            except PermissionError:
                time.sleep(0.5)
    print('wrote', pdf)


if __name__ == '__main__':
    main()
