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
    page_title="ADBO SMART – CIP – Reporte de Generación 52",
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


def gauge_carga(valor, titulo):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        number={"suffix": "%", "font": {"size": 22}},
        title={"text": titulo, "font": {"size": 14}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#0f172a"},
            "steps": [
                {"range": [0, 65], "color": "#22c55e"},
                {"range": [65, 75], "color": "#ef4444"},
                {"range": [75, 80], "color": "#fde047"},
                {"range": [80, 100], "color": "#84cc16"},
            ],
        }
    ))
    fig.update_layout(height=240, margin=dict(l=10, r=10, t=50, b=10))
    return fig

# ======================================================
# TÍTULO
# ======================================================
st.title("ADBO SMART – CIP – Generación 52")
st.caption("Datos actualizados automáticamente desde Google Sheets")

# ======================================================
# CARGA DE DATOS
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
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


df = load_data()

# ======================================================
# FILTRO DÍA
# ======================================================
fecha_dia = df["FECHA DEL REGISTRO"].max()
df_dia = df[df["FECHA DEL REGISTRO"] == fecha_dia]

st.info(f"📅 Día analizado: {fecha_dia.date()}")

# ======================================================
# KPIs GENERALES DEL DÍA
# ======================================================
st.markdown("## 📊 KPIs Generales del Día")

k1, k2, k3, k4 = st.columns(4)
k1.metric("🔋 Generación", format_number(df_dia["TOTAL GENERADO KW-H"].sum(), decimals=0))
k2.metric("⛽ Consumo", format_number(df_dia["CONSUMO (GLS)"].sum()))
k3.metric("💰 Costos", format_number(df_dia["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
k4.metric("⚡ Valor prom. KW", format_number(df_dia["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# ======================================================
# DONAS POR LOCACIÓN (DÍA)
# ======================================================
st.markdown("## 🍩 Distribución por Locación")

gen_loc = df_dia.groupby("LOCACIÓN", as_index=False)["TOTAL GENERADO KW-H"].sum()
con_loc = df_dia.groupby("LOCACIÓN", as_index=False)["CONSUMO (GLS)"].sum()
cost_loc = df_dia.groupby("LOCACIÓN", as_index=False)["COSTOS DE GENERACIÓN USD"].sum()

c1, c2, c3 = st.columns(3)

c1.plotly_chart(px.pie(gen_loc, names="LOCACIÓN", values="TOTAL GENERADO KW-H", hole=0.55,
                       title="🔋 Generación por Locación"), use_container_width=True)
c2.plotly_chart(px.pie(con_loc, names="LOCACIÓN", values="CONSUMO (GLS)", hole=0.55,
                       title="⛽ Consumo por Locación"), use_container_width=True)
c3.plotly_chart(px.pie(cost_loc, names="LOCACIÓN", values="COSTOS DE GENERACIÓN USD", hole=0.55,
                       title="💰 Costos USD por Locación"), use_container_width=True)

st.markdown("---")

# ======================================================
# PROMEDIO KW POR LOCACIÓN
# ======================================================
st.markdown("## ⚡ Valor promedio KW por Locación")

df_kw_loc = df_dia.groupby("LOCACIÓN", as_index=False)["VALOR POR KW GENERADO"].mean()

st.dataframe(
    df_kw_loc.style.format({"VALOR POR KW GENERADO": "{:,.2f}"}),
    use_container_width=True
)

st.markdown("---")

# ======================================================
# ÚLTIMOS 7 DÍAS
# ======================================================
st.markdown("## 📈 Tendencia últimos 7 días")

fecha_min_7 = fecha_dia - pd.Timedelta(days=6)
df_7 = df[df["FECHA DEL REGISTRO"] >= fecha_min_7]

gen_7 = df_7.groupby("FECHA DEL REGISTRO", as_index=False)["TOTAL GENERADO KW-H"].sum()
con_7 = df_7.groupby("FECHA DEL REGISTRO", as_index=False)["CONSUMO (GLS)"].sum()

fig_gen = px.line(gen_7, x="FECHA DEL REGISTRO", y="TOTAL GENERADO KW-H",
                  markers=True, title="🔋 Generación diaria (7 días)")
fig_gen.update_layout(
    yaxis=dict(range=[0, gen_7["TOTAL GENERADO KW-H"].max() * 1.15],
               tickfont=dict(size=14)),
    xaxis=dict(tickfont=dict(size=14))
)

fig_con = px.line(con_7, x="FECHA DEL REGISTRO", y="CONSUMO (GLS)",
                  markers=True, title="⛽ Consumo diario (7 días)")
fig_con.update_layout(
    yaxis=dict(range=[0, con_7["CONSUMO (GLS)"].max() * 1.15],
               tickfont=dict(size=14)),
    xaxis=dict(tickfont=dict(size=14))
)

st.plotly_chart(fig_gen, use_container_width=True)
st.plotly_chart(fig_con, use_container_width=True)

st.markdown("---")

# ======================================================
# VELOCÍMETROS
# ======================================================
st.markdown("## 🔌 Carga Prime (%) por Generador")

for loc in df_dia["LOCACIÓN"].dropna().unique():
    with st.expander(f"📍 {loc}", expanded=True):
        gens = df_dia[df_dia["LOCACIÓN"] == loc]["GENERADOR"].unique()
        cols = st.columns(min(4, len(gens)))

        for i, gen in enumerate(gens):
            valor = (
                df_dia[(df_dia["LOCACIÓN"] == loc) & (df_dia["GENERADOR"] == gen)]
                ["%CARGA PRIME"].mean() * 100
            )

            if pd.notna(valor):
                with cols[i % len(cols)]:
                    st.plotly_chart(gauge_carga(valor, gen), use_container_width=True)

st.caption("ADBO SMART · Inteligencia de Negocios & IA")



