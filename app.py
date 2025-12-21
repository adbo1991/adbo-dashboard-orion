# -*- coding: utf-8 -*-
"""
ADBO SMART – CIP – Reporte de Generación Orión Bloque 52
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO
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
def format_number(value, currency=False, decimals=2):
    if pd.isna(value):
        return "—"
    formatted = f"{value:,.{decimals}f}"
    parts = formatted.split(",")
    if len(parts) > 2:
        formatted = "'".join(parts[:-1]) + "," + parts[-1]
    return f"USD {formatted}" if currency else formatted


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
        number={"suffix": "%", "font": {"size": 18}},
        title={"text": titulo, "font": {"size": 13}},
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
# CARGA DE DATOS (PRIVATE SHEET)
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
    ws = sheet.get_worksheet_by_id(540053809)

    values = ws.get_all_values()
    header, rows = values[0], values[1:]

    df_raw = pd.DataFrame(rows, columns=header)

    buffer = StringIO()
    df_raw.to_csv(buffer, index=False)
    buffer.seek(0)

    df = pd.read_csv(
        buffer,
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
        dayfirst=True
    )

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

c1, c2 = st.columns(2)
if c1.button("📅 Últimos 7 días"):
    st.session_state.modo = "7d"
if c2.button("📌 Último registro"):
    st.session_state.modo = "last"

fecha_min = fecha_max if st.session_state.modo == "last" else fecha_max - pd.Timedelta(days=6)
st.info(f"Período activo: {fecha_min.date()} → {fecha_max.date()}")

df_f = df[(df["FECHA DEL REGISTRO"] >= fecha_min) & (df["FECHA DEL REGISTRO"] <= fecha_max)]

# ======================================================
# GRÁFICOS
# ======================================================
st.markdown("---")

# 🔹 Generación diaria
gen_day = df_f.groupby("FECHA DEL REGISTRO", as_index=False)["TOTAL GENERADO KW-H"].sum()
fig_gen = px.line(
    gen_day,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    markers=True,
    title="⚡ Generación total diaria"
)

fig_gen.update_traces(
    text=gen_day["TOTAL GENERADO KW-H"].round(0),
    textposition="top center",
    textfont=dict(size=14),
    cliponaxis=False
)

fig_gen.update_layout(
    margin=dict(t=90),
    title_font=dict(size=16),
    hovermode="x unified"
)

st.plotly_chart(fig_gen, use_container_width=True)

# 🔹 Consumo diario
con_day = df_f.groupby("FECHA DEL REGISTRO", as_index=False)["CONSUMO (GLS)"].sum()
fig_con = px.line(
    con_day,
    x="FECHA DEL REGISTRO",
    y="CONSUMO (GLS)",
    markers=True,
    title="⛽ Consumo diario"
)

fig_con.update_traces(
    text=con_day["CONSUMO (GLS)"].round(0),
    textposition="top center",
    textfont=dict(size=14),
    cliponaxis=False
)

fig_con.update_layout(
    margin=dict(t=90),
    title_font=dict(size=16),
    hovermode="x unified"
)

st.plotly_chart(fig_con, use_container_width=True)

# 🔹 Generación por locación
gen_loc = df_f.groupby(["FECHA DEL REGISTRO", "LOCACIÓN"], as_index=False)["TOTAL GENERADO KW-H"].sum()
fig_bar = px.bar(
    gen_loc,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    color="LOCACIÓN",
    barmode="group",
    color_discrete_map=COLOR_LOCACION,
    title="📊 Generación por locación"
)

fig_bar.update_traces(
    texttemplate="%{y:,.0f}",
    textposition="outside",
    textfont=dict(size=13),
    cliponaxis=False
)

fig_bar.update_layout(margin=dict(t=90))
st.plotly_chart(fig_bar, use_container_width=True)

# ======================================================
# VELOCÍMETROS
# ======================================================
st.markdown("---")
st.markdown("## 🔌 Carga Prime (%) por Generador")

for loc in df_f["LOCACIÓN"].dropna().unique():
    df_loc = df_f[df_f["LOCACIÓN"] == loc]

    with st.expander(f"📍 {loc}", expanded=True):
        gens = df_loc["GENERADOR"].dropna().unique()
        cols = st.columns(min(4, len(gens)))

        for i, gen in enumerate(gens):
            df_gen = df_loc[df_loc["GENERADOR"] == gen]
            valor = (
                df_gen.sort_values("FECHA DEL REGISTRO").iloc[-1]["%CARGA PRIME"] * 100
                if st.session_state.modo == "last"
                else df_gen["%CARGA PRIME"].mean() * 100
            )

            if pd.notna(valor) and valor > 0:
                with cols[i % len(cols)]:
                    st.plotly_chart(gauge_carga(valor, gen), use_container_width=True)

st.caption("ADBO SMART · Inteligencia de Negocios & IA")

