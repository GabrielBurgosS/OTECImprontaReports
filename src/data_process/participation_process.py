import pandas as pd

def participation_process(df_part: pd.DataFrame) -> pd.DataFrame:
    # Column accomodations
    df_part = df_part.rename(columns={'Unnamed: 0':'Nombre'})
    df_part = df_part.loc[:, ~df_part.columns.str.contains('Completado')]
    # df_part = df_part.drop(columns=['Institución'])
    part_columns = [column for column in df_part.columns if column not in ['Nombre','Dirección de correo']]
    # Calculations
    df_part[part_columns] = df_part[part_columns].map(lambda x: 1 if x == 'Finalizado' else 0) # type: ignore
    df_part['Elementos Totales'] = len(part_columns)
    df_part['Participación'] = df_part[part_columns].sum(axis=1)
    df_part[r'% de Participación'] = df_part["Participación"]/df_part["Elementos Totales"]
    # Formatting
    df_part[r'% de Participación'] = df_part[r'% de Participación'].apply(lambda x: round(x,2))
    df_part['Participación'] = df_part['Participación'].apply(lambda x: f'{x} elementos' if x != 1 else f'{x} elemento')
    # Final drop
    df_part = df_part.drop(columns=part_columns+['Elementos Totales'])
    return df_part