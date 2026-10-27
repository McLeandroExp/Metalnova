# Informe MetalNova — carpeta de trabajo

> **Corte de cifras:** 2026-10-24. **Entrega:** 26/10/2026.
> **Documento vigente:** `MetalNova_Informe_Caso_Practico_v0.3_final.docx` (57 páginas, 10.242 palabras).
> **Documento auxiliar:** `MetalNova_Guion_Defensa_v0.1.docx` (2 páginas).

## 1. Contenido de esta carpeta

| Archivo | Para qué sirve |
|---|---|
| `MetalNova_Informe_Caso_Practico_v0.3_final.docx` | Informe completo: portada del usuario, preliminares, Introducción, secciones 2–7, referencias y anexos A–G, con capturas D1–D8. |
| `MetalNova_Guion_Defensa_v0.1.docx` | Guion de exposición y preguntas previsibles, separado del informe. |
| `MetalNova_Informe_Caso_Practico_v0.3.docx` | Copia de respaldo del mismo contenido; Word presenta un bloqueo con ese nombre exacto. |
| `MetalNova_Informe_Caso_Practico_v0.2.docx` | Versión anterior, con el esqueleto de 2–7. |
| `ESQUEMA_DETALLADO.md` | Estructura, figuras, tablas y correspondencia con la rúbrica. |
| `TABLA_MAESTRA_CIFRAS.md` / `.csv` | Cifras congeladas y trazabilidad. |
| `REFERENCIAS.md` | 32 referencias en APA 7. |
| `build_informe.py` | Genera una versión desde cero. **No lo ejecutes si quieres conservar la portada editada.** |
| `write_sections_2_7.py` | Redacta las secciones 2–7 sobre la v0.2. |
| `make_figuras_v1.py` | Genera las figuras F2–F10. |
| `edit_final_v0.3.py` | Agrega capturas D5–D8, quita notas de tablas y aplica el estilo de referencias. |

## 2. Qué contiene la versión final

- Portada del usuario, sin modificaciones.
- Tabla de contenidos y listas **numeradas** (sin “—”).
- Resumen y abstract.
- Introducción completa.
- **Sección 2:** Business Intelligence, OEE, TPM/confiabilidad, calidad/energía, modelado dimensional, analítica, IoT/calidad de datos, BABOK/CRISP-DM y síntesis.
- **Sección 3:** diseño, caso, fuentes, modelo dimensional, arquitectura y decisiones tecnológicas, reglas IoT, KPIs, tablero/alerta, validación y ética.
- **Sección 4:** volumen, OEE, Loss Tree, focos, causas, confiabilidad, calidad/energía, alertas, tablero, validación y priorización.
- **Sección 5:** discusión, contraste con el caso/literatura, limitaciones y validez.
- **Sección 6:** conclusiones.
- **Sección 7:** recomendaciones y hoja de ruta.
- **Referencias** APA 7 con estilo `Referencias APA` (sangría francesa, Times New Roman 12, títulos en cursiva).
- **Anexos A–G:** caso, diccionario, matriz de aceptación, capturas D1–D8, reproducción, glosario y tabla maestra.
- **Figuras F1–F10** y **tablas T1–T20**.

## 3. Correcciones aplicadas

- Títulos, TOC, cuerpo, listas y referencias en **Times New Roman 12**.
- Tablas y figuras en **Arial 8**.
- **Todas las tablas con todos los bordes**.
- **Sin notas de tablas**; solo se conservan las notas de figuras/capturas.
- La advertencia de datos sintéticos quedó **solo en la metodología** (3.2, 3.3, 3.6 y 3.10).
- Anexo H eliminado del informe y trasladado a `MetalNova_Guion_Defensa_v0.1.docx`.
- Capturas D5–D8 insertadas en el Anexo D.
- Listas de tablas, figuras y anexos con **páginas reales**.
- Referencias con estilo `Referencias APA` de Word.

## 4. Extensión y estructura

- **57 páginas**.
- **10.242 palabras**.
- 25 tablas: T1–T20 y B1–B5.
- 18 figuras: F1–F10 y D1–D8.
- Referencias: 32 entradas.

## 5. Pendientes menores

- Revisar la bibliografía contra la portada de los ejemplares de la asignatura (autor, año, edición y editorial).
- Si se quiere, convertir las referencias a fuentes del Administrador de fuentes de Word; el formato visual ya es APA 7.
- Confirmar si el Anexo D se quiere a página completa (aumentaría la extensión).

## 6. Advertencias de honestidad académica

- El escenario `calibracion` fue diseñado para producir señal; no es una fábrica real.
- Los ahorros son hipotéticos y dependen de USD 220/h, USD 18/unidad y USD 0,12/kWh.
- No se afirma causalidad entre scrap y producto, turno, energía o temperatura.
- El ERP no tiene una fuente etiquetada.
- La cadencia IoT es de dos lecturas por turno; el estado `unknown` no se emite.
- La definición de FPY es literal (“sin retrabajo”).

## 7. Estado técnico

- Documento generado con `python-docx` y cerrado con Microsoft Word.
- Tamaño carta, márgenes de 2,54 cm, Times New Roman 12, Arial 8 en tablas/figuras,
  interlineado doble, sangría de 1,27 cm.
- Numeración romana en preliminares y arábiga desde la Introducción.
- El DOCX no está protegido ni firmado.
