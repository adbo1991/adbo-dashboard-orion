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
# CONFIGURACIÓN GENERAL
# ======================================================
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación Orión Bloque 52",
    layout="wide"
)

# ======================================================
# COLORES POR LOCACIÓN
# ======================================================
COLOR_LOCACION = {
    "PEÑA BLANCA": "#38bdf8",  # celeste
    "OCANO": "#f59e0b",        # naranja
    "CFE": "#6b7280"           # gris
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
    idx = row.index.get_loc("LOCACIÓN")
    styles[idx] = f"background-color:{color};color:white;font-weight:600;"
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
# CARGA DE DATOS
# ======================================================
import gspread
from google.oauth2.service_account import Credentials

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

    # 👉 Abre el Google Sheet por ID
    sheet = gc.open_by_key("1p9aVrwHFNIfW_08yj3RkqF4u8qdGxIrRFc63ZXjH55I")

    # 👉 Hoja por GID
    worksheet = sheet.get_worksheet_by_id(540053809)

    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    # ===============================
    # LIMPIEZA
    # ===============================
    df = df[
        (df["REGISTRO CORRECTO"] == 1) &
        (df["POTENCIA ACTIVA (KW)"].notna()) &
        (df["POTENCIA ACTIVA (KW)"] != "")
    ].copy()

    df["FECHA DEL REGISTRO"] = pd.to_datetime(
        df["FECHA DEL REGISTRO"],
        dayfirst=True,
        errors="coerce"
    )

    cols_numeric = [
        "TOTAL GENERADO KW-H",
        "CONSUMO (GLS)",
        "COSTOS DE GENERACIÓN USD",
        "VALOR POR KW GENERADO",
        "%CARGA PRIME"
    ]

    for c in cols_numeric:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

df = load_data

# ===============================
# SEGURIDAD NUMÉRICA (CRÍTICO)
# ===============================
numeric_cols = [
    "TOTAL GENERADO KW-H",
    "CONSUMO (GLS)",
    "COSTOS DE GENERACIÓN USD",
    "VALOR POR KW GENERADO",
    "%CARGA PRIME"
]

for c in numeric_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
# ======================================================
# KPIs HISTÓRICOS (NO DESAPARECEN)
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

b1, b2 = st.columns(2)
if b1.button("📅 Últimos 7 días"):
    st.session_state.modo = "7d"
if b2.button("📌 Último registro"):
    st.session_state.modo = "last"

fecha_min = fecha_max if st.session_state.modo == "last" else fecha_max - pd.Timedelta(days=6)
st.info(f"Período activo: {fecha_min.date()} → {fecha_max.date()}")

df_f = df[(df["FECHA DEL REGISTRO"] >= fecha_min) & (df["FECHA DEL REGISTRO"] <= fecha_max)]

# ======================================================
# KPIs FILTRADOS
# ======================================================
st.markdown("### 📊 KPIs del período seleccionado")
f1, f2, f3, f4 = st.columns(4)

f1.metric("🔋 Generación", format_number(df_f["TOTAL GENERADO KW-H"].sum(), decimals=0))
f2.metric("⛽ Consumo", format_number(df_f["CONSUMO (GLS)"].sum()))
f3.metric("💰 Costos", format_number(df_f["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
f4.metric("⚡ Valor prom. KW", format_number(df_f["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# ======================================================
# TABLA RESUMEN POR LOCACIÓN Y GENERADOR
# ======================================================
st.markdown("### 📋 Resumen por Locación y Generador")

df_tabla = (
    df_f.groupby(["LOCACIÓN", "GENERADOR"], dropna=True)
    .agg({
        "HORAS OPERATIVAS": "sum",
        "TOTAL GENERADO KW-H": "sum",
        "CONSUMO (GLS)": "sum",
        "%CARGA PRIME": "mean",
        "VALOR POR KW GENERADO": "mean"
    })
    .reset_index()
    .sort_values(["LOCACIÓN", "GENERADOR"])
)

# ---------- FORMATOS ----------
df_tabla["HORAS OPERATIVAS"] = df_tabla["HORAS OPERATIVAS"].round(2)
df_tabla["TOTAL GENERADO KW-H"] = df_tabla["TOTAL GENERADO KW-H"].round(2)
df_tabla["CONSUMO (GLS)"] = df_tabla["CONSUMO (GLS)"].round(2)
df_tabla["VALOR POR KW GENERADO"] = df_tabla["VALOR POR KW GENERADO"].round(2)

# % carga prime → porcentaje SIN decimales
df_tabla["%CARGA PRIME"] = (df_tabla["%CARGA PRIME"] * 100).round(0).astype("Int64")

# ---------- VISUAL ----------
st.dataframe(
    df_tabla.style
        .apply(style_locacion, axis=1)
        .format({
            "HORAS OPERATIVAS": "{:,.2f}",
            "TOTAL GENERADO KW-H": "{:,.2f}",
            "CONSUMO (GLS)": "{:,.2f}",
            "VALOR POR KW GENERADO": "{:,.2f}",
            "%CARGA PRIME": "{}%"
        }),
    use_container_width=True
)

# ======================================================
# GRÁFICOS PRINCIPALES
# ======================================================
st.markdown("---")
gen_loc = df_f.groupby(["FECHA DEL REGISTRO","LOCACIÓN"], as_index=False)["TOTAL GENERADO KW-H"].sum()
fig_bar = px.bar(
    gen_loc,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    color="LOCACIÓN",
    barmode="group",
    color_discrete_map=COLOR_LOCACION,
    title="Generación por Locación"
)

gen_day = df_f.groupby("FECHA DEL REGISTRO", as_index=False)["TOTAL GENERADO KW-H"].sum()
fig_line = px.line(gen_day, x="FECHA DEL REGISTRO", y="TOTAL GENERADO KW-H",
                   markers=True, title="Generación diaria")

con_day = df_f.groupby("FECHA DEL REGISTRO", as_index=False)["CONSUMO (GLS)"].sum()
fig_con = px.line(con_day, x="FECHA DEL REGISTRO", y="CONSUMO (GLS)",
                  markers=True, title="Consumo diario")

st.plotly_chart(fig_bar, use_container_width=True)
st.plotly_chart(fig_line, use_container_width=True)
st.plotly_chart(fig_con, use_container_width=True)

# ======================================================
# VELOCÍMETROS (AL FINAL)
# ======================================================
st.markdown("---")
st.markdown("## 🔌 Carga Prime (%) por Generador")

for loc in df_f["LOCACIÓN"].dropna().unique():
    df_loc = df_f[df_f["LOCACIÓN"] == loc]

    with st.expander(f"📍 {loc}", expanded=True):
        gens = df_loc["GENERADOR"].dropna().unique()
        cols = st.columns(min(4, len(gens)))
        col_i = 0

        for gen in gens:
            df_gen = df_loc[df_loc["GENERADOR"] == gen]

            valor = (
                df_gen.sort_values("FECHA DEL REGISTRO").iloc[-1]["%CARGA PRIME"] * 100
                if st.session_state.modo == "last"
                else df_gen["%CARGA PRIME"].mean() * 100
            )

            if pd.isna(valor) or valor <= 0:
                continue

            with cols[col_i % len(cols)]:
                st.plotly_chart(gauge_carga(valor, gen), use_container_width=True)
            col_i += 1

st.caption("ADBO SMART · Inteligencia de Negocios & IA")
