# -*- coding: utf-8 -*-
"""
ADBO SMART – CIP – Reporte de Generación B52
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO
import gspread
from google.oauth2.service_account import Credentials
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación B52",
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


def gauge_carga(valor, voltaje, titulo):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        number={"suffix": "%", "font": {"size": 22}},
        title={
            "text": f"{titulo}<br><span style='font-size:14px'>⚡ {voltaje:.0f} V</span>",
            "font": {"size": 14}
        },
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#0f172a"},
            "steps": [
                {"range": [0, 65], "color": "#76a5af"},
                {"range": [65, 75], "color": "#6aa84f"},
                {"range": [75, 80], "color": "#e2b969"},
                {"range": [80, 100], "color": "#9b2f2f"},
            ],
        }
    ))
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=60, b=10))
    return fig

# ======================================================
# TÍTULO
# ======================================================
st.title("ADBO SMART – CIP – Generación B52")
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
        "HORAS OPERATIVAS",
        "VOLTAJE (>=480V)"
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
# KPIs DEL DÍA
# ======================================================
st.markdown("## 📊 KPIs Generales del Día")

k1, k2, k3, k4 = st.columns(4)
k1.metric("🔋 Generación", format_number(df_dia["TOTAL GENERADO KW-H"].sum(), decimals=0))
k2.metric("⛽ Consumo", format_number(df_dia["CONSUMO (GLS)"].sum()))
k3.metric("💰 Costos", format_number(df_dia["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
k4.metric("⚡ Valor prom. KW", format_number(df_dia["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# ======================================================
# DONAS POR LOCACIÓN
# ======================================================
st.markdown("## 🛢️ Distribución por Locación")

gen_loc = df_dia.groupby("LOCACIÓN", as_index=False)["TOTAL GENERADO KW-H"].sum()
con_loc = df_dia.groupby("LOCACIÓN", as_index=False)["CONSUMO (GLS)"].sum()
cost_loc = df_dia.groupby("LOCACIÓN", as_index=False)["COSTOS DE GENERACIÓN USD"].sum()

c1, c2, c3 = st.columns(3)

def donut(fig, unidad):
    fig.update_traces(
        textinfo="label+percent+value",
        texttemplate=f"<b>%{{label}}</b><br>%{{value:,.0f}} {unidad}<br>(%{{percent}})"
    )
    return fig

fig1 = px.pie(gen_loc, names="LOCACIÓN", values="TOTAL GENERADO KW-H", hole=0.55,
              title="🔋 Generación por Locación")
c1.plotly_chart(donut(fig1, "kWh"), use_container_width=True)

fig2 = px.pie(con_loc, names="LOCACIÓN", values="CONSUMO (GLS)", hole=0.55,
              title="⛽ Consumo por Locación")
c2.plotly_chart(donut(fig2, "GLS"), use_container_width=True)

fig3 = px.pie(cost_loc, names="LOCACIÓN", values="COSTOS DE GENERACIÓN USD", hole=0.55,
              title="💰 Costos USD por Locación")
c3.plotly_chart(donut(fig3, "USD"), use_container_width=True)

st.markdown("---")

# ======================================================
# TENDENCIA 7 DÍAS
# ======================================================
st.markdown("## 📈 Tendencia últimos 7 días")

df_7 = df[df["FECHA DEL REGISTRO"] >= fecha_dia - pd.Timedelta(days=6)]

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
            df_tmp = df_dia[
                (df_dia["LOCACIÓN"] == loc) &
                (df_dia["GENERADOR"] == gen)
            ]

            valor = df_tmp["%CARGA PRIME"].mean() * 100
            voltaje = df_tmp["VOLTAJE (>=480V)"].mean()

            if pd.notna(valor):
                with cols[i % len(cols)]:
                    st.plotly_chart(
                        gauge_carga(valor, voltaje, gen),
                        use_container_width=True
                    )

st.caption("ADBO SMART · Inteligencia de Negocios & IA")

#%%

def generar_pdf_reporte(df_dia, fecha_dia):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elementos = []

    # TÍTULO
    elementos.append(Paragraph(
        "<b>ADBO SMART – CIP – Reporte Diario B52</b>",
        styles["Title"]
    ))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph(
        f"<b>Fecha:</b> {fecha_dia.strftime('%d-%m-%Y')}",
        styles["Normal"]
    ))
    elementos.append(Spacer(1, 12))

    # KPIs
    total_gen = df_dia["TOTAL GENERADO KW-H"].sum()
    total_con = df_dia["CONSUMO (GLS)"].sum()
    total_cost = df_dia["COSTOS DE GENERACIÓN USD"].sum()
    valor_kw = df_dia["VALOR POR KW GENERADO"].mean()

    elementos.append(Paragraph(f"🔋 Generación total: {total_gen:,.0f}", styles["Normal"]))
    elementos.append(Paragraph(f"⛽ Consumo total: {total_con:,.2f}", styles["Normal"]))
    elementos.append(Paragraph(f"💰 Costos USD: {total_cost:,.2f}", styles["Normal"]))
    elementos.append(Paragraph(f"⚡ Valor prom. KW: {valor_kw:,.2f}", styles["Normal"]))
    elementos.append(Spacer(1, 16))

    # TABLA POR LOCACIÓN
    tabla_df = (
        df_dia.groupby("LOCACIÓN", as_index=False)
        .agg({
            "TOTAL GENERADO KW-H": "sum",
            "CONSUMO (GLS)": "sum",
            "COSTOS DE GENERACIÓN USD": "sum"
        })
    )

    data = [tabla_df.columns.tolist()] + tabla_df.values.tolist()

    tabla = Table(data, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONT", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "RIGHT")
    ]))

    elementos.append(Paragraph("<b>Resumen por Locación</b>", styles["Heading2"]))
    elementos.append(tabla)

    doc.build(elementos)
    buffer.seek(0)
    return buffer

pdf_buffer = generar_pdf_reporte(df_dia, fecha_dia)

st.download_button(
    label="📄 Descargar PDF del día",
    data=pdf_buffer,
    file_name=f"Reporte_B52_{fecha_dia.strftime('%Y%m%d')}.pdf",
    mime="application/pdf"
)

modo_impresion = st.toggle("🖨️ Modo impresión", value=False)

if modo_impresion:
    st.markdown("""
    <style>
    /* Ocultar botones */
    button, .stDownloadButton {
        display: none !important;
    }

    /* Quitar sombras */
    div[data-testid="metric-container"] {
        box-shadow: none !important;
        border: 1px solid #ccc;
    }

    /* Forzar colores */
    * {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    /* Evitar cortes */
    .js-plotly-plot {
        page-break-inside: avoid;
    }

    /* Tamaño letras */
    h1, h2, h3 {
        font-size: 22px !important;
    }
    </style>
    """, unsafe_allow_html=True)