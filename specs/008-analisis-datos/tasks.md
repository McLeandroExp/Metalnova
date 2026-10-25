# Tareas — Incremento 008

| ID | Tarea | Requisito | Estado |
|---|---|---|---|
| T-801 | Especificación del incremento | — | hecha |
| T-802 | Plan técnico | — | hecha |
| T-803 | Dependencias de análisis + rebuild del ingestor | FR-810 | hecha |
| T-804 | Consultas de extracción e inventario | FR-801 | hecha |
| T-805 | Auditoría de calidad de datos | FR-802 | hecha |
| T-806 | Descriptiva global y por planta | FR-803 | hecha |
| T-807 | Distribuciones y normalidad | FR-804 | hecha |
| T-808 | Atípicos univariantes y multivariantes | FR-805 | hecha |
| T-809 | Correlación Pearson/Spearman + FDR | FR-806 | hecha |
| T-810 | Comparaciones por grupo y asociaciones | FR-807, FR-809 | hecha |
| T-811 | Análisis temporal | FR-808 | hecha |
| T-812 | 18 figuras PNG | FR-810 | hecha |
| T-813 | Informe `docs/ANALISIS_DATOS.md` | FR-810 | hecha |
| T-814 | Manifiesto reproducible | FR-811 | hecha |
| T-815 | `validate_analysis.py` | FR-812 | hecha |
| T-816 | `sql/validation/08_analisis.sql` | FR-812 | hecha |
| T-817 | Documentación transversal | FR-813 | hecha |
| T-818 | `verification.md` con evidencia real | AC-807 | hecha |
| T-819 | Commit de cierre | — | pendiente |

Notas de ejecución:

- **T-803:** `docker compose build ingestor` instaló pandas 2.2.3, numpy 2.1.3, scipy 1.14.1 y
  matplotlib 3.9.2; la imagen resultante ejecuta el análisis sin Python local.
- **T-804…T-811:** corrida `eda-20261025T172443-9ba731` en 22,8 s y 660,9 MB de pico.
  Extracción: 9.360 máquina-día, 28.080 máquina-turno, 540 planta-día, 76.021 paradas
  consolidadas, 2.628 mantenimientos, 401.787 eventos históricos y 51 eventos `sim-*`.
- **T-812:** 18 figuras F01–F18 en `docs/analysis/figures/`; todas con nota de datos sintéticos.
- **T-813:** informe con resumen ejecutivo, 17 tablas y las 18 figuras.
- **T-814:** `manifest.json` con versiones, filtros, recuentos y SHA-256 de 42 archivos.
- **T-815:** `validate_analysis.py` → **54/54** comprobaciones OK.
- **T-816:** `08_analisis.sql` → **22/22** controles OK.
- **T-817:** `README.md`, `specs/README.md`, `docs/DATA_DICTIONARY.md`, `docs/DECISIONS.md`
  (D-024…D-027), `docs/TEST_PLAN.md` (P-042…P-046) y `docs/analysis/README.md`.
- **T-818:** `verification.md` con comandos, salidas y fecha.
- **T-819:** pendiente del commit de cierre.
