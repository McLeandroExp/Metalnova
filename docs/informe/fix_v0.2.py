"""Corrige el DOCX v0.1 sin tocar la portada editada por el usuario.

- Fuerza Times New Roman 12 en títulos, TOC y cuerpo.
- Corrige bordes, anchos y alineación de tablas.
- Elimina las menciones a "datos sintéticos" fuera de la metodología.
- Extrae el Anexo H a un documento independiente y lo elimina del informe.
- Guarda como v0.2.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

BASE = Path(__file__).resolve().parent
SRC = BASE / "MetalNova_Informe_Caso_Practico_v0.1.docx"
DST = BASE / "MetalNova_Informe_Caso_Practico_v0.2.docx"
GUIDE = BASE / "MetalNova_Guion_Defensa_v0.1.docx"

NEGRO = RGBColor(0, 0, 0)

# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------


def force_style(style, size=12, bold=None, italic=None, color=NEGRO):
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        rfonts.attrib.pop(qn(f"w:{attr}"), None)
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn(f"w:{attr}"), "Times New Roman")
    style.font.name = "Times New Roman"
    style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    if color is not None:
        style.font.color.rgb = color


def force_run(run, size=12, bold=None, italic=None):
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    run.font.color.rgb = NEGRO
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        rfonts.attrib.pop(qn(f"w:{attr}"), None)
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn(f"w:{attr}"), "Times New Roman")


# ---------------------------------------------------------------------------
# Tablas
# ---------------------------------------------------------------------------


def set_cell_border(cell, edge, sz=8, val="single"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    el = borders.find(qn(f"w:{edge}"))
    if el is None:
        el = OxmlElement(f"w:{edge}")
        borders.append(el)
    el.set(qn("w:val"), val)
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:space"), "0")
    el.set(qn("w:color"), "000000")


def clear_cell_borders(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    old = tc_pr.find(qn("w:tcBorders"))
    if old is not None:
        tc_pr.remove(old)
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tc_pr.append(borders)


def set_cell_margins(cell, top=40, bottom=40, left=80, right=80):
    tc_pr = cell._tc.get_or_add_tcPr()
    old = tc_pr.find(qn("w:tcMar"))
    if old is not None:
        tc_pr.remove(old)
    mar = OxmlElement("w:tcMar")
    for edge, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:w"), str(value))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tc_pr.append(mar)


def set_table_borders(table):
    tbl_pr = table._tbl.tblPr
    old = tbl_pr.find(qn("w:tblBorders"))
    if old is not None:
        tbl_pr.remove(old)
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


def set_repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:tblHeader")) is None:
        el = OxmlElement("w:tblHeader")
        el.set(qn("w:val"), "true")
        tr_pr.append(el)


def set_cant_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:cantSplit")) is None:
        el = OxmlElement("w:cantSplit")
        el.set(qn("w:val"), "true")
        tr_pr.append(el)


def fix_table(table, widths):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.allow_autofit = False
    tbl_pr = table._tbl.tblPr
    for old in tbl_pr.findall(qn("w:tblW")):
        tbl_pr.remove(old)
    tbl_w = OxmlElement("w:tblW")
    tbl_w.set(qn("w:w"), "9360")
    tbl_w.set(qn("w:type"), "dxa")
    tbl_pr.append(tbl_w)
    for old in tbl_pr.findall(qn("w:tblLayout")):
        tbl_pr.remove(old)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)
    set_table_borders(table)

    for i, width in enumerate(widths):
        table.columns[i].width = width
    for row in table.rows:
        set_cant_split(row)
        for i, width in enumerate(widths):
            row.cells[i].width = width
    set_repeat_header(table.rows[0])

    for ri, row in enumerate(table.rows):
        for cell in row.cells:
            clear_cell_borders(cell)
            set_cell_margins(cell)
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1
                p.paragraph_format.left_indent = Cm(0)
                p.paragraph_format.first_line_indent = Cm(0)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if ri == 0 else WD_ALIGN_PARAGRAPH.LEFT
                for run in p.runs:
                    run.font.name = "Arial"
                    run.font.size = Pt(8)
                    run.font.color.rgb = NEGRO
                    rpr = run._element.get_or_add_rPr()
                    rfonts = rpr.find(qn("w:rFonts"))
                    if rfonts is None:
                        rfonts = OxmlElement("w:rFonts")
                        rpr.append(rfonts)
                    for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
                        rfonts.attrib.pop(qn(f"w:{attr}"), None)
                    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
                        rfonts.set(qn(f"w:{attr}"), "Arial")
                    if ri == 0:
                        run.bold = True
    for cell in table.rows[0].cells:
        set_cell_border(cell, "top", 8)
        set_cell_border(cell, "bottom", 8)
    for cell in table.rows[-1].cells:
        set_cell_border(cell, "bottom", 8)


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------


def rewrite_paragraph(p, text, size=12):
    for run in list(p.runs):
        run._element.getparent().remove(run._element)
    run = p.add_run(text)
    force_run(run, size=size)
    if p.style.name == "AbstractText":
        p.paragraph_format.first_line_indent = Cm(0)
    else:
        p.paragraph_format.first_line_indent = Cm(1.27)
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_after = Pt(0)


def remove_paragraph(p):
    el = p._p
    parent = el.getparent()
    if parent is not None:
        parent.remove(el)


def fix_texts(doc):
    in_method = False
    for p in doc.paragraphs:
        text = p.text
        if p.style.name == "Heading 1" and text.startswith("3."):
            in_method = True
        elif p.style.name == "Heading 1" and text.startswith("4."):
            in_method = False

        # Menciones que deben quedar solo en metodología.
        if not in_method:
            new = text
            new = new.replace("integra datos sintéticos de IoT/SCADA", "integra datos de IoT/SCADA")
            new = new.replace("integra datos sintéticos de", "integra datos de")
            new = new.replace("Los datos son sintéticos y los ahorros son hipotéticos.", "Los ahorros son hipotéticos.")
            new = new.replace("Data are synthetic and savings are hypothetical.", "Savings are hypothetical.")
            new = new.replace("integrates synthetic data from IoT/SCADA", "integrates data from IoT/SCADA")
            new = new.replace("prototipo académico con datos sintéticos", "prototipo académico con un conjunto de datos preparado para el caso")
            new = new.replace("datos industriales sintéticos", "datos industriales")
            new = new.replace("usa datos sintéticos reproducibles", "usa datos reproducibles")
            new = new.replace("Los datos son sintéticos; el escenario calibracion", "El escenario calibracion")
            new = new.replace("Datos sintéticos, calibración, ERP, IoT, FPY", "Diseño académico, calibración, ERP, IoT, FPY")
            new = new.replace("Datos sintéticos. ", "")
            if new != text:
                if p.style.name == "Note":
                    for run in list(p.runs):
                        run._element.getparent().remove(run._element)
                    run = p.add_run(new)
                    run.font.name = "Arial"
                    run.font.size = Pt(8)
                    run.font.color.rgb = NEGRO
                else:
                    rewrite_paragraph(p, new)

    # Declaración explícita en 3.3 (metodología).
    for p in doc.paragraphs:
        if p.text.startswith("Contenido previsto: IoT/SCADA, MES, CMMS"):
            new_p = deepcopy(p._p)
            p._p.addnext(new_p)
            # Convertir el clon en párrafo normal con el texto de declaración.
            from docx.text.paragraph import Paragraph
            q = Paragraph(new_p, p._parent)
            rewrite_paragraph(
                q,
                "Los datos son sintéticos: se generaron con semilla 42, 180 días y un escenario "
                "calibrado para que la señal del caso fuera visible; no son telemetría real ni "
                "una implantación en MetalNova.",
            )
            break


# ---------------------------------------------------------------------------
# Extracción del Anexo H
# ---------------------------------------------------------------------------


def extract_annex_h(doc):
    start = None
    for i, p in enumerate(doc.paragraphs):
        if p.style.name == "Heading 1" and p.text.startswith("Anexo H."):
            start = i
            break
    if start is None:
        return []
    data = []
    for p in doc.paragraphs[start:]:
        data.append(
            {
                "style": p.style.name,
                "text": p.text,
                "runs": [(r.text, bool(r.bold), bool(r.italic)) for r in p.runs],
            }
        )
    return data


def remove_annex_h(doc):
    # Quitar la entrada H de la lista de anexos.
    for p in doc.paragraphs:
        if p.style.name == "ListEntry" and p.text.startswith("H\t"):
            remove_paragraph(p)
            break

    # Quitar el título y todo el contenido posterior, conservando el sectPr final.
    start = None
    for p in doc.paragraphs:
        if p.style.name == "Heading 1" and p.text.startswith("Anexo H."):
            start = p
            break
    if start is None:
        return
    body = doc.element.body
    prev = start._p.getprevious()
    if prev is not None and prev.tag == qn("w:p"):
        text = "".join(prev.itertext()).strip()
        has_break = prev.find(qn("w:r")) is not None and prev.findall(".//" + qn("w:br"))
        if not text and has_break:
            body.remove(prev)
    el = start._p
    while el is not None:
        nxt = el.getnext()
        if el.tag == qn("w:sectPr"):
            break
        body.remove(el)
        el = nxt


def build_guide(data):
    g = Document()
    sec = g.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11)
    for m in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(sec, m, Inches(1))

    normal = g.styles["Normal"]
    force_style(normal, 12)
    normal.paragraph_format.line_spacing = 2.0
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    normal.paragraph_format.first_line_indent = Cm(1.27)

    for name in ("Heading 1", "Heading 2"):
        st = g.styles[name]
        force_style(st, 12, bold=True, italic=False)
        st.paragraph_format.line_spacing = 2.0
        st.paragraph_format.space_before = Pt(12)
        st.paragraph_format.space_after = Pt(0)
        st.paragraph_format.first_line_indent = Cm(0)
        st.paragraph_format.keep_with_next = True

    p = g.add_paragraph(style="Heading 1")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Guion de exposición y preguntas previsibles")
    force_run(r, 12, bold=True)

    p = g.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("Caso MetalNova de BI — Examen Complexivo")
    force_run(r, 12, italic=True)

    p = g.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("Autor: Leandro Arguello · Quito, 2026")
    force_run(r, 12)

    for item in data:
        if item["style"] == "Heading 1":
            continue  # el título ya se agregó
        style = item["style"] if item["style"] in ("Heading 2", "List Bullet") else "Normal"
        p = g.add_paragraph(style=style)
        if style == "Normal":
            p.paragraph_format.first_line_indent = Cm(1.27)
        else:
            p.paragraph_format.first_line_indent = Cm(0)
        for text, bold, italic in item["runs"]:
            r = p.add_run(text)
            force_run(r, 12, bold=bold, italic=italic)
        if not item["runs"]:
            r = p.add_run(item["text"])
            force_run(r, 12)

    # Pie de página simple con número.
    footer = g.sections[0].footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run()
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t")
    t.text = "1"
    fld3 = OxmlElement("w:fldChar")
    fld3.set(qn("w:fldCharType"), "end")
    run._r.append(fld1)
    run._r.append(instr)
    run._r.append(fld2)
    run._r.append(t)
    run._r.append(fld3)
    force_run(run, 12)

    g.save(GUIDE)


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------


def main():
    doc = Document(SRC)

    # 1. Títulos y TOC en Times New Roman 12.
    for name, bold, italic in [
        ("Heading 1", True, False),
        ("Heading 2", True, False),
        ("Heading 3", True, True),
        ("toc 1", False, False),
        ("toc 2", False, False),
        ("toc 3", False, False),
    ]:
        if name in [s.name for s in doc.styles]:
            force_style(doc.styles[name], 12, bold=bold, italic=italic)

    # Tablas y figuras: Arial 8; el número va en negrita por run.
    for name, bold in (("Caption", False), ("Note", None)):
        if name in [s.name for s in doc.styles]:
            st = doc.styles[name]
            rpr = st.element.get_or_add_rPr()
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is None:
                rfonts = OxmlElement("w:rFonts")
                rpr.append(rfonts)
            for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
                rfonts.attrib.pop(qn(f"w:{attr}"), None)
            for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
                rfonts.set(qn(f"w:{attr}"), "Arial")
            st.font.name = "Arial"
            st.font.size = Pt(8)
            st.font.bold = bold
            st.font.color.rgb = NEGRO

    # 2. Runs de títulos con fuente explícita.
    for p in doc.paragraphs:
        if p.style.name in ("Heading 1", "Heading 2", "Heading 3"):
            for r in p.runs:
                force_run(r, 12, bold=True, italic=(p.style.name == "Heading 3"))

    # 3. Texto: quitar menciones fuera de metodología.
    data = extract_annex_h(doc)
    fix_texts(doc)

    # 4. Tablas.
    widths = [
        [Inches(2.0), Inches(3.3), Inches(1.2)],  # T1
        [Inches(1.3), Inches(2.1), Inches(3.1)],  # B1
        [Inches(1.9), Inches(3.4), Inches(1.2)],  # B2
        [Inches(1.2), Inches(3.5), Inches(1.8)],  # B3
        [Inches(1.2), Inches(5.3)],                # B4
        [Inches(1.3), Inches(2.8), Inches(2.4)],  # B5
    ]
    for table, w in zip(doc.tables, widths):
        fix_table(table, w)

    # 5. Quitar Anexo H y guardar.
    remove_annex_h(doc)
    doc.save(DST)

    # 6. Documento independiente del guion.
    build_guide(data)

    print(DST)
    print(GUIDE)


if __name__ == "__main__":
    main()
