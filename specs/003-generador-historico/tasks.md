# Tareas — Incremento 003

| ID | Tarea | Requisito | Estado |
|---|---|---|---|
| T-301 | Validar y ampliar el catálogo de referencia sembrado en 002 | FR-303 | hecha |
| T-302 | Motor de simulación por transición de estado | FR-304 | hecha |
| T-303 | `generate_history.py` con parámetros y semilla | FR-301,302 | hecha |
| T-304 | Escenarios base y degradado | FR-309 | hecha |
| T-305 | Generar microparadas, fallas, mantenimientos, calidad, energía, temperatura | FR-310 | hecha |
| T-306 | Exportar CSV/Parquet + manifiesto | FR-306,307 | hecha |
| T-307 | Verificar recuento ≥ 200 000 y cobertura 180 días | FR-305, AC-301,302 | hecha |
| T-308 | `load_history.py` con carga por lotes idempotente | FR-308 | hecha |
| T-309 | Pruebas de integridad post-carga | AC-303,304,307 | hecha |
| T-310 | Prueba de reproducibilidad (misma semilla) | AC-305 | hecha |
| T-311 | Documentar duraciones y tamaños | AC-306 | hecha |
| T-312 | Commit `feat: generador histórico 180 días` | — | hecha |
| T-313 | `verify_history.py` y `sql/validation/02_historico.sql` | AC-301…307 | hecha |
| T-314 | Documentar comandos, parámetros y métricas en `README.md` | AC-306 | hecha |

Evidencia completa en `verification.md`. Todas las pruebas se ejecutaron y observaron antes de
marcar las tareas como `hecha`.
