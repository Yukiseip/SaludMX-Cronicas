import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os

# 1. Configuración de la página
st.set_page_config(
    page_title="SaludMX Crónicas - Mortalidad",
    layout="wide",
    page_icon="⚕️"
)

# Estilos CSS adicionales para mantener diseño profesional y limpio
st.markdown("""
<style>
    .kpi-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        border-left: 5px solid #0d6efd;
    }
    .kpi-title {
        color: #6c757d;
        font-size: 13px;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .kpi-value {
        color: #212529;
        font-size: 32px;
        font-weight: 800;
        margin: 10px 0;
    }
    .kpi-subtitle {
        font-size: 12px;
        color: #adb5bd;
    }
    .positive-delta { color: #dc3545; font-weight: bold; } /* Rojo es peor (tasa mayor a la nacional) */
    .negative-delta { color: #198754; font-weight: bold; } /* Verde es mejor (tasa menor a la nacional) */
</style>
""", unsafe_allow_html=True)

st.title("⚕️ SaludMX Crónicas: Mortalidad por Enfermedades Crónicas")
st.markdown("Dashboard interactivo sobre mortalidad de las tres principales causas crónicas en México (2020-2024). Analiza las disparidades geográficas frente a la media nacional.")

# 2. Carga de datos
@st.cache_data
def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'data', 'processed', 'salud_mexico.duckdb')
    
    if not os.path.exists(db_path):
        st.error(f"⚠️ No se encontró la base de datos en {db_path}. Por favor ejecuta transform_data.py primero.")
        st.stop()
        
    conn = duckdb.connect(db_path, read_only=True)
    df = conn.execute("SELECT * FROM mortalidad").fetchdf()
    conn.close()
    
    # Carga optimizada del nuevo mapa states_simple.geojson
    ruta_optimizada = os.path.join(base_dir, 'data', 'raw', 'mexico-geojson-main', 'states_simple.geojson')
    
    mx_geojson = None
    
    if os.path.exists(ruta_optimizada):
        try:
            with open(ruta_optimizada, 'r', encoding='utf-8-sig') as f:
                mx_geojson = json.load(f)
        except Exception as e:
            print(f"Error parseando {ruta_optimizada}: {e}")
                
    if not mx_geojson:
        st.warning("⚠️ No se encontró el mapa optimizado states_simple.geojson. Se desactivará el mapa interactivo.")
        
    return df, mx_geojson

df, mx_geojson = load_data()

# Diccionario universal CVE_ENT para empatar EXACTAMENTE los nombres en Dataframe
# con los polígonos del GeoJSON sin importar cómo vengan escritos (con actentos, sin asientos, etc.)
cve_map = {
    "Aguascalientes": "01", "Baja California": "02", "Baja California Sur": "03",
    "Campeche": "04", "Coahuila de Zaragoza": "05", "Colima": "06",
    "Chiapas": "07", "Chihuahua": "08", "Ciudad de México": "09",
    "Durango": "10", "Guanajuato": "11", "Guerrero": "12",
    "Hidalgo": "13", "Jalisco": "14", "Estado de México": "15",
    "Michoacán de Ocampo": "16", "Morelos": "17", "Nayarit": "18",
    "Nuevo León": "19", "Oaxaca": "20", "Puebla": "21",
    "Querétaro": "22", "Quintana Roo": "23", "San Luis Potosí": "24",
    "Sinaloa": "25", "Sonora": "26", "Tabasco": "27",
    "Tamaulipas": "28", "Tlaxcala": "29", "Veracruz de Ignacio de la Llave": "30",
    "Yucatán": "31", "Zacatecas": "32"
}

# 3. Sidebar: Filtros
st.sidebar.markdown("### ⚙️ Panel de Filtros")

causas = sorted(df['causa'].unique())
causa_sel = st.sidebar.selectbox("Causa de Muerte", causas)

sexos = ["Total", "Hombres", "Mujeres"]
sexo_sel = st.sidebar.selectbox("Sexo", sexos)

anios = sorted(df['anio'].unique())
min_anio = min(anios)
max_anio = max(anios)
anio_rango = st.sidebar.slider("Rango de Años", min_value=int(min_anio), max_value=int(max_anio), value=(int(min_anio), int(max_anio)))

entidades = sorted(df['entidad'].unique())
entidades_sel = st.sidebar.multiselect("Entidad Federativa (Vacío = Nacional)", entidades, default=[])

st.sidebar.markdown("---")
st.sidebar.info("💡 **Consejo:** Deja el filtro de Entidad vacío para ver el panorama general del país en gráficas, o selecciona múltiples estados para compararlos contra el Promedio Nacional.")

# 4. Procesamiento de Datos Filtrados
# Filtrar general por causa, sexo y años
df_filtrado = df[
    (df['causa'] == causa_sel) & 
    (df['sexo'] == sexo_sel) & 
    (df['anio'].astype(int) >= anio_rango[0]) & 
    (df['anio'].astype(int) <= anio_rango[1])
]

# Total Nacional (Dinámico sobre la consulta de años)
df_nacional = df_filtrado.groupby('anio').agg(
    def_nac=('defunciones', 'sum'),
    pob_nac=('poblacion', 'sum')
).reset_index()

total_def_nac = df_nacional['def_nac'].sum()
total_pob_nac = df_nacional['pob_nac'].sum()
# Promedio Ponderado Estricto Nacional
tasa_nac_agg = (total_def_nac / total_pob_nac) * 100000 if total_pob_nac > 0 else 0

# Filtro entidades específicas si se seleccionaron
df_entidad = df_filtrado.copy()
if entidades_sel:
    df_entidad = df_entidad[df_entidad['entidad'].isin(entidades_sel)]

# Calculo de KPIs de la selección actual
total_def_ent = df_entidad['defunciones'].sum()
agg_entidad = df_entidad.groupby(['entidad', 'anio']).agg({'defunciones': 'sum', 'poblacion': 'max'}).reset_index()
total_pob_ent = agg_entidad['poblacion'].sum() 
tasa_ent_agg = (total_def_ent / total_pob_ent) * 100000 if total_pob_ent > 0 else 0

# 5. Visualización KPIs Métrica Principal
st.markdown("### 📊 Panorama Metodológico")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Defunciones Relacionadas</div>
        <div class="kpi-value">{total_def_ent:,.0f}</div>
        <div class="kpi-subtitle">Periodo {anio_rango[0]} - {anio_rango[1]}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #ffc107;">
        <div class="kpi-title">Tasa de Mortalidad Promedio</div>
        <div class="kpi-value">{tasa_ent_agg:,.1f}</div>
        <div class="kpi-subtitle">Muertes por cada 100,000 habitantes</div>
    </div>
    """, unsafe_allow_html=True)

diff_nac = tasa_ent_agg - tasa_nac_agg
delta_color = "positive-delta" if diff_nac > 0 else "negative-delta"
delta_sign = "+" if diff_nac >= 0 else ""

with col3:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #6c757d;">
        <div class="kpi-title">Diferencia vs Nacional</div>
        <div class="kpi-value"><span class="{delta_color}">{delta_sign}{diff_nac:,.1f}</span></div>
        <div class="kpi-subtitle">Referencia país: {tasa_nac_agg:,.1f}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 6. Gráficos y Tendencias
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### 📈 Evolución Temporal")
    df_line = df_entidad.groupby('anio').agg(def_sum=('defunciones', 'sum'), pob_sum=('poblacion', 'max')).reset_index()
    df_line['tasa'] = (df_line['def_sum'] / df_line['pob_sum']) * 100000
    
    df_line_nac = df_nacional.copy()
    df_line_nac['tasa_nacional'] = (df_line_nac['def_nac'] / df_line_nac['pob_nac']) * 100000
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=df_line['anio'], y=df_line['tasa'], 
        mode='lines+markers', name='Tasa Selección', 
        line=dict(color='#0d6efd', width=3),
        hovertemplate="<b>Año:</b> %{x}<br><b>Tasa:</b> %{y:.1f}<extra></extra>"
    ))
    
    if entidades_sel: # Mostrar comparativo nacional sólo si el usuario seleccionó estados para filtrar
        fig_line.add_trace(go.Scatter(
            x=df_line_nac['anio'], y=df_line_nac['tasa_nacional'], 
            mode='lines', name='Promedio Nacional', 
            line=dict(color='#6c757d', dash='dash'),
            hovertemplate="<b>Año:</b> %{x}<br><b>Nacional:</b> %{y:.1f}<extra></extra>"
        ))
        
    fig_line.update_layout(
        xaxis_title="", 
        yaxis_title="Tasa por 100,000 habitantes", 
        margin=dict(l=0, r=0, t=30, b=0), 
        plot_bgcolor="white", 
        xaxis=dict(type='category'),
        legend_title_text="Clasificación",
        hovermode="x unified" # Hover elegante y moderno
    )
    st.plotly_chart(fig_line, use_container_width=True)

with col_chart2:
    st.markdown("#### 🏢 Entidades Federativas en el Periodo")
    df_bar = df_filtrado.groupby('entidad').agg(def_sum=('defunciones', 'sum'), pob_sum=('poblacion', 'sum')).reset_index()
    df_bar['tasa'] = (df_bar['def_sum'] / df_bar['pob_sum']) * 100000
    df_bar = df_bar.sort_values('tasa', ascending=True) # Sort para gráfico de barras horizontales
    
    fig_bar = px.bar(
        df_bar, x='tasa', y='entidad', orientation='h',
        color_discrete_sequence=['#ffc107'],
        labels={'entidad': 'Estado', 'tasa': 'Tasa por 100k hab'}
    )
    # Se agrega una linea para el promedio nacional
    fig_bar.add_vline(x=tasa_nac_agg, line_dash="dash", annotation_text="Promedio Nacional", annotation_position="bottom right", line_color="#6c757d")
    fig_bar.update_layout(
        xaxis_title="Tasa Promedio por 100,000 habitantes", 
        yaxis_title="", 
        margin=dict(l=0, r=0, t=30, b=0), 
        plot_bgcolor="white"
    )
    fig_bar.update_traces(hovertemplate="<b>%{y}</b><br>Tasa: %{x:.1f}<extra></extra>")
    st.plotly_chart(fig_bar, use_container_width=True)


st.markdown("#### 🗺️ Dispersión Geoespacial del Riesgo Sanitario")
if mx_geojson:
    # Vinculamos exactamente la entidad con el id cve del JSON
    # Esto garantiza que siempre cargue sin importar cómo se escribió el estado en los CSV de origen
    df_bar['cve_ent'] = df_bar['entidad'].map(cve_map)
    
    fig_map = px.choropleth(
        df_bar,
        geojson=mx_geojson,
        locations='cve_ent',
        featureidkey='properties.CVE_ENT', # Mapeamos llave del JSON con nuestro dataframe
        color='tasa',
        color_continuous_scale="Reds",
        hover_name='entidad',
        hover_data={'cve_ent': False, 'tasa': ':.1f'},
        labels={'tasa': 'Tasa de Mortalidad (100k)'}
    )
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        dragmode=False,
        coloraxis_colorbar=dict(title="Tasa")
    )
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.info("Para visualizar el mapa interactivo, asegúrese de colocar el archivo JSON en las carpetas descritas en las instrucciones.")

# 7. Sección de Insights 
st.markdown("---")
st.markdown("### 🔍 Hallazgos Principales")

text_dif = "superan a la media del país" if diff_nac > 0 else "se ubican por debajo de la media nacional"

insights = [
    f"🩺 **Enfoque sobre {causa_sel}:** Al analizar de manera segmentada el periodo de {anio_rango[0]} a {anio_rango[1]}, saltan a simple vista marcadas desigualdades en la eficacia del sistema preventivo entre los estados.",
    f"📉 **Brechas Regionales:** Las cifras actuales demuestran que las entidades elegidas **{text_dif}**, reportando una diferencia ajustada de {abs(diff_nac):,.1f} decesos por cada 100,000 habitantes.",
    f"📍 **Zonas Prioritarias:** El mapa coroplético destaca (en sus tonalidades rojizas más puras) aquellos Polos que requieren de una urgencia presupuestal inmediata orientada a la contención de enfermedades sistémicas.",
    f"👥 **Grupos Clínicos:** Si procedes a cruzar y alternar las variables por _Sexo_, evidenciarás un patrón claro que ayudará en el diseño de campañas de intervención focalizada."
]

for insight in insights:
    st.markdown(insight)
