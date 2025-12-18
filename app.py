# -*- coding: utf-8 -*-
"""
ADBO SMART – CIP – Reporte de Generación Orión Bloque 52
Autor: Alexander Becerra
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime
import tempfile

# --------------------------------------------------
# Configuración general
# --------------------------------------------------
st.set_page_config(
    page_title="ADBO SMART – CIP – Reporte de Generación Orión Bloque 52",
    layout="wide"
)

# --------------------------------------------------
# CSS (alto contraste OK iPhone)
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
""", unsafe_allow_html=True)

# --------------------------------------------------
# Funciones auxiliares
# --------------------------------------------------
def format_number(value, currency=False, decimals=2):
    if pd.isna(value):
        return "—"
    formatted = f"{value:,.{decimals}f}"          # 23,241,321.20
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
# Exportar PDF (KPIs + Tablas)
# --------------------------------------------------
def export_pdf_kpis_tables(
    kpi_hist,
    kpi_periodo,
    df_gen_loc,
    df_gen_dia,
    df_cons_dia,
    fecha_min,
    fecha_max
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        c = canvas.Canvas(tmp.name, pagesize=A4)
        w, h = A4

        # HEADER
        c.setFont("Helvetica-Bold", 15)
        c.drawString(2 * cm, h - 2 * cm, "ADBO SMART – CIP – Reporte de Generación")
        c.setFont("Helvetica", 11)
        c.drawString(2 * cm, h - 3 * cm, "Orión Bloque 52")

        c.setFont("Helvetica", 9)
        c.drawString(2 * cm, h - 3.8 * cm,
                     f"Período: {fecha_min.date()} a {fecha_max.date()}")
        c.drawString(2 * cm, h - 4.4 * cm,
                     f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        y = h - 6 * cm

        # KPIs históricos
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "KPIs Históricos")
        y -= 0.6 * cm

        c.setFont("Helvetica", 10)
        for k, v in kpi_hist.items():
            c.drawString(2 * cm, y, f"{k}: {v}")
            y -= 0.5 * cm

        # KPIs período
        y -= 0.6 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "KPIs del Período Seleccionado")
        y -= 0.6 * cm

        c.setFont("Helvetica", 10)
        for k, v in kpi_periodo.items():
            c.drawString(2 * cm, y, f"{k}: {v}")
            y -= 0.5 * cm

        # Tabla: Generación por locación
        c.showPage()
        y = h - 2 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "Generación por Locación")
        y -= 1 * cm

        c.setFont("Helvetica", 9)
        for _, r in df_gen_loc.iterrows():
            c.drawString(2 * cm, y,
                         f"{r['LOCACIÓN']}: {format_number(r['TOTAL GENERADO KW-H'], decimals=0)}")
            y -= 0.45 * cm

        # Tabla: Generación diaria
        c.showPage()
        y = h - 2 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "Generación Diaria")
        y -= 1 * cm

        c.setFont("Helvetica", 9)
        for _, r in df_gen_dia.iterrows():
            c.drawString(2 * cm, y,
                         f"{r['FECHA DEL REGISTRO'].date()} → "
                         f"{format_number(r['TOTAL GENERADO KW-H'], decimals=0)}")
            y -= 0.45 * cm

        # Tabla: Consumo diario
        c.showPage()
        y = h - 2 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "Consumo Diario")
        y -= 1 * cm

        c.setFont("Helvetica", 9)
        for _, r in df_cons_dia.iterrows():
            c.drawString(2 * cm, y,
                         f"{r['FECHA DEL REGISTRO'].date()} → "
                         f"{format_number(r['CONSUMO (GLS)'])}")
            y -= 0.45 * cm

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(2 * cm, 1.8 * cm,
                     "ADBO SMART · Inteligencia de Negocios & IA")

        c.save()
        return tmp.name


# --------------------------------------------------
# Título
# --------------------------------------------------
st.title("ADBO SMART – CIP – Reporte de Generación Orión Bloque 52")
st.caption("Datos actualizados automáticamente desde Google Sheets")

# --------------------------------------------------
# Carga de datos
# --------------------------------------------------
@st.cache_data(ttl=900)
def load_data():
    sheet_id = "1p9aVrwHFNIfW_08yj3RkqF4u8qdGxIrRFc63ZXjH55I"
    gid = 540053809
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    df = pd.read_csv(url, engine="python", decimal=",", thousands=".", on_bad_lines="skip")

    df = df[(df["REGISTRO CORRECTO"] == 1) &
            (df["POTENCIA ACTIVA (KW)"].notna())]

    df["FECHA DEL REGISTRO"] = pd.to_datetime(df["FECHA DEL REGISTRO"],
                                              dayfirst=True, errors="coerce")

    for c in ["TOTAL GENERADO KW-H", "CONSUMO (GLS)",
              "COSTOS DE GENERACIÓN USD", "VALOR POR KW GENERADO"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


df = load_data()

# --------------------------------------------------
# KPIs históricos
# --------------------------------------------------
st.markdown("### 📊 KPIs Históricos (acumulado total)")

h1, h2, h3, h4 = st.columns(4)
h1.metric("🔋 Total Generado", format_number(df["TOTAL GENERADO KW-H"].sum(), decimals=0))
h2.metric("⛽ Consumo Total", format_number(df["CONSUMO (GLS)"].sum()))
h3.metric("💰 Costos Totales", format_number(df["COSTOS DE GENERACIÓN USD"].sum(), currency=True))
h4.metric("⚡ Valor Prom. KW", format_number(df["VALOR POR KW GENERADO"].mean(), currency=True))

st.markdown("---")

# --------------------------------------------------
# Filtro rápido
# --------------------------------------------------
fecha_max = df["FECHA DEL REGISTRO"].max()
fecha_min = fecha_max - pd.Timedelta(days=6)

if st.button("📌 Último registro"):
    fecha_min = fecha_max

df_filtrado = df[(df["FECHA DEL REGISTRO"] >= fecha_min) &
                 (df["FECHA DEL REGISTRO"] <= fecha_max)]

# --------------------------------------------------
# KPIs período
# --------------------------------------------------
st.markdown("### 📊 KPIs del período seleccionado")

k1, k2, k3, k4 = st.columns(4)

gen_now = df_filtrado["TOTAL GENERADO KW-H"].sum()
con_now = df_filtrado["CONSUMO (GLS)"].sum()
cost_now = df_filtrado["COSTOS DE GENERACIÓN USD"].sum()
val_now = df_filtrado["VALOR POR KW GENERADO"].mean()

k1.metric("🔋 Generación", format_number(gen_now, decimals=0))
k2.metric("⛽ Consumo", format_number(con_now))
k3.metric("💰 Costos", format_number(cost_now, currency=True))
k4.metric("⚡ Valor prom. KW", format_number(val_now, currency=True))

st.markdown("---")

# --------------------------------------------------
# Agregaciones
# --------------------------------------------------
gen_fecha = df_filtrado.groupby(["FECHA DEL REGISTRO", "LOCACIÓN"],
                                as_index=False)["TOTAL GENERADO KW-H"].sum()

gen_total = df_filtrado.groupby("FECHA DEL REGISTRO",
                                as_index=False)["TOTAL GENERADO KW-H"].sum()

consumo = df_filtrado.groupby("FECHA DEL REGISTRO",
                              as_index=False)["CONSUMO (GLS)"].sum()

# --------------------------------------------------
# Botón Exportar PDF
# --------------------------------------------------
st.markdown("### 📤 Exportar")

if st.button("📄 Exportar KPIs + Tablas (PDF)"):
    pdf = export_pdf_kpis_tables(
        {
            "Total Generado": format_number(df["TOTAL GENERADO KW-H"].sum(), decimals=0),
            "Consumo Total": format_number(df["CONSUMO (GLS)"].sum()),
            "Costos Totales": format_number(df["COSTOS DE GENERACIÓN USD"].sum(), currency=True),
            "Valor Prom. KW": format_number(df["VALOR POR KW GENERADO"].mean(), currency=True),
        },
        {
            "Generación (período)": format_number(gen_now, decimals=0),
            "Consumo (período)": format_number(con_now),
            "Costos (período)": format_number(cost_now, currency=True),
            "Valor Prom. KW (período)": format_number(val_now, currency=True),
        },
        gen_fecha.groupby("LOCACIÓN", as_index=False)["TOTAL GENERADO KW-H"].sum(),
        gen_total,
        consumo,
        fecha_min,
        fecha_max
    )

    with open(pdf, "rb") as f:
        st.download_button(
            "⬇️ Descargar PDF",
            f,
            file_name="ADBO_SMART_Reporte_Generacion.pdf",
            mime="application/pdf"
        )

# --------------------------------------------------
st.caption("ADBO SMART · Inteligencia de Negocios & IA")
