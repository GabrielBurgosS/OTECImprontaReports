"""Regression tests that pin the numbers produced by the original processing logic.

The refactor must keep these results: participation ratio over all activities,
grades converted to the 1-7 scale with missing grades as 0, and the final merge.
"""
from pathlib import Path

import pytest

from src.data_process.report_maker import final_report, single_report

FIXTURES = Path(__file__).parent / 'fixtures'
PART = str(FIXTURES / 'part_sample.csv')
GRADES = str(FIXTURES / 'grades_sample.csv')


def by_email(df):
    return df.set_index('Dirección de correo')


def test_participation_ratio_counts_finished_activities():
    df = by_email(single_report('participation', PART))
    assert df.loc['ana.perez@example.com', '% de Participación'] == 1.0
    assert df.loc['bruno.diaz@example.com', '% de Participación'] == 0.5
    assert df.loc['carla.rojas@example.com', '% de Participación'] == 0.0
    assert df.loc['diego.munoz@example.com', '% de Participación'] == 0.75
    assert df.loc['bruno.diaz@example.com', 'Participación'] == '2 elementos'


def test_grades_converted_to_chilean_scale_and_missing_is_zero():
    df = by_email(single_report('grades', GRADES))
    diag = [c for c in df.columns if 'Diagnóstico' in c][0]
    final = [c for c in df.columns if 'Final' in c][0]
    assert df.loc['ana.perez@example.com', [diag, final]].tolist() == [7.0, 7.0]
    assert df.loc['bruno.diaz@example.com', [diag, final]].tolist() == [4.6, 0]
    assert df.loc['carla.rojas@example.com', [diag, final]].tolist() == [0, 0]
    assert df.loc['diego.munoz@example.com', [diag, final]].tolist() == [4.0, 3.7]


def test_final_report_keeps_unmatched_participants():
    df = final_report(single_report('participation', PART), single_report('grades', GRADES))
    assert len(df) == 5
    assert list(df.columns[:2]) == ['ID', 'Nombre']
    eva = by_email(df).loc['eva.solo@example.com']
    assert eva['Nombre'] == 'Eva Solo Notas'
    assert eva['% de Participación'] != eva['% de Participación']  # NaN: not in participation
    assert by_email(df).loc['ana.perez@example.com', 'ID'] == '11111111-1'


@pytest.mark.parametrize('email,name', [('ana.perez@example.com', 'Ana Pérez Soto'),
                                        ('diego.munoz@example.com', 'Diego Muñoz')])
def test_names_are_title_case(email, name):
    df = final_report(single_report('participation', PART), single_report('grades', GRADES))
    assert by_email(df).loc[email, 'Nombre'] == name
