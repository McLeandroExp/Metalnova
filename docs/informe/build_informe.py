"""Genera el borrador DOCX del informe MetalNova (Entrega 1).

Uso:
    python docs/informe/build_informe.py
"""
from __future__ import annotations

import csv
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parent.parent
FIG = BASE / "figuras"
OUT = BASE / "MetalNova_Informe_Caso_Practico_v0.1.docx"
MASTER_CSV = BASE / "TABLA_MAESTRA_CIFRAS.csv"

AZUL = RGBColor(0x1F, 0x38, 0x64)
GRIS = RGBColor(0x40, 0x40, 0x40)
NEGRO = RGBColor(0, 0, 0)

# ---------------------------------------------------------------------------
# Utilidades de formato
# ---------------------------------------------------------------------------


def set_run_font(run, name="Times New Roman", size=12, bold=None, italic=None, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    rfonts.set(qn("w:eastAsia"), name)


def style_font(style, name="Times New Roman", size=12, bold=None, italic=None, color=NEGRO):
    style.font.name = name
    style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    if color is not None:
        style.font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)


def clean_inline(text: str) -> str:
    return str(text).replace("`", "").replace("**", "")


def add_rich_runs(paragraph, text: str, name="Times New Roman", size=12, bold=False, italic=False):
    """Agrega texto con marcas simples **negrita** y *cursiva*."""
    text = str(text).replace("`", "")
    parts = text.split("**")
    for i, part in enumerate(parts):
        if not part:
            continue
        subparts = part.split("*")
        for j, sub in enumerate(subparts):
            if not sub:
                continue
            run = paragraph.add_run(sub)
            set_run_font(
                run,
                name,
                size,
                bold=(bold or i % 2 == 1),
                italic=(italic or j % 2 == 1),
            )


def add_page_field(paragraph, fmt: str | None = None):
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE " + (f"\\* {fmt}" if fmt else "")
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    txt = OxmlElement("w:t")
    txt.text = "1"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(txt)
    run._r.append(fld_end)


def set_page_number_format(section, fmt: str, start: int | None = None):
    sect_pr = section._sectPr
    pg_num = sect_pr.find(qn("w:pgNumType"))
    if pg_num is None:
        pg_num = OxmlElement("w:pgNumType")
        sect_pr.append(pg_num)
    pg_num.set(qn("w:fmt"), fmt)
    if start is not None:
        pg_num.set(qn("w:start"), str(start))


def config_header(section, fmt: str | None, first_page_blank: bool = False):
    section.different_first_page_header_footer = first_page_blank
    section.header.is_linked_to_previous = False
    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1
    add_page_field(p, fmt)
    if first_page_blank:
        first = section.first_page_header
        first.is_linked_to_previous = False
        for paragraph in first.paragraphs:
            paragraph.text = ""


def add_toc_field(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-2" \\h \\z \\u '
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    txt = OxmlElement("w:t")
    txt.text = "Actualice el campo en Word (F9) para generar la tabla de contenidos."
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(txt)
    run._r.append(fld_end)


def set_cell_border(cell, edge: str, sz: int = 8, val: str = "single"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    element = borders.find(qn(f"w:{edge}"))
    if element is None:
        element = OxmlElement(f"w:{edge}")
        borders.append(element)
    element.set(qn("w:val"), val)
    element.set(qn("w:sz"), str(sz))
    element.set(qn("w:space"), "0")
    element.set(qn("w:color"), "000000")


def set_table_borders(table):
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "bottom"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "8")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    for edge in ("left", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tbl_pr.append(borders)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_cant_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    cant_split.set(qn("w:val"), "true")
    tr_pr.append(cant_split)


def add_table_apa(doc, headers, rows, caption_num, caption_title, note=None, widths=None, font_size=8):
    p = doc.add_paragraph(style="Caption")
    r = p.add_run(f"Tabla {caption_num}")
    r.bold = True
    r2 = p.add_run(". ")
    r2.bold = True
    r3 = p.add_run(caption_title)
    r3.italic = True

    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.allow_autofit = False
    set_table_borders(table)
    tbl_pr = table._tbl.tblPr
    tbl_w = OxmlElement("w:tblW")
    tbl_w.set(qn("w:w"), "9360")
    tbl_w.set(qn("w:type"), "dxa")
    tbl_pr.append(tbl_w)
    tbl_layout = OxmlElement("w:tblLayout")
    tbl_layout.set(qn("w:type"), "fixed")
    tbl_pr.append(tbl_layout)

    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    set_cant_split(hdr)
    for i, text in enumerate(headers):
        cell = hdr.cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1
        p.paragraph_format.left_indent = Cm(0)
        p.paragraph_format.first_line_indent = Cm(0)
        run = p.add_run(clean_inline(text))
        set_run_font(run, "Arial", font_size, bold=True)
    for i, row_data in enumerate(rows):
        row = table.rows[i + 1]
        set_cant_split(row)
        for j, text in enumerate(row_data):
            cell = row.cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j > 0 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1
            p.paragraph_format.left_indent = Cm(0)
            p.paragraph_format.first_line_indent = Cm(0)
            run = p.add_run(clean_inline(text))
            set_run_font(run, "Arial", font_size)
    for cell in table.rows[0].cells:
        set_cell_border(cell, "bottom", 8)
    if widths:
        for i, width in enumerate(widths):
            table.columns[i].width = width
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = width
    if note:
        p = doc.add_paragraph(style="Note")
        run = p.add_run("Nota. ")
        set_run_font(run, "Arial", 8, italic=True)
        run2 = p.add_run(clean_inline(note))
        set_run_font(run2, "Arial", 8)
    return table


def add_figure_apa(doc, image_path, caption_num, caption_title, note=None, width=Inches(6.2)):
    p = doc.add_paragraph(style="Caption")
    r = p.add_run(f"Figura {caption_num}")
    r.bold = True
    r2 = p.add_run(". ")
    r2.bold = True
    r3 = p.add_run(caption_title)
    r3.italic = True

    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(6)
    p_img.paragraph_format.space_after = Pt(3)
    run = p_img.add_run()
    run.add_picture(str(image_path), width=width)
    if note:
        p = doc.add_paragraph(style="Note")
        run = p.add_run("Nota. ")
        set_run_font(run, "Arial", 8, italic=True)
        run2 = p.add_run(clean_inline(note))
        set_run_font(run2, "Arial", 8)


def add_heading_custom(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    return p


def add_body(doc, text, style="Normal"):
    p = doc.add_paragraph(style=style)
    add_rich_runs(p, text, "Times New Roman", 12)
    return p


def add_list_entry(doc, number, title, page="—"):
    p = doc.add_paragraph(style="ListEntry")
    p.paragraph_format.tab_stops.add_tab_stop(Inches(0.9), WD_TAB_ALIGNMENT.LEFT)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    run = p.add_run(f"{number}\t")
    run2 = p.add_run(title)
    run3 = p.add_run(f"\t{page}")
    return p


def add_reference(doc, text):
    p = doc.add_paragraph(style="Reference")
    add_rich_runs(p, text, "Times New Roman", 12)
    return p


def add_bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Cm(0.75)
    p.paragraph_format.first_line_indent = Cm(-0.4)
    add_rich_runs(p, text, "Times New Roman", 12)


def read_case_text():
    path = PROJECT / "docs" / "reference" / "caso_practico.txt"
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


# ---------------------------------------------------------------------------
# Documento
# ---------------------------------------------------------------------------


def build():
    doc = Document()

    # Estilos base
    styles = doc.styles
    normal = styles["Normal"]
    style_font(normal, "Times New Roman", 12)
    normal.paragraph_format.line_spacing = 2.0
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    normal.paragraph_format.first_line_indent = Cm(1.27)

    for name, size, bold, italic, align in [
        ("Heading 1", 12, True, False, WD_ALIGN_PARAGRAPH.CENTER),
        ("Heading 2", 12, True, False, WD_ALIGN_PARAGRAPH.LEFT),
        ("Heading 3", 12, True, True, WD_ALIGN_PARAGRAPH.LEFT),
    ]:
        st = styles[name]
        style_font(st, "Times New Roman", size, bold=bold, italic=italic)
        st.paragraph_format.line_spacing = 2.0
        st.paragraph_format.space_before = Pt(12)
        st.paragraph_format.space_after = Pt(0)
        st.paragraph_format.alignment = align
        st.paragraph_format.first_line_indent = Cm(0)
        st.paragraph_format.keep_with_next = True

    # Estilos personalizados
    from docx.enum.style import WD_STYLE_TYPE

    def ensure_style(name, base="Normal"):
        try:
            return styles[name]
        except KeyError:
            return styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)

    st = ensure_style("CoverText")
    style_font(st, "Times New Roman", 12)
    st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    st.paragraph_format.line_spacing = 1.15
    st.paragraph_format.space_after = Pt(6)
    st.paragraph_format.first_line_indent = Cm(0)

    st = ensure_style("CoverTitle")
    style_font(st, "Times New Roman", 12, bold=True)
    st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    st.paragraph_format.line_spacing = 1.5
    st.paragraph_format.space_before = Pt(24)
    st.paragraph_format.space_after = Pt(18)
    st.paragraph_format.first_line_indent = Cm(0)

    st = ensure_style("PrelimTitle")
    style_font(st, "Times New Roman", 12, bold=True)
    st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    st.paragraph_format.line_spacing = 2.0
    st.paragraph_format.space_before = Pt(0)
    st.paragraph_format.space_after = Pt(12)
    st.paragraph_format.first_line_indent = Cm(0)

    st = ensure_style("Caption")
    style_font(st, "Arial", 8)
    st.paragraph_format.line_spacing = 1.0
    st.paragraph_format.space_before = Pt(8)
    st.paragraph_format.space_after = Pt(3)
    st.paragraph_format.first_line_indent = Cm(0)
    st.paragraph_format.keep_with_next = True

    st = ensure_style("Note")
    style_font(st, "Arial", 8)
    st.paragraph_format.line_spacing = 1.0
    st.paragraph_format.space_before = Pt(3)
    st.paragraph_format.space_after = Pt(8)
    st.paragraph_format.first_line_indent = Cm(0)

    st = ensure_style("Reference")
    style_font(st, "Times New Roman", 12)
    st.paragraph_format.line_spacing = 2.0
    st.paragraph_format.space_after = Pt(0)
    st.paragraph_format.left_indent = Cm(1.27)
    st.paragraph_format.first_line_indent = Cm(-1.27)
    st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    st = ensure_style("ListEntry")
    style_font(st, "Times New Roman", 12)
    st.paragraph_format.line_spacing = 1.15
    st.paragraph_format.space_after = Pt(0)
    st.paragraph_format.first_line_indent = Cm(0)

    st = ensure_style("AbstractText")
    style_font(st, "Times New Roman", 12)
    st.paragraph_format.line_spacing = 2.0
    st.paragraph_format.space_after = Pt(0)
    st.paragraph_format.first_line_indent = Cm(0)
    st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    st = ensure_style("CaseText")
    style_font(st, "Times New Roman", 10.5)
    st.paragraph_format.line_spacing = 1.0
    st.paragraph_format.space_after = Pt(3)
    st.paragraph_format.first_line_indent = Cm(0)

    # Sección 1: portada
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    for m in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(section, m, Inches(1))
    section.header.is_linked_to_previous = False

    # Portada
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.add_run().add_picture(str(FIG / "logo-uce.png"), width=Inches(1.0))

    for text in [
        "UNIVERSIDAD CENTRAL DEL ECUADOR",
        "FACULTAD DE CIENCIAS APLICADAS",
        "CARRERA DE SISTEMAS DE LA INFORMACIÓN",
        "INTELIGENCIA DE NEGOCIOS",
        "EXAMEN COMPLEXIVO",
    ]:
        p = doc.add_paragraph(style="CoverText")
        r = p.add_run(text)
        set_run_font(r, "Times New Roman", 12, bold=True)

    p = doc.add_paragraph(style="CoverTitle")
    r = p.add_run(
        "CASO METALNOVA DE BI:\n"
        "DISEÑO Y EVALUACIÓN DE UN PROTOTIPO DE INTELIGENCIA DE NEGOCIO\n"
        "PARA MEDIR EL OEE Y PRIORIZAR PÉRDIDAS EN UNA FÁBRICA\n"
        "DE COMPONENTES AUTOMOTRICES"
    )
    set_run_font(r, "Times New Roman", 12, bold=True)

    p = doc.add_paragraph(style="CoverText")
    p.paragraph_format.space_before = Pt(24)
    r = p.add_run("INFORME DE CASO PRÁCTICO")
    set_run_font(r, "Times New Roman", 12, bold=True)

    p = doc.add_paragraph(style="CoverText")
    p.paragraph_format.space_before = Pt(24)
    r = p.add_run("Autor: Leandro Arguello")
    set_run_font(r, "Times New Roman", 12)

    p = doc.add_paragraph(style="CoverText")
    r = p.add_run("Quito, 2026")
    set_run_font(r, "Times New Roman", 12)

    p = doc.add_paragraph(style="CoverText")
    r = p.add_run("Período académico: 2026-2026")
    set_run_font(r, "Times New Roman", 12)

    # Sección 2: preliminares
    section2 = doc.add_section(WD_SECTION.NEW_PAGE)
    set_page_number_format(section2, "lowerRoman", 1)
    config_header(section2, "roman", first_page_blank=False)

    p = doc.add_paragraph(style="PrelimTitle")
    p.add_run("TABLA DE CONTENIDOS")
    add_toc_field(doc)

    # Listas
    doc.add_page_break()
    p = doc.add_paragraph(style="PrelimTitle")
    p.add_run("LISTAS DE TABLAS, FIGURAS Y ANEXOS")

    p = doc.add_paragraph(style="Heading 3")
    p.add_run("Lista de tablas")
    table_entries = [
        ("T1", "Requisitos del caso vs. alcance del prototipo"),
        ("T2", "Fórmulas y definiciones de KPI"),
        ("T3", "Síntesis de literatura y vacíos"),
        ("T4", "Fuentes de datos y fuente de verdad"),
        ("T5", "Hechos, dimensiones y granularidad"),
        ("T6", "Reglas de calidad y temporalidad IoT"),
        ("T7", "Regla de excepción de máquina crítica"),
        ("T8", "Estrategia de validación y evidencias"),
        ("T9", "Volumen y cobertura de datos"),
        ("T10", "KPIs globales"),
        ("T11", "OEE y A/P/Q en ventanas de 30 días"),
        ("T12", "Loss Tree global"),
        ("T13", "Focos por planta, línea, máquina y turno"),
        ("T14", "Downtime por causa"),
        ("T15", "Perfiles de confiabilidad"),
        ("T16", "Calidad y energía"),
        ("T17", "Alertas, validación y desempeño"),
        ("T18", "Comparación caso vs. prototipo"),
        ("T19", "Limitaciones y amenazas a la validez"),
        ("T20", "Acciones priorizadas e impacto hipotético"),
        ("B1", "Diccionario de datos seleccionado"),
        ("B2", "Matriz de aceptación del caso"),
        ("B3", "Guía de reproducción"),
        ("B4", "Glosario y abreviaturas"),
        ("B5", "Tabla maestra de cifras (resumen)"),
    ]
    for num, title in table_entries:
        add_list_entry(doc, num, title)

    p = doc.add_paragraph(style="Heading 3")
    p.add_run("Lista de figuras")
    figure_entries = [
        ("F1", "Árbol del problema: la caída del OEE y sus efectos"),
        ("F2", "Marco conceptual del OEE y las pérdidas"),
        ("F3", "Fases del diseño metodológico"),
        ("F4", "Arquitectura de componentes"),
        ("F5", "Modelo dimensional en estrella"),
        ("F6", "OEE global y A/P/Q en ventanas de 30 días"),
        ("F7", "Loss Tree global"),
        ("F8", "Pareto de downtime con curva acumulada"),
        ("F9", "Dispersión de confiabilidad"),
        ("F10", "Vista integrada de las cuatro páginas del tablero"),
        ("D1", "Página 01 Executive Plant Performance"),
        ("D2", "Página 02 OEE & Loss Tree"),
        ("D3", "Página 03 Maintenance Reliability"),
        ("D4", "Página 04 Quality & Energy"),
        ("D5", "Detalle máquina"),
        ("D6", "Detalle causa"),
        ("D7", "Tooltip máquina"),
        ("D8", "Modelo validado (T-604)"),
    ]
    for num, title in figure_entries:
        add_list_entry(doc, num, title)

    p = doc.add_paragraph(style="Heading 3")
    p.add_run("Lista de anexos")
    annex_entries = [
        ("A", "Texto completo del caso práctico original"),
        ("B", "Diccionario de datos seleccionado"),
        ("C", "Matriz de aceptación del caso"),
        ("D", "Capturas completas del tablero"),
        ("E", "Guía de reproducción"),
        ("F", "Glosario y abreviaturas"),
        ("G", "Tabla maestra de cifras y trazabilidad"),
        ("H", "Guion de exposición y preguntas previsibles"),
    ]
    for num, title in annex_entries:
        add_list_entry(doc, num, title)

    p = doc.add_paragraph(style="Note")
    run = p.add_run(
        "Nota. La paginación de estas listas se actualizará al cerrar el documento. "
        "Los títulos corresponden a la estructura aprobada."
    )
    set_run_font(run, "Arial", 8)

    # Resumen
    doc.add_page_break()
    add_heading_custom(doc, "Resumen", 1)
    add_body(
        doc,
        "El caso MetalNova describe una fábrica de componentes automotrices con 52 máquinas "
        "críticas, datos fragmentados y una caída del OEE de 78 % a 66 %. Este trabajo diseña y "
        "evalúa un prototipo de Business Intelligence que integra datos sintéticos de IoT/SCADA, "
        "MES, CMMS, calidad y turnos en PostgreSQL, los transforma con un modelo dimensional y los "
        "expone en Power BI. La investigación es aplicada, cuantitativa y longitudinal, con 180 días, "
        "401.838 eventos y un escenario calibrado para producir señal. Los resultados muestran que "
        "la caída se explica principalmente por la pérdida de rendimiento (82,51 % de los minutos "
        "equivalentes perdidos), no por la disponibilidad (4,30 %). P-SUR, la línea L3-2, la máquina "
        "M-047 y el turno C concentran el deterioro; las microparadas y la falla mecánica son las "
        "causas no planificadas más relevantes, aunque no explican la mayor parte de la pérdida. El "
        "prototipo valida 49/49 comprobaciones de KPI, 11/11 de calidad IoT y 12/12 fórmulas SQL, y "
        "demuestra latencia de milisegundos y frescura de 0,35 s. Se concluye que el OEE debe "
        "gestionarse con una definición única, agregación ponderada y análisis del Loss Tree; se "
        "recomienda priorizar scrap y rendimiento en P-SUR, intervenir M-047 y mejorar la calidad de "
        "los datos antes de escalar. Los datos son sintéticos y los ahorros son hipotéticos.",
        style="AbstractText",
    )
    p = doc.add_paragraph(style="AbstractText")
    r = p.add_run("Palabras clave: ")
    set_run_font(r, "Times New Roman", 12, italic=True)
    r2 = p.add_run("OEE, inteligencia de negocios, mantenimiento industrial, calidad de datos.")
    set_run_font(r2, "Times New Roman", 12)

    # Abstract
    doc.add_page_break()
    add_heading_custom(doc, "Abstract", 1)
    add_body(
        doc,
        "The MetalNova case describes an automotive components factory with 52 critical machines, "
        "fragmented data and an OEE drop from 78% to 66%. This work designs and evaluates a Business "
        "Intelligence prototype that integrates synthetic data from IoT/SCADA, MES, CMMS, quality and "
        "shifts in PostgreSQL, transforms it into a dimensional model and exposes it in Power BI. The "
        "research is applied, quantitative and longitudinal, covering 180 days, 401,838 events and a "
        "calibrated scenario designed to produce signal. Results show that the decline is mainly "
        "explained by performance loss (82.51% of equivalent minutes lost), not by availability "
        "(4.30%). P-SUR, line L3-2, machine M-047 and shift C concentrate the deterioration; "
        "micro-stops and mechanical failure are the most relevant unplanned causes, although they do "
        "not explain most of the loss. The prototype validates 49/49 KPI checks, 11/11 IoT quality "
        "checks and 12/12 SQL formulas, and demonstrates millisecond latency and 0.35 s freshness. It "
        "is concluded that OEE should be managed with a single definition, weighted aggregation and "
        "Loss Tree analysis; it is recommended to prioritize scrap and performance in P-SUR, "
        "intervene M-047 and improve data quality before scaling. Data are synthetic and savings are "
        "hypothetical.",
        style="AbstractText",
    )
    p = doc.add_paragraph(style="AbstractText")
    r = p.add_run("Keywords: ")
    set_run_font(r, "Times New Roman", 12, italic=True)
    r2 = p.add_run("OEE, business intelligence, industrial maintenance, data quality.")
    set_run_font(r2, "Times New Roman", 12)

    # Sección 3: cuerpo
    section3 = doc.add_section(WD_SECTION.NEW_PAGE)
    set_page_number_format(section3, "decimal", 1)
    config_header(section3, None, first_page_blank=False)

    # 1. Introducción
    add_heading_custom(doc, "1. Introducción", 1)
    add_heading_custom(doc, "1.1 Contexto y problema", 2)
    add_body(
        doc,
        "MetalNova fabrica componentes automotrices en tres plantas, seis líneas y 52 máquinas "
        "críticas. Dispone de sensores IoT, SCADA, MES, CMMS, ERP y registros de calidad, pero cada "
        "área analiza sus datos por separado. En los últimos seis meses el OEE cayó de 78 % a 66 %, "
        "el downtime no planificado aumentó, el scrap pasó de 3,8 % a 6,1 % y el consumo energético "
        "por unidad creció 14 %. La pérdida estimada supera USD 540.000 mensuales y la planta con "
        "peor desempeño incumple fechas de entrega a clientes Tier-1 (Caso de estudio A, 2026).",
    )
    add_body(
        doc,
        "La discusión interna está mal planteada. Producción atribuye la caída a mantenimiento; "
        "mantenimiento la atribuye a los cambios de producto y a las microparadas no registradas. "
        "Ninguna de las dos áreas puede sostener su hipótesis con una definición única de OEE, una "
        "fuente de verdad para las paradas o una conciliación entre conteos, tiempos y calidad. El "
        "problema no es solo operativo: es un problema de gobierno del dato y de medición.",
    )
    add_body(
        doc,
        "Para este trabajo, el caso se tradujo en un prototipo académico con datos sintéticos. El "
        "escenario calibrado reprodujo la tendencia de 78,02 % a 66,00 % en ventanas de 30 días; no "
        "es telemetría real ni una implantación en MetalNova (MetalNova Smart Factory BI, 2026). Los "
        "resultados del prototipo muestran que la pérdida dominante es rendimiento (82,51 % de "
        "3.528.469 minutos equivalentes), no disponibilidad (4,30 %). Esa diferencia es la que "
        "permite reorientar la discusión: el problema principal no es “parar”, sino perder velocidad "
        "y unidades.",
    )
    add_figure_apa(
        doc,
        FIG / "figura1_arbol_problema.png",
        "1",
        "Árbol del problema: la caída del OEE y sus efectos",
        "Datos sintéticos. Elaboración propia con cifras del prototipo (corte 2026-10-24). "
        "La valorización económica usa supuestos declarados y no representa un ahorro realizado.",
        width=Inches(6.2),
    )

    add_heading_custom(doc, "1.2 Pregunta principal y preguntas específicas", 2)
    add_body(
        doc,
        "La pregunta principal del caso es: ¿qué activos, turnos, productos y causas de parada "
        "explican la caída del OEE y cuál es su impacto en throughput, scrap y costo? (Caso de "
        "estudio A, 2026). Para responderla se formularon seis preguntas específicas:",
    )
    for text in [
        "¿Qué componente del OEE —disponibilidad, rendimiento o calidad— explica la mayor pérdida?",
        "¿Qué plantas, líneas, máquinas, turnos y productos concentran el deterioro?",
        "¿Qué causas de parada son relevantes y cómo se distinguen las microparadas de las fallas?",
        "¿Cómo se relacionan el scrap, la energía por unidad buena y las condiciones de operación?",
        "¿Cómo priorizar intervenciones con impacto económico y criticidad operacional?",
        "¿Qué calidad, temporalidad y latencia tienen los datos IoT que alimentan el tablero?",
    ]:
        add_bullet(doc, text)

    add_heading_custom(doc, "1.3 Objetivos", 2)
    add_body(
        doc,
        "El objetivo general es diseñar y evaluar un prototipo de Business Intelligence que integre "
        "datos industriales sintéticos para medir el OEE de forma consistente, localizar las pérdidas "
        "de disponibilidad, rendimiento y calidad y priorizar acciones de mantenimiento y producción. "
        "Los objetivos específicos son:",
    )
    for text in [
        "Construir un modelo dimensional con hechos y dimensiones conformadas para producción, paradas, mantenimiento y calidad.",
        "Implementar un pipeline histórico y una ingesta continua simulada con idempotencia y latencia verificable.",
        "Definir y validar los diez KPIs obligatorios del caso con agregación ponderada y tratamiento explícito de casos borde.",
        "Desarrollar un tablero con cuatro vistas principales, filtros, drill-through, tooltip y una regla de alerta accionable.",
        "Analizar el Loss Tree por activo, turno, producto y causa, sin afirmar causalidad no demostrada.",
        "Priorizar un plan de mejora con impacto observado, impacto hipotético, supuestos y criticidad.",
    ]:
        add_bullet(doc, text)

    add_heading_custom(doc, "1.4 Justificación", 2)
    add_body(
        doc,
        "La investigación se justifica en tres planos. En el académico, aplica conceptos de Business "
        "Intelligence, modelado dimensional, gobierno de indicadores y calidad de datos a un caso "
        "industrial concreto (Curto Díaz, 2010; Howson, 2008; Kimball & Ross, 2013). En el práctico, "
        "demuestra cómo pasar de datos fragmentados a una lectura única del OEE y a decisiones de "
        "mantenimiento y producción trazables. En el metodológico, hace explícitos los supuestos, "
        "usa datos sintéticos reproducibles, valida los KPI de forma independiente y distingue lo "
        "observado de lo hipotético. Esa transparencia es especialmente importante porque el "
        "escenario fue calibrado para producir señal y no para simular una fábrica real.",
    )
    add_body(
        doc,
        "El trabajo también responde a una necesidad formativa: el informe debe funcionar como "
        "memoria de un examen complexivo, es decir, debe demostrar dominio del problema, del método, "
        "de las herramientas y de los resultados, no solo la existencia de un tablero. Por eso el "
        "documento incluye decisiones tecnológicas, validación, limitaciones y un guion de defensa.",
    )

    add_heading_custom(doc, "1.5 Alcance y limitaciones", 2)
    add_body(
        doc,
        "El prototipo cubre las tres plantas, las seis líneas y las 52 máquinas del caso, con 180 "
        "días de historia (2026-04-22 a 2026-10-18) y 401.838 eventos de origen, de los cuales "
        "343.050 son eventos de máquina. Incluye cuatro páginas principales de Power BI, páginas de "
        "drill-through y un tooltip, y se ejecuta de forma local con PostgreSQL en Docker y Power BI "
        "Desktop, sin nube. La Tabla 1 resume la correspondencia entre los requisitos del caso y la "
        "evidencia del prototipo.",
    )
    add_table_apa(
        doc,
        ["Requisito del caso", "Evidencia en el prototipo", "Estado"],
        [
            ["≥ 200.000 eventos y ≥ 90 días", "401.838 eventos; 180 días; 343.050 eventos de máquina", "Cumple"],
            ["Modelo multidimensional con hechos y dimensiones conformadas", "4 hechos analíticos + 2 capas crudas; 10 dimensiones; 27 relaciones", "Cumple"],
            ["4 vistas, 9 KPIs y navegación máquina → detalle", "4 páginas principales + 4 de apoyo; 24 tarjetas; drill-through y tooltip", "Cumple"],
            ["Manejo explícito de calidad y temporalidad IoT", "Cuarentena, tardío/reordenado, vista de señal; 11/11 validaciones", "Cumple con matiz"],
            ["Plan de mejora priorizado y cuantificado", "5 acciones con impacto observado/hipotético y supuestos", "Cumple"],
            ["Latencia < 10 minutos", "Latencia de pipeline 0,7–54,9 ms; frescura DirectQuery 0,35 s", "Cumple"],
        ],
        "1",
        "Requisitos del caso vs. alcance del prototipo",
        "Datos sintéticos. Elaboración propia a partir de la documentación del prototipo y del enunciado del caso. "
        "El matiz de IoT se refiere a que el estado `unknown` no se emite; el hueco se declara en la vista de señal.",
        widths=[Inches(2.1), Inches(3.4), Inches(1.0)],
    )
    add_body(
        doc,
        "Las limitaciones deben leerse junto con los resultados. Los datos son sintéticos; el "
        "escenario `calibracion` fue diseñado para que la caída del OEE fuera visible; el ERP no "
        "tiene una fuente etiquetada; la cadencia IoT es de dos lecturas por turno y no de 15 "
        "minutos; el estado `unknown` no se emite; la definición de FPY es literal (“sin retrabajo”) "
        "y no la lectura clásica de “buenas de primera pasada”; y el tablero no es una implantación "
        "en producción. Por lo tanto, no se afirma causalidad ni se presentan ahorros como "
        "realizados.",
    )

    add_heading_custom(doc, "1.6 Estructura del informe", 2)
    add_body(
        doc,
        "El informe se organiza en ocho secciones. La sección 2 presenta el marco teórico del OEE, "
        "el mantenimiento, la calidad, el Business Intelligence, la calidad de datos y los marcos de "
        "trabajo. La sección 3 describe la metodología experimental, el modelo, la arquitectura y las "
        "decisiones tecnológicas. La sección 4 presenta los resultados. La sección 5 los discute y "
        "los contrasta con el caso y la literatura. La sección 6 concluye, la sección 7 recomienda y "
        "la sección 8 contiene las referencias. Los anexos A–H incluyen el caso original, el "
        "diccionario de datos, la matriz de aceptación, las capturas, la guía de reproducción, el "
        "glosario, la tabla maestra de cifras y el guion de defensa.",
    )

    # Esqueleto de secciones 2-8
    skeleton = [
        ("2. Marco teórico", [
            ("2.1 Business Intelligence", "Concepto, arquitectura, ciclo de valor y factores de éxito (Curto Díaz, 2010; Howson, 2008)."),
            ("2.2 OEE y las seis grandes pérdidas", "Fórmula, componentes, limitaciones y críticas (Nakajima, 1988; Muchiri & Pintelon, 2008; Jonsson & Lesshammar, 1999; Dal et al., 2000)."),
            ("2.3 TPM, mantenimiento y confiabilidad", "MTBF, MTTR, fallas cortas y microparadas (Ahuja & Khamba, 2008; Swanson, 2001; Mobley, 2002; ISO 14224:2016)."),
            ("2.4 Calidad, rendimiento y energía", "Scrap, FPY y kWh por unidad buena; diferencia entre calidad y FPY."),
            ("2.5 Modelado dimensional y KPIs", "Hechos, dimensiones conformadas, jerarquías y gobierno de indicadores (Kimball & Ross, 2013; Parmenter, 2015; ISO 22400-2:2014)."),
            ("2.6 Analítica descriptiva, diagnóstica y predictiva", "Alcance del prototipo y trabajo futuro (Witten & Frank, 2005)."),
            ("2.7 IoT, Industria 4.0 y calidad de datos", "CPS, sensores, latencia, duplicados, eventos tardíos y cuarentena (Lee et al., 2015; Batini et al., 2009)."),
            ("2.8 Business Analysis y CRISP-DM", "Business Understanding, requisitos y evaluación de soluciones (IIBA, 2015; Wirth & Hipp, 2000)."),
            ("2.9 Síntesis y marco conceptual", "Vacíos identificados y marco propio del informe."),
        ]),
        ("3. Metodología experimental", [
            ("3.1 Diseño de la investigación", "Investigación aplicada, cuantitativa, longitudinal, no experimental; estudio de caso con unidades embebidas."),
            ("3.2 Caso y unidad de análisis", "3 plantas, 6 líneas, 52 máquinas, 180 días y 28.080 combinaciones máquina-turno-día."),
            ("3.3 Fuentes de datos y generación sintética", "IoT/SCADA, MES, CMMS, calidad y turnos; ERP parcial; semilla 42 y escenario calibrado."),
            ("3.4 Modelo dimensional", "Hechos, dimensiones, granularidad, jerarquías y reglas de integridad."),
            ("3.5 Arquitectura y decisiones tecnológicas", "PostgreSQL, Docker, Python, Power BI, DirectQuery, CSV, TMDL/PBIR y pgAdmin; alternativas descartadas."),
            ("3.6 Calidad y temporalidad IoT", "Duplicados, tardíos, reordenados, faltantes, fuera de rango y solapes."),
            ("3.7 Operacionalización de KPIs", "Fórmulas, agregación ponderada, NULL y casos borde."),
            ("3.8 Construcción del tablero y regla de alerta", "Cuatro páginas, filtros, drill-through, tooltip y regla multicriterio."),
            ("3.9 Validación y reproducibilidad", "49/49, 12/12, 11/11, 5/5, 17/17, 7/7; SHA-256 y validadores."),
            ("3.10 Consideraciones éticas", "Datos sintéticos, ausencia de datos personales, secretos y límites de causalidad."),
        ]),
        ("4. Análisis y resultados", [
            ("4.1 Volumen y calidad de los datos", "401.838 eventos; 343.050 de máquina; 0 duplicados; 2 rechazos; 1 tardío; 1 reordenado."),
            ("4.2 OEE global y evolución", "71,9645 % global; 78,0226 → 65,9961 %; A/P/Q; scrap y energía."),
            ("4.3 Loss Tree", "Rendimiento 82,51 %; calidad 13,19 %; disponibilidad 4,30 %; 4.269.957 unidades no producidas."),
            ("4.4 Focos por planta, línea, máquina, turno y producto", "P-SUR, L3-2, M-047, turno C y PRD-009."),
            ("4.5 Causas de parada", "Microparadas y F-MEC; Pareto con curva acumulada."),
            ("4.6 Confiabilidad", "MTBF, MTTR, fallas cortas y microparadas; M-047, M-015 y M-025."),
            ("4.7 Calidad y energía", "Scrap por turno/producto, FPY y kWh por unidad buena."),
            ("4.8 Alertas de máquina crítica", "3.284 alertas, 248 críticas y ejemplos accionables."),
            ("4.9 Tablero", "Cuatro páginas, navegación y evidencia visual."),
            ("4.10 Validación y desempeño", "49/49, 12/12, 11/11; DirectQuery 35,46 s y frescura 0,35 s."),
            ("4.11 Priorización económica", "Cinco acciones y su impacto hipotético."),
        ]),
        ("5. Discusión", [
            ("5.1 Rendimiento vs. disponibilidad", "La caída no es principalmente un problema de paradas."),
            ("5.2 Microparadas y fallas cortas", "M-047, M-015 y M-025: el promedio oculta."),
            ("5.3 Calidad y causalidad", "Asociación descriptiva, confusión producto-planta y límites."),
            ("5.4 Del dato al dinero", "Supuestos, sensibilidad y diferencia entre pérdida y ahorro."),
            ("5.5 Contraste con el caso y la literatura", "Coincidencias, brechas y límites del OEE."),
            ("5.6 Aportes metodológicos", "Contrato único de KPI, agregación ponderada, cuarentena y reproducibilidad."),
            ("5.7 Limitaciones y amenazas a la validez", "Datos sintéticos, calibración, ERP, IoT, FPY y ausencia de implantación."),
            ("5.8 Implicaciones", "Qué haría MetalNova y qué requiere una implantación real."),
        ]),
        ("6. Conclusiones", [
            ("6.1 Respuesta a la pregunta principal", "Síntesis de la evidencia."),
            ("6.2 Cumplimiento de objetivos", "Objetivo → resultado → evidencia."),
            ("6.3 Hallazgos principales", "Cinco o seis hallazgos numerados."),
            ("6.4 Aportes del trabajo", "Académicos, metodológicos y prácticos."),
            ("6.5 Trabajo futuro", "Datos reales, causalidad y mantenimiento predictivo."),
        ]),
        ("7. Recomendaciones", [
            ("7.1 Acciones operativas priorizadas", "A1–A5 con responsable, KPI, horizonte e impacto hipotético."),
            ("7.2 Mejoras de datos y BI", "FPY, Pareto acumulado, temperatura, ERP, unknown, cadencia y materialización."),
            ("7.3 Gobernanza", "Revisión mensual, dueño del dato, playbook y validación de costos."),
            ("7.4 Investigación futura", "Datos reales, diseño causal y mantenimiento predictivo."),
            ("7.5 Hoja de ruta", "0–30, 31–90 y 91–180 días."),
        ]),
    ]
    for title, subs in skeleton:
        doc.add_page_break()
        add_heading_custom(doc, title, 1)
        p = doc.add_paragraph(style="Normal")
        add_rich_runs(
            p,
            "[Sección en desarrollo para la Entrega 2. El esquema detallado, las figuras y "
            "las tablas están en docs/informe/ESQUEMA_DETALLADO.md.]",
            "Times New Roman",
            12,
            italic=True,
        )
        for sub, desc in subs:
            add_heading_custom(doc, sub, 2)
            if sub.startswith("3.5"):
                add_body(
                    doc,
                    "La arquitectura se eligió para cumplir tres restricciones del caso: "
                    "ejecución local, reproducibilidad y volumen manejable en un equipo de 8 GB. "
                    "Las alternativas se evaluaron antes de fijar el stack y quedaron registradas "
                    "en docs/DECISIONS.md. Las decisiones principales son:",
                )
                for bullet in [
                    "PostgreSQL 16.4 en Docker: permite SQL analítico, vistas, restricciones de integridad y un volumen local; se descartó PostgreSQL nativo y la nube por reproducibilidad y control del entorno.",
                    "Docker Compose: aísla base, pgAdmin e ingestor, publica solo en loopback y conserva los datos en volúmenes; se descartó la instalación manual por fragilidad.",
                    "Python 3.13 en contenedor: genera, carga, simula y valida; las dependencias quedan versionadas y no se instalan en Windows.",
                    "Power BI Desktop con DirectQuery: la frescura medida es 0,35 s, la apertura 35,46 s y el filtro ~0,5 s; se descartó Import y Power BI Service porque no hacían falta para cumplir los umbrales.",
                    "CSV en streaming: el histórico pesa ~99 MB, se inspecciona y se carga por lotes; se descartó Parquet para no añadir pyarrow ni complejidad.",
                    "TMDL y PBIR generados por código, con pgAdmin para verificación: el modelo y las páginas quedan versionados y validables; no se construyó API REST, aplicación web, Kafka ni MQTT por alcance académico y límite de memoria.",
                ]:
                    add_bullet(doc, bullet)
                add_body(
                    doc,
                    "Estas decisiones explican por qué el prototipo no es una aplicación web ni un "
                    "servicio en la nube: es un banco de trabajo analítico local que prioriza la "
                    "trazabilidad y la posibilidad de repetir la demo sin internet.",
                )
            else:
                add_body(doc, f"Contenido previsto: {desc}")

    # Referencias
    doc.add_page_break()
    add_heading_custom(doc, "8. Referencias bibliográficas", 1)
    refs = (BASE / "REFERENCIAS.md").read_text(encoding="utf-8").splitlines()
    started = False
    for line in refs:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(">"):
            continue
        if line.startswith("Ahuja"):
            started = True
        if started:
            add_reference(doc, line)

    # Anexos
    annex_titles = [
        ("Anexo A. Texto completo del caso práctico original", "Texto reproducido del enunciado. La empresa y los datos son ficticios."),
        ("Anexo B. Diccionario de datos seleccionado", "Tablas, granularidad y columnas principales."),
        ("Anexo C. Matriz de aceptación del caso", "Correspondencia entre los criterios f.1–f.5 y la evidencia."),
        ("Anexo D. Capturas completas del tablero", "Páginas 01–04 y páginas de apoyo."),
        ("Anexo E. Guía de reproducción", "Comandos, entorno y corte de datos."),
        ("Anexo F. Glosario y abreviaturas", "Términos técnicos y siglas."),
        ("Anexo G. Tabla maestra de cifras y trazabilidad", "Resumen de la tabla maestra del corte 2026-10-24."),
        ("Anexo H. Guion de exposición y preguntas previsibles", "Guion de 10 minutos y preguntas frecuentes."),
    ]
    for title, desc in annex_titles:
        doc.add_page_break()
        add_heading_custom(doc, title, 1)
        p = doc.add_paragraph(style="Normal")
        r = p.add_run(desc)
        set_run_font(r, "Times New Roman", 12, italic=True)

        if title.startswith("Anexo A"):
            for line in read_case_text():
                text = line.strip()
                if not text:
                    continue
                p = doc.add_paragraph(style="CaseText")
                text = text.lstrip("* ").strip()
                es_titulo = text.startswith(
                    (
                        "CASO DE ESTUDIO A",
                        "CASO METALNOVA",
                        "1. Contexto",
                        "2. Metodología",
                        "a. Planificación",
                        "b. Modelado",
                        "c. Desarrollo",
                        "d. Dashboard",
                        "e. Análisis",
                        "f. Producto",
                    )
                )
                add_rich_runs(p, text, "Times New Roman", 10.5, bold=es_titulo)

        elif title.startswith("Anexo B"):
            add_table_apa(
                doc,
                ["Tabla", "Grano", "Columnas principales"],
                [
                    ["fact_produccion", "orden + máquina + turno + día", "tiempo_planificado, runtime, total/good/scrap, ciclo ideal, energía"],
                    ["fact_parada", "episodio de parada", "inicio, fin, duración, causa, planificada, microparada, OT"],
                    ["fact_mantenimiento", "orden de trabajo", "tipo, técnico, fechas, duración, costo, estado"],
                    ["fact_calidad", "inspección / lote", "inspeccionadas, buenas, defectuosas, retrabajo"],
                    ["fact_evento", "evento crudo", "source_system, source_event_id, event_time, payload"],
                    ["fact_evento_rechazado", "evento en cuarentena", "motivo, payload, recibido_at"],
                    ["dim_maquina", "máquina", "planta, línea, tipo, criticidad, perfil"],
                    ["dim_producto", "producto", "familia, ciclo ideal, unidad"],
                    ["dim_tiempo", "día", "año, trimestre, mes, día"],
                    ["dim_causa", "causa", "categoría, detalle, planificada"],
                ],
                "B1",
                "Diccionario de datos seleccionado",
                "Datos sintéticos. El diccionario completo está en `docs/DATA_DICTIONARY.md`.",
            )

        elif title.startswith("Anexo C"):
            add_table_apa(
                doc,
                ["Criterio del caso", "Evidencia", "Veredicto"],
                [
                    ["f.1 Fórmulas de OEE reconciliadas", "12/12 SQL; 49/49 Python; OEE 71,9645 %", "Cumple"],
                    ["f.2 Modelo con múltiples hechos y dimensiones", "4 hechos analíticos + 2 crudos; 10 dimensiones; 27 relaciones", "Cumple con matiz"],
                    ["f.3 4 vistas, 9 KPIs y navegación", "4 páginas principales; 24 tarjetas; drill-through y tooltip", "Cumple"],
                    ["f.4 Calidad y temporalidad IoT", "Cuarentena, tardío/reordenado, 11/11 y 5/5", "Cumple con matiz"],
                    ["f.5 Plan de mejora priorizado", "5 acciones con impacto, supuesto y criticidad", "Cumple"],
                ],
                "B2",
                "Matriz de aceptación del caso",
                "Datos sintéticos. El detalle está en `docs/verification/bloque6-producto-criterios.md`.",
                widths=[Inches(2.0), Inches(3.5), Inches(1.0)],
            )

        elif title.startswith("Anexo D"):
            add_body(
                doc,
                "Las figuras D1–D4 reproducen las cuatro páginas principales. Las figuras D5–D8 "
                "(detalle de máquina, detalle de causa, tooltip y validación T-604) se incorporarán "
                "en la versión final; los archivos están disponibles en docs/capturas/.",
                style="Normal",
            )
            captures = [
                ("01-executive.png", "D1", "Página 01 Executive Plant Performance"),
                ("02-oee-loss-tree.png", "D2", "Página 02 OEE & Loss Tree"),
                ("03-maintenance.png", "D3", "Página 03 Maintenance Reliability"),
                ("04-quality-energy.png", "D4", "Página 04 Quality & Energy"),
            ]
            for filename, num, cap in captures:
                add_figure_apa(
                    doc,
                    PROJECT / "docs" / "capturas" / filename,
                    num,
                    cap,
                    "Datos sintéticos. Captura de Power BI Desktop, 2026-10-23. "
                    "La barra amarilla y el panel de filtros son parte de la interfaz de Power BI, no del informe.",
                    width=Inches(6.2),
                )

        elif title.startswith("Anexo E"):
            add_table_apa(
                doc,
                ["Paso", "Comando", "Resultado esperado"],
                [
                    ["1. Arrancar", "docker compose up -d", "db healthy; pgAdmin en 127.0.0.1:5050"],
                    ["2. Aplicar esquema", "docker compose exec -T db psql -U metalinova -d metalinova -f /sql/apply_all.sql", "Esquema, catálogo y vistas KPI"],
                    ["3. Generar histórico", "docker compose run --rm ingestor python src/generate_history.py --seed 42 --end-date 2026-10-18 --escenario calibracion", "CSV + manifest"],
                    ["4. Cargar", "docker compose run --rm ingestor python src/load_history.py", "Carga idempotente"],
                    ["5. Verificar", "docker compose run --rm ingestor python src/verify_history.py", "17/17 OK"],
                    ["6. Validar KPIs", "docker compose run --rm ingestor python src/validate_data.py", "49/49 OK"],
                    ["7. Abrir Power BI", "Abrir powerbi/final/MetalNova.pbip y actualizar", "4 páginas principales"],
                    ["8. Simular evento", "docker compose --profile tools run --rm ingestor python src/simulate_events.py --scenario stop M-001 --once", "Parada visible en KPI"],
                ],
                "B3",
                "Guía de reproducción",
                "Datos sintéticos. Los comandos se ejecutan desde la raíz del proyecto. No se incluyen credenciales.",
                widths=[Inches(1.2), Inches(3.6), Inches(1.7)],
            )

        elif title.startswith("Anexo F"):
            add_table_apa(
                doc,
                ["Término", "Definición"],
                [
                    ["OEE", "Overall Equipment Effectiveness: disponibilidad × rendimiento × calidad."],
                    ["A/P/Q", "Disponibilidad, rendimiento y calidad."],
                    ["MTBF", "Mean Time Between Failures: tiempo operativo / número de fallas."],
                    ["MTTR", "Mean Time To Repair: minutos de reparación / reparaciones."],
                    ["FPY", "First Pass Yield: unidades sin retrabajo / unidades procesadas."],
                    ["MES", "Manufacturing Execution System."],
                    ["CMMS", "Computerized Maintenance Management System."],
                    ["SCADA", "Supervisory Control and Data Acquisition."],
                    ["IoT", "Internet of Things."],
                    ["BI", "Business Intelligence."],
                    ["DAX", "Data Analysis Expressions (lenguaje de medidas de Power BI)."],
                    ["DirectQuery", "Modo de conexión de Power BI que consulta la fuente en tiempo de visualización."],
                ],
                "B4",
                "Glosario y abreviaturas",
                "Datos sintéticos. Términos usados en el informe.",
                widths=[Inches(1.2), Inches(5.2)],
            )

        elif title.startswith("Anexo G"):
            add_table_apa(
                doc,
                ["Bloque", "Cifra principal", "Valor"],
                [
                    ["Volumen", "Eventos de origen", "401.838"],
                    ["Volumen", "Eventos de máquina", "343.050"],
                    ["OEE", "OEE global 180 días", "71,9645 %"],
                    ["OEE", "OEE inicio → cierre 30 días", "78,0226 % → 65,9961 %"],
                    ["Loss Tree", "Pérdida total", "3.528.469,08 min"],
                    ["Loss Tree", "Participación de rendimiento", "82,51 %"],
                    ["Mantenimiento", "MTBF / MTTR", "85,6078 h / 17,8392 min"],
                    ["Calidad", "Scrap / FPY", "4,8411 % / 97,6295 %"],
                    ["Energía", "kWh por unidad buena", "0,340312"],
                    ["Alertas", "Alertas / críticas", "3.284 / 248"],
                ],
                "B5",
                "Tabla maestra de cifras (resumen)",
                "Datos sintéticos. Corte 2026-10-24. La tabla completa está en `docs/informe/TABLA_MAESTRA_CIFRAS.md`.",
                widths=[Inches(1.3), Inches(3.0), Inches(2.1)],
            )

        elif title.startswith("Anexo H"):
            add_heading_custom(doc, "H.1 Guion de 10 minutos", 2)
            for text in [
                "Minuto 0–1: problema, pregunta y advertencia de datos sintéticos.",
                "Minuto 1–3: arquitectura y modelo dimensional; por qué PostgreSQL, Docker y Power BI.",
                "Minuto 3–5: OEE, A/P/Q y Loss Tree; la pérdida dominante es rendimiento.",
                "Minuto 5–7: P-SUR, L3-2, M-047, turno C; microparadas y F-MEC.",
                "Minuto 7–8: confiabilidad, calidad y energía; M-015 y M-025 como casos que el promedio oculta.",
                "Minuto 8–9: validación, latencia y tablero; drill-through y alerta.",
                "Minuto 9–10: recomendaciones A1–A5, limitaciones y cierre.",
            ]:
                add_bullet(doc, text)
            add_heading_custom(doc, "H.2 Preguntas previsibles", 2)
            qa = [
                ("¿Los datos son reales?", "No. Son sintéticos y el escenario fue calibrado para producir señal; no se presenta como telemetría real."),
                ("¿Por qué la caída es de rendimiento y no de disponibilidad?", "Porque el Loss Tree muestra 2.911.218 min de pérdida de rendimiento (82,51 %) frente a 151.831 min de disponibilidad (4,30 %)."),
                ("¿Por qué M-047 es crítica?", "OEE 51,81 % en 180 días, 47,47 % en 30 días, 6.473 min de downtime, 1.178 microparadas y 262,97 fallas cortas/100 h."),
                ("¿Por qué M-015 y M-025 aparecen si tienen MTBF alto?", "Porque su tasa de microparadas es alta; el MTBF solo cuenta fallas formales y oculta las paradas breves."),
                ("¿Por qué FPY 97,63 % no coincide con calidad 95,16 %?", "Porque FPY usa “inspeccionadas − retrabajo” y no descuenta el scrap no retrabajado; es una definición literal documentada."),
                ("¿Por qué DirectQuery y no Import?", "Porque la frescura de 0,35 s y la apertura de 35,46 s cumplen los umbrales; no se requiere nube."),
                ("¿Por qué PostgreSQL y Docker?", "Porque permiten SQL analítico, reproducibilidad, aislamiento y ejecución local en 8 GB."),
                ("¿Por qué no se usó machine learning?", "Porque el objetivo era descriptivo/diagnóstico y los datos sintéticos no justifican un modelo predictivo; queda como trabajo futuro."),
                ("¿Se puede afirmar causalidad?", "No. Las relaciones scrap-producto-turno-energía son descriptivas y hay confusión producto-planta."),
                ("¿Los ahorros son reales?", "No. Son hipotéticos y dependen de USD 220/h, USD 18/unidad y USD 0,12/kWh, supuestos declarados."),
                ("¿Qué falta para una implantación real?", "Datos reales, ERP etiquetado, mayor cadencia IoT, validación de costos, gobierno del dato y despliegue controlado."),
                ("¿Qué haría primero en MetalNova?", "A1 y A2 en P-SUR; A3 por criticidad de M-047; A4 como sostén de confiabilidad; A5 como mejora continua."),
            ]
            for q, a in qa:
                p = doc.add_paragraph(style="Normal")
                r = p.add_run(f"P: {q} ")
                set_run_font(r, "Times New Roman", 12, bold=True)
                r2 = p.add_run(f"R: {a}")
                set_run_font(r2, "Times New Roman", 12)

    # Propiedades del documento
    props = doc.core_properties
    props.title = (
        "Caso MetalNova de BI: diseño y evaluación de un prototipo de inteligencia "
        "de negocio para medir el OEE y priorizar pérdidas"
    )
    props.author = "Leandro Arguello"
    props.subject = "Informe de caso práctico — Examen Complexivo"
    props.keywords = "OEE; Business Intelligence; mantenimiento industrial; calidad de datos"
    props.comments = "Datos sintéticos. Corte 2026-10-24. Documento de trabajo v0.1."

    # Guardar
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
