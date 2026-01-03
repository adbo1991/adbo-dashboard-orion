# -*- coding: utf-8 -*-
"""
ADBO SMART – CIP – Reporte de Generación B52
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import plotly.io as pio
import gspread
from google.oauth2.service_account import Credentials

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================
st.set_page_config(
    page_title="ADBO SMART – CIP – Generación B52",
    layout="wide"
)

# ======================================================
# FUNCIONES SEGURAS
# ======================================================
def safe_sum(series):
    return series.sum() if series.notna().any() else 0

def safe_mean(series):
    return series.mean() if series.notna().any() else 0

def fig_to_image(fig, width, height):
    return BytesIO(
        fig.to_image(
            format="png",
            width=width,
            height=height,
            scale=2,
            engine="kaleido"  # 🔥 CLAVE PARA STREAMLIT CLOUD
        )
    )

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
        "VALOR POR KW GENERADO"
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
# KPIs (ROBUSTOS)
# ======================================================
k1, k2, k3, k4 = st.columns(4)

k1.metric("🔋 Generación", f"{safe_sum(df_dia['TOTAL GENERADO KW-H']):,.0f}")
k2.metric("⛽ Consumo", f"{safe_sum(df_dia['CONSUMO (GLS)']):,.2f}")
k3.metric("💰 Costos", f"USD {safe_sum(df_dia['COSTOS DE GENERACIÓN USD']):,.2f}")
k4.metric("⚡ Valor prom. KW", f"USD {safe_mean(df_dia['VALOR POR KW GENERADO']):,.2f}")

# ======================================================
# GRÁFICOS DASHBOARD
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
# PDF HORIZONTAL – MISMO DASHBOARD
# ======================================================
def generar_pdf_reporte():
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

    kpis = Table([
        ["🔋 Generación", f"{safe_sum(df_dia['TOTAL GENERADO KW-H']):,.0f} kWh"],
        ["⛽ Consumo", f"{safe_sum(df_dia['CONSUMO (GLS)']):,.2f} GLS"],
        ["💰 Costos", f"USD {safe_sum(df_dia['COSTOS DE GENERACIÓN USD']):,.2f}"],
        ["⚡ Valor KW", f"USD {safe_mean(df_dia['VALOR POR KW GENERADO']):,.2f}"]
    ], colWidths=[180]*4)

    kpis.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONT", (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 12),
    ]))

    elementos.append(kpis)
    elementos.append(Spacer(1, 16))

    elementos.append(Table([[
        Image(fig_to_image(fig_gen_loc, 450, 350), 240, 200),
        Image(fig_to_image(fig_con_loc, 450, 350), 240, 200),
        Image(fig_to_image(fig_cost_loc, 450, 350), 240, 200),
    ]]))

    elementos.append(Spacer(1, 20))
    elementos.append(Image(fig_to_image(fig_gen_7, 1100, 400), 760, 260))
    elementos.append(Spacer(1, 12))
    elementos.append(Image(fig_to_image(fig_con_7, 1100, 400), 760, 260))

    doc.build(elementos)
    buffer.seek(0)
    return buffer


st.download_button(
    "📄 Descargar PDF horizontal",
    data=generar_pdf_reporte(),
    file_name=f"Reporte_B52_{fecha_dia.strftime('%Y%m%d')}.pdf",
    mime="application/pdf"
)
