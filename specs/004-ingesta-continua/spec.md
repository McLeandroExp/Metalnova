# Incremento 004 — Ingesta continua simulada

Estado: hecho (2026-10-21) · Depende de: 003 · Habilita: 006

## Contexto

Simula la llegada de eventos nuevos (máquina, parada, calidad, mantenimiento) con latencia
cercana al tiempo real. Es la pieza que permite demostrar el objetivo de < 10 minutos.

## Requisitos funcionales

| ID | Requisito |
|---|---|
| FR-401 | Intervalo configurable (por defecto 60 s). |
| FR-402 | Emite eventos por transición para las 3 plantas y 52 máquinas. |
| FR-403 | Inserciones idempotentes (`ON CONFLICT` sobre clave estable): reiniciar no duplica. |
| FR-404 | Registra `generated_at`, `event_time` e `ingested_at` (y `processed_at` si aplica). |
| FR-405 | Logs legibles con hora, nº de eventos, duración y errores; sin contraseñas. |
| FR-406 | Reintentos limitados ante error de base, sin duplicar registros. |
| FR-407 | Salida limpia con Ctrl+C. |
| FR-408 | Escenario reproducible que provoca un cambio visible en KPI/gráficos. |
| FR-409 | Identificador de ejecución (`run_id`) para análisis de fallos. |
| FR-410 | Uso de transacciones y operaciones por lotes. |

## Criterios de aceptación

| ID | Criterio |
|---|---|
| AC-401 | Tras ejecutar el simulador, aparecen filas nuevas en PostgreSQL. |
| AC-402 | Reiniciar el proceso no genera duplicados (recuento estable). |
| AC-403 | La latencia `ingested_at − generated_at` se mide y se registra por ejecución. |
| AC-404 | Ctrl+C termina el proceso de forma controlada. |
| AC-405 | Los errores quedan registrados de forma comprensible. |
| AC-406 | El escenario reproducible altera un KPI observable (p. ej. parada de una máquina concreta). |

## Fuera de alcance

Construcción del informe Power BI (006). La verificación end-to-end evento→informe pertenece a 007.

## Dependencias

003 (datos históricos cargados).
