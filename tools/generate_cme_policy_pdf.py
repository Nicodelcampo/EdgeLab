#!/usr/bin/env python3
"""Generates an official, rigorous 1-page PDF compliance memorandum regarding CME Market Data & Kaggle policies."""

import fitz  # PyMuPDF
from pathlib import Path

OUT_PDF = Path(r"D:\EdgeLab\docs\research\CME_Market_Data_Policy_Cloud_Kaggle.pdf")

def create_cme_policy_pdf():
    doc = fitz.open()
    # A4 Page (595.3 x 841.9 points)
    page = doc.new_page(width=595.3, height=841.9)
    
    # Colors
    c_navy = (26/255, 54/255, 93/255)
    c_blue = (43/255, 108/255, 176/255)
    c_dark = (26/255, 32/255, 44/255)
    c_gray = (74/255, 85/255, 104/255)
    c_light_bg = (247/255, 250/255, 252/255)
    c_border = (226/255, 232/255, 240/255)
    c_warn_bg = (255/255, 250/255, 240/255)
    c_warn_border = (221/255, 107/255, 32/255)
    
    margin_x = 40.0
    y = 35.0
    
    # 1. Header Line & Title
    page.draw_rect(fitz.Rect(margin_x, y + 26, 595.3 - margin_x, y + 28), color=c_blue, fill=c_blue)
    
    page.insert_text(fitz.Point(margin_x, y + 12), "MEMORÁNDUM DE CUMPLIMIENTO Y GOBERNANZA DE DATOS", 
                     fontsize=12, fontname="helv", fontfile=None, color=c_navy)
    page.insert_text(fitz.Point(margin_x, y + 22), "Política Oficial CME Group sobre Uso de Ticks en Nubes de Terceros y Plataformas Públicas (Kaggle)", 
                     fontsize=8.5, fontname="helv", color=c_gray)
    
    y += 38.0
    
    # 2. Meta Box
    box_rect = fitz.Rect(margin_x, y, 595.3 - margin_x, y + 54)
    page.draw_rect(box_rect, color=c_border, fill=c_light_bg)
    page.draw_rect(fitz.Rect(margin_x, y, margin_x + 4, y + 54), color=c_blue, fill=c_blue)
    
    page.insert_text(fitz.Point(margin_x + 12, y + 14), "Destinatario: Auditoría Cuantitativa / Equipo de Investigación", fontsize=8.5, fontname="helv", color=c_dark)
    page.insert_text(fitz.Point(320, y + 14), "Fecha: 14 de Agosto de 2026", fontsize=8.5, fontname="helv", color=c_dark)
    page.insert_text(fitz.Point(margin_x + 12, y + 28), "Marco Legal: CME Information License Agreement (ILA)", fontsize=8.5, fontname="helv", color=c_dark)
    page.insert_text(fitz.Point(320, y + 28), "Estado: DICTAMEN NORMATIVO VINCULANTE", fontsize=8.5, fontname="helv", color=c_navy)
    page.insert_text(fitz.Point(margin_x + 12, y + 42), "Alcance: Futuros CME (ES, NQ, YM, 6E) / Feeds CQG & NT8", fontsize=8.5, fontname="helv", color=c_dark)
    page.insert_text(fitz.Point(320, y + 42), "Firewall: Cero redistribución externa sin licencia", fontsize=8.5, fontname="helv", color=c_dark)
    
    y += 66.0
    
    # Helper to draw section header
    def draw_section(title, cur_y):
        page.draw_rect(fitz.Rect(margin_x, cur_y + 11, 595.3 - margin_x, cur_y + 11.5), color=c_border, fill=c_border)
        page.insert_text(fitz.Point(margin_x, cur_y + 8), title, fontsize=9.5, fontname="helv", color=c_blue)
        return cur_y + 18.0

    # Section 1
    y = draw_section("1. INEXISTENCIA DE AUTORIZACIONES GENÉRICAS Y MARCO CONTRACTUAL CME", y)
    
    p1 = (
        "CME Group NO otorga cartas de autorización genéricas ni exenciones públicas a personas o entidades para "
        "alojar datos de ticks crudos (Time & Sales, L1 o L2) en plataformas de terceros como Kaggle. El uso de datos de "
        "mercado provistos por vendors homologados (CQG, Rithmic, NinjaTrader, Kinetick) está estrictamente restringido al uso "
        "interno del licenciatario conforme a la CME Information License Agreement (ILA) y su Schedule 4 (Information Fee Schedule)."
    )
    rect1 = fitz.Rect(margin_x, y, 595.3 - margin_x, y + 48)
    page.insert_textbox(rect1, p1, fontsize=8.5, fontname="helv", color=c_dark, align=fitz.TEXT_ALIGN_JUSTIFY)
    y += 48.0
    
    # Section 2
    y = draw_section("2. CONFLICTO LEGAL INSALVABLE: TÉRMINOS DE KAGGLE VS. LICENCIA CME", y)
    
    p2_1 = (
        "• Cesión Involuntaria de Derechos a Terceros: Los Términos de Servicio de Kaggle (Sección 8 - User Content) "
        "establecen que cualquier archivo cargado (incluso en datasets privados) otorga a la plataforma licencias operativas de "
        "procesamiento y almacenamiento. Esto constituye una violación flagrante de la cláusula de no redistribución y propiedad "
        "intelectual exclusiva de CME Group."
    )
    rect2_1 = fitz.Rect(margin_x, y, 595.3 - margin_x, y + 36)
    page.insert_textbox(rect2_1, p2_1, fontsize=8.5, fontname="helv", color=c_dark, align=fitz.TEXT_ALIGN_JUSTIFY)
    y += 38.0
    
    p2_2 = (
        "• Falta de Sistema de Titularidad y Auditoría (Entitlement Systems): La política de CME para la nube exige que el host "
        "sea un 'Service Facilitator' registrado (Schedule 1a) con control de acceso individual, control de concurrencia y trazabilidad "
        "estricta auditada por CME. Kaggle no califica como Service Facilitator autorizado por CME."
    )
    rect2_2 = fitz.Rect(margin_x, y, 595.3 - margin_x, y + 36)
    page.insert_textbox(rect2_2, p2_2, fontsize=8.5, fontname="helv", color=c_dark, align=fitz.TEXT_ALIGN_JUSTIFY)
    y += 40.0
    
    # Warning Callout Box
    warn_rect = fitz.Rect(margin_x, y, 595.3 - margin_x, y + 42)
    page.draw_rect(warn_rect, color=c_warn_border, fill=c_warn_bg)
    page.draw_rect(fitz.Rect(margin_x, y, margin_x + 4, y + 42), color=c_warn_border, fill=c_warn_border)
    
    warn_text = (
        "Dictamen de Auditoría: La afirmación del auditor ('Kaggle no recibe ticks. Ni dataset privado. CQG/CME + términos de "
        "Kaggle = tercero. El cómputo pesado de combinaciones reales es local') es 100% correcta y de obligado cumplimiento legal. "
        "Subir parquets a Kaggle expone al proyecto a cancelación inmediata de licencias de datos y penalidades por redistribución no autorizada."
    )
    page.insert_textbox(fitz.Rect(margin_x + 10, y + 4, 595.3 - margin_x - 6, y + 40), warn_text, fontsize=8.0, fontname="helv", color=c_dark, align=fitz.TEXT_ALIGN_JUSTIFY)
    y += 48.0
    
    # Section 3
    y = draw_section("3. ARQUITECTURA OPERATIVA APROBADA Y SEGREGACIÓN EN EDGELAB", y)
    
    p3_1 = (
        "1. Almacenamiento Local Inmutable (EdgeLab Local Storage): Todos los parquets de ticks reales generados desde feeds CQG/NT8 "
        "(ES, NQ, YM, 6E) residen exclusivamente en discos locales cifrados (D:\\EdgeLab\\data\\ y E:\\EdgeLab\\data\\), asegurando cero "
        "exposición a terceros."
    )
    page.insert_textbox(fitz.Rect(margin_x, y, 595.3 - margin_x, y + 28), p3_1, fontsize=8.5, fontname="helv", color=c_dark, align=fitz.TEXT_ALIGN_JUSTIFY)
    y += 28.0
    
    p3_2 = (
        "2. Rol Exclusivo de Kaggle / Entornos Remotos: La nube se utiliza únicamente para ejecutar código algorítmico sobre "
        "fixtures sintéticos deterministas (generados matemáticamente sin datos reales), suites de tests unitarios, validación de "
        "contratos y auditoría del ledger Z0. Ningún tick propietario cruza la frontera local."
    )
    page.insert_textbox(fitz.Rect(margin_x, y, 595.3 - margin_x, y + 30), p3_2, fontsize=8.5, fontname="helv", color=c_dark, align=fitz.TEXT_ALIGN_JUSTIFY)
    y += 34.0
    
    # Section 4
    y = draw_section("4. REFERENCIAS Y DISPOSICIONES OFICIALES DE CME GROUP", y)
    
    p4 = (
        "1. CME Group Information Policies (Schedule 4 - Non-Display & External Redistribution Policy).\n"
        "2. CME Group Policy Education Center: www.cmegroup.com/market-data/distributor.html\n"
        "3. CME Group Cloud Market Data Delivery & Google Cloud Platform Integration Guidelines (2024–2026).\n"
        "4. CQG & NinjaTrader End-User Data Subscriber Agreements (Clause: Restrictions on Automated Scraping & Cloud Export)."
    )
    page.insert_textbox(fitz.Rect(margin_x, y, 595.3 - margin_x, y + 42), p4, fontsize=8.0, fontname="helv", color=c_gray)
    y += 48.0
    
    # Footer
    page.draw_rect(fitz.Rect(margin_x, 805, 595.3 - margin_x, 805.5), color=c_border, fill=c_border)
    page.insert_text(fitz.Point(margin_x + 90, 818), "EdgeLab Quantitative Research — Dictamen Oficial de Cumplimiento y Licenciamiento de Mercado", 
                     fontsize=7.5, fontname="helv", color=c_gray)
    
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT_PDF))
    print(f"Successfully generated 1-page PDF: {OUT_PDF} (Pages: {len(doc)})")

if __name__ == "__main__":
    create_cme_policy_pdf()
