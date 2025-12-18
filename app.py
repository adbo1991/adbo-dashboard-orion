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
    page_title="ADBO SMART | Reporte de Generación",
    layout="wide"
)

# --------------------------------------------------
# CSS (contraste OK en iPhone)
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
# Títulos
# --------------------------------------------------
st.title("ADBO SMART · Reporte de Generación")
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
# KPIs
# --------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

col1.metric("🔋 Total Generado (KW-H)", f"{df['TOTAL GENERADO KW-H'].sum():,.0f}")
col2.metric("⛽ Consumo Total (GLS)", f"{df['CONSUMO (GLS)'].sum():,.0f}")
col3.metric("💰 Costos Totales (USD)", f"${df['COSTOS DE GENERACIÓN USD'].sum():,.2f}")
col4.metric("⚡ Valor Promedio por KW", f"${df['VALOR POR KW GENERADO'].mean():,.2f}")

st.markdown("---")

# --------------------------------------------------
# Agregaciones
# --------------------------------------------------
gen_fecha = df.groupby(
    ["FECHA DEL REGISTRO", "LOCACIÓN"], as_index=False
)["TOTAL GENERADO KW-H"].sum()

gen_total = df.groupby(
    "FECHA DEL REGISTRO", as_index=False
)["TOTAL GENERADO KW-H"].sum()

consumo = df.groupby(
    "FECHA DEL REGISTRO", as_index=False
)["CONSUMO (GLS)"].sum()

fecha_max = df["FECHA DEL REGISTRO"].max()
fecha_min = fecha_max - pd.Timedelta(days=14)

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
fig_barras.update_xaxes(range=[fecha_min, fecha_max])

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