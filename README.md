# SaludMX Crónicas ⚕️

**Mortalidad por Enfermedades Crónicas en México (INEGI)**

## 📊 Descripción del Proyecto

**SaludMX Crónicas** es un dashboard interactivo que permite visualizar y analizar la mortalidad por las tres principales enfermedades crónicas en México entre 2020 y 2024:

- Enfermedades del Corazón (I00–I99)
- Diabetes Mellitus (E10–E14)
- Tumores Malignos (C00–C97)

Utiliza datos oficiales del INEGI y permite comparar tasas por entidad federativa contra el promedio nacional ponderado, con visualizaciones interactivas y un mapa de México.

## 🛠️ Tecnologías Utilizadas

- Python, Pandas, DuckDB
- Streamlit (Dashboard)
- Plotly (Visualizaciones y mapa)
- Geopandas (Lectura de GeoJSON)

## 📥 Archivos Necesarios y Dónde Descargarlos

Para replicar este proyecto necesitarás los siguientes archivos:

### 1. Datos de Defunciones (EDR - INEGI)
- **Fuente oficial**: [Estadísticas de Defunciones Registradas (EDR)](https://www.inegi.org.mx/programas/edr/)
- Descarga los tabulados o datos abiertos de los años **2020 a 2024** (preferiblemente en formato CSV o Excel).
- Colócalos en: `data/raw/edr/{año}/`

### 2. Población por Entidad Federativa (Censo 2020)
- Descarga los datos de población total por entidad del Censo 2020.
- **Enlace recomendado**: [INEGI - Censo de Población y Vivienda 2020](https://www.inegi.org.mx/programas/ccpv/2020/)
- Busca la tabla de "Población total por entidad federativa".
- Guarda el archivo como `poblacion_entidades_2020.xlsx` o `.csv` en: `data/raw/censo/`

### 3. GeoJSON de Entidades Federativas de México (Importante para el mapa)
- **Archivo recomendado (versión simplificada 2024/2025)**:
  - Descarga: [states_simple.geojson](https://figshare.com/articles/dataset/_b_Mexico_GeoJSON_States_and_Municipalities_2024_b_/31236322)
  - Renombra el archivo a: **`mexico_estados.geojson`**
  - Colócalo en: `data/raw/geojson/mexico_estados.geojson`

**Nota**: Este GeoJSON es el que mejor funciona con el dashboard actual. Si usas otro, asegúrate de que los nombres de los estados coincidan.

## 🚀 Cómo correr el proyecto localmente

### 1. Clonar o descargar el repositorio

### 2. Crear y activar entorno virtual

```bash
python -m venv venv
venv\Scripts\activate        # En Windows
3. Instalar dependencias
Bashpip install -r requirements.txt
4. Procesar los datos
Bashpython transform_data.py
5. Ejecutar el dashboard
Bashstreamlit run app.py

📌 Notas Importantes

Se utiliza población fija del Censo 2020 para el cálculo de tasas.
El promedio nacional se calcula de forma ponderada.
Los nombres de las entidades fueron normalizados para coincidir con el GeoJSON.
El mapa requiere que el archivo mexico_estados.geojson esté correctamente ubicado y nombrado.

## 💡 Insights Clave Encontrados

Mediante SaludMX Crónicas, es posible extraer de manera simple los siguientes insights:

1. **Magnitud del Problema**: Las tasas de mortalidad por enfermedades del corazón se elevan significativamente año con año superando otras crónicas, sugiriendo la urgencia de fortalecer los primeros niveles de atención y factores dietéticos.
2. **Disparidad Entitativa**: Claramente visible en el mapa coroplético, los estados del norte muestran una tendencia al alza a las enfermedades correlacionadas con el síndrome metabólico, divergiendo dramáticamente de la media nacional ponderada.
3. **Impacto por Sexo**: Los desglosemos permiten observar de manera tangible cómo afecciones como la Diabetes Mellitus afectan asimétricamente a distintos géneros dependiendo de la región, destacando la necesidad de campañas enfocadas.
