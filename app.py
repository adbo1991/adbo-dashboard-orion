# -*- coding: utf-8 -*-
"""
ADBO SMART – CIP – Reporte de Generación Orión Bloque 52
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==================================================
# CONFIGURACIÓN GENERAL
# ==================================================
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación Orión Bloque 52",
    layout="wide"
)

# ==================================================
# CSS (contraste OK móvil)
# ==================================================
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
    font-weight: 500;
}
div[data-testid="metric-container"] div {
    color: #111827 !important;
    font-size: 1.6rem;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# FUNCIONES AUXILIARES
# ==================================================
def format_number(value, currency=False, decimals=2):
    if pd.isna(value):
        return "—"
    formatted = f"{value:,.{decimals}f}"
    parts = formatted.split(",")
    if len(parts) > 2:
        formatted = "'".join(parts[:-1]) + "," + parts[-1]
    return f"USD {formatted}" if currency else formatted


def gauge_carga(value, title):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "%", "font": {"size": 18}},
            title={"text": title, "font": {"size": 12}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#111827"},
                "steps": [
                    {"range": [0, 60], "color": "#d1fae5"},   # verde pálido
                    {"range": [60, 80], "color": "#4ade80"}, # verde grass
                    {"range": [80, 95], "color": "#fde68a"}, # amarillo
                    {"range": [95, 100], "color": "#ef4444"} # rojo crítico
                ],
                "threshold": {
                    "line": {"color": "red", "width": 3},
                    "thickness": 0.75,
                    "value": 95
                }
            }
        )
    )
    fig.update_layout(height=220, margin=dict(l=10, r=10, t=40, b=10))
    return fig

# ==================================================
# ESTADO DE FILTROS
# ==================================================
if "modo" not in st.session_state:
    st.session_state.modo = "7d"

# ==================================================
# TÍTULO
# ==================================================
st.title("ADBO SMART – CIP – Reporte de Generación Orión Bloque 52")
st.caption("Datos actualizados automáticamente desde Google Sheets")

# ==================================================
# CARGA DE DATOS
# ==================================================
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
        "VALOR POR KW GENERADO",
        "%CARGA PRIME"
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


df = load_data()

# ==================================================
# KPIs HISTÓRICOS
# ==================================================
st.markdown("## 📊 KPIs Históricos (acumulado total)")
c1, c2, c3, c4 = st.columns(4)

c1.metric("🔋 Total Generado", format_number(df["TOTAL GENERADO KW-H"].sum(), decimals=0))
c2.metric("⛽ Consumo Total", format_number(df["CONSUMO (GLS)"].sum()))
c3.metric("💰 Costos Totales", format_number(df["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
c4.metric("⚡ Valor Prom. KW", format_number(df["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# ==================================================
# BOTONES DE FILTRO
# ==================================================
b1, b2, b3 = st.columns([1,1,2])

with b1:
    if st.button("📅 Últimos 7 días"):
        st.session_state.modo = "7d"

with b2:
    if st.button("📌 Último registro"):
        st.session_state.modo = "last"

with b3:
    if st.button("♻️ Reset filtros"):
        st.session_state.modo = "7d"

# ==================================================
# DATA FILTRADA
# ==================================================
fecha_max = df["FECHA DEL REGISTRO"].max()

if st.session_state.modo == "last":
    fecha_min = fecha_max
else:
    fecha_min = fecha_max - pd.Timedelta(days=6)

st.info(f"📅 Período activo: {fecha_min.date()} → {fecha_max.date()}")

df_f = df[
    (df["FECHA DEL REGISTRO"] >= fecha_min) &
    (df["FECHA DEL REGISTRO"] <= fecha_max)
]

# ==================================================
# KPIs FILTRADOS
# ==================================================
st.markdown("## 📈 KPIs del período seleccionado")
k1, k2, k3, k4 = st.columns(4)

k1.metric("🔋 Generación", format_number(df_f["TOTAL GENERADO KW-H"].sum(), decimals=0))
k2.metric("⛽ Consumo", format_number(df_f["CONSUMO (GLS)"].sum()))
k3.metric("💰 Costos", format_number(df_f["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
k4.metric("⚡ Valor prom. KW", format_number(df_f["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# ==================================================
# GRÁFICOS PRINCIPALES
# ==================================================
gen_loc = df_f.groupby(["FECHA DEL REGISTRO", "LOCACIÓN"], as_index=False)["TOTAL GENERADO KW-H"].sum()
gen_tot = df_f.groupby("FECHA DEL REGISTRO", as_index=False)["TOTAL GENERADO KW-H"].sum()
con_tot = df_f.groupby("FECHA DEL REGISTRO", as_index=False)["CONSUMO (GLS)"].sum()

fig_bar = px.bar(
    gen_loc,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    color="LOCACIÓN",
    barmode="group",
    title="Generación por Locación"
)

fig_gen = px.line(
    gen_tot,
    x="FECHA DEL REGISTRO",
    y="TOTAL GENERADO KW-H",
    markers=True,
    title="Generación Total Diaria"
)

fig_con = px.line(
    con_tot,
    x="FECHA DEL REGISTRO",
    y="CONSUMO (GLS)",
    markers=True,
    title="Consumo Diario"
)

st.plotly_chart(fig_bar, use_container_width=True)
st.plotly_chart(fig_gen, use_container_width=True)
st.plotly_chart(fig_con, use_container_width=True)

# ==================================================
# VELOCÍMETROS (AL FINAL)
# ==================================================
st.markdown("---")
st.markdown("## 🔌 Carga Prime (%) por Generador")

for loc in df_f["LOCACIÓN"].dropna().unique():
    with st.expander(f"📍 {loc}", expanded=True):

        df_loc = df_f[df_f["LOCACIÓN"] == loc]
        gens = df_loc["GENERADOR"].dropna().unique()

        cols = st.columns(min(4, len(gens)))

        for i, gen in enumerate(gens):
            with cols[i % len(cols)]:
                df_gen = df_loc[df_loc["GENERADOR"] == gen]

                if st.session_state.modo == "last":
                    valor = df_gen.sort_values("FECHA DEL REGISTRO")["%CARGA PRIME"].iloc[-1]
                else:
                    valor = df_gen["%CARGA PRIME"].mean()

                st.plotly_chart(
                    gauge_carga(valor * 100, gen),
                    use_container_width=True
                )

st.markdown("---")
st.caption("ADBO SMART · Inteligencia de Negocios & IA")
