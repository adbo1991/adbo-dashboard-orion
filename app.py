# -*- coding: utf-8 -*-
"""
ADBO SMART | Dashboard de Generación
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# Configuración general
# --------------------------------------------------
st.set_page_config(
    page_title="ADBO SMART | Dashboard de Generación",
    layout="wide"
)

# --------------------------------------------------
# Branding visual (CSS)
# --------------------------------------------------
st.markdown(
    """
    <style>
    .stMetric {
        background-color: #f5f6f7;
        padding: 12px;
        border-radius: 10px;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# Encabezado
# --------------------------------------------------
st.title("ADBO SMART · Reporte de Generación")
st.caption("Datos actualizados automáticamente desde Google Sheets")

# --------------------------------------------------
# Carga de datos (cacheada)
# --------------------------------------------------
@st.cache_data(ttl=900)  # refresca cada 15 minutos
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

    num_cols = [
        "TOTAL GENERADO KW-H",
        "CONSUMO (GLS)",
        "COSTOS DE GENERACIÓN USD",
        "VALOR POR KW GENERADO"
    ]

    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

df = load_data()

# --------------------------------------------------
# KPIs PRINCIPALES
# --------------------------------------------------
total_generado = df["TOTAL GENERADO KW-H"].sum()
total_consumo = df["CONSUMO (GLS)"].sum()
total_costos = df["COSTOS DE GENERACIÓN USD"].sum()
valor_kw = df["VALOR POR KW GENERADO"].mean()

col1, col2, col3, col4 = st.columns(4)

col1.metric("🔋 Total Generado (KW-H)", f"{total_generado:,.0f}")
col2.metric("⛽ Consumo Total (GLS)", f"{total_consumo:,.0f}")
col3.metric("💰 Costos Totales (USD)", f"${total_costos:,.2f}")
col4.metric("⚡ Valor Promedio por KW", f"${valor_kw:,.3f}")

st.markdown("---")

# --------------------------------------------------
# Agregaciones
# --------------------------------------------------
gen_fecha = (
    df.groupby(["FECHA DEL REGISTRO", "LOCACIÓN"], as_index=False)
      .agg({"TOTAL GENERADO KW-H": "sum"})
)

gen_total = (
    df.groupby("FECHA DEL REGISTRO", as_index=False)
      .agg({"TOTAL GENERADO KW-H": "sum"})
)

consumo = (
    df.groupby("FECHA DEL REGISTRO", as_index=False)
      .agg({"CONSUMO (GLS)": "sum"})
)

# --------------------------------------------------
# Rango inicial
# --------------------------------------------------
fecha_max = df["FECHA DEL REGISTRO"].max()
fecha_min_15 = fecha_max - pd.Timedelta(days=14)

# --------------------------------------------------
# Gráficos
# --------------------------------------------------
fig_barras = px.bar(
    gen_fecha,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    color="LOCACIÓN",
    barmode="group",
    title="Total Generado KW-H por Locación"
)

fig_barras.update_xaxes(range=[fecha_min_15, fecha_max])

fig_total = px.line(
    gen_total,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    markers=True,
    title="Total Generado KW-H Diario"
)

fig_total.update_xaxes(
    range=[fecha_min_15, fecha_max],
    rangeselector=dict(
        buttons=[
            dict(count=7, label="7d", step="day", stepmode="backward"),
            dict(count=15, label="15d", step="day", stepmode="backward"),
            dict(count=30, label="30d", step="day", stepmode="backward"),
            dict(step="all", label="Todo")
        ]
    ),
    rangeslider=dict(visible=True)
)

fig_consumo = px.line(
    consumo,
    x="FECHA DEL REGISTRO",
    y="CONSUMO (GLS)",
    markers=True,
    title="Consumo Diario (GLS)"
)

fig_consumo.update_xaxes(
    range=[fecha_min_15, fecha_max],
    rangeselector=dict(
        buttons=[
            dict(count=7, label="7d", step="day", stepmode="backward"),
            dict(count=15, label="15d", step="day", stepmode="backward"),
            dict(count=30, label="30d", step="day", stepmode="backward"),
            dict(step="all", label="Todo")
        ]
    ),
    rangeslider=dict(visible=True)
)

# --------------------------------------------------
# Render
# --------------------------------------------------
st.plotly_chart(fig_barras, use_container_width=True)
st.plotly_chart(fig_total, use_container_width=True)
st.plotly_chart(fig_consumo, use_container_width=True)

st.markdown("---")
st.caption("ADBO SMART · Inteligencia de Negocios")