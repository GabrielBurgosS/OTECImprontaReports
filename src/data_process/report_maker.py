import pandas as pd
from typing import Literal

from src.data_process.grades_process import grades_process
from src.data_process.participation_process import participation_process

def single_report(type: Literal['participation', 'grades'], csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    process_function = participation_process if type == 'participation' else grades_process
    df = process_function(df)
    return df

def final_report(df_part: pd.DataFrame, df_grades: pd.DataFrame) -> pd.DataFrame:
    df = pd.merge(df_part,df_grades, on=['Nombre','Dirección de correo'])
    df['Nombre'] = df['Nombre'].apply(lambda x: x.title())
    df = df.rename(columns={'Número de ID':'ID'})
    moves = ['ID','Nombre']
    new_order = moves + [column for column in df.columns if column not in moves]
    df = df[new_order]
    df = df.sort_values(by='Nombre')
    return df

def weekly_report(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(by='Nombre')
    df = df.rename(columns={'Numero de ID':'ID'})
    df['% de Participación'] = df['% de Participación'].apply(lambda x: round(x,2))
    df['Nombre'] = df['Nombre'].apply(lambda x: x.title())
    return df

def auto_report_maker(course_dict: dict) -> pd.DataFrame:
    type = course_dict["info"]["type"]
    if type == 'weekly':
        df = single_report('participation', course_dict['downloads']['participation'])
        df = weekly_report(df)
    elif type == 'final':
        df_part = single_report('participation', course_dict['downloads']['participation'])
        df_grades = single_report('grades', course_dict['downloads']['grades'])
        df = final_report(df_part, df_grades)
    return df
    
if __name__ == "__main__":
    course_dict = {
        'info':{	
            'id': 109,
            'type': 'weekly'
        },
        'downloads':{
            'participation': r'download_temp\part ID109 07-04 (003620).csv',
            'grades': None
        }
    }
    print(auto_report_maker(course_dict))
    