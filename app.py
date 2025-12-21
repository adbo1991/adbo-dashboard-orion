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
# HELPERS
# ======================================================
def euro_to_float(series):
    return pd.to_numeric(
        series
        .astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip(),
        errors="coerce"
    )

def format_number(v, currency=False, dec=2):
    if pd.isna(v):
        return "—"
    txt = f"{v:,.{dec}f}".replace(",", "'")
    return f"USD {txt}" if currency else txt

def gauge_carga(valor, titulo):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        number={"suffix": "%"},
        title={"text": titulo},
        gauge={"axis": {"range": [0, 100]}}
    ))
    fig.update_layout(height=220)
    return fig

# ======================================================
# LOAD DATA
# ======================================================
@st.cache_data(ttl=900)
def load_data():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    gc = gspread.authorize(creds)
    sheet = gc.open_by_key("1p9aVrwHFNIfW_08yj3RkqF4u8qdGxIrRFc63ZXjH55I")
    ws = sheet.get_worksheet_by_id(540053809)

    df = pd.DataFrame(ws.get_all_records())

    df = df[
        (df["REGISTRO CORRECTO"] == 1) &
        (df["POTENCIA ACTIVA (KW)"] != "")
    ].copy()

    df["FECHA DEL REGISTRO"] = pd.to_datetime(
        df["FECHA DEL REGISTRO"],
        dayfirst=True,
        errors="coerce"
    )

    for c in [
        "TOTAL GENERADO KW-H",
        "CONSUMO (GLS)",
        "COSTOS DE GENERACIÓN USD",
        "VALOR POR KW GENERADO",
        "HORAS OPERATIVAS",
        "%CARGA PRIME"
    ]:
        if c in df.columns:
            df[c] = euro_to_float(df[c])

    return df

df = load_data()

# ======================================================
# KPIs HISTÓRICOS
# ======================================================
st.markdown("### 📊 KPIs Históricos (acumulado total)")
k1, k2, k3, k4 = st.columns(4)

k1.metric("🔋 Total Generado", format_number(df["TOTAL GENERADO KW-H"].sum(), dec=0))
k2.metric("⛽ Consumo Total", format_number(df["CONSUMO (GLS)"].sum()))
k3.metric("💰 Costos Totales", format_number(df["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
k4.metric("⚡ Valor prom. KW", format_number(df["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# ======================================================
# FILTRO FECHA
# ======================================================
fecha_max = df["FECHA DEL REGISTRO"].max()
modo = st.radio("Modo", ["Últimos 7 días", "Último registro"], horizontal=True)

fecha_min = fecha_max if modo == "Último registro" else fecha_max - pd.Timedelta(days=6)
df_f = df[df["FECHA DEL REGISTRO"] >= fecha_min]

st.info(f"Período activo: {fecha_min.date()} → {fecha_max.date()}")

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

st.dataframe(
    tabla.style.format({
        "HORAS OPERATIVAS": "{:,.2f}",
        "TOTAL GENERADO KW-H": "{:,.2f}",
        "CONSUMO (GLS)": "{:,.2f}",
        "%CARGA PRIME": "{:.0f}%",
        "VALOR POR KW GENERADO": "{:,.2f}"
    }),
    use_container_width=True
)

# ======================================================
# VELOCÍMETROS
# ======================================================
st.markdown("## 🔌 Carga Prime (%) por Generador")

for loc in df_f["LOCACIÓN"].dropna().unique():
    with st.expander(f"📍 {loc}", expanded=True):
        for gen, g in df_f[df_f["LOCACIÓN"] == loc].groupby("GENERADOR"):
            val = g["%CARGA PRIME"].iloc[-1]
            if pd.isna(val) or val <= 0:
                continue
            st.plotly_chart(gauge_carga(val, gen), use_container_width=True)

st.caption("ADBO SMART · Inteligencia de Negocios & IA")
