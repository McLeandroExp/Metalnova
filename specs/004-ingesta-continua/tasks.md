# Tareas — Incremento 004

Todas las tareas cerradas el 2026-10-21. La evidencia de cada criterio está en
`verification.md` y en `logs/ingest_004_*.txt`.

| ID | Tarea | Requisito | Estado |
|---|---|---|---|
| T-401 | `ingest.py` con inserción idempotente y métricas | FR-403,404,410 | hecha |
| T-402 | `simulate_events.py` bucle configurable | FR-401,402 | hecha |
| T-403 | Timestamps `generated_at`/`event_time`/`ingested_at` y `run_id` | FR-404,409 | hecha |
| T-404 | Logs estructurados sin secretos | FR-405 | hecha |
| T-405 | Reintentos limitados con backoff | FR-406 | hecha |
| T-406 | Salida limpia con Ctrl+C | FR-407 | hecha |
| T-407 | Escenario reproducible `--scenario stop M-001` | FR-408, AC-406 | hecha |
| T-408 | Prueba de aparición de eventos nuevos | AC-401 | hecha |
| T-409 | Prueba de no-duplicación al reiniciar | AC-402 | hecha |
| T-410 | Medición de latencia por ejecución | AC-403 | hecha |
| T-411 | Documentar comandos de inicio/parada | — | hecha |
| T-412 | Commit `feat: ingesta continua simulada` | — | hecha |
