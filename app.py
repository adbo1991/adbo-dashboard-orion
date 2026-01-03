# -*- coding: utf-8 -*-
"""
ADBO SMART – CIP – Reporte de Generación B52
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from io import StringIO, BytesIO
import gspread
from google.oauth2.service_account import Credentials

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación B52",
    layout="wide"
)

# ======================================================
# FUNCIONES AUXILIARES
# ======================================================
def fig_to_image(fig, width, height):
    return BytesIO(
        pio.to_image(
            fig,
            format="png",
            width=width,
            height=height,
            scale=2
        )
    )

def gauge_carga(valor, voltaje, titulo):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        number={"suffix": "%"},
        title={"text": f"{titulo}<br><span style='font-size:12px'>⚡ {voltaje:.0f} V</span>"},
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
    fig.update_layout(height=260)
    return fig

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
    df = pd.DataFrame(rows, columns=header)

    df = df[
        (df["REGISTRO CORRECTO"] == "1") &
        (df["POTENCIA ACTIVA (KW)"] != "")
    ]

    df["FECHA DEL REGISTRO"] = pd.to_datetime(
        df["FECHA DEL REGISTRO"], dayfirst=True
    )

    for c in [
        "TOTAL GENERADO KW-H",
        "CONSUMO (GLS)",
        "COSTOS DE GENERACIÓN USD",
        "VALOR POR KW GENERADO",
        "%CARGA PRIME",
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

st.title("ADBO SMART – CIP – Generación B52")
st.caption(f"📅 Día analizado: {fecha_dia.date()}")

# ======================================================
# KPIs
# ======================================================
k1, k2, k3, k4 = st.columns(4)
k1.metric("🔋 Generación", f"{df_dia['TOTAL GENERADO KW-H'].sum():,.0f}")
k2.metric("⛽ Consumo", f"{df_dia['CONSUMO (GLS)'].sum():,.2f}")
k3.metric("💰 Costos", f"USD {df_dia['COSTOS DE GENERACIÓN USD'].sum():,.2f}")
k4.metric("⚡ Valor prom. KW", f"USD {df_dia['VALOR POR KW GENERADO'].mean():,.2f}")

# ======================================================
# GRÁFICOS
# ======================================================
gen_loc = df_dia.groupby("LOCACIÓN", as_index=False)["TOTAL GENERADO KW-H"].sum()
con_loc = df_dia.groupby("LOCACIÓN", as_index=False)["CONSUMO (GLS)"].sum()
cost_loc = df_dia.groupby("LOCACIÓN", as_index=False)["COSTOS DE GENERACIÓN USD"].sum()

fig_gen_loc = px.pie(gen_loc, names="LOCACIÓN", values="TOTAL GENERADO KW-H", hole=0.55)
fig_con_loc = px.pie(con_loc, names="LOCACIÓN", values="CONSUMO (GLS)", hole=0.55)
fig_cost_loc = px.pie(cost_loc, names="LOCACIÓN", values="COSTOS DE GENERACIÓN USD", hole=0.55)

df_7 = df[df["FECHA DEL REGISTRO"] >= fecha_dia - pd.Timedelta(days=6)]
gen_7 = df_7.groupby("FECHA DEL REGISTRO", as_index=False)["TOTAL GENERADO KW-H"].sum()
con_7 = df_7.groupby("FECHA DEL REGISTRO", as_index=False)["CONSUMO (GLS)"].sum()

fig_gen_7 = px.line(gen_7, x="FECHA DEL REGISTRO", y="TOTAL GENERADO KW-H", markers=True)
fig_con_7 = px.line(con_7, x="FECHA DEL REGISTRO", y="CONSUMO (GLS)", markers=True)

st.plotly_chart(fig_gen_7, use_container_width=True)
st.plotly_chart(fig_con_7, use_container_width=True)

# ======================================================
# PDF HORIZONTAL
# ======================================================
def generar_pdf_reporte(df_dia, fecha_dia):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("<b>ADBO SMART – CIP – Reporte Diario B52</b>", styles["Title"]))
    elementos.append(Paragraph(f"Fecha: {fecha_dia.strftime('%d-%m-%Y')}", styles["Normal"]))
    elementos.append(Spacer(1, 12))

    kpi_table = Table([
        ["🔋 Generación", f"{df_dia['TOTAL GENERADO KW-H'].sum():,.0f} kWh"],
        ["⛽ Consumo", f"{df_dia['CONSUMO (GLS)'].sum():,.2f} GLS"],
        ["💰 Costos", f"USD {df_dia['COSTOS DE GENERACIÓN USD'].sum():,.2f}"],
        ["⚡ Valor KW", f"USD {df_dia['VALOR POR KW GENERADO'].mean():,.2f}"],
    ], colWidths=[180]*4)

    kpi_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONT", (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 12),
    ]))

    elementos.append(kpi_table)
    elementos.append(Spacer(1, 16))

    elementos.append(
        Table([[
            Image(fig_to_image(fig_gen_loc, 450, 350), 240, 200),
            Image(fig_to_image(fig_con_loc, 450, 350), 240, 200),
            Image(fig_to_image(fig_cost_loc, 450, 350), 240, 200),
        ]])
    )

    elementos.append(Spacer(1, 20))
    elementos.append(Image(fig_to_image(fig_gen_7, 1100, 400), 760, 260))
    elementos.append(Spacer(1, 12))
    elementos.append(Image(fig_to_image(fig_con_7, 1100, 400), 760, 260))

    doc.build(elementos)
    buffer.seek(0)
    return buffer


pdf_buffer = generar_pdf_reporte(df_dia, fecha_dia)

st.download_button(
    label="📄 Descargar PDF horizontal",
    data=pdf_buffer,
    file_name=f"Reporte_B52_{fecha_dia.strftime('%Y%m%d')}.pdf",
    mime="application/pdf"
)
