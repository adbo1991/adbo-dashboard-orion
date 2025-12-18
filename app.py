# -*- coding: utf-8 -*-
"""
ADBO SMART | Dashboard de Generación
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import tempfile
import os
from datetime import datetime

# --------------------------------------------------
# Configuración general
# --------------------------------------------------
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación Orión Bloque 52",
    layout="wide"
)

# --------------------------------------------------
# CSS (contraste OK iPhone)
# --------------------------------------------------
st.markdown(
    """
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
    body {
        background-color: #0f172a;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# Funciones auxiliares
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
    delta = (current - previous) / previous * 100
    arrow = "↑" if delta >= 0 else "↓"
    return f"{arrow} {abs(delta):.1f}%"


# --------------------------------------------------
# Exportar PDF (KPIs + Gráficos)
# --------------------------------------------------
def export_pdf(
    kpi_hist, kpi_now,
    fig_barras, fig_total, fig_consumo
):
    with tempfile.TemporaryDirectory() as tmpdir:

        bar_path = os.path.join(tmpdir, "bar.png")
        total_path = os.path.join(tmpdir, "total.png")
        cons_path = os.path.join(tmpdir, "cons.png")

        pio.write_image(fig_barras, bar_path, width=900, height=500)
        pio.write_image(fig_total, total_path, width=900, height=500)
        pio.write_image(fig_consumo, cons_path, width=900, height=500)

        pdf_path = os.path.join(tmpdir, "ADBO_SMART_Reporte_Generacion.pdf")
        c = canvas.Canvas(pdf_path, pagesize=A4)
        w, h = A4

        # HEADER
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2 * cm, h - 2 * cm,
                     "ADBO SMART – CIP – Reporte de Generación")
        c.setFont("Helvetica", 11)
        c.drawString(2 * cm, h - 3 * cm,
                     "Orión Bloque 52")
        c.setFont("Helvetica", 9)
        c.drawString(2 * cm, h - 3.8 * cm,
                     f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        # KPIs HISTÓRICOS
        y = h - 5 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "KPIs Históricos")
        c.setFont("Helvetica", 10)

        for k, v in kpi_hist.items():
            y -= 0.7 * cm
            c.drawString(2 * cm, y, f"{k}: {v}")

        # KPIs PERÍODO
        y -= 1.2 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "KPIs Período Seleccionado")
        c.setFont("Helvetica", 10)

        for k, v in kpi_now.items():
            y -= 0.7 * cm
            c.drawString(2 * cm, y, f"{k}: {v}")

        # GRÁFICOS
        c.showPage()
        c.drawImage(bar_path, 2 * cm, h - 9 * cm, width=17 * cm, height=7 * cm)
        c.drawImage(total_path, 2 * cm, h - 17 * cm, width=17 * cm, height=7 * cm)

        c.showPage()
        c.drawImage(cons_path, 2 * cm, h - 9 * cm, width=17 * cm, height=7 * cm)

        c.save()
        return pdf_path


# --------------------------------------------------
# Título + Botón PDF
# --------------------------------------------------
col_t, col_b = st.columns([6, 1])

with col_t:
    st.title("ADBO SMART – CIP – Reporte de Generación Orión Bloque 52")
    st.caption("Datos actualizados automáticamente desde Google Sheets")

with col_b:
    st.markdown("### ")
    export = st.button("📄 Exportar PDF")

# --------------------------------------------------
# Carga de datos
# --------------------------------------------------
@st.cache_data(ttl=900)
def load_data():
    sheet_id = "1p9aVrwHFNIfW_08yj3RkqF4u8qdGxIrRFc63ZXjH55I"
    gid = 540053809
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    df = pd.read_csv(url, engine="python", decimal=",", thousands=".", on_bad_lines="skip")

    df = df[(df["REGISTRO CORRECTO"] == 1) & (df["POTENCIA ACTIVA (KW)"].notna())]

    df["FECHA DEL REGISTRO"] = pd.to_datetime(df["FECHA DEL REGISTRO"], dayfirst=True)

    for c in [
        "TOTAL GENERADO KW-H",
        "CONSUMO (GLS)",
        "COSTOS DE GENERACIÓN USD",
        "VALOR POR KW GENERADO"
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


df = load_data()

# --------------------------------------------------
# KPIs HISTÓRICOS
# --------------------------------------------------
st.markdown("### 🗂️ KPIs Históricos")

h1, h2, h3, h4 = st.columns(4)

h1.metric("🔋 Total Generado", format_number(df["TOTAL GENERADO KW-H"].sum(), decimals=0))
h2.metric("⛽ Consumo Total", format_number(df["CONSUMO (GLS)"].sum()))
h3.metric("💰 Costos Totales", format_number(df["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
h4.metric("⚡ Valor Prom. KW", format_number(df["VALOR POR KW GENERADO"].mean(), currency=True))

# --------------------------------------------------
# Filtros
# --------------------------------------------------
fecha_max = df["FECHA DEL REGISTRO"].max()
fecha_min = fecha_max - pd.Timedelta(days=6)

if "only_last" not in st.session_state:
    st.session_state.only_last = False

if st.button("📌 Último registro"):
    st.session_state.only_last = not st.session_state.only_last

if st.session_state.only_last:
    fecha_min = fecha_max

df_f = df[(df["FECHA DEL REGISTRO"] >= fecha_min) & (df["FECHA DEL REGISTRO"] <= fecha_max)]

# --------------------------------------------------
# KPIs FILTRADOS + COMPARATIVO
# --------------------------------------------------
st.markdown("### 📊 KPIs Período Seleccionado")

k1, k2, k3, k4 = st.columns(4)

gen_now = df_f["TOTAL GENERADO KW-H"].sum()
con_now = df_f["CONSUMO (GLS)"].sum()
cost_now = df_f["COSTOS DE GENERACIÓN USD"].sum()
val_now = df_f["VALOR POR KW GENERADO"].mean()

k1.metric("🔋 Generación", format_number(gen_now, decimals=0))
k2.metric("⛽ Consumo", format_number(con_now))
k3.metric("💰 Costos", format_number(cost_now, currency=True))
k4.metric("⚡ Valor prom. KW", format_number(val_now, currency=True))

# --------------------------------------------------
# Gráficos
# --------------------------------------------------
gen_fecha = df_f.groupby(["FECHA DEL REGISTRO", "LOCACIÓN"], as_index=False)["TOTAL GENERADO KW-H"].sum()
gen_total = df_f.groupby("FECHA DEL REGISTRO", as_index=False)["TOTAL GENERADO KW-H"].sum()
consumo = df_f.groupby("FECHA DEL REGISTRO", as_index=False)["CONSUMO (GLS)"].sum()

fig_barras = px.bar(gen_fecha, x="FECHA DEL REGISTRO", y="TOTAL GENERADO KW-H", color="LOCACIÓN")
fig_total = px.line(gen_total, x="FECHA DEL REGISTRO", y="TOTAL GENERADO KW-H", markers=True)
fig_consumo = px.line(consumo, x="FECHA DEL REGISTRO", y="CONSUMO (GLS)", markers=True)

st.plotly_chart(fig_barras, use_container_width=True)
st.plotly_chart(fig_total, use_container_width=True)
st.plotly_chart(fig_consumo, use_container_width=True)

# --------------------------------------------------
# Descargar PDF
# --------------------------------------------------
if export:
    pdf = export_pdf(
        {
            "Total Generado": format_number(df["TOTAL GENERADO KW-H"].sum(), decimals=0),
            "Consumo Total": format_number(df["CONSUMO (GLS)"].sum()),
            "Costos Totales": format_number(df["COSTOS DE GENERACIÓN USD"].sum(), currency=True),
            "Valor Prom. KW": format_number(df["VALOR POR KW GENERADO"].mean(), currency=True)
        },
        {
            "Generación": format_number(gen_now, decimals=0),
            "Consumo": format_number(con_now),
            "Costos": format_number(cost_now, currency=True),
            "Valor Prom. KW": format_number(val_now, currency=True)
        },
        fig_barras, fig_total, fig_consumo
    )

    with open(pdf, "rb") as f:
        st.download_button(
            "⬇️ Descargar PDF",
            f,
            file_name="ADBO_SMART_Reporte_Generacion.pdf",
            mime="application/pdf"
        )

st.caption("ADBO SMART · Inteligencia de Negocios & IA")