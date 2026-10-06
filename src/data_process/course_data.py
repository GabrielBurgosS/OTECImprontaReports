from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.data_process.report_maker import final_report, single_report, weekly_report

IDENTITY_COLUMNS = ('Nombre', 'Apellido(s)', 'Número de ID', 'Dirección de correo')


@dataclass
class CourseData:
    """Clean data of one course: one row per student, sorted by name.

    students columns: ID, Nombre, Dirección de correo, Participación, % de Participación
    and one column per quiz (grade on the 1-7 scale, 0 when missing).
    """
    students: pd.DataFrame
    quizzes: list[str]
    warnings: list[str] = field(default_factory=list)


def load_course_data(participation_csv: Path, grades_csv: Path | None = None) -> CourseData:
    participation = single_report('participation', str(participation_csv))
    if grades_csv is None:
        students = weekly_report(participation)
        students.insert(0, 'ID', None)
        return CourseData(students.reset_index(drop=True), [])
    grades = single_report('grades', str(grades_csv))
    quizzes = [column for column in grades.columns if column not in IDENTITY_COLUMNS]
    students = final_report(participation, grades)
    return CourseData(students.reset_index(drop=True), quizzes, list(students.attrs.get('unmatched', [])))
