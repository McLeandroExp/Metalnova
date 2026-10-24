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
| P-013 | DirectQuery vs Import | 006 | mediciones | decisión documentada | apertura 35,46 s; filtro 0,5 s; frescura 0,35 s; D-019 | 2026-10-21 | superada |
| P-014 | Evento nuevo visible en informe | 007 | escenario reproducible | cambio visible | `--scenario stop M-001 --once`: M-001 turno B con 20 min de downtime y 1 falla | 2026-10-22 | superada |
| P-015 | Backup y restauración | 007 | `pg_dump` / `pg_restore` | recuentos coinciden | 401.832 / 28.080 / 76.042 / 28.080 idénticos en base temporal; base eliminada | 2026-10-22 | superada |
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
| P-028 | Calibración del histórico | 006 | `generate_history.py --escenario calibracion` + `load_history.py --reset` + `validate_data.py` + `03_calibracion.sql` | OEE ~78→66; dispersión 5–10 pp; 49/49 y 7/7 | OEE 78,02→66,00 %; plantas 81,98/78,00/73,44 → 69,32/66,07/62,04; 49/49 y 7/7 OK | 2026-10-21 | superada |
| P-029 | Reproducibilidad calibrada | 006 | regenerar misma semilla y escenario | seis CSV idénticos | SHA-256 idéntico en los seis CSV; mismo `run_id` | 2026-10-21 | superada |
| P-030 | Alerta crítica optimizada | 006 | `EXPLAIN ANALYZE` filtrado + `validate_data.py` | consulta < 1 s y regla correcta | 464/335/369 ms; 28.101 filas; 49/49 OK; 13 alertas último turno | 2026-10-21 | superada |
| P-031 | OEE último mes no vacío | 006 | DAX/ADOMD + tarjeta del informe | valor del último mes con hechos | 0,655105 por DAX (`MAX(v_loss_tree[anio_mes])=2026-10`); tarjeta visible tras reabrir el `.pbip` | 2026-10-22 | superada |
| P-032 | Calidad IoT: rango, tardío y reordenado | 006/G5 | `python src/validate_iot.py` | 11/11 y limpieza de datos de prueba | 11/11 OK; 2 rechazos con motivo y evento tardío con `tardio=true`/`reordenado=true` | 2026-10-22 | superada |
| P-033 | Escenario inválido reproducible | 006/G5 | `simulate_events.py --scenario invalid M-001 --once` | 2 rechazos, 2 aceptados y 0 errores | `rechazados=2 motivos=timestamp_anterior_al_rango,timestamp_futuro tardio=true reordenado=true` | 2026-10-22 | superada |
| P-034 | Cobertura de señal IoT | 006/G5 | `sql/validation/04_iot.sql` | 5/5 cheques OK | 5/5 OK; 9.360 filas máquina-día, 52/52 máquinas, 0 estados inválidos | 2026-10-22 | superada |
| P-035 | Modelo TMDL regenerado | 006 | `python tools/generate_tmdl.py` + `validate_model.py` | referencias y tipos coherentes | 15 tablas, 27 relaciones, 70 medidas; OK | 2026-10-22 | superada |
| P-036 | Referencias del informe PBIR | 006 | `python tools/validate_report.py` | todos los `queryRef` existen | 8 páginas, 105 visuales, 0 errores; solo avisos de solapamiento si los hay | 2026-10-22 | superada |
| P-037 | Arranque en frío | 007 | `docker compose down` + `up -d` | datos intactos y `db` healthy | 401.832 eventos, 28.080 producciones, 76.042 paradas; healthy | 2026-10-22 | superada |
| P-038 | Backup y restauración | 007 | `pg_dump -Fc` + `pg_restore` en base temporal | recuentos idénticos | 401.832 / 28.080 / 76.042 / 28.080; base temporal eliminada | 2026-10-22 | superada |
| P-039 | Latencia end-to-end | 007 | eventos `run_id LIKE 'sim-%'` | < 10 min | 0,7–55 ms; frescura DirectQuery 0,35 s | 2026-10-22 | superada |
| P-040 | Evento visible tras la ingesta | 007 | `--scenario stop M-001 --once` + vista | cambio observable | M-001 turno B: 20 min de downtime y 1 falla | 2026-10-22 | superada |
| P-041 | Tarjetas sin redondeo automático y tabla de alertas con medidas | 006 | `generate_pbir.py` + `validate_report.py` + ADOMD + revisión visual | conteos exactos, OEE visible, unidades explícitas | 70 medidas; tarjetas con `labelDisplayUnits=1D`; OEE de alertas corregido al redondear `oee` a 6 decimales; tabla sin fila de totales (`total.totals = false`); confirmación visual del usuario y captura de las 8 páginas | 2026-10-23 | superada |

### Evidencia del incremento 005

- `logs/validation_005.txt`: 49/49 comprobaciones OK; resumen global, aditividad, recuentos y
  casos borde.
- `logs/kpi_checks_005.txt`: 20 vistas, parámetros, OEE mensual, MTBF/MTTR, alertas, FPY y
  participación del Loss Tree.
- Detalle por criterio en `specs/005-kpi-y-vistas/verification.md`.

### Evidencia de calibración del 006

- `data/processed/manifest.json`: `run_id = hist-h3a58b2b659`, semilla 42, 180 días, escenario
  `calibracion`, factores por planta y perfiles.
- `data/processed/load_manifest.json`: 28.080 órdenes, 76.021 paradas, 2.628 mantenimientos,
  28.080 producciones, 28.080 inspecciones y 401.787 eventos.
- `validate_data.py`: 49/49; OEE global 71,96 % en 180 días y 78,02 → 66,00 % en ventanas de
  30 días.
- `verify_history.py`: 17/17; 43 eventos de la ingesta 004 sobre el histórico calibrado.
- `backups/metalinova_pre_calibracion_20261021.dump`: respaldo de la base anterior (no versionado).

### Evidencia de calidad IoT y páginas PBIR (006)

- `logs/iot_invalid_scenario.txt`: corrida `--scenario invalid M-001` con 2 rechazos, 2 eventos
  aceptados y marcas `tardio=true`/`reordenado=true`.
- `python src/validate_iot.py`: 11/11 comprobaciones, incluida la limpieza de los datos de prueba.
- `sql/validation/04_iot.sql`: 5/5 chequeos de cuarentena, rango, cobertura, estados y cadencia.
- `tools/generate_tmdl.py`: 15 tablas, 27 relaciones y 70 medidas.
- `tools/generate_pbir.py`: 7 páginas generadas (4 principales, 2 de drill-through y 1 tooltip)
  y 94 visuales; la página de validación de T-604 queda oculta.
- `tools/validate_report.py`: 8 páginas y 105 visuales; todas las referencias existen en el TMDL.

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
