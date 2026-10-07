"""Fill every bundled template through Excel and check the result with Excel itself.

Needs Microsoft Excel; skipped automatically where it is not installed.
"""
from pathlib import Path

import pytest

from src.data_process.course_data import load_course_data
from src.report_export.template_writer import ExcelWriter
from src.report_export.templates import GRADE, TemplateCatalog, suggest_grade_mapping

win32com_client = pytest.importorskip('win32com.client')

FIXTURES = Path(__file__).parent / 'fixtures'
EXCEL_ERRORS = {-2146826281, -2146826246, -2146826259, -2146826288, -2146826252, -2146826265, -2146826273}

EXPECTED_CONDITION = {
    'final': ['Aprobado', 'Abandono', 'Sin Participar', 'Reprobado', 'Sin Participar'],
    'semanal': ['Aprobado', 'Participando', 'Sin Participar', 'Reprobado', 'Sin Participar'],
    'part': ['Participando', 'Participando', 'Sin Participar', 'Participando', 'Sin Participar'],
}


def _excel_available() -> bool:
    try:
        with ExcelWriter():
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _excel_available(), reason='Microsoft Excel is not available')


@pytest.fixture(scope='module')
def catalog(tmp_path_factory):
    return TemplateCatalog(tmp_path_factory.mktemp('plantillas'))


@pytest.fixture(scope='module')
def data():
    return load_course_data(FIXTURES / 'part_sample.csv', FIXTURES / 'grades_sample.csv')


@pytest.fixture(scope='module')
def excel():
    with ExcelWriter() as writer:
        yield writer.app


def fill(catalog, data, template_id, attendance, output):
    layout = catalog.layout(template_id)
    mapping = suggest_grade_mapping(layout.headers(GRADE), data.quizzes).mapping
    with ExcelWriter() as writer:
        writer.fill(catalog.get(template_id).path, layout, data, mapping, attendance, output)


def inspect(excel, path):
    book = excel.Workbooks.Open(str(path))
    sheet = book.Worksheets(1)
    table = sheet.ListObjects(1)
    cells = [v for row in sheet.UsedRange.Value for v in row]
    info = {
        'rows': table.ListRows.Count,
        'headers': list(table.HeaderRowRange.Value[0]),
        'body': [list(r) for r in table.DataBodyRange.Value],
        'charts': sheet.ChartObjects().Count,
        'cf': sheet.Cells.FormatConditions.Count,
        'texts': [v for v in cells if isinstance(v, str)],
        'errors': [v for v in cells if v in EXCEL_ERRORS],
    }
    book.Close(False)
    return info


@pytest.mark.parametrize('template_id,attendance', [
    ('inicial', 'none'), ('semanal', 'none'),
    ('part', 'none'), ('part', 'zoom'), ('part', 'presencial'),
    ('final', 'none'), ('final', 'zoom'), ('final', 'presencial'),
])
def test_fill_template(catalog, data, excel, tmp_path, template_id, attendance):
    output = tmp_path / f'{template_id}_{attendance}.xlsx'
    fill(catalog, data, template_id, attendance, output)
    template = inspect(excel, catalog.get(template_id).path)
    result = inspect(excel, output)

    assert result['rows'] == len(data.students) == 5
    assert result['errors'] == []
    assert result['charts'] == template['charts']
    assert [r[1] for r in result['body']] == ['Ana Pérez Soto', 'Bruno Díaz Lara', 'Carla Rojas Vega',
                                              'Diego Muñoz', 'Eva Solo Notas']
    if template_id in EXPECTED_CONDITION:
        condition = result['headers'].index('Condición')
        assert [r[condition] for r in result['body']] == EXPECTED_CONDITION[template_id]

    if attendance == 'none':
        assert 'dd-mm' not in result['headers']
        assert not any('Asistencia' in t for t in result['texts'])
    elif attendance == 'zoom':
        assert result['cf'] == template['cf']
        assert 'dd-mm' in result['headers'] and 'Asistencia Zoom' in result['texts']
    else:
        assert 'Asistencia Zoom' not in result['texts']
        assert result['texts'].count('Asistencia Presencial') == 2  # group header + summary block


def test_grows_table_beyond_template_rows(catalog, excel, tmp_path):
    import pandas as pd
    data = load_course_data(FIXTURES / 'part_sample.csv', FIXTURES / 'grades_sample.csv')
    data.students = pd.concat([data.students] * 12, ignore_index=True)  # 60 rows > 22 template rows
    output = tmp_path / 'semanal_grande.xlsx'
    fill(catalog, data, 'semanal', 'none', output)
    result = inspect(excel, output)
    assert result['rows'] == 60
    assert result['errors'] == []


def test_ids_are_kept_as_text(catalog, data, excel, tmp_path):
    output = tmp_path / 'final_ids.xlsx'
    fill(catalog, data, 'final', 'zoom', output)
    assert inspect(excel, output)['body'][0][0] == '11111111-1'


def test_other_excel_instances_survive(catalog, data, tmp_path):
    """A hidden Excel with no workbook (like Excel sitting on its start screen) must not be closed."""
    import pythoncom
    other = win32com_client.DispatchEx('Excel.Application')
    try:
        fill(catalog, data, 'final', 'zoom', tmp_path / 'final.xlsx')
        assert other.Workbooks.Count == 0  # raises if the process was killed
    finally:
        other.Quit()
        del other
        pythoncom.CoFreeUnusedLibraries()
