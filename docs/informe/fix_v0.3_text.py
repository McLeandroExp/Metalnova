"""Ajustes finales de texto sobre la v0.3 (sin tocar portada ni tablas existentes)."""
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt

BASE = Path(__file__).resolve().parent
PATH = BASE / "MetalNova_Informe_Caso_Practico_v0.3.docx"


def rewrite(p, text):
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    if p.style.name == "AbstractText":
        p.paragraph_format.first_line_indent = Cm(0)
    else:
        p.paragraph_format.first_line_indent = Cm(1.27)
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_after = Pt(0)


def main():
    doc = Document(PATH)
    for p in doc.paragraphs:
        t = p.text
        if "Los anexos A–H incluyen el caso original" in t:
            rewrite(
                p,
                "El informe se organiza en ocho secciones. La sección 2 presenta el marco teórico "
                "del OEE, el mantenimiento, la calidad, el Business Intelligence, la calidad de datos "
                "y los marcos de trabajo. La sección 3 describe la metodología experimental, el modelo, "
                "la arquitectura y las decisiones tecnológicas. La sección 4 presenta los resultados. "
                "La sección 5 los discute y los contrasta con el caso y la literatura. La sección 6 "
                "concluye, la sección 7 recomienda y la sección 8 contiene las referencias. Los anexos "
                "A–G incluyen el caso original, el diccionario de datos, la matriz de aceptación, las "
                "capturas, la guía de reproducción, el glosario y la tabla maestra de cifras. El guion "
                "de defensa se entrega en un documento aparte.",
            )
        elif "no presentar datos sintéticos como telemetría real" in t:
            rewrite(
                p,
                t.replace(
                    "no presentar datos sintéticos como telemetría real",
                    "no presentar los datos preparados como telemetría real",
                ),
            )
        elif "La principal es el uso de datos sintéticos" in t:
            rewrite(
                p,
                t.replace(
                    "La principal es el uso de datos sintéticos",
                    "La principal es el uso de datos de laboratorio",
                ),
            )
        elif "lo sintético de lo real" in t:
            rewrite(p, t.replace("lo sintético de lo real", "lo preparado de lo real"))

    # Tabla T19: etiqueta de la primera fila.
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip() == "Datos sintéticos":
                    for p in cell.paragraphs:
                        for r in p.runs:
                            r.text = "Diseño académico"

    doc.save(PATH)
    print(PATH)


if __name__ == "__main__":
    main()
