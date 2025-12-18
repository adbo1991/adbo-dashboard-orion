# -*- coding: utf-8 -*-
"""
ADBO SMART – CIP – Reporte de Generación Orión Bloque 52
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta

# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación Orión Bloque 52",
    layout="wide"
)

# --------------------------------------------------
# ESTILOS (iPhone OK)
# --------------------------------------------------
st.markdown("""
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
}
div[data-testid="metric-container"] div {
    color: #111827 !important;
    font-size: 1.6rem;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# FUNCIONES AUXILIARES
# --------------------------------------------------
def format_number(value, currency=False, decimals=2):
    if pd.isna(value):
        return "—"
    formatted = f"{value:,.{decimals}f}"
    parts = formatted.split(",")
    if len(parts) > 2:
        formatted = "'".join(parts[:-1]) + "," + parts[-1]
    return f"USD {formatted}" if currency else formatted


def delta_percent(current, previous):
    if previous in [0, None] or pd.isna(previous):
        return "—"
    delta = (current - previous) / previous * 100
    arrow = "↑" if delta >= 0 else "↓"
    return f"{arrow} {abs(delta):.1f}%"


def gauge(value, title):
    return go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": "%", "font": {"size": 34}},
        title={"text": title, "font": {"size": 15}},
        gauge={
            "axis": {"range": [0, 100]},
            "steps": [
                {"range": [0, 60], "color": "#DCFCE7"},   # verde pálido
                {"range": [60, 80], "color": "#4ADE80"}, # verde grass
                {"range": [80, 95], "color": "#FACC15"}, # amarillo
                {"range": [95, 100], "color": "#DC2626"} # rojo
            ],
            "bar": {"color": "#065F46"}
        }
    ))

# --------------------------------------------------
# TÍTULO
# --------------------------------------------------
st.title("ADBO SMART – CIP – Reporte de Generación Orión Bloque 52")
st.caption("Datos actualizados automáticamente desde Google Sheets")

# --------------------------------------------------
# CARGA DE DATOS
# --------------------------------------------------
@st.cache_data(ttl=900)
def load_data():
    sheet_id = "1p9aVrwHFNIfW_08yj3RkqF4u8qdGxIrRFc63ZXjH55I"
    gid = 540053809
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    df = pd.read_csv(url, engine="python", decimal=",", thousands=".", on_bad_lines="skip")

    df = df[
        (df["REGISTRO CORRECTO"] == 1) &
        (df["POTENCIA ACTIVA (KW)"].notna())
    ]

    df["FECHA DEL REGISTRO"] = pd.to_datetime(df["FECHA DEL REGISTRO"], dayfirst=True)

    for c in [
        "TOTAL GENERADO KW-H",
        "CONSUMO (GLS)",
        "COSTOS DE GENERACIÓN USD",
        "VALOR POR KW GENERADO",
        "%CARGA PRIME"
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


df = load_data()

# --------------------------------------------------
# KPIs HISTÓRICOS
# --------------------------------------------------
st.markdown("### 📊 KPIs Históricos (acumulado total)")
c1, c2, c3, c4 = st.columns(4)

c1.metric("🔋 Total Generado", format_number(df["TOTAL GENERADO KW-H"].sum(), decimals=0))
c2.metric("⛽ Consumo Total", format_number(df["CONSUMO (GLS)"].sum()))
c3.metric("💰 Costos Totales", format_number(df["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
c4.metric("⚡ Valor Prom. KW", format_number(df["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# --------------------------------------------------
# FILTROS
# --------------------------------------------------
if "modo" not in st.session_state:
    st.session_state.modo = "7d"

col_f1, col_f2, col_f3 = st.columns([1,1,2])

if col_f1.button("🗓 Últimos 7 días"):
    st.session_state.modo = "7d"

if col_f2.button("📌 Último registro"):
    st.session_state.modo = "last"

if col_f3.button("🔄 Reset filtros"):
    st.session_state.modo = "7d"

fecha_max = df["FECHA DEL REGISTRO"].max()

if st.session_state.modo == "last":
    fecha_min = fecha_max
    st.info(f"📌 Mostrando último registro: {fecha_max.date()}")
else:
    fecha_min = fecha_max - timedelta(days=6)
    st.info(f"🗓 Período activo: {fecha_min.date()} → {fecha_max.date()}")

df_f = df[
    (df["FECHA DEL REGISTRO"] >= fecha_min) &
    (df["FECHA DEL REGISTRO"] <= fecha_max)
]

# --------------------------------------------------
# KPIs FILTRADOS
# --------------------------------------------------
st.markdown("### 📊 KPIs del período seleccionado")

k1, k2, k3, k4 = st.columns(4)

k1.metric("🔋 Generación", format_number(df_f["TOTAL GENERADO KW-H"].sum(), decimals=0))
k2.metric("⛽ Consumo", format_number(df_f["CONSUMO (GLS)"].sum()))
k3.metric("💰 Costos", format_number(df_f["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
k4.metric("⚡ Valor prom. KW", format_number(df_f["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# --------------------------------------------------
# VELOCÍMETROS CARGA PRIME
# --------------------------------------------------
st.markdown("### 🔌 Carga Prime (%) por Locación")

locs = df_f["LOCACIÓN"].dropna().unique()
cols = st.columns(len(locs))

for i, loc in enumerate(locs):
    dfl = df_f[df_f["LOCACIÓN"] == loc]

    if st.session_state.modo == "last":
        val = dfl.sort_values("FECHA DEL REGISTRO")["%CARGA PRIME"].iloc[-1]
    else:
        val = dfl["%CARGA PRIME"].mean()

    with cols[i]:
        st.plotly_chart(gauge(val * 100, loc), use_container_width=True)

st.markdown("---")

# --------------------------------------------------
# GRÁFICOS
# --------------------------------------------------
gen_loc = df_f.groupby(["FECHA DEL REGISTRO", "LOCACIÓN"], as_index=False)["TOTAL GENERADO KW-H"].sum()

fig_bar = px.bar(
    gen_loc,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    color="LOCACIÓN",
    barmode="group",
    title="Generación por Locación"
)

fig_line = px.line(
    df_f.groupby("FECHA DEL REGISTRO", as_index=False)["TOTAL GENERADO KW-H"].sum(),
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    markers=True,
    title="Generación Total Diaria"
)

fig_cons = px.line(
    df_f.groupby("FECHA DEL REGISTRO", as_index=False)["CONSUMO (GLS)"].sum(),
    x="FECHA DEL REGISTRO",
    y="CONSUMO (GLS)",
    markers=True,
    title="Consumo Diario"
)

st.plotly_chart(fig_bar, use_container_width=True)
st.plotly_chart(fig_line, use_container_width=True)
st.plotly_chart(fig_cons, use_container_width=True)

st.markdown("---")
st.caption("ADBO SMART · Inteligencia de Negocios & IA")
