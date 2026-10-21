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
| P-010 | No duplicación al reiniciar | 004 | reiniciar simulador | recuento estable | — | — | pendiente |
| P-011 | Latencia | 004/007 | log de métricas | evidencia presente | — | — | pendiente |
| P-012 | Validación de KPI | 005 | `validate_data.py` | diferencias < tolerancia | 49/49 comprobaciones OK; diferencia máxima 4,37e-11 (< 1e-9) | 2026-10-20 | superada |
| P-013 | DirectQuery vs Import | 006 | mediciones | decisión documentada | — | — | pendiente |
| P-014 | Evento nuevo visible en informe | 007 | escenario reproducible | cambio visible | — | — | pendiente |
| P-015 | Backup y restauración | 007 | `pg_dump` / `pg_restore` | recuentos coinciden | — | — | pendiente |
| P-016 | pgAdmin operativo | 001 | `curl http://127.0.0.1:5050/login` + login | HTTP 200 y login OK | `/login` 200 · POST 302 · `/browser/` 200 | 2026-10-19 | superada |
| P-017 | Carga idempotente del histórico | 003 | re-ejecutar `load_history.py` | 0 insertadas y recuentos estables | 0 insertadas en las 6 tablas; recuentos idénticos | 2026-10-19 | superada |
| P-018 | Integridad del histórico | 003 | `sql/validation/02_historico.sql` | todos los chequeos OK | 24 chequeos con `estado = OK` | 2026-10-19 | superada |
| P-019 | Casos borde de KPI | 005 | `validate_data.py` (bloque de borde) | NULL intencional, sin NaN | división por cero → NULL; parada sin producción → MTBF NULL y downtime 20 min; alerta `sin_alerta` | 2026-10-20 | superada |
| P-020 | Vistas KPI idempotentes | 005 | re-ejecutar `/sql/apply_all.sql` | sin errores ni duplicados | 20 vistas recreadas; `EXIT=0` | 2026-10-20 | superada |

### Evidencia del incremento 005

- `logs/validation_005.txt`: 49/49 comprobaciones OK; resumen global, aditividad, recuentos y
  casos borde.
- `logs/kpi_checks_005.txt`: 20 vistas, parámetros, OEE mensual, MTBF/MTTR, alertas, FPY y
  participación del Loss Tree.
- Detalle por criterio en `specs/005-kpi-y-vistas/verification.md`.

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
