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
# CONFIG
# ======================================================
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación Orión Bloque 52",
    layout="wide"
)

COLOR_LOCACION = {
    "PEÑA BLANCA": "#38bdf8",
    "OCANO": "#f59e0b",
    "CFE": "#6b7280"
}

# ======================================================
# FORMATO NUMÉRICO (IGUAL AL CSV ORIGINAL)
# ======================================================
def euro_to_float(series):
    return (
        series.astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .replace("", pd.NA)
        .astype(float)
    )

def fmt(value, currency=False, decimals=2):
    if pd.isna(value):
        return "—"
    txt = f"{value:,.{decimals}f}".replace(",", "'")
    return f"USD {txt}" if currency else txt

# ======================================================
# DATA
# ======================================================
@st.cache_data(ttl=900)
def load_data():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key("1p9aVrwHFNIfW_08yj3RkqF4u8qdGxIrRFc63ZXjH55I")
    ws = sheet.get_worksheet_by_id(540053809)

    df = pd.DataFrame(ws.get_all_records())

    # FILTROS BASE (IGUAL QUE ANTES)
    df = df[
        (df["REGISTRO CORRECTO"] == 1) &
        (df["POTENCIA ACTIVA (KW)"] != "")
    ].copy()

    df["FECHA DEL REGISTRO"] = pd.to_datetime(
        df["FECHA DEL REGISTRO"],
        dayfirst=True,
        errors="coerce"
    )

    num_cols = [
        "TOTAL GENERADO KW-H",
        "CONSUMO (GLS)",
        "COSTOS DE GENERACIÓN USD",
        "VALOR POR KW GENERADO",
        "%CARGA PRIME",
        "HORAS OPERATIVAS"
    ]

    for c in num_cols:
        if c in df.columns:
            df[c] = euro_to_float(df[c])

    return df

df = load_data()

# ======================================================
# KPIs HISTÓRICOS
# ======================================================
st.markdown("### 📊 KPIs Históricos (acumulado total)")
k1, k2, k3, k4 = st.columns(4)

k1.metric("🔋 Total Generado", fmt(df["TOTAL GENERADO KW-H"].sum(), decimals=0))
k2.metric("⛽ Consumo Total", fmt(df["CONSUMO (GLS)"].sum()))
k3.metric("💰 Costos Totales", fmt(df["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
k4.metric("⚡ Valor prom. KW", fmt(df["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# ======================================================
# FILTRO FECHA
# ======================================================
fecha_max = df["FECHA DEL REGISTRO"].max()
modo = st.radio("Modo", ["7d", "last"], horizontal=True)

fecha_min = fecha_max if modo == "last" else fecha_max - pd.Timedelta(days=6)
df_f = df[(df["FECHA DEL REGISTRO"] >= fecha_min)]

st.info(f"Período activo: {fecha_min.date()} → {fecha_max.date()}")

# ======================================================
# KPIs FILTRADOS
# ======================================================
st.markdown("### 📊 KPIs del período seleccionado")
f1, f2, f3, f4 = st.columns(4)

f1.metric("🔋 Generación", fmt(df_f["TOTAL GENERADO KW-H"].sum(), decimals=0))
f2.metric("⛽ Consumo", fmt(df_f["CONSUMO (GLS)"].sum()))
f3.metric("💰 Costos", fmt(df_f["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
f4.metric("⚡ Valor prom. KW", fmt(df_f["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# ======================================================
# TABLA
# ======================================================
st.markdown("### 📋 Resumen por Locación y Generador")

tabla = (
    df_f.groupby(["LOCACIÓN", "GENERADOR"])
    .agg({
        "HORAS OPERATIVAS": "sum",
        "TOTAL GENERADO KW-H": "sum",
        "CONSUMO (GLS)": "sum",
        "%CARGA PRIME": "mean",
        "VALOR POR KW GENERADO": "mean"
    })
    .reset_index()
)

tabla["%CARGA PRIME"] = tabla["%CARGA PRIME"].round(0)

st.dataframe(
    tabla.style.format({
        "HORAS OPERATIVAS": "{:,.2f}",
        "TOTAL GENERADO KW-H": "{:,.2f}",
        "CONSUMO (GLS)": "{:,.2f}",
        "VALOR POR KW GENERADO": "{:,.2f}",
        "%CARGA PRIME": "{:.0f}%"
    }),
    use_container_width=True
)

# ======================================================
# VELOCÍMETROS
# ======================================================
st.markdown("## 🔌 Carga Prime (%) por Generador")

for loc in df_f["LOCACIÓN"].dropna().unique():
    with st.expander(f"📍 {loc}", expanded=True):
        for gen, gdf in df_f[df_f["LOCACIÓN"] == loc].groupby("GENERADOR"):
            val = gdf["%CARGA PRIME"].iloc[-1 if modo == "last" else slice(None)].mean()
            if pd.isna(val) or val <= 0:
                continue

            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=val,
                number={"suffix": "%"},
                gauge={"axis": {"range": [0, 100]}}
            ))
            fig.update_layout(height=220)
            st.plotly_chart(fig, use_container_width=True)

st.caption("ADBO SMART · Inteligencia de Negocios & IA")

