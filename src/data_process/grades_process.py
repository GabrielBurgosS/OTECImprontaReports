import re

import pandas as pd

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    # 'Cuestionario:Prueba Final (Real)' -> 'Prueba Final'
    df.columns = [re.sub(r'^[^:]+:', '', column).replace('(Real)', '').strip() if '(Real)' in column else column
                  for column in df.columns]
    return df

def grades_process(df_grades: pd.DataFrame) -> pd.DataFrame:
    # Column accomodations
    df_grades['Nombre'] = df_grades['Nombre']+' '+df_grades['Apellido(s)']
    df_grades = df_grades.drop(columns=['Institución','Departamento','Total del curso (Real)','Última descarga de este curso'])
    df_grades = clean_columns(df_grades)
    grades_columns = [column for column in df_grades.columns if column not in ['Nombre','Apellido(s)','Número de ID','Dirección de correo']]
    # Processing grades
    df_grades[grades_columns] = df_grades[grades_columns].apply(lambda x: x.replace('-','-30'))
    df_grades[grades_columns] = df_grades[grades_columns].astype(float)
    df_grades[grades_columns] = (df_grades[grades_columns]/100)*6+1
    # Final format
    df_grades[grades_columns] = df_grades[grades_columns].map(lambda x: round(x,1)) # type: ignore
    df_grades[grades_columns] = df_grades[grades_columns].map(lambda x: 0 if x < 0 else x) # type: ignore
    # df_grades = 
    return df_grades