import pandas as pd

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df['fecha_de_publicacion'] = pd.to_datetime(df['fecha_de_publicacion'], errors='coerce')
    df['titulo'] = df['titulo'].fillna('Unknown')
    df = df.dropna(subset=['autor', 'texto_completo', 'publicacion', 'fecha_de_publicacion', 'editorial', 'tipo_fuente', 'idioma'])
    df = df[df['idioma'] == 'English']
    columns_to_drop = ['resumen', 'seccion', 'lugar_publicacion', 'idioma', 'tipo_documento', 'id_proQuest', 
                        'url', 'copyright', 'ultima_actualizacion', 'anio_publicación', 
                        'pais_publicacion', 'materia_publicacion']
    df = df.drop(columns=columns_to_drop, errors='ignore')
    return df
