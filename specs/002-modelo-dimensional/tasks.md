# Tareas — Incremento 002

| ID | Tarea | Requisito | Estado |
|---|---|---|---|
| T-201 | `sql/schema/01_dimensiones.sql` (10 dimensiones) | FR-201 | hecha |
| T-202 | `sql/schema/02_hechos.sql` (4 hechos + evento + cuarentena) | FR-202,203,204 | hecha |
| T-203 | Constraints inline (PK, FK, UNIQUE, CHECK) | FR-205 | hecha |
| T-204 | `sql/schema/03_comentarios.sql` con el grano documentado | FR-206 | hecha |
| T-205 | Garantizar idempotencia de los scripts | FR-207, AC-202 | hecha |
| T-206 | `sql/indexes/01_indices.sql` | FR-208 | hecha |
| T-207 | `es_retrabajo` y `unidades_retrabajo` en `fact_calidad` | FR-209 | hecha |
| T-208 | `temperatura_c` y `energia_kwh` en `fact_evento` | FR-210 | hecha |
| T-209 | `sql/views/01_vistas_base.sql` (4 vistas) | FR-211 | hecha |
| T-210 | `sql/validation/01_integridad.sql` | AC-203, AC-206 | hecha |
| T-211 | Crear esquema en base limpia | AC-201 | hecha |
| T-212 | Ejecutar scripts dos veces y comparar objetos/filas | AC-202 | hecha |
| T-213 | Escribir `docs/DATA_DICTIONARY.md` completo | FR-206, AC-205 | hecha |
| T-214 | Commit `feat: modelo dimensional` | — | hecha |
| T-215 | `sql/schema/04_catalogo_referencia.sql` (catálogo sintético) | FR-201 | hecha |
| T-216 | `sql/apply_all.sql` + montaje de `sql/` en el contenedor `db` | FR-207 | hecha |
