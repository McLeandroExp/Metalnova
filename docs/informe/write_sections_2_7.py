"""Redacta las secciones 2-7 del informe sobre la v0.2, sin tocar portada ni tablas existentes.

Guarda como v0.3.
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

BASE = Path(__file__).resolve().parent
SRC = BASE / "MetalNova_Informe_Caso_Practico_v0.2.docx"
DST = BASE / "MetalNova_Informe_Caso_Practico_v0.3.docx"
FIG = BASE / "figuras"
NEGRO = RGBColor(0, 0, 0)


def set_cell_margins(cell, top=10, bottom=10, left=60, right=60):
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


def set_all_borders(table):
    tbl_pr = table._tbl.tblPr
    old = tbl_pr.find(qn("w:tblBorders"))
    if old is not None:
        tbl_pr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")
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


SKIP = (
    "La arquitectura del prototipo sigue una lógica por capas",
    "Witten y Frank (2005) ubican",
    "El BABOK (IIBA, 2015) aporta",
    "La ingesta continua simulada emite eventos",
    "La consecuencia práctica es que el prototipo no es una aplicación",
    "La caída no es un problema de disponibilidad.",
    "El Pareto muestra que las microparadas",
    "La literatura sobre OEE advierte",
    "M-047 es el caso opuesto",
    "El informe evita la trampa",
    "El plan de mejora usa metas parciales",
    "La validez interna se apoya",
    "Parmenter (2015) recuerda",
    "Los KPIs se calcularon en vistas SQL",
    "La calidad de los datos es razonable",
    "El tablero tiene cuatro páginas principales y cuatro de apoyo",
)


class Writer:
    def __init__(self, doc, ref):
        self.doc = doc
        self.ref = ref

    def _place(self, el):
        self.ref._p.addprevious(el)

    def h(self, text, level=1, page_break=False):
        p = self.doc.add_paragraph(style=f"Heading {level}")
        p.add_run(text)
        p.paragraph_format.page_break_before = page_break
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        self._place(p._p)

    def p(self, text, style="Normal"):
        if any(marker in str(text) for marker in SKIP):
            return
        p = self.doc.add_paragraph(style=style)
        p.add_run(str(text).replace("`", ""))
        self._place(p._p)

    def bullet(self, text):
        p = self.doc.add_paragraph(style="List Bullet")
        p.add_run(str(text).replace("`", ""))
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.4)
        self._place(p._p)

    def caption(self, kind, num, title):
        p = self.doc.add_paragraph(style="Caption")
        r = p.add_run(f"{kind} {num}")
        r.bold = True
        r2 = p.add_run(". ")
        r2.bold = True
        r3 = p.add_run(title)
        r3.italic = True
        self._place(p._p)

    def note(self, text):
        p = self.doc.add_paragraph(style="Note")
        r = p.add_run("Nota. ")
        r.italic = True
        p.add_run(text)
        self._place(p._p)

    def table(self, num, title, headers, rows, widths, note=None):
        self.caption("Tabla", num, title)
        table = self.doc.add_table(rows=1 + len(rows), cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        table.allow_autofit = False
        tbl_pr = table._tbl.tblPr
        for old in tbl_pr.findall(qn("w:tblW")):
            tbl_pr.remove(old)
        tw = OxmlElement("w:tblW")
        tw.set(qn("w:w"), "9360")
        tw.set(qn("w:type"), "dxa")
        tbl_pr.append(tw)
        for old in tbl_pr.findall(qn("w:tblLayout")):
            tbl_pr.remove(old)
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        tbl_pr.append(layout)
        set_all_borders(table)
        for i, w in enumerate(widths):
            table.columns[i].width = w
        for row in table.rows:
            set_cant_split(row)
            for i, w in enumerate(widths):
                row.cells[i].width = w
        set_repeat_header(table.rows[0])

        for ri, row in enumerate(table.rows):
            for cell in row.cells:
                set_cell_margins(cell)
                for p in cell.paragraphs:
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(0)
                    p.paragraph_format.line_spacing = 1
                    p.paragraph_format.left_indent = Cm(0)
                    p.paragraph_format.first_line_indent = Cm(0)
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if ri == 0 else WD_ALIGN_PARAGRAPH.LEFT

        for j, h in enumerate(headers):
            cell = table.rows[0].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.first_line_indent = Cm(0)
            r = p.add_run(h)
            r.font.name = "Arial"
            r.font.size = Pt(8)
            r.bold = True
            r.font.color.rgb = NEGRO

        for i, row_data in enumerate(rows):
            for j, value in enumerate(row_data):
                cell = table.rows[i + 1].cells[j]
                cell.text = ""
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.first_line_indent = Cm(0)
                r = p.add_run(str(value).replace("`", ""))
                r.font.name = "Arial"
                r.font.size = Pt(8)
                r.font.color.rgb = NEGRO

        for ri, row in enumerate(table.rows):
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = ri < len(table.rows) - 1

        self._place(table._tbl)
        if note:
            self.note(note)

    def figure(self, num, title, filename, note=None, width=5.6):
        self.caption("Figura", num, title)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(3)
        p.add_run().add_picture(str(FIG / filename), width=Inches(width))
        self._place(p._p)
        if note:
            self.note(note)


# ---------------------------------------------------------------------------
# Datos de tablas
# ---------------------------------------------------------------------------

T2 = [
    ["OEE", "A × P × Q", "71,9645 %"],
    ["Disponibilidad", "runtime / tiempo planificado", "98,7918 %"],
    ["Rendimiento", "(ciclo ideal × total count) / runtime", "76,5505 %"],
    ["Calidad", "good count / total count", "95,1589 %"],
    ["MTBF", "horas operativas / fallas", "85,6078 h"],
    ["MTTR", "minutos de reparación / reparaciones", "17,8392 min"],
    ["Downtime no planificado", "minutos no planificados / planificado", "1,2114 %"],
    ["Scrap Rate", "scrap / total count", "4,8411 %"],
    ["FPY", "(inspeccionadas − retrabajo) / inspeccionadas", "97,6295 %"],
    ["Energía por unidad buena", "kWh / good count", "0,340312 kWh"],
]

T3 = [
    ["OEE", "Nakajima (1988); Muchiri y Pintelon (2008); Jonsson y Lesshammar (1999); Dal et al. (2000)", "Definición, componentes y críticas", "OEE aislado, sin Loss Tree ni priorización"],
    ["TPM y confiabilidad", "Ahuja y Khamba (2008); Swanson (2001); Mobley (2002); ISO 14224", "Mantenimiento, MTBF/MTTR y modos de falla", "Fallas cortas y microparadas fuera del promedio"],
    ["BI y modelado", "Curto Díaz (2010); Howson (2008); Kimball y Ross (2013); Parmenter (2015)", "Arquitectura, modelo estrella y KPIs", "Fuentes fragmentadas y KPI no comparable"],
    ["Calidad de datos", "Batini et al. (2009); Wang y Strong (1996)", "Dimensiones y métodos de calidad", "Cuarentena y trazabilidad de eventos IoT"],
    ["Industria 4.0", "Lee et al. (2015)", "CPS, sensores y latencia", "Eventos cercanos al tiempo real"],
    ["Método", "IIBA (2015); Wirth y Hipp (2000)", "Business Analysis y CRISP-DM", "Trazabilidad requisito → evidencia"],
]

T4 = [
    ["IoT/SCADA", "Transiciones, temperatura, energía", "Inicio/fin de parada; energía y temperatura", "OEE, paradas, alertas"],
    ["MES", "Órdenes y conteos", "Conteos de producción", "Producción y calidad"],
    ["CMMS", "Órdenes de trabajo", "Confirmación de reparación", "MTTR y mantenimiento"],
    ["Calidad", "Inspecciones y retrabajo", "Buenas, defectuosas y retrabajo", "FPY y scrap"],
    ["Turnos", "Calendario", "Tiempo planificado", "Disponibilidad"],
    ["ERP", "Órdenes y productos", "Parcial: sin `source_system='erp'`", "Limitación declarada"],
]

T5 = [
    ["fact_produccion", "orden + máquina + turno + día", "28.080"],
    ["fact_parada", "episodio de parada", "76.045"],
    ["fact_mantenimiento", "orden de trabajo", "2.628"],
    ["fact_calidad", "inspección / lote", "28.080"],
    ["fact_evento", "evento crudo", "401.838"],
    ["fact_evento_rechazado", "evento en cuarentena", "2"],
    ["dim_maquina", "máquina", "52"],
    ["dim_producto", "producto", "12"],
    ["dim_tiempo", "día", "1.095"],
    ["dim_causa", "causa", "13"],
]

T6 = [
    ["Duplicados", "`ON CONFLICT (source_system, source_event_id)`", "0 duplicados"],
    ["Fuera de rango", "Rechazo a `fact_evento_rechazado`", "2 rechazos"],
    ["Tardío", "Acepta y marca `payload.calidad.tardio`", "1 evento"],
    ["Reordenado", "Acepta y marca `payload.calidad.reordenado`", "1 evento"],
    ["Faltantes", "`v_calidad_senal_iot` declara el hueco", "gap máximo 210 min"],
    ["Solapes", "`v_parada_consolidada` une intervalos estrictos", "0 solapes; prueba 10+15 → 20 min"],
]

T7 = [
    ["OEE bajo", "< 55 %", "Revisar pérdida dominante con PDCA", "Producción"],
    ["MTBF bajo", "< 20 h", "Inspección preventiva anticipada", "Mantenimiento"],
    ["Temperatura alta", "> 85 °C durante 15 min", "Revisar refrigeración y lubricación", "Mantenimiento"],
    ["Downtime acumulado", "> 120 min/turno", "Reasignar capacidad o intervenir", "Producción"],
]

T8 = [
    ["KPI Python", "`validate_data.py`", "49/49"],
    ["Fórmulas SQL", "`07_kpi_formulas.sql`", "12/12"],
    ["Calidad IoT Python", "`validate_iot.py`", "11/11"],
    ["Calidad IoT SQL", "`04_iot.sql`", "5/5"],
    ["Histórico", "`verify_history.py`", "17/17"],
    ["Calibración", "`03_calibracion.sql`", "7/7"],
    ["Modelo semántico", "`validate_model.py`", "70 medidas, 27 relaciones, 15 tablas"],
    ["Informe", "`validate_report.py`", "8 páginas, 105 visuales"],
]

T9 = [
    ["Plantas / líneas / máquinas", "3 / 6 / 52"],
    ["Días con producción", "180"],
    ["Eventos de origen", "401.838"],
    ["Eventos de máquina", "343.050"],
    ["Órdenes", "28.080"],
    ["Paradas", "76.045"],
    ["Mantenimientos", "2.628"],
    ["Inspecciones", "28.080"],
    ["Eventos rechazados", "2"],
]

T10 = [
    ["OEE", "71,9645 %"],
    ["A / P / Q", "98,7918 / 76,5505 / 95,1589 %"],
    ["MTBF", "85,6078 h"],
    ["MTTR", "17,8392 min"],
    ["Downtime no planificado", "1,2114 %"],
    ["Scrap Rate", "4,8411 %"],
    ["FPY", "97,6295 %"],
    ["Energía por unidad buena", "0,340312 kWh"],
    ["Unidades producidas", "14.142.393"],
    ["Unidades scrap", "684.643"],
]

T11 = [
    ["Inicio (30 d)", "99,03", "81,78", "96,34", "78,02", "3,66", "0,3217"],
    ["Cierre (30 d)", "98,55", "71,31", "93,92", "65,99", "6,08", "0,3609"],
    ["Cambio", "−0,48", "−10,47", "−2,43", "−12,03", "+2,43", "+12,2 %"],
]

T12 = [
    ["Disponibilidad", "151.831", "4,30 %"],
    ["Rendimiento", "2.911.218,08", "82,51 %"],
    ["Calidad", "465.420,00", "13,19 %"],
    ["Total", "3.528.469,08", "100 %"],
]

T13 = [
    ["Planta", "P-SUR", "62,04 % (30 d); 67,73 % (180 d)"],
    ["Línea", "L3-2", "60,98 %"],
    ["Máquina", "M-047", "47,47 % (30 d); 51,81 % (180 d)"],
    ["Turno de M-047", "C", "45,33 %"],
    ["Producto 30 d", "PRD-009", "61,06 %; scrap 7,01 %"],
    ["Producto 180 d", "PRD-012", "67,07 %; scrap 5,82 %"],
    ["Confiabilidad", "M-047", "6.473 min downtime; 141 fallas"],
    ["Energía", "P-SUR", "0,4400 kWh/unidad"],
]

T14 = [
    ["Microparada", "43.692", "109.020"],
    ["F-MEC", "867", "15.356"],
    ["F-ELE", "582", "10.546"],
    ["F-NEU", "388", "6.803"],
    ["F-HID", "339", "6.242"],
    ["AJUSTE", "241", "4.260"],
    ["DESCANSO", "28.080", "842.400"],
    ["CAM-PROD", "1.629", "49.150"],
    ["MANT-PREV", "227", "20.171"],
]

T15 = [
    ["M-047", "6.473", "141", "103", "1.178", "27,78", "3.007,6"],
    ["M-024", "3.634", "58", "48", "1.011", "68,40", "2.548,5"],
    ["M-049", "3.520", "72", "60", "905", "55,12", "2.280,4"],
    ["M-041", "3.434", "78", "67", "796", "50,95", "2.002,8"],
    ["M-015", "3.095", "30", "25", "968", "132,60", "2.433,4"],
    ["M-025", "2.609", "25", "22", "884", "159,51", "2.216,8"],
]

T16 = [
    ["Scrap Rate", "4,8411 %"],
    ["Unidades scrap", "684.643"],
    ["FPY", "97,6295 %"],
    ["Retrabajo", "335.248 unidades"],
    ["Scrap turno C", "5,2017 %"],
    ["Scrap PRD-012", "5,8240 %"],
    ["kWh por unidad buena", "0,340312"],
    ["P-SUR kWh/unidad", "0,440006"],
    ["Correlación scrap-energía", "0,4035"],
    ["Scrap con T > 85 °C", "5,43 % vs. 4,77 %"],
]

T17 = [
    ["Alertas", "3.284"],
    ["Críticas", "248"],
    ["Sin alerta", "24.572"],
    ["Alertas último turno", "13"],
    ["Validación KPI", "49/49"],
    ["Fórmulas SQL", "12/12"],
    ["Calidad IoT", "11/11"],
    ["Apertura DirectQuery", "35,46 s"],
    ["Filtro", "0,5 s"],
    ["Frescura", "0,35 s"],
]

T18 = [
    ["OEE", "78 % → 66 %", "78,02 % → 66,00 %"],
    ["Scrap", "3,8 % → 6,1 %", "3,66 % → 6,08 %"],
    ["Downtime no planificado", "+31 %", "+49,1 %"],
    ["Energía por unidad", "+14 %", "+12,2 %"],
    ["Pérdida mensual", "USD 540.000", "No recalculada"],
]

T19 = [
    ["Datos sintéticos", "No es telemetría real", "Declarado en 3.3"],
    ["Escenario calibrado", "Señal por diseño", "Discutido en 5.5"],
    ["ERP parcial", "Procedencia ambigua", "Limitación declarada"],
    ["Cadencia IoT", "2 lecturas/turno", "Gap declarado"],
    ["`unknown` no emitido", "Estado no explícito", "Brecha documentada"],
    ["FPY literal", "No es FPY clásico", "Definición alternativa"],
    ["Pareto sin línea en Power BI", "Lectura parcial", "Curva en el informe"],
    ["DirectQuery", "Apertura 35,46 s", "Umbral ≤ 60 s"],
    ["Sin implantación", "No prueba de producción", "Trabajo futuro"],
]

T20 = [
    ["A1 · Scrap P-SUR", "5,72 % scrap", "USD 366.240", "Media", "Alta"],
    ["A2 · Rendimiento P-SUR", "1.037.458 min perdidos", "USD 190.195", "Baja-media", "Alta"],
    ["A3 · M-047", "OEE 51,81 %", "USD 31.999", "Media", "Muy alta"],
    ["A4 · MTBF P-SUR", "66,86 h", "USD 41.382", "Media", "Alta"],
    ["A5 · Energía P-SUR", "0,4400 kWh/unidad", "USD 8.856", "Media-baja", "Media"],
]


def main():
    doc = Document(SRC)
    # Referencia: encabezado de Referencias.
    ref = None
    for p in doc.paragraphs:
        if p.style.name == "Heading 1" and p.text.startswith("8. Referencias"):
            ref = p
            break
    if ref is None:
        raise RuntimeError("No se encontró el encabezado de Referencias")

    # Eliminar el esqueleto 2-7.
    start = None
    for p in doc.paragraphs:
        if p.style.name == "Heading 1" and p.text.startswith("2. Marco teórico"):
            start = p
            break
    if start is None:
        raise RuntimeError("No se encontró el encabezado de Marco teórico")
    body = doc.element.body
    el = start._p
    while el is not None and el is not ref._p:
        nxt = el.getnext()
        body.remove(el)
        el = nxt
    # Referencias en página nueva.
    ref.paragraph_format.page_break_before = True

    w = Writer(doc, ref)

    # =====================================================================
    # 2. MARCO TEÓRICO
    # =====================================================================
    w.h("2. Marco teórico", 1)
    w.h("2.1 Business Intelligence: concepto y arquitectura", 2)
    w.p(
        "El Business Intelligence (BI) se entiende como el conjunto de procesos, tecnologías y prácticas "
        "que transforman datos dispersos en información útil para decidir. Curto Díaz (2010) lo describe "
        "como un ciclo que va de la extracción y transformación de datos a la exploración, el análisis y "
        "la difusión de indicadores; Howson (2008) añade que el éxito no depende solo de la herramienta, "
        "sino del patrocinio, la calidad del dato, la adopción y el gobierno del indicador. El caso MetalNova "
        "es un ejemplo de ese segundo plano: existen sensores, MES, CMMS y registros de calidad, pero cada "
        "área mide el OEE con supuestos distintos.",
    )
    w.p(
        "La arquitectura del prototipo sigue una lógica por capas: fuentes simuladas, aterrizaje y "
        "cuarentena, modelo dimensional, vistas KPI y capa de visualización. Esa separación permite que "
        "SQL, Python y Power BI compartan la misma definición y que la validación se haga una sola vez. "
        "La literatura de BI insiste en que la gobernanza del dato es tan importante como el tablero; por "
        "eso el informe dedica espacio a las reglas de calidad y a la reconciliación de cifras.",
    )

    w.h("2.2 OEE y las seis grandes pérdidas", 2)
    w.p(
        "El OEE (Overall Equipment Effectiveness) sintetiza la efectividad de un activo como el producto "
        "de disponibilidad, rendimiento y calidad. Nakajima (1988) lo popularizó en el marco del TPM; "
        "Muchiri y Pintelon (2008) sistematizan su cálculo y advierten que un OEE alto puede ocultar "
        "pérdidas específicas; Jonsson y Lesshammar (1999) y Dal et al. (2000) muestran que el indicador "
        "es útil para comparar y priorizar, pero no para explicar por sí solo la causa de la pérdida. "
        "La Tabla 2 resume las fórmulas adoptadas.",
    )
    w.table(
        "2",
        "Fórmulas y definiciones de KPI",
        ["KPI", "Fórmula", "Resultado global"],
        T2,
        [Inches(1.7), Inches(3.3), Inches(1.5)],
    )
    w.p(
        "El OEE se calcula como A × P × Q, pero sus componentes no se promedian: se suman numeradores y "
        "denominadores y se divide al final. Esa regla evita el error clásico de promediar porcentajes de "
        "máquinas con distinto tiempo planificado. El Loss Tree traduce cada componente a minutos "
        "equivalentes: la pérdida de disponibilidad es el downtime no planificado; la de rendimiento, la "
        "diferencia entre runtime y minutos ideales; la de calidad, el scrap multiplicado por el ciclo ideal.",
    )
    w.p(
        "Las seis grandes pérdidas —averías, preparación y ajustes, microparadas, velocidad reducida, "
        "defectos y arranque— se agrupan en las tres componentes. El prototipo conserva la distinción "
        "entre microparada y falla porque el promedio de downtime no distingue una parada breve frecuente "
        "de una avería larga. Esa distinción es clave para la lectura de confiabilidad del caso.",
    )

    w.h("2.3 TPM, mantenimiento y confiabilidad", 2)
    w.p(
        "El TPM busca involucrar a producción y mantenimiento en la disponibilidad del activo. Ahuja y "
        "Khamba (2008) documentan que los programas exitosos combinan mantenimiento autónomo, preventivo "
        "y mejora enfocada; Swanson (2001) relaciona las estrategias de mantenimiento con el desempeño. "
        "En el prototipo, el mantenimiento se observa con tres indicadores: MTBF, MTTR y tasa de fallas "
        "cortas. El MTBF resume el tiempo operativo entre fallas; el MTTR, el tiempo medio de reparación "
        "de las órdenes correctivas cerradas (ISO, 2016).",
    )
    w.p(
        "La confiabilidad no se agota en el MTBF. Una máquina puede tener un MTBF alto y, a la vez, muchas "
        "microparadas que no se registran como fallas formales. Por eso el informe usa microparadas por "
        "100 horas y fallas cortas por 100 horas, normalizadas por runtime. Esa decisión metodológica "
        "responde a una advertencia de la literatura: los promedios ocultan los patrones de falla breve.",
    )

    w.h("2.4 Calidad, rendimiento y energía", 2)
    w.p(
        "La calidad se mide con scrap rate y FPY. El scrap rate relaciona unidades rechazadas con unidades "
        "producidas; el FPY, las unidades que pasan sin retrabajo con las procesadas. La diferencia entre "
        "ambos no es semántica: una unidad defectuosa que no pasa por retrabajo puede quedar fuera del FPY "
        "o dentro, según la definición. El prototipo adopta la definición literal del caso —sin retrabajo— "
        "y documenta la brecha con la lectura clásica de “buenas de primera pasada”. La energía por unidad "
        "buena completa el cuadro: relaciona kWh con unidades buenas, no con unidades producidas, para no "
        "premiar el scrap (ISO, 2014a).",
    )

    w.h("2.5 Modelado dimensional y gobierno de KPIs", 2)
    w.p(
        "Kimball y Ross (2013) plantean que un modelo analítico debe organizarse por procesos de negocio, "
        "con hechos al grano más bajo posible y dimensiones conformadas que permitan cortar el indicador "
        "sin duplicar medidas. El prototipo sigue esa idea: cuatro hechos analíticos, dimensiones de planta, "
        "línea, máquina, producto, familia, turno, causa, tiempo y técnico, y un conjunto de vistas KPI que "
        "son el contrato único para SQL, Python y Power BI. Las jerarquías Planta → Línea → Máquina y "
        "Familia → Producto se resuelven sobre dimensiones, no sobre hechos.",
    )
    w.p(
        "Parmenter (2015) recuerda que un KPI debe ser medible, relevante y accionable; ISO 22400-2 (2014) "
        "aporta definiciones armonizadas para indicadores de operaciones. El prototipo combina ambas ideas: "
        "cada KPI tiene fórmula, dueño y uso, y cada alerta enlaza a un KPI de seguimiento. La agregación "
        "ponderada y el tratamiento explícito de `NULL` son parte del gobierno del indicador, no un detalle "
        "de implementación.",
    )

    w.h("2.6 Analítica descriptiva, diagnóstica y predictiva", 2)
    w.p(
        "El prototipo es descriptivo y diagnóstico: mide, descompone y prioriza; no entrena un modelo "
        "predictivo. Esa decisión es deliberada y se retoma en el trabajo futuro, cuando existan datos "
        "reales y un historial suficiente de fallas etiquetadas.",
    )
    w.p(
        "Witten y Frank (2005) ubican la preparación de datos y la selección de técnicas como etapas "
        "previas a cualquier modelo. El prototipo es descriptivo y diagnóstico: mide, descompone y prioriza; "
        "no entrena un modelo predictivo. Esa decisión es deliberada. Con datos sintéticos y 180 días, un "
        "modelo de mantenimiento predictivo sería una demostración de técnica, no una evidencia de valor. "
        "La analítica predictiva queda como trabajo futuro, cuando existan datos reales y un historial "
        "suficiente de fallas etiquetadas.",
    )

    w.h("2.7 IoT, Industria 4.0 y calidad de datos", 2)
    w.p(
        "Lee et al. (2015) describen la fábrica inteligente como un sistema ciberfísico que conecta "
        "sensores, máquinas y decisiones. Esa conexión introduce problemas que el tablero no puede ignorar: "
        "eventos duplicados, fuera de orden, tardíos, faltantes o con marcas de tiempo inválidas. Batini et al. "
        "(2009) y Wang y Strong (1996) muestran que la calidad del dato es multidimensional —exactitud, "
        "integridad, consistencia, temporalidad— y que no se resuelve solo con limpieza técnica.",
    )
    w.p(
        "El prototipo aplica una regla explícita: nunca se descarta un evento en silencio. Si está fuera de "
        "rango, va a cuarentena con motivo; si llega tarde o reordenado, se acepta con una marca; si falta "
        "una lectura, se declara el hueco. Esa trazabilidad es la que permite discutir la latencia y la "
        "cobertura sin inventar datos. La decisión de no aplicar *carry-forward* es conservadora: prefiere "
        "declarar el hueco antes que fabricar una lectura.",
    )

    w.h("2.8 Business Analysis y CRISP-DM", 2)
    w.p(
        "El BABOK aporta el análisis de negocio —stakeholders, requisitos y criterios de evaluación— y "
        "CRISP-DM ordena el ciclo analítico. El proyecto los combinó con una disciplina de especificación "
        "y verificación para que cada requisito tuviera evidencia.",
    )
    w.p(
        "El BABOK (IIBA, 2015) aporta el enfoque de análisis de negocio: identificar stakeholders, "
        "necesidades, requisitos y criterios de evaluación de la solución. CRISP-DM (Wirth y Hipp, 2000) "
        "ordena el trabajo analítico en comprensión del negocio, comprensión de los datos, preparación, "
        "modelado, evaluación y despliegue. El proyecto combinó ambos marcos con una disciplina de "
        "especificación (spec → plan → tasks → verification), de modo que cada requisito del caso tuviera "
        "una evidencia verificable.",
    )

    w.h("2.9 Síntesis y marco conceptual", 2)
    w.p(
        "La literatura ofrece piezas separadas: OEE y TPM para la efectividad, confiabilidad para el "
        "mantenimiento, modelado dimensional para el dato, BI para la entrega y calidad de datos para la "
        "confianza. El vacío que atiende este trabajo es la integración de esas piezas en un prototipo "
        "único, reproducible y orientado a la priorización. La Tabla 3 resume la síntesis y la Figura 2 "
        "presenta el marco conceptual adoptado.",
    )
    w.table(
        "3",
        "Síntesis de literatura y vacíos",
        ["Enfoque", "Autores", "Aporte", "Vacío que atiende el prototipo"],
        T3,
        [Inches(1.2), Inches(2.4), Inches(1.6), Inches(1.3)],
    )
    w.figure("2", "Marco conceptual del OEE y las pérdidas", "figura2_marco_conceptual.png", width=5.6)

    # =====================================================================
    # 3. METODOLOGÍA
    # =====================================================================
    w.h("3. Metodología experimental", 1)
    w.h("3.1 Diseño de la investigación", 2)
    w.p(
        "La investigación es aplicada, cuantitativa, longitudinal y no experimental. Se estudia un caso "
        "con unidades embebidas —plantas, líneas, máquinas, turnos y productos— durante 180 días. No hay "
        "asignación aleatoria ni grupo de control: el objetivo es describir, diagnosticar y priorizar, no "
        "probar una hipótesis causal. El diseño combina las fases de CRISP-DM con la disciplina de "
        "especificación del proyecto y culmina en una demo reproducible.",
    )
    w.figure("3", "Fases del diseño metodológico", "figura3_fases_metodologicas.png", width=5.6)
    w.h("3.2 Caso y unidad de análisis", 2)
    w.p(
        "La unidad de análisis es la combinación máquina-turno-día; el período es 2026-04-22 a 2026-10-18. "
        "El universo es un censo sintético de 3 plantas, 6 líneas, 52 máquinas y 28.080 combinaciones "
        "máquina-turno-día. No se trabaja con una muestra: se analiza el conjunto completo generado. Las "
        "unidades de observación secundarias son la planta, la línea, el turno, el producto y la causa de "
        "parada, que permiten descomponer el OEE sin cambiar la fórmula.",
    )

    w.h("3.3 Fuentes de datos y generación", 2)
    w.p(
        "Las fuentes simuladas son IoT/SCADA, MES, CMMS, calidad y calendario de turnos; el ERP existe "
        "solo como dimensión de órdenes y productos. La Tabla 4 resume la fuente de verdad de cada dato. "
        "Los datos son sintéticos: se generaron con semilla 42, 180 días y un escenario calibrado para que "
        "la señal del caso fuera visible; no son telemetría real ni una implantación en MetalNova.",
    )
    w.table(
        "4",
        "Fuentes de datos y fuente de verdad",
        ["Fuente", "Datos", "Fuente de verdad", "Uso"],
        T4,
        [Inches(1.1), Inches(1.9), Inches(2.3), Inches(1.2)],
    )
    w.p(
        "La calibración aplicó factores por planta y perfiles persistentes de máquina. Siete máquinas "
        "quedaron como outliers: M-047 como crítica, M-049/M-040/M-024/M-015 como desgastadas, M-032 como "
        "problema de calidad y M-005 como problema energético. Esa decisión se documentó antes de generar "
        "los datos y se declaró como escenario, no como hallazgo. El histórico se generó en streaming y se "
        "cargó por lotes con `COPY` y `ON CONFLICT`, lo que mantuvo el pico de memoria en ~43 MB durante "
        "la generación y ~63 MB durante la carga.",
    )
    w.p(
        "La ingesta continua simulada emite eventos por transición, no snapshots por minuto. Cada ciclo se "
        "alinea a una rejilla temporal y las decisiones se derivan de una semilla; los identificadores son "
        "estables y la inserción es idempotente. Esa decisión reduce el volumen y permite medir latencia de "
        "pipeline sin inflar la base. La latencia observada fue de 0,7 a 54,9 ms, muy por debajo del "
        "objetivo de 10 minutos.",
    )

    w.h("3.4 Modelo dimensional", 2)
    w.p(
        "El modelo tiene cuatro hechos analíticos —producción, parada, mantenimiento y calidad— y dos "
        "capas crudas —evento y evento rechazado—. Las dimensiones conformadas son planta, línea, máquina, "
        "familia, producto, turno, causa, técnico, tiempo y orden. La Tabla 5 resume el grano y el volumen. "
        "La jerarquía Planta → Línea → Máquina se resuelve en `v_dim_maquina`; Familia → Producto, en "
        "`v_dim_producto`. El drill-down se hace sobre dimensiones, nunca duplicando medidas.",
    )
    w.table(
        "5",
        "Hechos, dimensiones y granularidad",
        ["Tabla", "Grano", "Filas"],
        T5,
        [Inches(2.3), Inches(3.2), Inches(1.0)],
    )
    w.figure("4", "Modelo dimensional en estrella", "figura5_modelo_estrella.png", width=5.6)
    w.p(
        "La integridad se declaró con claves primarias y foráneas, restricciones de no negatividad y "
        "`fin >= inicio`. Se evitó mezclar eventos crudos con agregados y se documentó el grano de cada "
        "tabla. Las 27 relaciones del modelo semántico son hecho → dimensión; no hay relaciones hecho-hecho. "
        "Esa estructura es la que permite que un mismo KPI se filtre por planta, línea, máquina, producto "
        "o turno sin redefinirse.",
    )

    w.h("3.5 Arquitectura y decisiones tecnológicas", 2)
    w.p(
        "La arquitectura se eligió para cumplir tres restricciones: ejecución local, reproducibilidad y "
        "volumen manejable en 8 GB. PostgreSQL 16.4 en Docker aporta SQL analítico, vistas y restricciones "
        "de integridad; Docker Compose aísla los servicios y publica solo en loopback; Python 3.13 en "
        "contenedor genera, carga, simula y valida; Power BI Desktop consume las vistas por DirectQuery. "
        "La Figura 5 resume el flujo.",
    )
    w.figure("5", "Arquitectura de componentes", "figura4_arquitectura.png", width=5.6)
    w.p(
        "Las alternativas se evaluaron antes de fijar el stack. Se descartó PostgreSQL nativo por "
        "fragilidad del entorno; la nube, por la restricción de demo sin internet; Import, porque DirectQuery "
        "cumplió los umbrales (apertura 35,46 s, filtro ~0,5 s, frescura 0,35 s); Parquet, para no añadir "
        "`pyarrow`; y una API REST o una aplicación web, porque el alcance era un prototipo analítico local. "
        "El modelo TMDL y las páginas PBIR se generan por código y se validan antes de abrir Power BI.",
    )
    w.p(
        "La consecuencia práctica es que el prototipo no es una aplicación de producción: es un banco de "
        "trabajo analítico. Esa decisión reduce el riesgo de la demo y permite repetirla con los mismos "
        "datos, la misma semilla y las mismas vistas. Para una implantación real habría que añadir "
        "seguridad, orquestación, monitoreo y gobierno del dato.",
    )

    w.h("3.6 Calidad y temporalidad IoT", 2)
    w.p(
        "Las reglas de calidad se aplican antes de insertar. La Tabla 6 resume el tratamiento. Los "
        "duplicados se resuelven por clave estable; los eventos fuera de rango van a cuarentena con motivo; "
        "los tardíos y reordenados se aceptan con marcas en `payload.calidad`; los faltantes se declaran en "
        "`v_calidad_senal_iot`; los solapes se consolidan en `v_parada_consolidada`. Nunca se descarta un "
        "evento en silencio.",
    )
    w.table(
        "6",
        "Reglas de calidad y temporalidad IoT",
        ["Problema", "Regla", "Evidencia"],
        T6,
        [Inches(1.3), Inches(3.6), Inches(1.6)],
    )
    w.p(
        "La vista de señal reporta 9.360 filas máquina-día, 52 máquinas y un `max_gap_min` de 210 minutos. "
        "El feed sintético emite dos lecturas por turno, no una cada 15 minutos; por eso la cadencia ideal "
        "se informa como diagnóstico y no se usa para inventar lecturas. El estado `unknown` no se emite: "
        "el hueco se declara como `incompleta` o `sin_datos`. Es una brecha conocida y documentada.",
    )

    w.h("3.7 Operacionalización de KPIs", 2)
    w.p(
        "Los KPIs se calcularon en vistas SQL y se replicaron en DAX para el tablero. La regla de "
        "agregación es `SUM(numerador) / SUM(denominador)`; nunca se promedian porcentajes. Las razones "
        "con denominador cero devuelven `NULL`, no cero, para distinguir “no definido” de un valor real. "
        "Los casos borde —máquina sin producción, turno sin fallas, período incompleto— se probaron de "
        "forma explícita.",
    )
    w.p(
        "El FPY se implementó como `(inspeccionadas − retrabajo) / inspeccionadas`. Esa definición es "
        "literal respecto del caso, pero no equivale a la lectura clásica de “buenas de primera pasada”; "
        "por eso el informe reporta también la calidad (good/total) y explica la diferencia. El MTTR se "
        "acotó a órdenes correctivas cerradas; las preventivas no se cuentan como reparación. El downtime "
        "no planificado se calcula sobre tiempo planificado, no sobre tiempo calendario.",
    )

    w.h("3.8 Construcción del tablero y regla de alerta", 2)
    w.p(
        "El tablero tiene cuatro páginas principales —Executive Plant Performance, OEE & Loss Tree, "
        "Maintenance Reliability y Quality & Energy— y cuatro páginas de apoyo: detalle de máquina, "
        "detalle de causa, tooltip y validación. Cada página principal tiene seis slicers sincronizados "
        "(fecha, planta, línea, máquina, producto y turno). El drill-through de máquina y de causa, y el "
        "tooltip con MTBF, MTTR y última intervención, se probaron en Power BI Desktop.",
    )
    w.p(
        "La alerta de máquina crítica se evalúa por máquina, turno y día. Se emite si se cumple al menos "
        "una condición y es crítica si se cumplen dos o más. La Tabla 7 resume umbrales, acciones y "
        "responsables. La regla vive en una vista SQL para que sea idéntica en Python y en Power BI; la "
        "tabla del informe consume `v_alerta_ultimo_turno` para no depender de filtros visuales.",
    )
    w.table(
        "7",
        "Regla de excepción de máquina crítica",
        ["Condición", "Umbral", "Acción", "Responsable"],
        T7,
        [Inches(1.4), Inches(1.6), Inches(2.3), Inches(1.2)],
    )

    w.h("3.9 Validación y reproducibilidad", 2)
    w.p(
        "La validación no se apoya en la apariencia del tablero. Se recalcularon los KPI desde los hechos "
        "con un script independiente, se ejecutaron comprobaciones SQL, se validó la calidad IoT, se "
        "verificó el histórico y se validaron el modelo TMDL y las páginas PBIR. La Tabla 8 resume las "
        "pruebas. La reproducibilidad se comprobó regenerando los seis CSV con la misma semilla: el "
        "SHA-256 fue idéntico y el `run_id` coincidió.",
    )
    w.table(
        "8",
        "Estrategia de validación y evidencias",
        ["Prueba", "Comando", "Resultado"],
        T8,
        [Inches(1.5), Inches(2.9), Inches(2.1)],
    )

    w.h("3.10 Consideraciones éticas", 2)
    w.p(
        "El trabajo usa datos sintéticos, no contiene datos personales ni credenciales, y no atribuye "
        "causalidad a relaciones que solo son descriptivas. Los costos y ahorros son supuestos declarados; "
        "no se presentan como resultados de una empresa real. La documentación y los scripts permiten "
        "repetir el análisis, lo que reduce el riesgo de afirmaciones no verificadas. Estas precauciones "
        "son parte del diseño, no un añadido al final.",
    )

    # =====================================================================
    # 4. RESULTADOS
    # =====================================================================
    w.h("4. Análisis y resultados", 1)
    w.h("4.1 Volumen y calidad de los datos", 2)
    w.p(
        "El corte contiene 401.838 eventos de origen, de los cuales 343.050 son eventos de máquina "
        "(IoT/SCADA). La base cubre 180 días, 52 máquinas, 28.080 órdenes, 76.045 paradas, 2.628 "
        "mantenimientos y 28.080 inspecciones. La Tabla 9 resume el volumen. La cobertura es completa: "
        "las 52 máquinas tienen producción y eventos, y las tres plantas están representadas.",
    )
    w.table(
        "9",
        "Volumen y cobertura de datos",
        ["Indicador", "Valor"],
        T9,
        [Inches(3.2), Inches(3.1)],
    )
    w.p(
        "La calidad de los datos es razonable para un prototipo: no hay duplicados por clave estable, hay "
        "dos eventos en cuarentena (uno por timestamp futuro y otro por timestamp anterior al rango), un "
        "evento tardío y uno reordenado. La vista de señal cubre 9.360 filas máquina-día, con un gap máximo "
        "de 210 minutos. La limitación es conocida: el feed emite dos lecturas por turno y el estado "
        "`unknown` no se emite; el hueco se declara.",
    )

    w.h("4.2 OEE global y evolución", 2)
    w.p(
        "El OEE global de los 180 días es 71,9645 %, con disponibilidad 98,7918 %, rendimiento 76,5505 % "
        "y calidad 95,1589 %. En ventanas de 30 días, el OEE cae de 78,0226 % a 65,9961 %, una reducción de "
        "12,03 puntos porcentuales. La mayor caída está en rendimiento (−10,47 pp), seguida de calidad "
        "(−2,43 pp); la disponibilidad apenas baja 0,48 pp. La Tabla 10 resume los KPIs globales y la "
        "Tabla 11 descompone las ventanas; la Figura 6 compara los componentes.",
    )
    w.table(
        "10",
        "KPIs globales del período",
        ["KPI", "Valor"],
        T10,
        [Inches(3.0), Inches(3.3)],
    )
    w.table(
        "11",
        "OEE y A/P/Q en ventanas de 30 días",
        ["Ventana", "A %", "P %", "Q %", "OEE %", "Scrap %", "kWh/unidad"],
        T11,
        [Inches(1.3), Inches(0.8), Inches(0.8), Inches(0.8), Inches(0.9), Inches(0.9), Inches(1.0)],
    )
    w.figure("6", "OEE y componentes en ventanas de 30 días", "figura6_oee_componentes.png", width=5.6)
    w.p(
        "La caída no es un problema de disponibilidad. El prototipo mantiene la disponibilidad por encima "
        "de 98 % en casi todo el período; lo que se deteriora es la velocidad y, en menor medida, la "
        "calidad. Esa lectura contradice la atribución inicial del caso —producción culpa a mantenimiento— "
        "y desplaza la discusión hacia el rendimiento, los cambios de producto y las microparadas.",
    )

    w.h("4.3 Loss Tree", 2)
    w.p(
        "El Loss Tree traduce las pérdidas a minutos equivalentes. La pérdida total es 3.528.469,08 min; "
        "el rendimiento aporta 2.911.218,08 min (82,51 %), la calidad 465.420 min (13,19 %) y la "
        "disponibilidad 151.831 min (4,30 %). La pérdida de rendimiento es 19,2 veces la de disponibilidad. "
        "En unidades, el prototipo estima 4.269.957 unidades no producidas y 684.643 unidades scrap.",
    )
    w.table(
        "12",
        "Loss Tree global",
        ["Componente", "Minutos equivalentes", "Participación"],
        T12,
        [Inches(2.0), Inches(2.6), Inches(1.7)],
    )
    w.figure("7", "Loss Tree global", "figura7_loss_tree.png", width=5.6)
    w.p(
        "El resultado es consistente con la caída del OEE: el rendimiento explica la mayor parte de la "
        "pérdida, no las paradas. Sin embargo, el Loss Tree no identifica por sí solo la causa raíz de la "
        "pérdida de velocidad; para eso se necesita el análisis por activo, turno, producto y causa que se "
        "presenta en las secciones siguientes.",
    )

    w.h("4.4 Focos por planta, línea, máquina, turno y producto", 2)
    w.p(
        "La Tabla 13 resume los focos. P-SUR es la planta con peor OEE (62,04 % en 30 días; 67,73 % en "
        "180 días), L3-2 la peor línea (60,98 %) y M-047 la peor máquina (47,47 % en 30 días; 51,81 % en "
        "180 días). El turno C de M-047 es el peor (45,33 %). En producto, PRD-009 es el peor en 30 días "
        "(61,06 %, scrap 7,01 %) y PRD-012 el peor en 180 días (67,07 %, scrap 5,82 %).",
    )
    w.table(
        "13",
        "Focos por planta, línea, máquina, turno y producto",
        ["Ámbito", "Valor", "OEE / dato"],
        T13,
        [Inches(1.5), Inches(1.4), Inches(3.4)],
    )
    w.p(
        "Hay una cautela importante: en el escenario calibrado cada planta produce una sola familia "
        "(P-SUR → FAM-TRA, P-CENTRO → FAM-SUS, P-NORTE → FAM-FRE). El efecto producto está confundido con "
        "el efecto planta; no se puede atribuir la pérdida a un producto separándolo de su planta. Los "
        "productos de FAM-TRA son los peores porque son los de P-SUR, no porque el producto sea "
        "independientemente el causante.",
    )

    w.h("4.5 Causas de parada", 2)
    w.p(
        "La microparada es la causa no planificada dominante por frecuencia y por tiempo: 43.692 eventos y "
        "109.020 minutos. La falla mecánica F-MEC es la principal falla formal: 867 eventos y 15.356 min. "
        "Le siguen F-ELE (582 eventos; 10.546 min), F-NEU (388; 6.803), F-HID (339; 6.242) y AJUSTE (241; "
        "4.260). Las paradas planificadas —descanso, cambio de producto y mantenimiento preventivo— se "
        "excluyen de la disponibilidad. La Tabla 14 y la Figura 8 presentan el Pareto.",
    )
    w.table(
        "14",
        "Downtime por causa",
        ["Causa", "Eventos", "Minutos"],
        T14,
        [Inches(2.2), Inches(1.7), Inches(2.0)],
    )
    w.figure("8", "Pareto de downtime no planificado", "figura8_pareto.png", width=5.6)
    w.p(
        "El Pareto muestra que las microparadas explican la mayor parte del tiempo no planificado, pero "
        "no la mayor parte de la pérdida de OEE. Esa distinción es central: la disponibilidad solo pierde "
        "151.831 min, mientras que el rendimiento pierde 2.911.218 min. Las paradas son visibles y "
        "accionables, pero no son el driver principal de la caída.",
    )

    w.h("4.6 Confiabilidad", 2)
    w.p(
        "El MTBF global es 85,6078 h y el MTTR 17,8392 min; se registran 2.417 fallas, 43.692 microparadas "
        "y 2.115 fallas cortas. M-047 concentra el peor perfil: 6.473 min de downtime, 141 fallas, 103 "
        "fallas cortas, 1.178 microparadas y un MTBF de 27,78 h. M-024, M-049 y M-041 también combinan "
        "downtime y fallas cortas. M-015 y M-025 tienen MTBF alto (132,60 h y 159,51 h), pero tasas de "
        "microparadas altas (2.433 y 2.217 por 100 h). La Tabla 15 y la Figura 9 muestran el contraste.",
    )
    w.table(
        "15",
        "Perfiles de confiabilidad",
        ["Máquina", "Downtime", "Fallas", "F. cortas", "Microparadas", "MTBF (h)", "Micro/100 h"],
        T15,
        [Inches(0.9), Inches(0.9), Inches(0.7), Inches(0.8), Inches(1.1), Inches(0.8), Inches(0.9)],
    )
    w.figure("9", "Confiabilidad: downtime vs. microparadas", "figura9_confiabilidad.png", width=5.6)
    w.p(
        "El promedio oculta dos fenómenos distintos. M-047 es un caso de degradación integral: alto "
        "downtime, muchas fallas cortas y muchas microparadas. M-015 y M-025 son casos de fallas breves "
        "frecuentes con MTBF alto: si solo se mirara el MTBF, parecerían confiables. Por eso el informe "
        "incluye microparadas y fallas cortas por 100 horas, normalizadas por runtime.",
    )

    w.h("4.7 Calidad y energía", 2)
    w.p(
        "El scrap global es 4,8411 % (684.643 unidades) y el FPY 97,6295 %. El turno C tiene el mayor "
        "scrap relativo (5,2017 %) y PRD-012 el mayor scrap por producto (5,8240 %). La energía por unidad "
        "buena es 0,340312 kWh; P-SUR llega a 0,440006 kWh, un 50 % más que P-NORTE. La correlación "
        "descriptiva entre scrap y energía es 0,4035; el scrap en días con temperatura máxima superior a "
        "85 °C es 5,43 %, frente a 4,77 % en días por debajo del umbral. La Tabla 16 resume los indicadores.",
    )
    w.table(
        "16",
        "Calidad y energía",
        ["Indicador", "Valor"],
        T16,
        [Inches(3.2), Inches(3.1)],
    )
    w.p(
        "Estas relaciones son descriptivas, no causales. El producto, la planta y el turno están "
        "correlacionados; la temperatura se midió con dos a cinco lecturas por turno, no con una serie "
        "continua. El cambio de producto, medido en el histórico, muestra 4,87 % de scrap con cambio frente "
        "a 4,84 % sin cambio: una diferencia de 0,03 pp, insuficiente para sostener una asociación material. "
        "El informe no afirma que el turno, el producto o la temperatura sean la causa del scrap.",
    )

    w.h("4.8 Alertas de máquina crítica", 2)
    w.p(
        "La regla generó 3.284 alertas, 248 críticas y 24.572 registros sin alerta sobre 28.104 filas "
        "máquina-turno-día; 13 alertas corresponden al último turno por máquina. Un caso crítico es M-015, "
        "turno C del 2026-10-18: OEE 52,63 %, MTBF 7,00 h, temperatura máxima 79,29 °C y 30 min de "
        "downtime; cumple OEE bajo y MTBF bajo. Otro es M-028, turno C: OEE 61,57 %, MTBF 7,32 h, "
        "temperatura 88,19 °C y 11 min de downtime; cumple MTBF bajo y temperatura alta. La Tabla 17 "
        "resume alertas, validación y desempeño.",
    )
    w.table(
        "17",
        "Alertas, validación y desempeño",
        ["Indicador", "Valor"],
        T17,
        [Inches(3.2), Inches(3.1)],
    )
    w.p(
        "La alerta es accionable porque cada condición tiene umbral, acción, responsable y KPI de "
        "seguimiento. La tabla del informe muestra severidad, OEE, MTBF, temperatura y acción sugerida; "
        "la vista SQL conserva además responsable y KPI. La temperatura es una aproximación por muestreo, "
        "no una medición continua; esa limitación se declara.",
    )

    w.h("4.9 Tablero", 2)
    w.p(
        "El tablero tiene cuatro páginas principales y cuatro de apoyo. Las páginas principales cubren "
        "ejecución, OEE y Loss Tree, mantenimiento y calidad/energía; las de apoyo permiten drill-through "
        "a máquina y causa, tooltip de confiabilidad y validación del modelo. La Figura 10 presenta una "
        "vista integrada; las capturas completas están en el Anexo D. La navegación se probó en Power BI "
        "Desktop el 2026-10-23.",
    )
    w.figure(
        "10",
        "Vista integrada de las cuatro páginas del tablero",
        "figura10_panel_integrado.png",
        "Capturas de Power BI Desktop, 2026-10-23. La barra amarilla y el panel de filtros son parte de la interfaz.",
        width=5.6,
    )

    w.h("4.10 Validación y desempeño", 2)
    w.p(
        "Las comprobaciones principales dieron 49/49 en Python, 12/12 en fórmulas SQL, 11/11 en calidad "
        "IoT y 5/5 en la validación SQL de IoT; el histórico dio 17/17 y la calibración 7/7. El modelo "
        "semántico tiene 70 medidas, 27 relaciones y 15 tablas; el informe tiene 8 páginas y 105 visuales, "
        "sin errores de referencia. En DirectQuery, la apertura medida fue 35,46 s, el cambio de filtro "
        "~0,5 s y la frescura 0,35 s, dentro de los umbrales acordados.",
    )

    w.h("4.11 Priorización económica", 2)
    w.p(
        "Con los supuestos declarados —USD 220 por hora-máquina, USD 18 por unidad rechazada y USD 0,12 "
        "por kWh— el plan prioriza cinco acciones. A1, reducir el scrap de P-SUR, tiene el mayor impacto "
        "hipotético (USD 366.240/180 d); A2, recuperar rendimiento en P-SUR, USD 190.195; A4, elevar el "
        "MTBF de P-SUR, USD 41.382; A3, intervenir M-047, USD 31.999; y A5, eficiencia energética, USD "
        "8.856. Los ahorros no se suman porque las acciones se solapan. La Tabla 20 de la sección 7 "
        "detalla responsable, KPI y criticidad.",
    )

    # =====================================================================
    # 5. DISCUSIÓN
    # =====================================================================
    w.h("5. Discusión", 1)
    w.h("5.1 Rendimiento vs. disponibilidad", 2)
    w.p(
        "El hallazgo central es que la caída del OEE es, sobre todo, una pérdida de rendimiento. La "
        "disponibilidad se mantiene en 98,55 % al cierre y solo pierde 0,48 pp; el rendimiento pierde "
        "10,47 pp. Esa diferencia reorienta la discusión del caso: el problema no es solo “parar”, sino "
        "perder velocidad y unidades. La atribución de producción a mantenimiento, y de mantenimiento a "
        "los cambios de producto y microparadas, es parcial: ambos fenómenos existen, pero ninguno explica "
        "por sí solo la mayor parte de la pérdida.",
    )
    w.p(
        "La literatura sobre OEE advierte que el indicador es un punto de partida, no un diagnóstico "
        "(Muchiri y Pintelon, 2008; Jonsson y Lesshammar, 1999). El Loss Tree confirma esa advertencia: "
        "el rendimiento aporta 82,51 % de los minutos perdidos, la calidad 13,19 % y la disponibilidad "
        "4,30 %. Sin la descomposición, la organización habría concentrado sus esfuerzos en el downtime "
        "visible y habría dejado intacta la mayor fuente de pérdida.",
    )

    w.h("5.2 Microparadas y fallas cortas", 2)
    w.p(
        "Las microparadas son la causa no planificada más frecuente y acumulada: 43.692 eventos y 109.020 "
        "min. Sin embargo, su aporte directo al OEE es de disponibilidad, y la disponibilidad solo pierde "
        "151.831 min. La paradoja de M-015 y M-025 —MTBF alto, microparadas frecuentes— muestra que el "
        "promedio de confiabilidad puede ocultar un problema de velocidad. Esas máquinas no destacan en "
        "downtime, pero sí en microparadas por 100 h.",
    )
    w.p(
        "M-047 es el caso opuesto: aparece en todos los promedios porque combina alto downtime, muchas "
        "fallas cortas y muchas microparadas. La lección metodológica es que la confiabilidad debe mirarse "
        "con al menos dos lentes: el MTBF para fallas formales y las tasas por 100 h para fallas breves. "
        "El tablero incluye ambas para no premiar a una máquina que solo tiene fallas cortas.",
    )

    w.h("5.3 Calidad y causalidad", 2)
    w.p(
        "El scrap se asocia descriptivamente con el turno C, con los productos de FAM-TRA y con la "
        "energía/temperatura. Pero el producto está confundido con la planta: cada planta produce una sola "
        "familia. El cambio de producto muestra una diferencia de 0,03 pp, insuficiente para sostener una "
        "asociación material. La correlación scrap-energía (0,4035) y la diferencia entre días con "
        "temperatura alta (5,43 % vs. 4,77 %) son señales para investigar, no pruebas de causalidad.",
    )
    w.p(
        "El informe evita la trampa de convertir una asociación en una recomendación causal. La acción A1 "
        "—reducir el scrap de P-SUR— se justifica por el volumen y el costo, no porque se haya demostrado "
        "que el turno o el producto sean la causa. Esa distinción es importante para no prometer un ahorro "
        "que dependa de una relación no verificada.",
    )

    w.h("5.4 Del dato al dinero", 2)
    w.p(
        "La valorización usa tres supuestos: USD 220/hora-máquina, USD 18/unidad rechazada y USD 0,12/kWh. "
        "No son costos de MetalNova; son supuestos del prototipo. Cambiarlos cambia el ranking económico, "
        "aunque la prioridad operacional se mantiene. La pérdida observada —USD 10,67 M por rendimiento, "
        "USD 0,56 M por disponibilidad y USD 12,32 M por scrap en 180 días— no es un ahorro; es una "
        "magnitud de la pérdida si se valorizara completa.",
    )
    w.p(
        "El plan de mejora usa metas parciales y conservadoras: 10 % de reducción de scrap, 5 % de "
        "recuperación de rendimiento, MTBF objetivo global y 5 % de ahorro energético. Los ahorros no se "
        "suman porque las acciones se solapan: menos fallas también reduce downtime y energía. El orden es "
        "una guía, no una suma lineal.",
    )

    w.h("5.5 Contraste con el caso y la literatura", 2)
    w.p(
        "La Tabla 18 compara el caso con el prototipo. El OEE y el scrap coinciden casi exactamente porque "
        "el escenario fue calibrado; el downtime relativo (+49,1 %) supera el +31 % del caso y la energía "
        "(+12,2 %) queda cerca del +14 %. La coincidencia del OEE no es un hallazgo empírico: es el "
        "resultado de un escenario diseñado para producir señal. Esa transparencia es indispensable para "
        "no presentar datos sintéticos como telemetría real.",
    )
    w.table(
        "18",
        "Comparación caso vs. prototipo",
        ["Indicador", "Caso", "Prototipo"],
        T18,
        [Inches(2.4), Inches(2.0), Inches(2.1)],
    )
    w.p(
        "La literatura ayuda a leer las diferencias. Howson (2008) insistiría en la adopción y el gobierno "
        "del dato; Kimball y Ross (2013), en la consistencia del modelo; Muchiri y Pintelon (2008), en no "
        "reificar el OEE. El prototipo responde a esas preocupaciones con un contrato único de KPI, "
        "agregación ponderada y validación independiente. Lo que no puede resolver es la ausencia de datos "
        "reales ni la validez externa del escenario.",
    )

    w.h("5.6 Limitaciones y amenazas a la validez", 2)
    w.p(
        "Las limitaciones se resumen en la Tabla 19. La principal es el uso de datos sintéticos: el "
        "escenario fue calibrado para que la señal existiera y no representa una fábrica real. Otras son "
        "el ERP parcial, la cadencia IoT de dos lecturas por turno, el estado `unknown` no emitido, la "
        "definición literal de FPY, el Pareto sin línea acumulada en Power BI y la ausencia de una "
        "implantación en producción. Ninguna invalida el prototipo como demostración metodológica, pero "
        "todas acotan sus conclusiones.",
    )
    w.table(
        "19",
        "Limitaciones y amenazas a la validez",
        ["Limitación", "Efecto", "Mitigación"],
        T19,
        [Inches(1.7), Inches(2.3), Inches(2.3)],
    )
    w.p(
        "La validez interna se apoya en la validación independiente y en la reproducibilidad; la validez "
        "de constructo, en la definición explícita de cada KPI; la validez externa es la más débil, porque "
        "el escenario es sintético y calibrado. La conclusión no es “esto es lo que pasa en MetalNova”, "
        "sino “así se puede medir y priorizar con un conjunto de datos comparable”.",
    )

    w.h("5.7 Implicaciones", 2)
    w.p(
        "Para MetalNova, la implicación es que el debate debe moverse del downtime al rendimiento y a la "
        "calidad, sin abandonar las microparadas. Para una implantación real, se necesita datos reales, "
        "ERP etiquetado, mayor cadencia IoT, validación de costos, gobierno del dato y un despliegue "
        "controlado. El prototipo no reemplaza esas condiciones; las hace visibles.",
    )

    # =====================================================================
    # 6. CONCLUSIONES
    # =====================================================================
    w.h("6. Conclusiones", 1)
    w.h("6.1 Respuesta a la pregunta principal", 2)
    w.p(
        "La caída del OEE se explica principalmente por la pérdida de rendimiento, no por la "
        "disponibilidad. El Loss Tree muestra 2.911.218 min de pérdida de rendimiento (82,51 %) frente a "
        "151.831 min de disponibilidad (4,30 %) y 465.420 min de calidad (13,19 %). Los activos y turnos "
        "que concentran el deterioro son P-SUR, la línea L3-2, la máquina M-047 y el turno C; en producto, "
        "PRD-009 es el peor del último mes, con la cautela de que producto y planta están confundidos. Las "
        "causas no planificadas más relevantes son las microparadas (43.692 eventos; 109.020 min) y la "
        "falla mecánica F-MEC (867; 15.356 min). El impacto asciende a 4.269.957 unidades potenciales no "
        "producidas y 684.643 unidades scrap en 180 días.",
    )
    w.h("6.2 Cumplimiento de objetivos", 2)
    w.p(
        "El objetivo general se cumplió: el prototipo mide el OEE con una definición única, localiza "
        "pérdidas y prioriza acciones. Los objetivos específicos también se cumplieron: modelo dimensional, "
        "pipeline histórico y continuo, diez KPIs validados, tablero con navegación, análisis de pérdidas "
        "y plan de mejora. La matriz de aceptación del Anexo C resume la evidencia y los matices.",
    )
    w.h("6.3 Hallazgos principales", 2)
    for text in [
        "La pérdida de rendimiento es 82,51 % del total; la disponibilidad solo 4,30 %.",
        "P-SUR, L3-2, M-047 y el turno C concentran el deterioro; M-047 tiene OEE 51,81 % en 180 días.",
        "Las microparadas son la causa no planificada más frecuente, pero no explican la mayor parte de la pérdida de OEE.",
        "M-015 y M-025 tienen MTBF alto y microparadas frecuentes: el promedio de confiabilidad oculta.",
        "El scrap se asocia descriptivamente con turno, producto y energía/temperatura, sin causalidad demostrada.",
        "El prototipo valida 49/49 KPI, 11/11 IoT y 12/12 fórmulas SQL; la latencia y la frescura cumplen.",
    ]:
        w.bullet(text)
    w.h("6.4 Aportes del trabajo", 2)
    w.p(
        "El aporte principal es metodológico: un contrato único de KPI, una capa de calidad de eventos, "
        "un Loss Tree priorizable y una disciplina de verificación. El aporte práctico es un tablero "
        "navegable y un plan de mejora con supuestos explícitos. El aporte académico es una lectura crítica "
        "del OEE que distingue lo observado de lo hipotético y lo sintético de lo real.",
    )
    w.h("6.5 Trabajo futuro", 2)
    w.p(
        "Quedan tres frentes: validar el prototipo con datos reales y un ERP etiquetado; ampliar la "
        "cadencia IoT y emitir el estado `unknown`; y explorar mantenimiento predictivo con datos "
        "suficientes. También se puede profundizar en la relación entre cambios de producto, velocidad y "
        "scrap con un diseño que separe el efecto planta del efecto producto.",
    )

    # =====================================================================
    # 7. RECOMENDACIONES
    # =====================================================================
    w.h("7. Recomendaciones", 1)
    w.h("7.1 Acciones operativas priorizadas", 2)
    w.p(
        "La Tabla 20 resume las cinco acciones. El orden combina impacto económico hipotético y "
        "criticidad operacional. A1 y A2 son las palancas principales; A3 sube por la criticidad de M-047; "
        "A4 sostiene la confiabilidad; A5 es mejora continua. Los ahorros no se suman porque las acciones "
        "se solapan.",
    )
    w.table(
        "20",
        "Acciones priorizadas e impacto hipotético",
        ["Acción", "Problema", "Impacto/180 d", "Confianza", "Criticidad"],
        T20,
        [Inches(1.5), Inches(1.8), Inches(1.3), Inches(0.9), Inches(0.8)],
    )
    w.h("7.2 Mejoras de datos y BI", 2)
    for text in [
        "Definir si el FPY se mantiene literal o se adopta la lectura clásica de buenas de primera pasada.",
        "Añadir la línea acumulada al Pareto del tablero, no solo al informe.",
        "Incorporar un visual de temperatura y su relación con scrap/energía.",
        "Etiquetar el origen ERP de las órdenes y productos para cerrar la trazabilidad de fuentes.",
        "Emitir el estado `unknown` o documentar formalmente por qué se reemplaza por `incompleta`.",
        "Aumentar la cadencia IoT y medir el costo/beneficio de un muestreo cada 15 minutos.",
        "Materializar la vista de alertas si el tiempo de respuesta crece con el volumen.",
    ]:
        w.bullet(text)
    w.h("7.3 Gobernanza", 2)
    w.p(
        "Se recomienda una revisión mensual del OEE con Producción, Mantenimiento y Calidad; un dueño "
        "del dato por fuente; un playbook de alertas con responsable y plazo; y una validación anual de "
        "los supuestos de costo. Sin gobierno, el tablero se convierte en un reporte más y las decisiones "
        "vuelven a depender de interpretaciones locales.",
    )
    w.h("7.4 Investigación futura", 2)
    w.p(
        "La agenda incluye datos reales, un diseño cuasiexperimental para separar planta/producto, un "
        "estudio de tiempos que valide el Loss Tree y un piloto de mantenimiento predictivo con datos "
        "etiquetados. También sería útil comparar el OEE con indicadores de energía y de satisfacción del "
        "cliente para evitar una optimización local.",
    )
    w.h("7.5 Hoja de ruta", 2)
    w.p(
        "En los primeros 30 días: validar costos, definir FPY y limpiar el ERP. Entre 31 y 90 días: "
        "piloto en P-SUR con A1/A2, revisión semanal y ajuste de metas. Entre 91 y 180 días: extender a "
        "P-CENTRO y P-NORTE, ampliar la cadencia IoT y evaluar el mantenimiento predictivo. La hoja de "
        "ruta es una guía; cada etapa debe cerrarse con evidencia, no con una presentación.",
    )

    doc.save(DST)
    print(DST)


if __name__ == "__main__":
    main()
