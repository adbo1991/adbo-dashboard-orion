# -*- coding: utf-8 -*-
"""
ADBO SMART – CIP – Reporte de Generación Orión Bloque 52
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación Orión Bloque 52",
    layout="wide"
)

# ======================================================
# COLORES POR LOCACIÓN
# ======================================================
COLOR_LOCACION = {
    "PEÑA BLANCA": "#38bdf8",
    "OCANO": "#f59e0b",
    "CFE": "#6b7280"
}

# ======================================================
# CSS
# ======================================================
st.markdown("""
<style>
div[data-testid="metric-container"] {
    background-color: #ffffff;
    border-radius: 14px;
    padding: 16px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.12);
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# UTILIDADES
# ======================================================
def parse_euro_number(series):
    return (
        series.astype(str)
        .str.replace(".", "", regex=False)   # miles
        .str.replace(",", ".", regex=False)  # decimales
        .replace({"": None, "nan": None})
        .astype(float)
    )

def format_number(value, currency=False, decimals=2):
    if pd.isna(value):
        return "—"
    formatted = f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"USD {formatted}" if currency else formatted

def style_locacion(row):
    color = COLOR_LOCACION.get(row["LOCACIÓN"], "#ffffff")
    styles = [""] * len(row)
    styles[row.index.get_loc("LOCACIÓN")] = f"background-color:{color};color:white;font-weight:600;"
    return styles

# ======================================================
# CARGA DE DATOS (GOOGLE SHEETS PRIVADO)
# ======================================================
@st.cache_data(ttl=900)
def load_data():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key("1p9aVrwHFNIfW_08yj3RkqF4u8qdGxIrRFc63ZXjH55I")
    worksheet = sheet.get_worksheet_by_id(540053809)

    df = pd.DataFrame(worksheet.get_all_records())
    if df.empty:
        return df

    # ---------------------------
    # PARSEO NUMÉRICO EUROPEO
    # ---------------------------
    cols_numeric = [
        "TOTAL GENERADO KW-H",
        "CONSUMO (GLS)",
        "COSTOS DE GENERACIÓN USD",
        "VALOR POR KW GENERADO",
        "%CARGA PRIME",
        "HORAS OPERATIVAS"
    ]

    for c in cols_numeric:
        if c in df.columns:
            df[c] = parse_euro_number(df[c])

    # ---------------------------
    # FILTROS Y FECHAS
    # ---------------------------
    df = df[
        (df["REGISTRO CORRECTO"] == 1) &
        (df["POTENCIA ACTIVA (KW)"].notna())
    ].copy()

    df["FECHA DEL REGISTRO"] = pd.to_datetime(
        df["FECHA DEL REGISTRO"],
        dayfirst=True,
        errors="coerce"
    )

    return df

# ======================================================
# TÍTULO
# ======================================================
st.title("ADBO SMART – CIP – Reporte de Generación Orión Bloque 52")
st.caption("Datos actualizados automáticamente desde Google Sheets")

df = load_data()
if df.empty:
    st.error("No hay datos disponibles")
    st.stop()

# ======================================================
# KPIs HISTÓRICOS
# ======================================================
st.markdown("### 📊 KPIs Históricos (acumulado total)")
k1, k2, k3, k4 = st.columns(4)

k1.metric("🔋 Total Generado", format_number(df["TOTAL GENERADO KW-H"].sum(), decimals=0))
k2.metric("⛽ Consumo Total", format_number(df["CONSUMO (GLS)"].sum()))
k3.metric("💰 Costos Totales", format_number(df["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
k4.metric("⚡ Valor prom. KW", format_number(df["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# ======================================================
# FILTROS
# ======================================================
fecha_max = df["FECHA DEL REGISTRO"].max()

if "modo" not in st.session_state:
    st.session_state.modo = "7d"

b1, b2 = st.columns(2)
if b1.button("📅 Últimos 7 días"):
    st.session_state.modo = "7d"
if b2.button("📌 Último registro"):
    st.session_state.modo = "last"

fecha_min = fecha_max if st.session_state.modo == "last" else fecha_max - pd.Timedelta(days=6)
st.info(f"Período activo: {fecha_min.date()} → {fecha_max.date()}")

df_f = df[(df["FECHA DEL REGISTRO"] >= fecha_min) & (df["FECHA DEL REGISTRO"] <= fecha_max)]

# ======================================================
# KPIs FILTRADOS
# ======================================================
st.markdown("### 📊 KPIs del período seleccionado")
f1, f2, f3, f4 = st.columns(4)

f1.metric("🔋 Generación", format_number(df_f["TOTAL GENERADO KW-H"].sum(), decimals=0))
f2.metric("⛽ Consumo", format_number(df_f["CONSUMO (GLS)"].sum()))
f3.metric("💰 Costos", format_number(df_f["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
f4.metric("⚡ Valor prom. KW", format_number(df_f["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# ======================================================
# TABLA RESUMEN
# ======================================================
st.markdown("### 📋 Resumen por Locación y Generador")

df_tabla = (
    df_f.groupby(["LOCACIÓN", "GENERADOR"], dropna=True)
    .agg({
        "HORAS OPERATIVAS": "sum",
        "TOTAL GENERADO KW-H": "sum",
        "CONSUMO (GLS)": "sum",
        "%CARGA PRIME": "mean",
        "VALOR POR KW GENERADO": "mean"
    })
    .reset_index()
)

df_tabla["%CARGA PRIME"] = (df_tabla["%CARGA PRIME"] * 100).round(0)

st.dataframe(
    df_tabla.style
        .apply(style_locacion, axis=1)
        .format({
            "HORAS OPERATIVAS": "{:,.2f}",
            "TOTAL GENERADO KW-H": "{:,.2f}",
            "CONSUMO (GLS)": "{:,.2f}",
            "VALOR POR KW GENERADO": "{:,.2f}",
            "%CARGA PRIME": "{}%"
        }),
    use_container_width=True
)

st.caption("ADBO SMART · Inteligencia de Negocios & IA")
