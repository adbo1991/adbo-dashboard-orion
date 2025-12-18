# -*- coding: utf-8 -*-
"""
ADBO SMART | Dashboard de Generación
Autor: Alexander Becerra
"""

# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# Configuración general
# --------------------------------------------------
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación Orión Bloque 52",
    layout="wide"
)

# --------------------------------------------------
# CSS (contraste OK iPhone)
# --------------------------------------------------
st.markdown(
    """
    <style>
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border-radius: 14px;
        padding: 18px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        text-align: center;
    }
    div[data-testid="metric-container"] label {
        color: #6b7280 !important;
        font-size: 0.85rem;
        font-weight: 500;
    }
    div[data-testid="metric-container"] div {
        color: #111827 !important;
        font-size: 1.6rem;
        font-weight: 700;
    }
    body {
        background-color: #0f172a;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# Función de formato numérico
# --------------------------------------------------
def format_number(value, currency=False):
    if pd.isna(value):
        return "—"
    formatted = f"{value:,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ".").replace("X", "'")
    return f"USD {formatted}" if currency else formatted

# --------------------------------------------------
# Título
# --------------------------------------------------
st.title("ADBO SMART – CIP – Reporte de Generación Orión Bloque 52")
st.caption("Datos actualizados automáticamente desde Google Sheets")

# --------------------------------------------------
# Carga de datos
# --------------------------------------------------
@st.cache_data(ttl=900)
def load_data():
    sheet_id = "1p9aVrwHFNIfW_08yj3RkqF4u8qdGxIrRFc63ZXjH55I"
    gid = 540053809
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    df = pd.read_csv(
        url,
        engine="python",
        decimal=",",
        thousands=".",
        on_bad_lines="skip"
    )

    df = df[
        (df["REGISTRO CORRECTO"] == 1) &
        (df["POTENCIA ACTIVA (KW)"].notna())
    ]

    df["FECHA DEL REGISTRO"] = pd.to_datetime(
        df["FECHA DEL REGISTRO"],
        dayfirst=True,
        errors="coerce"
    )

    for c in [
        "TOTAL GENERADO KW-H",
        "CONSUMO (GLS)",
        "COSTOS DE GENERACIÓN USD",
        "VALOR POR KW GENERADO"
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

df = load_data()

# --------------------------------------------------
# KPIs HISTÓRICOS (NO FILTRADOS)
# --------------------------------------------------
st.markdown("### 📌 KPIs Históricos")

h1, h2, h3, h4 = st.columns(4)

h1.metric("🔋 Total Generado", format_number(df["TOTAL GENERADO KW-H"].sum()))
h2.metric("⛽ Consumo Total", format_number(df["CONSUMO (GLS)"].sum()))
h3.metric("💰 Costos Totales", format_number(df["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
h4.metric("⚡ Valor Prom. por KW", format_number(df["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# --------------------------------------------------
# Filtros rápidos
# --------------------------------------------------
fecha_max = df["FECHA DEL REGISTRO"].max()
fecha_min = fecha_max - pd.Timedelta(days=6)

st.markdown("### 🔎 Filtros rápidos")

f1, f2 = st.columns([1, 3])

with f1:
    only_last = st.button("📌 Último registro")

if only_last:
    fecha_min = fecha_max

# --------------------------------------------------
# Data filtrada
# --------------------------------------------------
df_filtrado = df[
    (df["FECHA DEL REGISTRO"] >= fecha_min) &
    (df["FECHA DEL REGISTRO"] <= fecha_max)
]

# --------------------------------------------------
# KPIs FILTRADOS
# --------------------------------------------------
st.markdown("### 📊 KPIs del período seleccionado")

k1, k2, k3, k4 = st.columns(4)

k1.metric("🔋 Generación (período)", format_number(df_filtrado["TOTAL GENERADO KW-H"].sum()))
k2.metric("⛽ Consumo (período)", format_number(df_filtrado["CONSUMO (GLS)"].sum()))
k3.metric("💰 Costos (período)", format_number(df_filtrado["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
k4.metric("⚡ Valor Prom. KW (período)", format_number(df_filtrado["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# --------------------------------------------------
# Agregaciones filtradas
# --------------------------------------------------
gen_fecha = df_filtrado.groupby(
    ["FECHA DEL REGISTRO", "LOCACIÓN"], as_index=False
)["TOTAL GENERADO KW-H"].sum()

gen_total = df_filtrado.groupby(
    "FECHA DEL REGISTRO", as_index=False
)["TOTAL GENERADO KW-H"].sum()

consumo = df_filtrado.groupby(
    "FECHA DEL REGISTRO", as_index=False
)["CONSUMO (GLS)"].sum()

# --------------------------------------------------
# Gráficos
# --------------------------------------------------
fig_barras = px.bar(
    gen_fecha,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    color="LOCACIÓN",
    title="Total Generado por Locación"
)

fig_total = px.line(
    gen_total,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    markers=True,
    title="Generación Total Diaria"
)

fig_consumo = px.line(
    consumo,
    x="FECHA DEL REGISTRO",
    y="CONSUMO (GLS)",
    markers=True,
    title="Consumo Diario (GLS)"
)

st.plotly_chart(fig_barras, use_container_width=True)
st.plotly_chart(fig_total, use_container_width=True)
st.plotly_chart(fig_consumo, use_container_width=True)

st.markdown("---")
st.caption("ADBO SMART · Inteligencia de Negocios & IA")