# -*- coding: utf-8 -*-
"""
ADBO SMART – CIP – Reporte de Generación Orión Bloque 52
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ======================================================
# CONFIGURACIÓN
# ======================================================
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación Orión Bloque 52",
    layout="wide"
)

# ======================================================
# COLORES
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
div[data-testid="metric-container"] label {
    color: #6b7280 !important;
}
div[data-testid="metric-container"] div {
    color: #111827 !important;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# FUNCIONES
# ======================================================
def abbreviate_number(value, currency=False):
    if pd.isna(value):
        return "—"
    abs_v = abs(value)
    if abs_v >= 1_000_000_000:
        s = f"{value/1_000_000_000:.2f}B"
    elif abs_v >= 1_000_000:
        s = f"{value/1_000_000:.2f}M"
    elif abs_v >= 1_000:
        s = f"{value/1_000:.1f}K"
    else:
        s = f"{value:.0f}"
    return f"USD {s}" if currency else s


def style_locacion(row):
    color = COLOR_LOCACION.get(row["LOCACIÓN"], "#ffffff")
    styles = [""] * len(row)
    styles[row.index.get_loc("LOCACIÓN")] = (
        f"background-color:{color};color:white;font-weight:600;"
    )
    return styles


def gauge_carga(valor, titulo):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        number={"suffix": "%"},
        title={"text": titulo},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#0f172a"},
            "steps": [
                {"range": [0, 60], "color": "#d1fae5"},
                {"range": [60, 80], "color": "#4ade80"},
                {"range": [80, 95], "color": "#fde68a"},
                {"range": [95, 100], "color": "#ef4444"},
            ],
        }
    ))
    fig.update_layout(height=220, margin=dict(l=10, r=10, t=40, b=10))
    return fig

# ======================================================
# TÍTULO
# ======================================================
st.title("ADBO SMART – CIP – Reporte de Generación Orión Bloque 52")
st.caption("Datos actualizados automáticamente desde Google Sheets")

# ======================================================
# CARGA DE DATOS
# ======================================================
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
    df["FECHA"] = df["FECHA DEL REGISTRO"].dt.date

    for c in [
        "TOTAL GENERADO KW-H",
        "CONSUMO (GLS)",
        "COSTOS DE GENERACIÓN USD",
        "VALOR POR KW GENERADO",
        "%CARGA PRIME",
        "HORAS OPERATIVAS"
    ]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


df = load_data()

# ======================================================
# KPIs HISTÓRICOS
# ======================================================
st.markdown("### 📊 KPIs Históricos (acumulado total)")
k1, k2, k3, k4 = st.columns(4)

k1.metric("🔋 Total Generado", abbreviate_number(df["TOTAL GENERADO KW-H"].sum()))
k2.metric("⛽ Consumo Total", abbreviate_number(df["CONSUMO (GLS)"].sum()))
k3.metric("💰 Costos Totales", abbreviate_number(df["COSTOS DE GENERACIÓN USD"].sum(), True))
k4.metric("⚡ Valor prom. KW", abbreviate_number(df["VALOR POR KW GENERADO"].mean(), True))

st.markdown("---")

# ======================================================
# FILTROS
# ======================================================
fecha_max = df["FECHA"].max()
modo = st.radio("Modo", ["Últimos 7 días", "Último registro"], horizontal=True)

fecha_min = fecha_max if modo == "Último registro" else fecha_max - pd.Timedelta(days=6)
st.info(f"Período activo: {fecha_min} → {fecha_max}")

df_f = df[(df["FECHA"] >= fecha_min) & (df["FECHA"] <= fecha_max)]

# ======================================================
# GRÁFICOS
# ======================================================
st.markdown("## 📈 Evolución diaria")

gen_day = df_f.groupby("FECHA", as_index=False)["TOTAL GENERADO KW-H"].sum()
fig_gen = px.line(gen_day, x="FECHA", y="TOTAL GENERADO KW-H",
                  text=gen_day["TOTAL GENERADO KW-H"].apply(abbreviate_number),
                  markers=True, title="🔋 Generación diaria")
fig_gen.update_traces(textposition="top center")
st.plotly_chart(fig_gen, use_container_width=True)

con_day = df_f.groupby("FECHA", as_index=False)["CONSUMO (GLS)"].sum()
fig_con = px.line(con_day, x="FECHA", y="CONSUMO (GLS)",
                  text=con_day["CONSUMO (GLS)"].apply(abbreviate_number),
                  markers=True, title="⛽ Consumo diario")
fig_con.update_traces(textposition="top center")
st.plotly_chart(fig_con, use_container_width=True)

# ======================================================
# VELOCÍMETROS
# ======================================================
st.markdown("---")
st.markdown("## 🔌 Carga Prime (%) por Generador")

for loc in df_f["LOCACIÓN"].dropna().unique():
    with st.expander(f"📍 {loc}", expanded=True):
        df_loc = df_f[df_f["LOCACIÓN"] == loc]
        gens = df_loc["GENERADOR"].unique()
        cols = st.columns(min(4, len(gens)))

        for i, gen in enumerate(gens):
            val = df_loc[df_loc["GENERADOR"] == gen]["%CARGA PRIME"].mean() * 100
            if pd.notna(val) and val > 0:
                with cols[i % len(cols)]:
                    st.plotly_chart(gauge_carga(val, gen), use_container_width=True)

st.caption("ADBO SMART · Inteligencia de Negocios & IA")
