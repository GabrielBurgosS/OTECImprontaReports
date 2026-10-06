"""Fill report templates through Microsoft Excel (COM automation with pywin32), so charts,
icon sets, data bars and table formulas are preserved exactly as designed.

The app starts its own hidden Excel process and only ever closes that process (by PID):
any Excel window the user has open is never touched.
"""
import gc
import logging
import math
import shutil
import threading
import time
from pathlib import Path

import pandas as pd

from src.data_process.course_data import CourseData
from src.errors import ExcelError, TemplateError
from src.report_export.templates import (ATTENDANCE, EMAIL, FORMULA, GRADE, ID, NAME, PARTICIPATION,
                                         TemplateLayout, normalize)

logger = logging.getLogger(__name__)

ATTENDANCE_NONE, ATTENDANCE_ZOOM, ATTENDANCE_PRESENCIAL = 'none', 'zoom', 'presencial'
ATTENDANCE_LABELS = {ATTENDANCE_NONE: 'Sin asistencia', ATTENDANCE_ZOOM: 'Zoom',
                     ATTENDANCE_PRESENCIAL: 'Presencial'}

STUDENT_COLUMNS = {ID: 'ID', NAME: 'Nombre', EMAIL: 'Dirección de correo', PARTICIPATION: '% de Participación'}
QUIT_TIMEOUT = 10


def _cell_value(value):
    if value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NA:
        return None
    if hasattr(value, 'item'):  # numpy scalar -> python
        return value.item()
    return value


def _as_matrix(value) -> list[list]:
    """Range.Value returns a scalar for one cell and a tuple of tuples otherwise."""
    if isinstance(value, tuple):
        return [list(row) for row in value]
    return [[value]]


class ExcelWriter:
    """One hidden Excel process reused for every report of a run."""

    def __enter__(self) -> 'ExcelWriter':
        import pythoncom
        import win32process
        from win32com.client import DispatchEx
        # Worker threads need their own COM apartment; the main thread already has one and
        # uninitializing it would disconnect any other COM object the caller holds.
        self._owns_com = threading.current_thread() is not threading.main_thread()
        if self._owns_com:
            pythoncom.CoInitialize()
        try:
            self.app = DispatchEx('Excel.Application')  # always a new, private process
            self.pid = win32process.GetWindowThreadProcessId(self.app.Hwnd)[1]
            self.app.Visible = False
            self.app.DisplayAlerts = False
            self.app.ScreenUpdating = False
            self.app.AskToUpdateLinks = False
        except Exception as e:
            self._release_com()
            raise ExcelError(f'Could not start Excel: {e}') from e
        logger.debug('Excel %s iniciado (PID %s)', self.app.Version, self.pid)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            while self.app.Workbooks.Count:
                self.app.Workbooks(1).Close(False)
            gc.collect()  # release workbook/range proxies while Excel can still answer
            self.app.Quit()
        except Exception:
            logger.debug('Excel did not quit cleanly', exc_info=True)
        self.app = None
        gc.collect()
        self._wait_or_terminate()
        self._release_com()

    def _release_com(self) -> None:
        if self._owns_com:
            import pythoncom
            pythoncom.CoUninitialize()

    def _wait_or_terminate(self) -> None:
        """Make sure our own Excel process ends; never touch any other Excel process."""
        import pywintypes
        import win32api
        import win32con
        import win32event
        try:
            handle = win32api.OpenProcess(win32con.SYNCHRONIZE | win32con.PROCESS_TERMINATE, False, self.pid)
        except pywintypes.error:
            return  # already gone
        try:
            if win32event.WaitForSingleObject(handle, QUIT_TIMEOUT * 1000) != win32event.WAIT_OBJECT_0:
                logger.warning('Excel (PID %s) no se cerró a tiempo; se fuerza el cierre', self.pid)
                win32api.TerminateProcess(handle, 1)
        finally:
            win32api.CloseHandle(handle)

    def fill(self, template_path: Path, layout: TemplateLayout, data: CourseData,
             grade_mapping: dict, attendance: str, output_path: Path) -> None:
        shutil.copy2(template_path, output_path)
        book = None
        try:
            book = self.app.Workbooks.Open(str(output_path), UpdateLinks=0)
            sheet = book.Worksheets(layout.sheet)
            table = sheet.ListObjects(layout.table)
            formulas = {h: table.ListColumns(h).DataBodyRange.Cells(1, 1).Formula2
                        for h in layout.headers(FORMULA)}

            if layout.has_attendance:
                _apply_attendance(sheet, table, layout, attendance)
            _resize_rows(table, len(data.students))
            _write_columns(table, layout, data, grade_mapping)
            for header, formula in formulas.items():
                table.ListColumns(header).DataBodyRange.Formula2 = formula

            self.app.Calculate()
            book.Save()
        except TemplateError:
            _discard(book, output_path)
            raise
        except Exception as e:
            _discard(book, output_path)
            raise ExcelError(f'Excel failed filling {template_path.name}: {e}') from e
        book.Close(False)
        logger.info('Reporte guardado: %s', output_path.name)


def _discard(book, output_path: Path) -> None:
    if book is not None:
        try:
            book.Close(False)
        except Exception:
            pass
    time.sleep(0.2)  # let Excel release the file handle
    output_path.unlink(missing_ok=True)


def _resize_rows(table, rows: int) -> None:
    """Make the table body exactly *rows* long, adding/deleting rows only inside the table
    so the summary panel beside it does not move."""
    current = table.ListRows.Count
    if current == 0:
        raise TemplateError('Template table has no data rows',
                            'La tabla de la plantilla debe tener al menos una fila de datos vacía bajo los títulos.')
    if rows > current:
        # ListRows.Add also moves a totals row down, which a plain cell insert refuses to do
        for _ in range(rows - current):
            table.ListRows.Add()
    else:
        for index in range(current, rows, -1):
            table.ListRows(index).Delete()
    if table.ListRows.Count != rows:
        raise ExcelError(f'Table has {table.ListRows.Count} rows after resizing, expected {rows}')
    table.DataBodyRange.ClearContents()


def _write_columns(table, layout: TemplateLayout, data: CourseData, grade_mapping: dict) -> None:
    students = data.students
    for column in layout.columns:
        if column.role in STUDENT_COLUMNS:
            source = STUDENT_COLUMNS[column.role]
            values = students[source] if source in students else [None] * len(students)
            if column.role == PARTICIPATION:
                values = pd.Series(values).fillna(0)
        elif column.role == GRADE:
            quiz = grade_mapping.get(column.header)
            values = students[quiz] if quiz in students else [None] * len(students)
        else:
            continue
        target = table.ListColumns(column.header).DataBodyRange
        if column.role == ID:
            target.NumberFormat = '@'  # keep RUTs like 12345678-9 as text
        target.Value = [[_cell_value(v)] for v in values]


def _apply_attendance(sheet, table, layout: TemplateLayout, attendance: str) -> None:
    attendance_headers = layout.headers(ATTENDANCE)
    if attendance == ATTENDANCE_ZOOM:
        return
    used = sheet.UsedRange
    values = _as_matrix(used.Value)
    top, left = used.Row, used.Column
    if attendance == ATTENDANCE_PRESENCIAL:
        for r, row in enumerate(values):
            for c, value in enumerate(row):
                if isinstance(value, str) and 'asistencia zoom' in normalize(value):
                    sheet.Cells(top + r, left + c).Value = 'Asistencia Presencial'
        logger.debug('Asistencia marcada como presencial')
        return

    # No attendance: clear the summary block about attendance, then delete the columns.
    table_cols = range(table.Range.Column, table.Range.Column + table.Range.Columns.Count)
    for r, row in enumerate(values):
        for c, value in enumerate(row):
            if isinstance(value, str) and 'asistencia' in normalize(value) and left + c not in table_cols:
                _clear_block(sheet, values, top, left, r, c)
    columns = sorted((table.ListColumns(h).Range.Column for h in attendance_headers), reverse=True)
    for column in columns:
        sheet.Columns(column).Delete()
    logger.debug('Columnas de asistencia eliminadas: %s', attendance_headers)


def _clear_block(sheet, values, top, left, r0, c0) -> None:
    """Clear the rectangular block that starts at a title cell and ends at the first empty row."""
    r_end = r0
    while r_end + 1 < len(values) and values[r_end + 1][c0] not in (None, ''):
        r_end += 1
    c_end = c0
    for row in values[r0:r_end + 1]:
        for c in range(c0, len(row)):
            if row[c] not in (None, ''):
                c_end = max(c_end, c)
    block = sheet.Range(sheet.Cells(top + r0, left + c0), sheet.Cells(top + r_end, left + c_end))
    logger.debug('Bloque de resumen de asistencia eliminado: %s', block.Address)
    block.Clear()
