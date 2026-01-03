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
def format_number(value, currency=False, decimals=2):
    if pd.isna(value):
        return "—"
    formatted = f"{value:,.{decimals}f}"
    return f"USD {formatted}" if currency else formatted


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

# ======================================================
# GRÁFICOS (MISMO DASHBOARD)
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

# ======================================================
# EXPORTAR GRÁFICOS COMO IMÁGENES
# ======================================================
pio.write_image(fig_gen_loc, "gen_loc.png", width=450, height=350, scale=2)
pio.write_image(fig_con_loc, "con_loc.png", width=450, height=350, scale=2)
pio.write_image(fig_cost_loc, "cost_loc.png", width=450, height=350, scale=2)

pio.write_image(fig_gen_7, "gen_7.png", width=1100, height=400, scale=2)
pio.write_image(fig_con_7, "con_7.png", width=1100, height=400, scale=2)

# ======================================================
# PDF HORIZONTAL – MISMO LAYOUT
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

    # TÍTULO
    elementos.append(Paragraph("<b>ADBO SMART – CIP – Reporte Diario B52</b>", styles["Title"]))
    elementos.append(Paragraph(f"Fecha: {fecha_dia.strftime('%d-%m-%Y')}", styles["Normal"]))
    elementos.append(Spacer(1, 12))

    # KPIs
    total_gen = df_dia["TOTAL GENERADO KW-H"].sum()
    total_con = df_dia["CONSUMO (GLS)"].sum()
    total_cost = df_dia["COSTOS DE GENERACIÓN USD"].sum()
    valor_kw = df_dia["VALOR POR KW GENERADO"].mean()

    kpi_table = Table([
        ["🔋 Generación", f"{total_gen:,.0f} kWh"],
        ["⛽ Consumo", f"{total_con:,.2f} GLS"],
        ["💰 Costos", f"USD {total_cost:,.2f}"],
        ["⚡ Valor KW", f"USD {valor_kw:,.2f}"],
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

    # DONAS
    donas = Table([
        [
            Image("gen_loc.png", 240, 200),
            Image("con_loc.png", 240, 200),
            Image("cost_loc.png", 240, 200)
        ]
    ])
    elementos.append(donas)
    elementos.append(Spacer(1, 20))

    # TENDENCIAS
    elementos.append(Image("gen_7.png", 760, 260))
    elementos.append(Spacer(1, 12))
    elementos.append(Image("con_7.png", 760, 260))

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