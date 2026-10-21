# Plan de pruebas — MetalNova Smart Factory BI

Resultados reproducibles. Una prueba solo se marca como superada con evidencia observada.

## Registro

| ID | Prueba | Incremento | Comando | Resultado esperado | Resultado observado | Fecha | Veredicto |
|---|---|---|---|---|---|---|---|
| P-001 | Compose válido | 001 | `docker compose config` | sin errores | configuración renderizada | 2026-10-18 | superada |
| P-002 | Base saludable | 001 | `docker compose ps` | `db healthy` | `Up (healthy)` | 2026-10-18 | superada |
| P-003 | Conectividad Python | 001 | `check_connection.py` | `SELECT 1 -> 1` | `SELECT 1 -> 1` + `Conexión OK` | 2026-10-18 | superada |
| P-004 | Persistencia tras reinicio | 001 | `down` → `up -d` | datos intactos | `filas=1` | 2026-10-18 | superada |
| P-005 | Esquema idempotente | 002 | re-ejecutar DDL | sin duplicados | solo NOTICE; recuentos idénticos | 2026-10-19 | superada |
| P-006 | Integridad referencial | 002 | `sql/validation/01_integridad.sql` | 0 huérfanos | 21 chequeos con 0 incidencias | 2026-10-19 | superada |
| P-007 | Recuento mínimo de eventos | 003 | `verify_history.py` | ≥ 200 000 | `fact_evento = 405.995` | 2026-10-19 | superada |
| P-008 | Cobertura 180 días | 003 | min/max fecha | 180 días | `2026-04-22 → 2026-10-18`; 180 días distintos | 2026-10-19 | superada |
| P-009 | Reproducibilidad | 003 | regenerar misma semilla | recuentos idénticos | mismo `run_id`; 6 CSV con SHA-256 idéntico | 2026-10-19 | superada |
| P-010 | No duplicación al reiniciar | 004 | reiniciar simulador | recuento estable | mismo ciclo: 0 insertados; mismo escenario: 0 insertados y 2 duplicados por `ON CONFLICT`; recuentos estables | 2026-10-21 | superada |
| P-011 | Latencia | 004/007 | log de métricas | evidencia presente | 0,004411–0,035976 s por ejecución; registrada por `run_id` | 2026-10-21 | superada |
| P-012 | Validación de KPI | 005 | `validate_data.py` | diferencias < tolerancia | 49/49 comprobaciones OK; diferencia máxima 4,37e-11 (< 1e-9) | 2026-10-20 | superada |
| P-013 | DirectQuery vs Import | 006 | mediciones | decisión documentada | — | — | pendiente |
| P-014 | Evento nuevo visible en informe | 007 | escenario reproducible | cambio visible | — | — | pendiente |
| P-015 | Backup y restauración | 007 | `pg_dump` / `pg_restore` | recuentos coinciden | — | — | pendiente |
| P-016 | pgAdmin operativo | 001 | `curl http://127.0.0.1:5050/login` + login | HTTP 200 y login OK | `/login` 200 · POST 302 · `/browser/` 200 | 2026-10-19 | superada |
| P-017 | Carga idempotente del histórico | 003 | re-ejecutar `load_history.py` | 0 insertadas y recuentos estables | 0 insertadas en las 6 tablas; recuentos idénticos | 2026-10-19 | superada |
| P-018 | Integridad del histórico | 003 | `sql/validation/02_historico.sql` | todos los chequeos OK | 24 chequeos con `estado = OK` | 2026-10-19 | superada |
| P-019 | Casos borde de KPI | 005 | `validate_data.py` (bloque de borde) | NULL intencional, sin NaN | división por cero → NULL; parada sin producción → MTBF NULL y downtime 20 min; alerta `sin_alerta` | 2026-10-20 | superada |
| P-020 | Vistas KPI idempotentes | 005 | re-ejecutar `/sql/apply_all.sql` | sin errores ni duplicados | 20 vistas recreadas; `EXIT=0` | 2026-10-20 | superada |
| P-021 | Eventos nuevos visibles | 004 | `simulate_events.py --once` + recuento | recuento aumenta | `fact_evento` 405.995 → 405.997; `fact_parada` 76.827 → 76.828 | 2026-10-21 | superada |
| P-022 | Cobertura de plantas y máquinas | 004 | 600 ciclos `--dry-run` | 52 máquinas / 3 plantas | `cobertura_maquinas=52/52`, `cobertura_plantas=3`; 729 eventos y 363 paradas generadas | 2026-10-21 | superada |
| P-023 | Salida limpia con SIGINT | 004 | `docker kill -s INT` | código 0 y cierre ordenado | `motivo=interrumpido`, `EXIT_CODE=0`, métricas escritas | 2026-10-21 | superada |
| P-024 | Error de base comprensible | 004 | `POSTGRES_PORT=5999` | error registrado y sin secretos | 2 reintentos + `ERROR … (OperationalError)`, `EXIT_CODE=2`, JSON `error_conexion` | 2026-10-21 | superada |
| P-025 | Escenario altera un KPI | 004 | `--scenario stop M-001` + vista | downtime y fallas cambian | M-001: sin fila → 20 min y 1 falla; P-NORTE: 5 → 25 min y 0 → 1 falla | 2026-10-21 | superada |
| P-026 | Histórico no bloqueado por ingesta | 004 | `load_history.py` tras eventos `sim-*` | 0 insertadas | 0 insertadas en las 6 tablas; `verify_history.py` 17/17 OK | 2026-10-21 | superada |
| P-027 | KPI validan tras la ingesta | 004 | `validate_data.py` | 49/49 OK | 49/49 comprobaciones OK | 2026-10-21 | superada |

### Evidencia del incremento 005

- `logs/validation_005.txt`: 49/49 comprobaciones OK; resumen global, aditividad, recuentos y
  casos borde.
- `logs/kpi_checks_005.txt`: 20 vistas, parámetros, OEE mensual, MTBF/MTTR, alertas, FPY y
  participación del Loss Tree.
- Detalle por criterio en `specs/005-kpi-y-vistas/verification.md`.

### Evidencia del incremento 004

- `logs/ingest_004_ac401.txt` · `_ac402.txt` · `_ac402_scenario.txt`: eventos nuevos y
  no-duplicación (incluido el camino `ON CONFLICT`).
- `logs/ingest_004_ac404.txt`: SIGINT real, cierre ordenado y `EXIT_CODE=0`.
- `logs/ingest_004_ac405.txt` + `_ac405_metrics.json`: reintentos limitados, error comprensible y
  `EXIT_CODE=2`.
- `logs/ingest_004_ac406.txt` + `_evidence.txt`: escenario `stop M-001`, parada en `fact_parada` y
  cambio en las vistas KPI.
- `logs/ingest_004_cobertura.txt`: 52/52 máquinas y 3/3 plantas.
- `logs/ingest_004_verify_history.txt`, `_validate_data.txt`, `_load_history_idem.txt`:
  regresiones del histórico y de los KPI.
- Detalle por criterio en `specs/004-ingesta-continua/verification.md`.

## Plantilla de resultado

```text
Prueba:        P-0XX
Fecha/hora:    AAAA-MM-DD HH:MM
Versión:       <commit o estado>
Configuración: <parámetros>
Comando:       <comando exacto>
Salida:        <salida observada>
Esperado:      <resultado esperado>
Veredicto:     superada | fallida | bloqueada
Notas:         <observaciones>
```
