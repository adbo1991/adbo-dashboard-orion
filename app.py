# -*- coding: utf-8 -*-
"""
ADBO SMART – CIP – Reporte de Generación Orión Bloque 52
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación Orión Bloque 52",
    layout="wide"
)

# --------------------------------------------------
# CSS
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
div[data-testid="metric-container"] label {
    color: #6b7280 !important;
    font-size: 0.85rem;
}
div[data-testid="metric-container"] div {
    color: #111827 !important;
    font-size: 1.6rem;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# FUNCIONES
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
    d = (current - previous) / previous * 100
    arrow = "↑" if d >= 0 else "↓"
    return f"{arrow} {abs(d):.1f}%"


def gauge_chart(value, title):
    return go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": "%"},
        title={"text": title},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#2563eb"},
            "steps": [
                {"range": [0, 60], "color": "#fee2e2"},
                {"range": [60, 85], "color": "#fef3c7"},
                {"range": [85, 100], "color": "#dcfce7"},
            ],
        }
    ))

# --------------------------------------------------
# TÍTULO
# --------------------------------------------------
st.title("ADBO SMART – CIP – Reporte de Generación Orión Bloque 52")
st.caption("Datos actualizados automáticamente desde Google Sheets")

# --------------------------------------------------
# CARGA DE DATOS
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
        df["FECHA DEL REGISTRO"], dayfirst=True, errors="coerce"
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

# --------------------------------------------------
# FILTROS
# --------------------------------------------------
fecha_max = df["FECHA DEL REGISTRO"].max()
fecha_min_default = fecha_max - pd.Timedelta(days=6)

if "modo" not in st.session_state:
    st.session_state.modo = "7d"

b1, b2, b3 = st.columns(3)

if b1.button("📅 Últimos 7 días"):
    st.session_state.modo = "7d"

if b2.button("📌 Último registro"):
    st.session_state.modo = "last"

if b3.button("♻ Reset filtros"):
    st.session_state.modo = "7d"

if st.session_state.modo == "last":
    fecha_min = fecha_max
else:
    fecha_min = fecha_min_default

st.info(f"📆 Período activo: {fecha_min.date()} → {fecha_max.date()}")

df_f = df[
    (df["FECHA DEL REGISTRO"] >= fecha_min) &
    (df["FECHA DEL REGISTRO"] <= fecha_max)
]

# --------------------------------------------------
# 🔌 CARGA PRIME (%) POR LOCACIÓN
# --------------------------------------------------
st.markdown("### 🔌 Carga Prime (%) por Locación")

locaciones = df_f["LOCACIÓN"].dropna().unique()
cols = st.columns(len(locaciones))

for i, loc in enumerate(locaciones):
    df_loc = df_f[df_f["LOCACIÓN"] == loc]

    if st.session_state.modo == "last":
        value = df_loc.sort_values("FECHA DEL REGISTRO")["%CARGA PRIME"].iloc[-1]
    else:
        value = df_loc["%CARGA PRIME"].mean()

    with cols[i]:
        st.plotly_chart(
            gauge_chart(value, f"{loc}"),
            use_container_width=True
        )

# --------------------------------------------------
# GRÁFICOS
# --------------------------------------------------
gen_loc = df_f.groupby(
    ["FECHA DEL REGISTRO", "LOCACIÓN"], as_index=False
)["TOTAL GENERADO KW-H"].sum()

gen_total = df_f.groupby(
    "FECHA DEL REGISTRO", as_index=False
)["TOTAL GENERADO KW-H"].sum()

consumo = df_f.groupby(
    "FECHA DEL REGISTRO", as_index=False
)["CONSUMO (GLS)"].sum()

st.plotly_chart(
    px.bar(
        gen_loc,
        x="FECHA DEL REGISTRO",
        y="TOTAL GENERADO KW-H",
        color="LOCACIÓN",
        barmode="group",
        title="Generación por Locación"
    ),
    use_container_width=True
)

st.plotly_chart(
    px.line(gen_total, x="FECHA DEL REGISTRO", y="TOTAL GENERADO KW-H", markers=True),
    use_container_width=True
)

st.plotly_chart(
    px.line(consumo, x="FECHA DEL REGISTRO", y="CONSUMO (GLS)", markers=True),
    use_container_width=True
)

st.caption("ADBO SMART · Inteligencia de Negocios & IA")
