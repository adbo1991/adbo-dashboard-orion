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
    padding: 18px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
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


def gauge(value, title):
    return go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "%"},
            title={"text": title},
            gauge={
                "axis": {"range": [0, 100]},
                "steps": [
                    {"range": [0, 60], "color": "#d1fae5"},
                    {"range": [60, 80], "color": "#4ade80"},
                    {"range": [80, 95], "color": "#fde68a"},
                    {"range": [95, 100], "color": "#ef4444"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "value": 95
                }
            }
        )
    )

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
# KPIs
# --------------------------------------------------
st.markdown("### 📊 KPIs del período")

k1, k2, k3, k4 = st.columns(4)

k1.metric("🔋 Generación", format_number(df_f["TOTAL GENERADO KW-H"].sum(), decimals=0))
k2.metric("⛽ Consumo", format_number(df_f["CONSUMO (GLS)"].sum()))
k3.metric("💰 Costos", format_number(df_f["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
k4.metric("⚡ Valor prom. KW", format_number(df_f["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# --------------------------------------------------
# CARGA PRIME POR GENERADOR / LOCACIÓN
# --------------------------------------------------
st.markdown("### 🔌 Carga Prime (%) por Generador")

locs = df_f["LOCACIÓN"].dropna().unique()
cols = st.columns(len(locs))

for i, loc in enumerate(locs):
    with cols[i]:
        st.markdown(f"#### 📍 {loc}")
        df_loc = df_f[df_f["LOCACIÓN"] == loc]

        for gen in df_loc["GENERADOR"].dropna().unique():
            df_gen = df_loc[df_f["GENERADOR"] == gen]

            if st.session_state.modo == "last":
                val = df_gen.sort_values("FECHA DEL REGISTRO")["%CARGA PRIME"].iloc[-1]
            else:
                val = df_gen["%CARGA PRIME"].mean()

            st.plotly_chart(gauge(val * 100, gen), use_container_width=True)

st.markdown("---")

# --------------------------------------------------
# GRÁFICOS
# --------------------------------------------------
st.markdown("### 📈 Gráficos")

gen_loc = df_f.groupby(["FECHA DEL REGISTRO", "LOCACIÓN"], as_index=False)["TOTAL GENERADO KW-H"].sum()

fig = px.bar(
    gen_loc,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    color="LOCACIÓN",
    barmode="group",
    title="Generación por Locación"
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# EXPORTAR EXCEL (VISIBLE Y FUNCIONAL)
# --------------------------------------------------
st.markdown("### 📥 Exportar")

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

