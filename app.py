# -*- coding: utf-8 -*-
"""
ADBO SMART | CIP – Reporte de Generación Orión Bloque 52
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from io import BytesIO

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación Orión Bloque 52",
    layout="wide"
)

# --------------------------------------------------
# ESTILOS
# --------------------------------------------------
st.markdown("""
<style>
div[data-testid="metric-container"] {
    background-color: #ffffff;
    border-radius: 14px;
    padding: 16px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.10);
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# FUNCIONES
# --------------------------------------------------
def format_number(value, currency=False, decimals=2):
    if pd.isna(value):
        return "—"
    f = f"{value:,.{decimals}f}"
    p = f.split(",")
    if len(p) > 2:
        f = "'".join(p[:-1]) + "," + p[-1]
    return f"USD {f}" if currency else f


def gauge_small(value, title):
    return go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "%", "font": {"size": 20}},
            title={"text": title, "font": {"size": 12}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#2563eb"},
                "steps": [
                    {"range": [0, 60], "color": "#d1fae5"},
                    {"range": [60, 80], "color": "#4ade80"},
                    {"range": [80, 95], "color": "#fde68a"},
                    {"range": [95, 100], "color": "#ef4444"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 3},
                    "value": 95
                }
            }
        )
    ).update_layout(height=220, margin=dict(t=30, b=0, l=0, r=0))


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
# TÍTULO
# --------------------------------------------------
st.title("ADBO SMART – CIP – Reporte de Generación Orión Bloque 52")
st.caption("Datos actualizados automáticamente desde Google Sheets")

# --------------------------------------------------
# KPIs HISTÓRICOS
# --------------------------------------------------
st.markdown("### 📊 KPIs Históricos (acumulado total)")

h1, h2, h3, h4 = st.columns(4)

h1.metric("🔋 Total Generado", format_number(df["TOTAL GENERADO KW-H"].sum(), decimals=0))
h2.metric("⛽ Consumo Total", format_number(df["CONSUMO (GLS)"].sum()))
h3.metric("💰 Costos Totales", format_number(df["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
h4.metric("⚡ Valor Prom. KW", format_number(df["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# --------------------------------------------------
# FILTROS
# --------------------------------------------------
if "modo" not in st.session_state:
    st.session_state.modo = "7d"

c1, c2, c3 = st.columns(3)

with c1:
    if st.button("📆 Últimos 7 días"):
        st.session_state.modo = "7d"

with c2:
    if st.button("📌 Último registro"):
        st.session_state.modo = "last"

with c3:
    if st.button("♻️ Reset filtros"):
        st.session_state.modo = "7d"

fecha_max = df["FECHA DEL REGISTRO"].max()
fecha_min = fecha_max if st.session_state.modo == "last" else fecha_max - timedelta(days=6)

st.info(f"📅 Período activo: {fecha_min.date()} → {fecha_max.date()}")

df_f = df[(df["FECHA DEL REGISTRO"] >= fecha_min) & (df["FECHA DEL REGISTRO"] <= fecha_max)]

# --------------------------------------------------
# KPIs PERÍODO
# --------------------------------------------------
st.markdown("### 📊 KPIs del período seleccionado")

k1, k2, k3, k4 = st.columns(4)

k1.metric("🔋 Generación", format_number(df_f["TOTAL GENERADO KW-H"].sum(), decimals=0))
k2.metric("⛽ Consumo", format_number(df_f["CONSUMO (GLS)"].sum()))
k3.metric("💰 Costos", format_number(df_f["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
k4.metric("⚡ Valor prom. KW", format_number(df_f["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# --------------------------------------------------
# GRÁFICOS PRINCIPALES
# --------------------------------------------------
st.markdown("### 📈 Análisis de Generación y Consumo")

gen_loc = df_f.groupby(["FECHA DEL REGISTRO", "LOCACIÓN"], as_index=False)["TOTAL GENERADO KW-H"].sum()
gen_total = df_f.groupby("FECHA DEL REGISTRO", as_index=False)["TOTAL GENERADO KW-H"].sum()
consumo = df_f.groupby("FECHA DEL REGISTRO", as_index=False)["CONSUMO (GLS)"].sum()

fig_bar = px.bar(
    gen_loc,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    color="LOCACIÓN",
    barmode="group",
    title="Generación por Locación"
)

fig_gen = px.line(
    gen_total,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    markers=True,
    title="Generación Total Diaria"
)

fig_con = px.line(
    consumo,
    x="FECHA DEL REGISTRO",
    y="CONSUMO (GLS)",
    markers=True,
    title="Consumo Diario"
)

st.plotly_chart(fig_bar, use_container_width=True)
st.plotly_chart(fig_gen, use_container_width=True)
st.plotly_chart(fig_con, use_container_width=True)

st.markdown("---")

# --------------------------------------------------
# VELOCÍMETROS (AL FINAL)
# --------------------------------------------------
st.markdown("### 🔌 Carga Prime (%) por Generador")

for loc in df_f["LOCACIÓN"].dropna().unique():
    with st.expander(f"📍 {loc}", expanded=False):
        df_loc = df_f[df_f["LOCACIÓN"] == loc]
        gens = df_loc["GENERADOR"].dropna().unique()
        cols = st.columns(min(4, len(gens)))

        for i, gen in enumerate(gens):
            df_gen = df_loc[df_loc["GENERADOR"] == gen]
            val = (
                df_gen.sort_values("FECHA DEL REGISTRO")["%CARGA PRIME"].iloc[-1]
                if st.session_state.modo == "last"
                else df_gen["%CARGA PRIME"].mean()
            )

            with cols[i % len(cols)]:
                st.plotly_chart(gauge_small(val * 100, gen), use_container_width=True)

st.markdown("---")

# --------------------------------------------------
# EXPORTAR
# --------------------------------------------------
st.markdown("### 📥 Exportar información")

resumen = df_f.groupby(["LOCACIÓN", "GENERADOR"], as_index=False).agg({
    "TOTAL GENERADO KW-H": "sum",
    "CONSUMO (GLS)": "sum",
    "COSTOS DE GENERACIÓN USD": "sum",
    "%CARGA PRIME": "mean"
})

buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    df_f.to_excel(writer, index=False, sheet_name="Datos Filtrados")
    resumen.to_excel(writer, index=False, sheet_name="Resumen")

st.download_button(
    "📥 Descargar KPIs + Resumen (Excel)",
    data=buffer.getvalue(),
    file_name="ADBO_CIP_Reporte.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.caption("ADBO SMART · Inteligencia de Negocios & IA")


