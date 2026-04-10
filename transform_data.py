import os
import glob
import pandas as pd
import duckdb

def transform_data():
    print("Iniciando transformación de datos...")

    # Define paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
    PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')

    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # 1. Diccionarios de mapeo
    # Se normalizan los nombres para coincidir con posibles GeoJSON y facilitar lectura
    entidades_map = {
        "01": "Aguascalientes", "02": "Baja California", "03": "Baja California Sur",
        "04": "Campeche", "05": "Coahuila de Zaragoza", "06": "Colima",
        "07": "Chiapas", "08": "Chihuahua", "09": "Ciudad de México",
        "10": "Durango", "11": "Guanajuato", "12": "Guerrero",
        "13": "Hidalgo", "14": "Jalisco", "15": "Estado de México",
        "16": "Michoacán de Ocampo", "17": "Morelos", "18": "Nayarit",
        "19": "Nuevo León", "20": "Oaxaca", "21": "Puebla",
        "22": "Querétaro", "23": "Quintana Roo", "24": "San Luis Potosí",
        "25": "Sinaloa", "26": "Sonora", "27": "Tabasco",
        "28": "Tamaulipas", "29": "Tlaxcala", "30": "Veracruz de Ignacio de la Llave",
        "31": "Yucatán", "32": "Zacatecas"
    }

    sexo_map = {1: "Hombres", 2: "Mujeres"}

    # 2. Cargar población (Censo 2020)
    # Buscamos el archivo de poblacion
    censo_path = os.path.join(RAW_DIR, 'censo', 'poblacion_entidades_2020.xlsx')
    try:
        # Leemos ignorando encabezados innecesarios y tomamos totales
        df_censo = pd.read_excel(censo_path, skiprows=4)
        df_censo.columns = ['entidad_raw', 'grupo_edad', 'total', 'hombres', 'mujeres']
        # Filtramos solo el total por entidad (para el calculo solicitado)
        df_censo = df_censo[df_censo['grupo_edad'] == 'Total'].copy()
        
        # Mapeo manual de la población por entidad (usando los nombres estandarizados)
        # Esto evitará problemas de tildes ('Michoacán' vs 'Michoacn')
        # Dado que las entidades vienen ordenadas 1 al 32, asignamos explícitamente:
        nombres_censo = df_censo['entidad_raw'].tolist()
        
        # Omitimos el primero si es "Estados Unidos Mexicanos"
        if "Estados Unidos" in str(nombres_censo[0]):
            df_censo = df_censo.iloc[1:33].copy()
            
        df_censo['entidad'] = list(entidades_map.values())
        
        poblacion = df_censo[['entidad', 'total', 'hombres', 'mujeres']].copy()
        print("Población del censo cargada correctamente.")
    except Exception as e:
        print(f"Error cargando censo: {e}")
        return

    # 3. Leer causas de defunciones
    csv_files = glob.glob(os.path.join(RAW_DIR, 'edr', '**', '*.csv'), recursive=True)
    if not csv_files:
        print("No se encontraron archivos CSV en data/raw/edr/")
        return

    dfs = []
    for file in csv_files:
        try:
            # Determinamos el año por el nombre de la carpeta (ej. 2020, 2021)
            year = os.path.basename(os.path.dirname(file))
            
            # Leemos solo columnas de interés para ahorrar RAM
            df_temp = pd.read_csv(file, usecols=['ent_resid', 'causa_def', 'sexo'], dtype=str)
            df_temp['anio'] = year
            dfs.append(df_temp)
        except Exception as e:
            print(f"Error procesando el archivo {file}: {e}")

    if not dfs:
        print("Ningún CSV pudo ser procesado.")
        return

    df_full = pd.concat(dfs, ignore_index=True)
    
    # 4. Limpieza y filtrado
    # Mapeo Entidad
    df_full['ent_resid'] = df_full['ent_resid'].str.zfill(2)
    df_full['entidad'] = df_full['ent_resid'].map(entidades_map)
    df_full = df_full.dropna(subset=['entidad']) # Ignoramos extranjeros/no especificado (99)

    # Mapeo Sexo
    df_full['sexo_int'] = pd.to_numeric(df_full['sexo'], errors='coerce')
    df_full['sexo_desc'] = df_full['sexo_int'].map(sexo_map)
    df_full = df_full.dropna(subset=['sexo_desc']) # Descartamos 'No especificado' para cálculos

    # Mapeo Causas (CIE-10)
    def map_causa(codigo):
        if not isinstance(codigo, str): return None
        if codigo.startswith('I'):
            return "Enfermedades del Corazón"
        elif codigo.startswith('E10') or codigo.startswith('E11') or codigo.startswith('E12') or codigo.startswith('E13') or codigo.startswith('E14'):
            return "Diabetes Mellitus"
        elif codigo.startswith('C'):
            return "Tumores Malignos"
        return None

    df_full['causa'] = df_full['causa_def'].apply(map_causa)
    df_full = df_full.dropna(subset=['causa'])

    # 5. Agregar defunciones (Hombres y Mujeres)
    agrupado = df_full.groupby(['anio', 'entidad', 'causa', 'sexo_desc']).size().reset_index(name='defunciones')
    
    # Calcular totales por sexo (Hombres + Mujeres)
    totales_sexo = agrupado.groupby(['anio', 'entidad', 'causa'])['defunciones'].sum().reset_index()
    totales_sexo['sexo_desc'] = 'Total'
    
    df_final = pd.concat([agrupado, totales_sexo], ignore_index=True)

    # 6. Unir con Población
    # Melt población para tener hombres, mujeres y total en formato largo
    pob_melt = pd.melt(poblacion, id_vars=['entidad'], value_vars=['total', 'hombres', 'mujeres'], 
                       var_name='sexo_tipo', value_name='poblacion')
    
    # Mapear nombres para que coincidan con sexo_desc
    map_sexo_pob = {'hombres': 'Hombres', 'mujeres': 'Mujeres', 'total': 'Total'}
    pob_melt['sexo_desc'] = pob_melt['sexo_tipo'].map(map_sexo_pob)
    pob_melt = pob_melt[['entidad', 'sexo_desc', 'poblacion']]

    df_master = pd.merge(df_final, pob_melt, on=['entidad', 'sexo_desc'], how='left')

    # Convertir a numérico
    df_master['defunciones'] = pd.to_numeric(df_master['defunciones'], errors='coerce').fillna(0)
    df_master['poblacion'] = pd.to_numeric(df_master['poblacion'], errors='coerce').fillna(0)

    # 7. Calcular tasa por 100,000 habitantes (entidad)
    df_master['tasa_100k'] = (df_master['defunciones'] / df_master['poblacion']) * 100000

    # 8. Calcular el Promedio Nacional Ponderado
    nac_agg = df_master.groupby(['anio', 'causa', 'sexo_desc']).agg(
        defunciones_nacional=('defunciones', 'sum'),
        poblacion_nacional=('poblacion', 'sum')
    ).reset_index()
    
    nac_agg['tasa_nacional'] = (nac_agg['defunciones_nacional'] / nac_agg['poblacion_nacional']) * 100000

    # Unir promedio nacional con los datos por entidad
    df_master = pd.merge(df_master, nac_agg[['anio', 'causa', 'sexo_desc', 'tasa_nacional']], 
                         on=['anio', 'causa', 'sexo_desc'], how='left')

    # Renombramos columna para mayor claridad en el dashboard
    df_master = df_master.rename(columns={'sexo_desc': 'sexo'})

    # 9. Guardar en DuckDB
    db_path = os.path.join(PROCESSED_DIR, 'salud_mexico.duckdb')
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print(f"Guardando datos en DuckDB: {db_path}")
    conn = duckdb.connect(db_path)
    # Crear tablas
    conn.execute("CREATE TABLE mortalidad AS SELECT * FROM df_master")
    conn.close()

    print("Transformación de datos finalizada exitosamente.")

if __name__ == "__main__":
    transform_data()
