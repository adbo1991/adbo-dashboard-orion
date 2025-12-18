# -*- coding: utf-8 -*-
"""
ADBO SMART | CIP – Reporte de Generación Orión Bloque 52
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# --------------------------------------------------
# Configuración general
# --------------------------------------------------
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación Orión Bloque 52",
    layout="wide"
)

# --------------------------------------------------
# CSS (alto contraste iPhone)
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
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# Funciones auxiliares
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
    if pd.isna(previous) or previous == 0:
        return "—"
    delta = (current - previous) / previous * 100
    arrow = "↑" if delta >= 0 else "↓"
    return f"{arrow} {abs(delta):.1f}%"


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
# KPIs HISTÓRICOS
# --------------------------------------------------
st.markdown("### 📊 KPIs Históricos (acumulado total)")

h1, h2, h3, h4 = st.columns(4)

h1.metric("🔋 Total Generado", format_number(df["TOTAL GENERADO KW-H"].sum(), decimals=0))
h2.metric("⛽ Consumo Total", format_number(df["CONSUMO (GLS)"].sum()))
h3.metric("💰 Costos Totales", format_number(df["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
h4.metric("⚡ Valor Prom. por KW", format_number(df["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# --------------------------------------------------
# Filtros rápidos con estado visible
# --------------------------------------------------
st.markdown("### 🔎 Filtros rápidos")

if "only_last" not in st.session_state:
    st.session_state.only_last = False

c1, c2, c3 = st.columns([1, 1, 4])

with c1:
    if st.button(
        "📌 Último registro",
        type="primary" if st.session_state.only_last else "secondary"
    ):
        st.session_state.only_last = True

with c2:
    if st.button("🔄 Reset filtros"):
        st.session_state.only_last = False

fecha_max = df["FECHA DEL REGISTRO"].max()

if st.session_state.only_last:
    fecha_min = fecha_max
    filtro_label = f"📍 **Último registro activo:** {fecha_max.date()}"
else:
    fecha_min = fecha_max - pd.Timedelta(days=6)
    filtro_label = f"📍 **Últimos 7 días:** {fecha_min.date()} → {fecha_max.date()}"

with c3:
    st.markdown(filtro_label)

# --------------------------------------------------
# Data filtrada
# --------------------------------------------------
df_filtrado = df[
    (df["FECHA DEL REGISTRO"] >= fecha_min) &
    (df["FECHA DEL REGISTRO"] <= fecha_max)
]

# --------------------------------------------------
# Período anterior
# --------------------------------------------------
dias = (fecha_max - fecha_min).days + 1
prev_max = fecha_min - pd.Timedelta(days=1)
prev_min = prev_max - pd.Timedelta(days=dias - 1)

df_prev = df[
    (df["FECHA DEL REGISTRO"] >= prev_min) &
    (df["FECHA DEL REGISTRO"] <= prev_max)
]

# --------------------------------------------------
# KPIs FILTRADOS + COMPARATIVO
# --------------------------------------------------
st.markdown("### 📊 KPIs del período seleccionado vs período anterior")

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "🔋 Generación",
    format_number(df_filtrado["TOTAL GENERADO KW-H"].sum(), decimals=0),
    delta_percent(
        df_filtrado["TOTAL GENERADO KW-H"].sum(),
        df_prev["TOTAL GENERADO KW-H"].sum()
    )
)

k2.metric(
    "⛽ Consumo",
    format_number(df_filtrado["CONSUMO (GLS)"].sum()),
    delta_percent(
        df_filtrado["CONSUMO (GLS)"].sum(),
        df_prev["CONSUMO (GLS)"].sum()
    )
)

k3.metric(
    "💰 Costos",
    format_number(df_filtrado["COSTOS DE GENERACIÓN USD"].sum(), currency=True),
    delta_percent(
        df_filtrado["COSTOS DE GENERACIÓN USD"].sum(),
        df_prev["COSTOS DE GENERACIÓN USD"].sum()
    )
)

k4.metric(
    "⚡ Valor prom. KW",
    format_number(df_filtrado["VALOR POR KW GENERADO"].mean(), currency=True),
    delta_percent(
        df_filtrado["VALOR POR KW GENERADO"].mean(),
        df_prev["VALOR POR KW GENERADO"].mean()
    )
)

st.markdown("---")

# --------------------------------------------------
# Gráficos
# --------------------------------------------------
gen_fecha = df_filtrado.groupby(
    ["FECHA DEL REGISTRO", "LOCACIÓN"], as_index=False
)["TOTAL GENERADO KW-H"].sum()

fig_barras = px.bar(
    gen_fecha,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    color="LOCACIÓN",
    barmode="group",
    title="Total Generado por Locación"
)

fig_total = px.line(
    df_filtrado.groupby("FECHA DEL REGISTRO", as_index=False)["TOTAL GENERADO KW-H"].sum(),
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    markers=True,
    title="Generación Total Diaria"
)

fig_consumo = px.line(
    df_filtrado.groupby("FECHA DEL REGISTRO", as_index=False)["CONSUMO (GLS)"].sum(),
    x="FECHA DEL REGISTRO",
    y="CONSUMO (GLS)",
    markers=True,
    title="Consumo Diario (GLS)"
)

st.plotly_chart(fig_barras, use_container_width=True)
st.plotly_chart(fig_total, use_container_width=True)
st.plotly_chart(fig_consumo, use_container_width=True)

# --------------------------------------------------
# EXPORTAR KPIs + TABLAS (CSV)
# --------------------------------------------------
st.markdown("---")
st.markdown("### 📤 Exportar")

export_df = pd.DataFrame({
    "Métrica": [
        "Generación período",
        "Consumo período",
        "Costos período",
        "Valor prom. KW"
    ],
    "Valor": [
        df_filtrado["TOTAL GENERADO KW-H"].sum(),
        df_filtrado["CONSUMO (GLS)"].sum(),
        df_filtrado["COSTOS DE GENERACIÓN USD"].sum(),
        df_filtrado["VALOR POR KW GENERADO"].mean()
    ]
})

csv = export_df.to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇️ Descargar KPIs + Resumen (CSV)",
    csv,
    "adbo_kpis_periodo.csv",
    "text/csv"
)

st.caption("ADBO SMART · Inteligencia de Negocios & IA")
